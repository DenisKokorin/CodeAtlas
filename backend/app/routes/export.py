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


def _validate_export_format(fmt: ExportFormat):
    if fmt not in ("markdown", "txt", "html", "docx", "json"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported format: {fmt!r}. "
                f"Available formats: markdown, txt, html, docx, json"
            ),
        )


def _build_file_response(content: str | bytes, media_type: str, filename: str):
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )


@router.get(
    "/{repository_id}/export",
    description=(
        "Export latest repository documentation in the specified format. "
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

    _validate_export_format(fmt)

    latest_version = crud.get_latest_documentation_version(
        db=db,
        repository_id=repository.id,
    )

    try:
        content, media_type, filename = export_documentation(
            repository=repository,
            documentation_version=latest_version,
            fmt=fmt,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail=str(exc),
        ) from exc

    return _build_file_response(
        content=content,
        media_type=media_type,
        filename=filename,
    )


@router.get(
    "/{repository_id}/documentation/versions/{version_id}/export",
    description=(
        "Export selected documentation version in the specified format. "
        "Supported formats: markdown, txt, html, docx, json."
    ),
)
async def export_repository_documentation_version(
    repository_id: int,
    version_id: int,
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

    documentation_version = crud.get_documentation_version_by_id(
        db=db,
        repository_id=repository.id,
        version_id=version_id,
    )

    if documentation_version is None:
        raise HTTPException(
            status_code=404,
            detail="Documentation version not found",
        )

    _validate_export_format(fmt)

    try:
        content, media_type, filename = export_documentation(
            repository=repository,
            documentation_version=documentation_version,
            fmt=fmt,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail=str(exc),
        ) from exc

    return _build_file_response(
        content=content,
        media_type=media_type,
        filename=filename,
    )
