import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, hash_refresh_token, verify_password


def serialize_json_field(value: Any) -> str | None:
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False)


def deserialize_json_field(value: str | None) -> Any:
    if not value:
        return None

    return json.loads(value)


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return (
        db.query(models.User)
        .filter(models.User.email == email.strip().lower())
        .first()
    )


def get_user_by_username(db: Session, username: str):
    return (
        db.query(models.User)
        .filter(models.User.username == username.strip())
        .first()
    )


def create_user(db: Session, user: schemas.UserRegister):
    db_user = models.User(
        email=user.email.strip().lower(),
        username=user.username.strip(),
        hashed_password=get_password_hash(user.password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db=db, email=email)

    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_refresh_token(
    db: Session,
    user_id: int,
    refresh_token: str,
    expires_at: datetime,
):
    db_token = models.RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=expires_at,
    )

    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return db_token


def get_active_refresh_token(db: Session, refresh_token: str):
    token_hash = hash_refresh_token(refresh_token)

    return (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.is_revoked.is_(False),
            models.RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )


def revoke_refresh_token(db: Session, refresh_token: str):
    db_token = get_active_refresh_token(db=db, refresh_token=refresh_token)

    if db_token is None:
        return None

    db_token.is_revoked = True
    db_token.revoked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_token)

    return db_token


def create_repository(
    db: Session,
    repository: schemas.RepositoryCreate,
    owner_id: int,
    github_info: dict | None = None,
):
    github_info = github_info or {}

    repository_name = (
        repository.name
        or (github_info.get("full_name") or "").split("/")[-1]
        or repository.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    )

    db_repository = models.Repository(
        owner_id=owner_id,
        name=repository_name,
        repo_url=repository.repo_url,
        description=repository.description or github_info.get("description"),
        status=repository.status,
        github_full_name=github_info.get("full_name"),
        github_default_branch=github_info.get("default_branch"),
        github_language=github_info.get("language"),
        github_updated_at=github_info.get("updated_at"),
    )

    db.add(db_repository)
    db.commit()
    db.refresh(db_repository)

    return db_repository


def get_repositories(
    db: Session,
    owner_id: int,
    search: str | None = None,
    status: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(models.Repository).filter(models.Repository.owner_id == owner_id)

    if search:
        search_pattern = f"%{search}%"

        query = query.filter(
            or_(
                models.Repository.name.ilike(search_pattern),
                models.Repository.repo_url.ilike(search_pattern),
                models.Repository.description.ilike(search_pattern),
                models.Repository.github_full_name.ilike(search_pattern),
            )
        )

    if status:
        query = query.filter(models.Repository.status == status)

    sort_fields = {
        "id": models.Repository.id,
        "name": models.Repository.name,
        "status": models.Repository.status,
        "created_at": models.Repository.created_at,
        "updated_at": models.Repository.updated_at,
        "documentation_updated_at": models.Repository.documentation_updated_at,
    }

    sort_column = sort_fields.get(sort_by, models.Repository.id)

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_repository_by_id(db: Session, repository_id: int, owner_id: int):
    return (
        db.query(models.Repository)
        .filter(
            models.Repository.id == repository_id,
            models.Repository.owner_id == owner_id,
        )
        .first()
    )


def update_repository(
    db: Session,
    repository_id: int,
    owner_id: int,
    repository_data: schemas.RepositoryUpdate,
):
    db_repository = get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=owner_id,
    )

    if db_repository is None:
        return None

    update_data = repository_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_repository, field, value)

    db.commit()
    db.refresh(db_repository)

    return db_repository


def delete_repository(db: Session, repository_id: int, owner_id: int):
    db_repository = get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=owner_id,
    )

    if db_repository is None:
        return None

    db.delete(db_repository)
    db.commit()

    return db_repository


def update_repository_github_metadata(
    db: Session,
    repository: models.Repository,
    github_info: dict,
):
    repository.github_full_name = github_info.get("full_name")
    repository.github_default_branch = github_info.get("default_branch")
    repository.github_language = github_info.get("language")
    repository.github_updated_at = github_info.get("updated_at")

    if not repository.description and github_info.get("description"):
        repository.description = github_info.get("description")

    db.commit()
    db.refresh(repository)

    return repository


def update_repository_status(
    db: Session,
    repository: models.Repository,
    status: str,
):
    repository.status = status

    db.commit()
    db.refresh(repository)

    return repository


