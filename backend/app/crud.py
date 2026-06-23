from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, hash_refresh_token, verify_password


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return (
        db.query(models.User)
        .filter(models.User.email == email.strip().lower())
        .first()
    )


def get_user_by_username(db: Session, username: str):
    return (
        db.query(models.User)
        .filter(models.User.username == username.strip())
        .first()
    )


def create_user(db: Session, user: schemas.UserRegister):
    db_user = models.User(
        email=user.email.strip().lower(),
        username=user.username.strip(),
        hashed_password=get_password_hash(user.password),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db=db, email=email)

    if user is None or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_refresh_token(
    db: Session,
    user_id: int,
    refresh_token: str,
    expires_at: datetime,
):
    db_token = models.RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=expires_at,
    )

    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return db_token


def get_active_refresh_token(db: Session, refresh_token: str):
    token_hash = hash_refresh_token(refresh_token)

    return (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.is_revoked.is_(False),
            models.RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )


def revoke_refresh_token(db: Session, refresh_token: str):
    db_token = get_active_refresh_token(db=db, refresh_token=refresh_token)

    if db_token is None:
        return None

    db_token.is_revoked = True
    db_token.revoked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_token)

    return db_token


def create_repository(
    db: Session,
    repository: schemas.RepositoryCreate,
    owner_id: int,
    github_info: dict | None = None,
):
    github_info = github_info or {}

    repository_name = (
        repository.name
        or (github_info.get("full_name") or "").split("/")[-1]
        or repository.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    )

    db_repository = models.Repository(
        owner_id=owner_id,
        name=repository_name,
        repo_url=repository.repo_url,
        description=repository.description or github_info.get("description"),
        status=repository.status,
        github_full_name=github_info.get("full_name"),
        github_default_branch=github_info.get("default_branch"),
        github_language=github_info.get("language"),
        github_updated_at=github_info.get("updated_at"),
    )

    db.add(db_repository)
    db.commit()
    db.refresh(db_repository)

    return db_repository


def get_repositories(
    db: Session,
    owner_id: int,
    search: str | None = None,
    status: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(models.Repository).filter(models.Repository.owner_id == owner_id)

    if search:
        search_pattern = f"%{search}%"

        query = query.filter(
            or_(
                models.Repository.name.ilike(search_pattern),
                models.Repository.repo_url.ilike(search_pattern),
                models.Repository.description.ilike(search_pattern),
                models.Repository.github_full_name.ilike(search_pattern),
            )
        )

    if status:
        query = query.filter(models.Repository.status == status)

    sort_fields = {
        "id": models.Repository.id,
        "name": models.Repository.name,
        "status": models.Repository.status,
        "created_at": models.Repository.created_at,
        "updated_at": models.Repository.updated_at,
        "documentation_updated_at": models.Repository.documentation_updated_at,
    }

    sort_column = sort_fields.get(sort_by, models.Repository.id)

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_repository_by_id(db: Session, repository_id: int, owner_id: int):
    return (
        db.query(models.Repository)
        .filter(
            models.Repository.id == repository_id,
            models.Repository.owner_id == owner_id,
        )
        .first()
    )


def update_repository(
    db: Session,
    repository_id: int,
    owner_id: int,
    repository_data: schemas.RepositoryUpdate,
):
    db_repository = get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=owner_id,
    )

    if db_repository is None:
        return None

    update_data = repository_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_repository, field, value)

    db.commit()
    db.refresh(db_repository)

    return db_repository


def delete_repository(db: Session, repository_id: int, owner_id: int):
    db_repository = get_repository_by_id(
        db=db,
        repository_id=repository_id,
        owner_id=owner_id,
    )

    if db_repository is None:
        return None

    db.delete(db_repository)
    db.commit()

    return db_repository


def update_repository_github_metadata(
    db: Session,
    repository: models.Repository,
    github_info: dict,
):
    repository.github_full_name = github_info.get("full_name")
    repository.github_default_branch = github_info.get("default_branch")
    repository.github_language = github_info.get("language")
    repository.github_updated_at = github_info.get("updated_at")

    if not repository.description and github_info.get("description"):
        repository.description = github_info.get("description")

    db.commit()
    db.refresh(repository)

    return repository


def update_repository_status(
    db: Session,
    repository: models.Repository,
    status: str,
):
    repository.status = status

    db.commit()
    db.refresh(repository)

    return repository


def save_repository_documentation(
    db: Session,
    repository: models.Repository,
    documentation: str,
    provider: str | None = None,
    source_updated_at: str | None = None,
):
    repository.generated_documentation = documentation
    repository.documentation_updated_at = datetime.now(timezone.utc)
    repository.documentation_provider = provider
    repository.documentation_source_updated_at = source_updated_at
    repository.documentation_is_stale = False
    repository.status = "ready"

    db.commit()
    db.refresh(repository)

    return repository
