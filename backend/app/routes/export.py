from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import get_current_user
from app.database import get_db
from app.services.export_service import (
    ExportFormat,
    export_documentation,
)

router = APIRouter(prefix="/repositories", tags=["Export"])


@router.get(
    "/{repository_id}/export",
    description=(
        "Export repository documentation in the specified format. "
        "Supported formats: markdown, txt, html, docx, json."
    ),
)
async def export_repository_documentation(
    repository_id: int,
    fmt: ExportFormat = Query(
        default="markdown",
        alias="format",
        description="Export format: markdown, txt, html, docx, json",
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = crud.get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    if not repository.generated_documentation:
        raise HTTPException(
            status_code=400,
            detail=(
                "Documentation has not been generated yet. "
                "Please call POST /repositories/{id}/generate-documentation first"
            ),
        )

    if fmt not in ("markdown", "txt", "html", "docx", "json"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported format: {fmt!r}. "
                f"Available formats: markdown, txt, html, docx, json"
            ),
        )

    try:
        content, media_type, filename = export_documentation(
            repository=repository,
            fmt=fmt,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail=str(exc),
        ) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )
