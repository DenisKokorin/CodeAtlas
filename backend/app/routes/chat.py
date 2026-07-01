"""
Chat/RAG endpoints for the "Спроси проект" feature.

All endpoints require authentication and verify repository ownership.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import rag_service
from app.services.embedding_service import is_embeddings_available

router = APIRouter(prefix="/repositories/{repository_id}/chat", tags=["Chat"])


def _get_repository_or_404(
    db: Session,
    repository_id: int,
    current_user: models.User,
) -> models.Repository:
    """Verify repository exists and belongs to the current user."""
    repository = crud.get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return repository


def _get_conversation_or_404(
    db: Session,
    conversation_id: int,
    repository_id: int,
    current_user: models.User,
) -> models.ChatConversation:
    """Verify conversation exists and belongs to the repository and user."""
    conversation = crud.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        repository_id=repository_id,
        user_id=current_user.id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.post(
    "/index",
    response_model=schemas.IndexStatusResponse,
)
async def rebuild_knowledge_index(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    (Re)build the RAG knowledge base for a repository.

    Fetches documentation + code from GitHub, chunks them, generates embeddings
    (if GEMINI_API_KEY is configured), and stores everything.

    Works in both Gemini and Mock modes.
    """
    repository = _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    try:
        result = await rag_service.build_index(
            db=db,
            repository=repository,
        )

        return {
            "repository_id": repository.id,
            "total_chunks": result["total_chunks"],
            "documentation_chunks": result["documentation_chunks"],
            "code_chunks": result["code_chunks"],
            "metadata_chunks": result["metadata_chunks"],
            "status": "indexed",
            "provider": result["provider"],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to build knowledge index: {exc!s}",
        ) from exc


@router.post(
    "/conversations",
    response_model=schemas.ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    repository_id: int,
    payload: schemas.CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new chat conversation for a repository."""
    _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    conversation = crud.create_conversation(
        db=db,
        repository_id=repository_id,
        user_id=current_user.id,
        title=payload.title,
    )

    return conversation


@router.get(
    "/conversations",
    response_model=schemas.ConversationListResponse,
)
async def list_conversations(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all chat conversations for a repository."""
    _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    conversations = crud.get_conversations_by_repository(
        db=db,
        repository_id=repository_id,
        user_id=current_user.id,
    )

    return {
        "items": conversations,
        "total": len(conversations),
    }


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.AskQuestionResponse,
)
async def ask_question(
    repository_id: int,
    conversation_id: int,
    payload: schemas.AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Ask a question about the repository.

    Uses RAG to find relevant context and generate an answer.
    Works in both Gemini (AI answer) and Mock (template answer) modes.
    """
    repository = _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    conversation = _get_conversation_or_404(
        db=db,
        conversation_id=conversation_id,
        repository_id=repository_id,
        current_user=current_user,
    )

    # Verify index has been built
    chunk_count = crud.get_knowledge_chunk_count_by_repository(
        db=db,
        repository_id=repository.id,
    )

    if not chunk_count or sum(chunk_count.values()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Knowledge index has not been built yet. "
                "Call POST /repositories/{id}/chat/index first."
            ),
        )

    result = await rag_service.answer_question(
        db=db,
        repository=repository,
        conversation=conversation,
        question=payload.question,
    )

    return result


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageListResponse,
)
async def get_conversation_history(
    repository_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    conversation = _get_conversation_or_404(
        db=db,
        conversation_id=conversation_id,
        repository_id=repository_id,
        current_user=current_user,
    )

    messages = crud.get_messages_by_conversation(
        db=db,
        conversation_id=conversation.id,
    )

    message_responses = []
    for msg in messages:
        sources = None

        if msg.sources_json:
            try:
                sources_data = json.loads(msg.sources_json)
                sources = [
                    schemas.SourceReference(**s) for s in sources_data
                ]
            except (json.JSONDecodeError, Exception):
                sources = None

        message_responses.append(
            schemas.MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                sources=sources,
                created_at=msg.created_at,
            )
        )

    return {
        "items": message_responses,
        "total": len(message_responses),
    }


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    repository_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a chat conversation and all its messages."""
    _get_repository_or_404(
        db=db,
        repository_id=repository_id,
        current_user=current_user,
    )

    deleted = crud.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        repository_id=repository_id,
        user_id=current_user.id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