def get_next_documentation_revision_number(
    db: Session,
    repository_id: int,
    app_version: str,
) -> int:
    latest_revision_number = (
        db.query(func.max(models.DocumentationVersion.revision_number))
        .filter(
            models.DocumentationVersion.repository_id == repository_id,
            models.DocumentationVersion.app_version == app_version,
        )
        .scalar()
    )

    return (latest_revision_number or 0) + 1


def create_documentation_version(
    db: Session,
    repository: models.Repository,
    app_version: str,
    documentation: str,
    business_summary: dict[str, Any] | None = None,
    quality_assessment: dict[str, Any] | None = None,
    critical_parts: dict[str, Any] | None = None,
    provider: str | None = None,
    source_updated_at: str | None = None,
):
    normalized_app_version = app_version.strip()
    revision_number = get_next_documentation_revision_number(
        db=db,
        repository_id=repository.id,
        app_version=normalized_app_version,
    )

    db.query(models.DocumentationVersion).filter(
        models.DocumentationVersion.repository_id == repository.id,
        models.DocumentationVersion.is_latest_for_repository.is_(True),
    ).update(
        {models.DocumentationVersion.is_latest_for_repository: False},
        synchronize_session=False,
    )

    db.query(models.DocumentationVersion).filter(
        models.DocumentationVersion.repository_id == repository.id,
        models.DocumentationVersion.app_version == normalized_app_version,
        models.DocumentationVersion.is_latest_for_app_version.is_(True),
    ).update(
        {models.DocumentationVersion.is_latest_for_app_version: False},
        synchronize_session=False,
    )

    db_version = models.DocumentationVersion(
        repository_id=repository.id,
        app_version=normalized_app_version,
        revision_number=revision_number,
        documentation=documentation,
        business_summary=serialize_json_field(business_summary),
        quality_assessment=serialize_json_field(quality_assessment),
        critical_parts=serialize_json_field(critical_parts),
        documentation_source="generated",
        provider=provider,
        source_updated_at=source_updated_at,
        is_latest_for_app_version=True,
        is_latest_for_repository=True,
    )

    db.add(db_version)
    db.flush()

    return db_version


def save_repository_documentation(
    db: Session,
    repository: models.Repository,
    documentation: str,
    app_version: str,
    business_summary: dict[str, Any] | None = None,
    quality_assessment: dict[str, Any] | None = None,
    critical_parts: dict[str, Any] | None = None,
    provider: str | None = None,
    source_updated_at: str | None = None,
):
    documentation_version = create_documentation_version(
        db=db,
        repository=repository,
        app_version=app_version,
        documentation=documentation,
        business_summary=business_summary,
        quality_assessment=quality_assessment,
        critical_parts=critical_parts,
        provider=provider,
        source_updated_at=source_updated_at,
    )

    repository.generated_documentation = documentation
    repository.documentation_updated_at = documentation_version.created_at
    repository.documentation_provider = provider
    repository.documentation_source_updated_at = source_updated_at
    repository.documentation_is_stale = False
    repository.status = "ready"

    db.commit()
    db.refresh(repository)
    db.refresh(documentation_version)

    return documentation_version



def update_documentation_version_content(
    db: Session,
    repository: models.Repository,
    documentation_version: models.DocumentationVersion,
    documentation: str,
):
    now = datetime.now(timezone.utc)

    documentation_version.documentation = documentation
    documentation_version.documentation_source = "manual_edit"
    documentation_version.updated_at = now

    if documentation_version.is_latest_for_repository:
        repository.generated_documentation = documentation
        repository.documentation_updated_at = now
        repository.documentation_is_stale = False
        repository.status = "ready"
        repository.updated_at = now

    db.commit()
    db.refresh(documentation_version)
    db.refresh(repository)

    return documentation_version

def get_documentation_versions(
    db: Session,
    repository_id: int,
):
    return (
        db.query(models.DocumentationVersion)
        .filter(models.DocumentationVersion.repository_id == repository_id)
        .order_by(
            models.DocumentationVersion.created_at.desc(),
            models.DocumentationVersion.id.desc(),
        )
        .all()
    )


def get_documentation_version_by_id(
    db: Session,
    repository_id: int,
    version_id: int,
):
    return (
        db.query(models.DocumentationVersion)
        .filter(
            models.DocumentationVersion.id == version_id,
            models.DocumentationVersion.repository_id == repository_id,
        )
        .first()
    )


