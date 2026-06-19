from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
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
