from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RepositoryBase(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    status: str = Field(default="new", min_length=1, max_length=50)

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, value: str):
        normalized_value = value.strip()

        if not normalized_value.startswith("https://github.com/"):
            raise ValueError("Repository URL must start with https://github.com/")

        return normalized_value


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, min_length=1, max_length=50)


class RepositoryResponse(BaseModel):
    id: int
    name: str
    repo_url: str
    description: Optional[str] = None
    status: str

    github_full_name: Optional[str] = None
    github_default_branch: Optional[str] = None
    github_language: Optional[str] = None
    github_updated_at: Optional[str] = None

    generated_documentation: Optional[str] = None
    documentation_updated_at: Optional[datetime] = None
    documentation_provider: Optional[str] = None
    documentation_source_updated_at: Optional[str] = None
    documentation_is_stale: bool = False

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]
    total: int
    page: int
    page_size: int


class RepositoryDocumentationResponse(BaseModel):
    repository_id: int
    documentation: Optional[str] = None
    provider: Optional[str] = None
    updated_at: Optional[datetime] = None
    source_updated_at: Optional[str] = None
    is_stale: bool = False


class GitHubRepositoryAnalyzeRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=255)

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, value: str):
        normalized_value = value.strip()

        if not normalized_value.startswith("https://github.com/"):
            raise ValueError("Repository URL must start with https://github.com/")

        return normalized_value


class GitHubRepositoryInfo(BaseModel):
    full_name: str | None
    html_url: str | None
    description: str | None
    language: str | None
    stars: int
    forks: int
    open_issues: int
    default_branch: str | None
    updated_at: str | None
