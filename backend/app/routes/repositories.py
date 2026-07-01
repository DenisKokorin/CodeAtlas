from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import documentation_service
from app.services.github_service import fetch_repository_info
from app.services.rag_service import build_index as build_rag_index

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def build_business_summary_response(
    repository: models.Repository,
    documentation_version: models.DocumentationVersion,
):
    business_summary = crud.deserialize_json_field(
        documentation_version.business_summary,
    )

    if business_summary is None:
        raise HTTPException(
            status_code=404,
            detail="Business summary has not been generated yet",
        )

    return {
        "repository_id": repository.id,
        "documentation_version_id": documentation_version.id,
        "app_version": documentation_version.app_version,
        "revision_number": documentation_version.revision_number,
        "display_name": documentation_version.display_name,
        "business_summary": business_summary,
    }


def build_quality_assessment_response(
    repository: models.Repository,
    documentation_version: models.DocumentationVersion,
):
    quality_assessment = crud.deserialize_json_field(
        documentation_version.quality_assessment,
    )

    if quality_assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Quality assessment has not been generated yet",
        )

    return {
        "repository_id": repository.id,
        "documentation_version_id": documentation_version.id,
        "app_version": documentation_version.app_version,
        "revision_number": documentation_version.revision_number,
        "display_name": documentation_version.display_name,
        "quality_assessment": quality_assessment,
    }


def build_critical_parts_response(
    repository: models.Repository,
    documentation_version: models.DocumentationVersion,
):
    critical_parts = crud.deserialize_json_field(
        documentation_version.critical_parts,
    )

    if critical_parts is None:
        raise HTTPException(
            status_code=404,
            detail="Critical parts have not been generated yet",
        )

    return {
        "repository_id": repository.id,
        "documentation_version_id": documentation_version.id,
        "app_version": documentation_version.app_version,
        "revision_number": documentation_version.revision_number,
        "display_name": documentation_version.display_name,
        "critical_parts": critical_parts,
    }


def get_owned_repository_or_404(
    db: Session,
    repository_id: int,
    owner_id: int,
):
    repository = crud.get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=owner_id,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


def get_latest_documentation_version_or_404(
    db: Session,
    repository: models.Repository,
):
    documentation_version = crud.get_latest_documentation_version(
        db=db,
        repository_id=repository.id,
    )

    if documentation_version is None:
        raise HTTPException(
            status_code=404,
            detail="Documentation has not been generated yet",
        )

    return documentation_version


def get_documentation_version_or_404(
    db: Session,
    repository: models.Repository,
    version_id: int,
):
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

    return documentation_version


@router.post(
    "/analyze",
    response_model=schemas.GitHubRepositoryInfo,
)
async def analyze_github_repository(
    payload: schemas.GitHubRepositoryAnalyzeRequest,
    current_user: models.User = Depends(get_current_user),
):
    return await fetch_repository_info(payload.repo_url)


