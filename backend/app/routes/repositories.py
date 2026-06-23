from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import documentation_service
from app.services.github_service import fetch_repository_info

router = APIRouter(prefix="/repositories", tags=["Repositories"])


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
    "/{repository_id}/generate-documentation",
    response_model=schemas.RepositoryDocumentationResponse,
)
async def generate_repository_documentation(
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

    crud.update_repository_status(db=db, repository=repository, status="processing")

    try:
        result = await documentation_service.generate_repository_documentation(
            repository=repository,
        )
    except Exception:
        crud.update_repository_status(db=db, repository=repository, status="error")
        raise

    updated_repository = crud.save_repository_documentation(
        db=db,
        repository=repository,
        documentation=result["documentation"],
        provider=result["provider"],
        source_updated_at=result["source_updated_at"],
    )

    return {
        "repository_id": updated_repository.id,
        "documentation": updated_repository.generated_documentation,
        "provider": updated_repository.documentation_provider,
        "updated_at": updated_repository.documentation_updated_at,
        "source_updated_at": updated_repository.documentation_source_updated_at,
        "is_stale": updated_repository.documentation_is_stale,
    }


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

    return {
        "repository_id": repository.id,
        "documentation": repository.generated_documentation,
        "provider": repository.documentation_provider,
        "updated_at": repository.documentation_updated_at,
        "source_updated_at": repository.documentation_source_updated_at,
        "is_stale": repository.documentation_is_stale,
    }
