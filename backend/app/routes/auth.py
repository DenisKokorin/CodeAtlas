from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import (
    create_access_token,
    create_refresh_token_value,
    get_current_user,
    get_refresh_token_expires_at,
)
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


def build_token_response(db: Session, user) -> schemas.TokenResponse:
    access_token = create_access_token(user)
    refresh_token = create_refresh_token_value()
    refresh_expires_at = get_refresh_token_expires_at()

    crud.create_refresh_token(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=refresh_expires_at,
    )

    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register_user(
    payload: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    if crud.get_user_by_email(db=db, email=payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    if crud.get_user_by_username(db=db, username=payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this username already exists",
        )

    user = crud.create_user(db=db, user=payload)

    return build_token_response(db=db, user=user)


@router.post("/login", response_model=schemas.TokenResponse)
def login_user(
    payload: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_token_response(db=db, user=user)


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_tokens(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    db_token = crud.get_active_refresh_token(
        db=db,
        refresh_token=payload.refresh_token,
    )

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db_token.user

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    crud.revoke_refresh_token(db=db, refresh_token=payload.refresh_token)

    return build_token_response(db=db, user=user)


@router.post("/logout")
def logout_user(
    payload: schemas.LogoutRequest,
    db: Session = Depends(get_db),
):
    crud.revoke_refresh_token(db=db, refresh_token=payload.refresh_token)

    return {"status": "ok"}


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user