@router.post("/", response_model=schemas.RepositoryResponse)
async def create_repository(
    repository: schemas.RepositoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    github_info = None

    try:
        github_info = await fetch_repository_info(repository.repo_url)
    except HTTPException:
        # Репозиторий всё равно можно сохранить вручную, если GitHub API временно недоступен.
        # Некорректный GitHub URL уже отсекается pydantic-валидацией и parse-функциями.
        github_info = None

    return crud.create_repository(
        db=db,
        repository=repository,
        owner_id=current_user.id,
        github_info=github_info,
    )


@router.get("/", response_model=schemas.RepositoryListResponse)
def read_repositories(
    search: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=50),
    sort_by: str = Query(
        default="id",
        pattern="^(id|name|status|created_at|updated_at|documentation_updated_at)$",
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_repositories(
        db=db,
        owner_id=current_user.id,
        search=search,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{repository_id}", response_model=schemas.RepositoryResponse)
def read_repository(
    repository_id: int,
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

    return repository


@router.put("/{repository_id}", response_model=schemas.RepositoryResponse)
def update_repository(
    repository_id: int,
    repository_data: schemas.RepositoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = crud.update_repository(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
        repository_data=repository_data,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.delete("/{repository_id}", response_model=schemas.RepositoryResponse)
def delete_repository(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = crud.delete_repository(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.get(
    "/{repository_id}/github-info",
    response_model=schemas.GitHubRepositoryInfo,
)
async def read_repository_github_info(
    repository_id: int,
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

    github_info = await fetch_repository_info(repository.repo_url)
    crud.update_repository_github_metadata(
        db=db,
        repository=repository,
        github_info=github_info,
    )

    return github_info


@router.post(
    "/{repository_id}/debug/gemini-raw-response",
)
async def debug_gemini_raw_response(
    repository_id: int,
    payload: schemas.DocumentationGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )

    debug_result = await documentation_service.generate_gemini_raw_debug_response(
        repository=repository,
    )
    debug_result["app_version"] = payload.app_version

    return debug_result


@router.post(
    "/{repository_id}/generate-documentation",
    response_model=schemas.RepositoryDocumentationResponse,
)
async def generate_repository_documentation(
    repository_id: int,
    payload: schemas.DocumentationGenerationRequest,
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

    crud.update_repository_status(db=db, repository=repository, status="processing")

    try:
        result = await documentation_service.generate_repository_documentation(
            repository=repository,
        )
    except Exception:
        crud.update_repository_status(db=db, repository=repository, status="error")
        raise

    documentation_version = crud.save_repository_documentation(
        db=db,
        repository=repository,
        documentation=result["documentation"],
        app_version=payload.app_version,
        business_summary=result.get("business_summary"),
        quality_assessment=result.get("quality_assessment"),
        critical_parts=result.get("critical_parts"),
        provider=result["provider"],
        source_updated_at=result["source_updated_at"],
    )

    # Auto-build RAG index after successful documentation generation
    try:
        await build_rag_index(db=db, repository=repository)
    except Exception:
        pass

    return {
        "repository_id": repository.id,
        "documentation": documentation_version.documentation,
        "provider": documentation_version.provider,
        "updated_at": documentation_version.created_at,
        "source_updated_at": documentation_version.source_updated_at,
        "is_stale": repository.documentation_is_stale,
        "documentation_version_id": documentation_version.id,
        "app_version": documentation_version.app_version,
        "revision_number": documentation_version.revision_number,
        "display_name": documentation_version.display_name,
        "documentation_source": documentation_version.documentation_source,
    }


@router.get(
    "/{repository_id}/documentation/versions",
    response_model=schemas.DocumentationVersionListResponse,
)
def read_documentation_versions(
    repository_id: int,
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

    versions = crud.get_documentation_versions(
        db=db,
        repository_id=repository.id,
    )

    return {
        "items": versions,
        "total": len(versions),
    }


@router.get(
    "/{repository_id}/documentation/versions/{version_id}",
    response_model=schemas.DocumentationVersionResponse,
)
def read_documentation_version(
    repository_id: int,
    version_id: int,
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

    return documentation_version


@router.put(
    "/{repository_id}/documentation/versions/{version_id}/content",
    response_model=schemas.DocumentationVersionResponse,
)
def update_documentation_version_content(
    repository_id: int,
    version_id: int,
    payload: schemas.DocumentationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_documentation_version_or_404(
        db=db,
        repository=repository,
        version_id=version_id,
    )

    return crud.update_documentation_version_content(
        db=db,
        repository=repository,
        documentation_version=documentation_version,
        documentation=payload.documentation,
    )


@router.get(
    "/{repository_id}/business-summary",
    response_model=schemas.BusinessSummaryResponse,
)
def read_latest_business_summary(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_latest_documentation_version_or_404(
        db=db,
        repository=repository,
    )

    return build_business_summary_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/quality-assessment",
    response_model=schemas.QualityAssessmentResponse,
)
def read_latest_quality_assessment(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_latest_documentation_version_or_404(
        db=db,
        repository=repository,
    )

    return build_quality_assessment_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/documentation/versions/{version_id}/business-summary",
    response_model=schemas.BusinessSummaryResponse,
)
def read_documentation_version_business_summary(
    repository_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_documentation_version_or_404(
        db=db,
        repository=repository,
        version_id=version_id,
    )

    return build_business_summary_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/documentation/versions/{version_id}/quality-assessment",
    response_model=schemas.QualityAssessmentResponse,
)
def read_documentation_version_quality_assessment(
    repository_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_documentation_version_or_404(
        db=db,
        repository=repository,
        version_id=version_id,
    )

    return build_quality_assessment_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/critical-parts",
    response_model=schemas.CriticalPartsResponse,
)
def read_latest_critical_parts(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_latest_documentation_version_or_404(
        db=db,
        repository=repository,
    )

    return build_critical_parts_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/documentation/versions/{version_id}/critical-parts",
    response_model=schemas.CriticalPartsResponse,
)
def read_documentation_version_critical_parts(
    repository_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    repository = get_owned_repository_or_404(
        db=db,
        repository_id=repository_id,
        owner_id=current_user.id,
    )
    documentation_version = get_documentation_version_or_404(
        db=db,
        repository=repository,
        version_id=version_id,
    )

    return build_critical_parts_response(
        repository=repository,
        documentation_version=documentation_version,
    )


@router.get(
    "/{repository_id}/documentation",
    response_model=schemas.RepositoryDocumentationResponse,
)
def read_repository_documentation(
    repository_id: int,
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

    latest_version = crud.get_latest_documentation_version(
        db=db,
        repository_id=repository.id,
    )

    return {
        "repository_id": repository.id,
        "documentation": repository.generated_documentation,
        "provider": repository.documentation_provider,
        "updated_at": repository.documentation_updated_at,
        "source_updated_at": repository.documentation_source_updated_at,
        "is_stale": repository.documentation_is_stale,
        "documentation_version_id": latest_version.id if latest_version else None,
        "app_version": latest_version.app_version if latest_version else None,
        "revision_number": latest_version.revision_number if latest_version else None,
        "display_name": latest_version.display_name if latest_version else None,
        "documentation_source": latest_version.documentation_source if latest_version else None,
    }