def get_latest_documentation_version(
    db: Session,
    repository_id: int,
):
    return (
        db.query(models.DocumentationVersion)
        .filter(
            models.DocumentationVersion.repository_id == repository_id,
            models.DocumentationVersion.is_latest_for_repository.is_(True),
        )
        .order_by(
            models.DocumentationVersion.created_at.desc(),
            models.DocumentationVersion.id.desc(),
        )
        .first()
    )


# --- RAG / Chat CRUD ---


def delete_knowledge_chunks_by_repository(db: Session, repository_id: int) -> None:
    db.query(models.KnowledgeChunk).filter(
        models.KnowledgeChunk.repository_id == repository_id
    ).delete()
    db.commit()


def save_knowledge_chunks(
    db: Session,
    repository_id: int,
    chunks: list[dict],
) -> list[models.KnowledgeChunk]:
    db_chunks: list[models.KnowledgeChunk] = []

    for chunk in chunks:
        db_chunk = models.KnowledgeChunk(
            repository_id=repository_id,
            chunk_type=chunk["chunk_type"],
            content=chunk["content"],
            embedding=chunk.get("embedding"),
            metadata_json=chunk.get("metadata_json"),
            source_path=chunk.get("source_path"),
            language=chunk.get("language"),
            token_count=chunk.get("token_count"),
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)

    db.commit()

    for db_chunk in db_chunks:
        db.refresh(db_chunk)

    return db_chunks


def get_knowledge_chunks_by_repository(
    db: Session,
    repository_id: int,
) -> list[models.KnowledgeChunk]:
    return (
        db.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.repository_id == repository_id)
        .all()
    )


def search_knowledge_chunks_keyword(
    db: Session,
    repository_id: int,
    query: str,
    top_k: int = 8,
) -> list[dict]:
    words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
    chunks = (
        db.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.repository_id == repository_id)
        .all()
    )

    scored: list[dict] = []

    for chunk in chunks:
        content_lower = chunk.content.lower()
        score = 0

        for word in words:
            score += content_lower.count(word)

        if score > 0:
            scored.append(
                {
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "source_path": chunk.source_path,
                    "chunk_type": chunk.chunk_type,
                    "relevance_score": score,
                }
            )

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    return scored[:top_k]


def get_knowledge_chunk_count_by_repository(
    db: Session,
    repository_id: int,
) -> dict[str, int]:
    chunks = (
        db.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.repository_id == repository_id)
        .all()
    )

    counts: dict[str, int] = {}

    for chunk in chunks:
        counts[chunk.chunk_type] = counts.get(chunk.chunk_type, 0) + 1

    return counts


def create_conversation(
    db: Session,
    repository_id: int,
    user_id: int,
    title: str | None = None,
) -> models.ChatConversation:
    db_conversation = models.ChatConversation(
        repository_id=repository_id,
        user_id=user_id,
        title=title,
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)

    return db_conversation


def get_conversations_by_repository(
    db: Session,
    repository_id: int,
    user_id: int,
) -> list[models.ChatConversation]:
    return (
        db.query(models.ChatConversation)
        .filter(
            models.ChatConversation.repository_id == repository_id,
            models.ChatConversation.user_id == user_id,
        )
        .order_by(models.ChatConversation.updated_at.desc())
        .all()
    )


def get_conversation_by_id(
    db: Session,
    conversation_id: int,
    repository_id: int,
    user_id: int,
) -> models.ChatConversation | None:
    return (
        db.query(models.ChatConversation)
        .filter(
            models.ChatConversation.id == conversation_id,
            models.ChatConversation.repository_id == repository_id,
            models.ChatConversation.user_id == user_id,
        )
        .first()
    )


def delete_conversation(
    db: Session,
    conversation_id: int,
    repository_id: int,
    user_id: int,
) -> models.ChatConversation | None:
    db_conversation = get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        repository_id=repository_id,
        user_id=user_id,
    )

    if db_conversation is None:
        return None

    db.delete(db_conversation)
    db.commit()

    return db_conversation


def create_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    sources_json: str | None = None,
) -> models.ChatMessage:
    db_message = models.ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources_json=sources_json,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message


def get_messages_by_conversation(
    db: Session,
    conversation_id: int,
) -> list[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.conversation_id == conversation_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


def get_recent_messages_by_conversation(
    db: Session,
    conversation_id: int,
    limit: int = 10,
) -> list[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.conversation_id == conversation_id)
        .order_by(models.ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
