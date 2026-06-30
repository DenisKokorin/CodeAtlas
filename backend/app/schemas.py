from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=3, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str):
        normalized_value = value.strip().lower()

        if "@" not in normalized_value or "." not in normalized_value.split("@")[-1]:
            raise ValueError("Invalid email")

        return normalized_value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Username cannot be empty")

        return normalized_value


class UserRegister(UserBase):
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long")

        return value


class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str):
        return value.strip().lower()


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


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
    owner_id: int
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


class DocumentationUpdateRequest(BaseModel):
    documentation: str = Field(
        ...,
        min_length=1,
        max_length=500000,
        description="Updated Markdown documentation content",
    )

    @field_validator("documentation")
    @classmethod
    def validate_documentation(cls, value: str):
        if not value.strip():
            raise ValueError("Documentation cannot be empty")

        return value


class DocumentationGenerationRequest(BaseModel):
    app_version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Manual application version, for example 1.0.0 or 1.1.0",
        examples=["1.0.0"],
    )

    @field_validator("app_version")
    @classmethod
    def validate_app_version(cls, value: str):
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Application version cannot be empty")

        return normalized_value


class DocumentationVersionListItem(BaseModel):
    id: int
    repository_id: int
    app_version: str
    revision_number: int
    display_name: str
    provider: Optional[str] = None
    source_updated_at: Optional[str] = None
    documentation_source: str = "generated"
    is_latest_for_app_version: bool
    is_latest_for_repository: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentationVersionResponse(DocumentationVersionListItem):
    documentation: str


class DocumentationVersionListResponse(BaseModel):
    items: list[DocumentationVersionListItem]
    total: int


class RepositoryDocumentationResponse(BaseModel):
    repository_id: int
    documentation: Optional[str] = None
    provider: Optional[str] = None
    updated_at: Optional[datetime] = None
    source_updated_at: Optional[str] = None
    is_stale: bool = False
    documentation_version_id: Optional[int] = None
    app_version: Optional[str] = None
    revision_number: Optional[int] = None
    display_name: Optional[str] = None
    documentation_source: Optional[str] = None


class BusinessSummaryResponse(BaseModel):
    repository_id: int
    documentation_version_id: int
    app_version: str
    revision_number: int
    display_name: str
    business_summary: dict[str, Any]


class QualityAssessmentResponse(BaseModel):
    repository_id: int
    documentation_version_id: int
    app_version: str
    revision_number: int
    display_name: str
    quality_assessment: dict[str, Any]


class CriticalPartsResponse(BaseModel):
    repository_id: int
    documentation_version_id: int
    app_version: str
    revision_number: int
    display_name: str
    critical_parts: dict[str, Any]


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

# --- RAG / Chat Schemas ---

class IndexStatusResponse(BaseModel):
    repository_id: int
    total_chunks: int
    documentation_chunks: int
    code_chunks: int
    metadata_chunks: int
    status: str
    provider: str

    class Config:
        from_attributes = True


class CreateConversationRequest(BaseModel):
    title: str | None = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    id: int
    repository_id: int
    user_id: int
    title: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class SourceReference(BaseModel):
    chunk_id: int
    source_path: str | None
    chunk_type: str
    relevance_score: float


class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[SourceReference] | None
    created_at: datetime

    class Config:
        from_attributes = True


class AskQuestionResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    provider: str


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int