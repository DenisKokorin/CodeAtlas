from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post(
    "/analyze",
    response_model=schemas.GitHubRepositoryInfo,
)
async def analyze_github_repository(
    payload: schemas.GitHubRepositoryAnalyzeRequest,
):
    return await fetch_repository_info(payload.repo_url)


@router.post("/", response_model=schemas.RepositoryResponse)
def create_repository(
    repository: schemas.RepositoryCreate,
    db: Session = Depends(get_db),
):
    return crud.create_repository(
        db=db,
        repository=repository,
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
):
    return crud.get_repositories(
        db=db,
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
):
    repository = crud.get_repository_by_id(
        db=db,
        repository_id=repository_id,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.put("/{repository_id}", response_model=schemas.RepositoryResponse)
def update_repository(
    repository_id: int,
    repository_data: schemas.RepositoryUpdate,
    db: Session = Depends(get_db),
):
    repository = crud.update_repository(
        db=db,
        repository_id=repository_id,
        repository_data=repository_data,
    )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@router.delete("/{repository_id}", response_model=schemas.RepositoryResponse)
def delete_repository(
    repository_id: int,
    db: Session = Depends(get_db),
):
    repository = crud.delete_repository(
        db=db,
        repository_id=repository_id,
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
):
    repository = crud.get_repository_by_id(db=db, repository_id=repository_id)

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    github_info = await fetch_repository_info(repository.repo_url)
    crud.update_repository_github_metadata(
        db=db,
        repository=repository,
        github_info=github_info,
    )

    return github_info
