from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user", index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    repositories = relationship(
        "Repository",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False, index=True)
    repo_url = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="new", index=True)

    github_full_name = Column(String(255), nullable=True)
    github_default_branch = Column(String(100), nullable=True)
    github_language = Column(String(100), nullable=True)
    github_updated_at = Column(String(50), nullable=True)

    generated_documentation = Column(Text, nullable=True)
    documentation_updated_at = Column(DateTime(timezone=True), nullable=True)
    documentation_provider = Column(String(50), nullable=True)
    documentation_source_updated_at = Column(String(50), nullable=True)
    documentation_is_stale = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="repositories")
    documentation_versions = relationship(
        "DocumentationVersion",
        back_populates="repository",
        cascade="all, delete-orphan",
    )


class DocumentationVersion(Base):
    __tablename__ = "documentation_versions"
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "app_version",
            "revision_number",
            name="uq_documentation_version_revision",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(
        Integer,
        ForeignKey("repositories.id"),
        nullable=False,
        index=True,
    )
    app_version = Column(String(50), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    documentation = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)
    source_updated_at = Column(String(50), nullable=True)
    is_latest_for_app_version = Column(Boolean, nullable=False, default=True)
    is_latest_for_repository = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    repository = relationship(
        "Repository",
        back_populates="documentation_versions",
    )

    @property
    def display_name(self) -> str:
        return f"Documentation {self.app_version} revision {self.revision_number}"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")
