from fastapi import APIRouter, Depends, Query

from app import models, schemas
from app.auth import get_current_user
from app.services.github_service import fetch_repository_info

router = APIRouter(prefix="/external", tags=["External API"])


@router.get(
    "/github/repository-info",
    response_model=schemas.GitHubRepositoryInfo,
)
async def get_github_repository_info(
    repo_url: str = Query(..., min_length=1, max_length=255),
    current_user: models.User = Depends(get_current_user),
):
    return await fetch_repository_info(repo_url)
