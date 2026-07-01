"""
RAG orchestration service.

Two primary operations:
1. build_index: Chunk all repository data, generate embeddings, store in DB
2. answer_question: Embed query, search chunks, generate answer with Gemini

Two modes:
- Gemini (full): embeddings + semantic search + AI answer
- Mock (fallback): keyword search + template answer (no API key needed)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.services import chunking_service, embedding_service
from app.services.documentation_service import (
    IGNORED_PATH_PARTS,
    is_ignored_path,
    get_int_env,
)
from app.services.documentation_providers.gemini_provider import (
    generate_gemini_documentation,
)
from app.services.github_service import (
    fetch_repository_file_text,
    fetch_repository_info,
    fetch_repository_tree,
)


def _get_rag_int_env(name: str, default: int) -> int:
    """Get RAG-specific integer env var with fallback."""
    return get_int_env(name, default)


async def build_index(
    db: Session,
    repository: models.Repository,
) -> dict[str, Any]:
    """
    Build or rebuild the knowledge index for a repository.

    Works in both Gemini and Mock modes.
    In Mock mode (no API key), chunks are stored without embeddings.
    """
    crud.delete_knowledge_chunks_by_repository(db=db, repository_id=repository.id)

    all_chunks: list[dict[str, Any]] = []

    # 1. Repository metadata chunk
    metadata_chunk = chunking_service.chunk_repository_metadata(
        name=repository.name,
        repo_url=repository.repo_url,
        description=repository.description,
        github_full_name=repository.github_full_name,
        github_language=repository.github_language,
        github_default_branch=repository.github_default_branch,
    )
    all_chunks.append(metadata_chunk)

    # 2. Documentation chunks
    if repository.generated_documentation:
        doc_chunks = chunking_service.chunk_documentation(
            repository.generated_documentation,
        )
        all_chunks.extend(doc_chunks)

    # 3. Code chunks from GitHub
    try:
        code_chunks = await _fetch_and_chunk_code(repository)
        all_chunks.extend(code_chunks)
    except HTTPException:
        pass
    except Exception:
        pass

    # 4. Generate embeddings if API key is available
    api_key = embedding_service.get_api_key()
    has_embeddings = bool(api_key)

    if has_embeddings:
        texts = [chunk["content"] for chunk in all_chunks]
        try:
            embeddings = await embedding_service.generate_embeddings_batch(
                texts=texts,
                api_key=api_key,
            )

            for i, chunk in enumerate(all_chunks):
                if i < len(embeddings) and embeddings[i]:
                    chunk["embedding"] = embedding_service.embedding_to_blob(
                        embeddings[i]
                    )
                else:
                    chunk["embedding"] = None
        except Exception:
            has_embeddings = False
            for chunk in all_chunks:
                chunk["embedding"] = None

    # 5. Count types before save
    doc_count = sum(1 for c in all_chunks if c["chunk_type"] == "documentation")
    code_count = sum(1 for c in all_chunks if c["chunk_type"] == "code")
    meta_count = sum(1 for c in all_chunks if c["chunk_type"] == "repository_metadata")

    # 6. Save to DB
    crud.save_knowledge_chunks(db=db, repository_id=repository.id, chunks=all_chunks)

    return {
        "total_chunks": len(all_chunks),
        "documentation_chunks": doc_count,
        "code_chunks": code_count,
        "metadata_chunks": meta_count,
        "provider": "gemini" if has_embeddings else "mock",
    }


async def _fetch_and_chunk_code(
    repository: models.Repository,
) -> list[dict[str, Any]]:
    """Fetch code files from GitHub and chunk them."""
    branch = repository.github_default_branch or "main"
    max_tree = _get_rag_int_env("DOCUMENTATION_MAX_GITHUB_TREE_ITEMS", 120)
    max_files = _get_rag_int_env("RAG_MAX_GITHUB_FILES", 50)
    max_chars = _get_rag_int_env("RAG_MAX_GITHUB_FILE_CHARS", 8000)

    tree = await fetch_repository_tree(
        repo_url=repository.repo_url,
        branch=branch,
        max_items=max_tree,
    )

    paths = _select_code_paths(tree, max_files)
    chunks: list[dict[str, Any]] = []

    for path in paths:
        try:
            content = await fetch_repository_file_text(
                repo_url=repository.repo_url,
                branch=branch,
                path=path,
                max_chars=max_chars,
            )

            if content:
                file_chunks = chunking_service.chunk_code_file(
                    file_path=path,
                    content=content,
                    max_chars=2000,
                )
                chunks.extend(file_chunks)
        except Exception:
            continue

    return chunks


def _select_code_paths(tree: list[dict], max_files: int) -> list[str]:
    """Select the most important file paths from the tree for indexing."""
    important_extensions = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb",
        ".rs", ".c", ".cpp", ".cs", ".swift", ".kt", ".php", ".sh",
        ".yaml", ".yml", ".json", ".toml", ".md", ".sql", ".css",
        ".scss", ".html", ".vue", ".svelte", ".tf", ".hcl",
    }
    important_names = {
        "readme.md", "readme.txt", "dockerfile", "makefile",
        "requirements.txt", "package.json", "pyproject.toml",
        "go.mod", "go.sum", "cargo.toml", "pom.xml", "build.gradle",
    }

    selected: list[str] = []

    for item in tree:
        path = item.get("path") or ""
        filename = path.rsplit("/", 1)[-1].lower() if "/" in path else path.lower()

        if item.get("type") != "blob" or is_ignored_path(path):
            continue

        if filename in important_names and path not in selected:
            selected.append(path)

        if len(selected) >= max_files:
            return selected

    for item in tree:
        path = item.get("path") or ""
        ext = os.path.splitext(path)[1].lower()

        if item.get("type") != "blob" or is_ignored_path(path):
            continue

        if path in selected:
            continue

        if ext in important_extensions:
            selected.append(path)

        if len(selected) >= max_files:
            break

    return selected


async def search_chunks(
    db: Session,
    repository_id: int,
    query_text: str,
    query_embedding: list[float] | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """
    Search knowledge chunks for relevant context.

    Two modes:
    - With query_embedding: cosine similarity (semantic search)
    - Without query_embedding: keyword search (LIKE on content)
    """
    if query_embedding:
        chunks = crud.get_knowledge_chunks_by_repository(
            db=db,
            repository_id=repository_id,
        )
        scored: list[dict[str, Any]] = []

        for chunk in chunks:
            if not chunk.embedding:
                continue

            chunk_embedding = embedding_service.blob_to_embedding(chunk.embedding)
            score = embedding_service.cosine_similarity(query_embedding, chunk_embedding)

            if score > 0.1:
                scored.append({
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "source_path": chunk.source_path,
                    "chunk_type": chunk.chunk_type,
                    "relevance_score": round(score, 4),
                })

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:top_k]

    return crud.search_knowledge_chunks_keyword(
        db=db,
        repository_id=repository_id,
        query=query_text,
        top_k=top_k,
    )


async def answer_question(
    db: Session,
    repository: models.Repository,
    conversation: models.ChatConversation,
    question: str,
    top_k: int = 8,
    max_history: int = 10,
) -> dict[str, Any]:
    """
    Answer a question using RAG.

    Uses Gemini for generation when API key is available.
    Embedding is best-effort: if it fails, falls back to keyword search
    but still uses Gemini for answer generation.
    Falls to full mock (template) only if Gemini generation itself fails.
    """
    # Save user message
    crud.create_message(
        db=db,
        conversation_id=conversation.id,
        role="user",
        content=question,
    )

    # Check if Gemini is available
    api_key = embedding_service.get_api_key()
    use_gemini = bool(api_key)

    if use_gemini:
        # Try embedding (best-effort), fall back to keyword search silently
        try:
            query_embedding = await embedding_service.generate_embedding(
                text=question,
                api_key=api_key,
            )
        except HTTPException:
            query_embedding = None

        results = await search_chunks(
            db=db,
            repository_id=repository.id,
            query_text=question,
            query_embedding=query_embedding,
            top_k=top_k,
        )

        # Build prompt with context
        history = crud.get_recent_messages_by_conversation(
            db=db,
            conversation_id=conversation.id,
            limit=max_history,
        )

        prompt = _build_prompt(question, results, history)

        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        max_tokens = _get_rag_int_env("DOCUMENTATION_MAX_OUTPUT_TOKENS", 1200)

        try:
            answer_text = await generate_gemini_documentation(
                prompt=prompt,
                api_key=api_key,
                model=gemini_model,
                max_output_tokens=max_tokens,
            )
        except HTTPException:
            # Gemini generation failed — fall back to mock entirely
            return await _answer_with_mock(
                db=db,
                conversation=conversation,
                question=question,
                top_k=top_k,
            )

        sources = _build_source_references(results)

        # Save assistant message
        crud.create_message(
            db=db,
            conversation_id=conversation.id,
            role="assistant",
            content=answer_text,
            sources_json=json.dumps(sources, ensure_ascii=False) if sources else None,
        )

        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "answer": answer_text,
            "sources": sources,
            "provider": "gemini",
        }

    return await _answer_with_mock(
        db=db,
        conversation=conversation,
        question=question,
        top_k=top_k,
    )


async def _answer_with_mock(
    db: Session,
    conversation: models.ChatConversation,
    question: str,
    top_k: int,
) -> dict[str, Any]:
    """Mock answer using keyword search + template."""
    # 1. Get the repo_id from conversation
    repo_id = conversation.repository_id

    # 2. Keyword search
    results = crud.search_knowledge_chunks_keyword(
        db=db,
        repository_id=repo_id,
        query=question,
        top_k=top_k,
    )

    if not results:
        answer_text = (
            "Это mock-ответ. По вашему вопросу не найдено релевантных разделов "
            "в документации и коде репозитория. Попробуйте переформулировать вопрос "
            "или используйте другие ключевые слова.\n\n"
            "*Для полноценных AI-ответов настройте GEMINI_API_KEY в .env*"
        )
        sources: list[dict[str, Any]] = []
    else:
        parts = [
            "**Mock-ответ на основе найденных разделов:**\n",
        ]
        sources = []
        rank = 1

        for r in results:
            source_label = r["source_path"] or r["chunk_type"]
            parts.append(f"**{rank}. {source_label}**")
            parts.append(r["content"][:500])
            parts.append("")
            rank += 1

            sources.append({
                "chunk_id": r["chunk_id"],
                "source_path": r["source_path"],
                "chunk_type": r["chunk_type"],
                "relevance_score": round(r["relevance_score"] / max(r["relevance_score"], 1), 4),
            })

        parts.append(
            "\n---\n"
            "*Это mock-ответ на основе поиска по ключевым словам. "
            "Для AI-генерации с семантическим поиском настройте GEMINI_API_KEY в .env*"
        )
        answer_text = "\n".join(parts)

    crud.create_message(
        db=db,
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        sources_json=json.dumps(sources, ensure_ascii=False) if sources else None,
    )

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "answer": answer_text,
        "sources": sources,
        "provider": "mock",
    }


def _build_prompt(
    question: str,
    chunks: list[dict[str, Any]],
    history: list[models.ChatMessage],
) -> str:
    """Build the RAG prompt with context, history, and question."""
    parts = [
        "You are a helpful assistant answering questions about a GitHub repository. "
        "Answer in the same language as the question. "
        "Use the context below to answer accurately. "
        "For each claim, reference the source file path in brackets like [README.md] or [src/main.py]. "
        "If the context does not contain enough information, say so honestly.",
        "",
        "## Context from the repository:",
    ]

    for i, chunk in enumerate(chunks, 1):
        source_label = chunk.get("source_path") or chunk.get("chunk_type", "unknown")
        parts.append(f"### Source {i}: {source_label}")
        parts.append(chunk.get("content", ""))
        parts.append("")

    if history:
        parts.append("## Conversation history:")

        for msg in history[-5:]:
            role_label = "User" if msg.role == "user" else "Assistant"
            parts.append(f"{role_label}: {msg.content}")
            parts.append("")

    parts.append(f"## User question:\n{question}")
    parts.append("")
    parts.append("## Answer:")

    return "\n".join(parts)


def _build_source_references(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build structured source references from search results."""
    return [
        {
            "chunk_id": r["chunk_id"],
            "source_path": r["source_path"],
            "chunk_type": r["chunk_type"],
            "relevance_score": round(r["relevance_score"], 4),
        }
        for r in results
        if r.get("relevance_score", 0) >= 0.1
    ]