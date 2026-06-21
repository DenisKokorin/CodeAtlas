from fastapi import APIRouter, Query

from app import schemas
from app.services.github_service import fetch_repository_info

router = APIRouter(prefix="/external", tags=["External API"])


@router.get(
    "/github/repository-info",
    response_model=schemas.GitHubRepositoryInfo,
)
async def get_github_repository_info(
    repo_url: str = Query(..., min_length=1, max_length=255),
):
    return await fetch_repository_info(repo_url)
