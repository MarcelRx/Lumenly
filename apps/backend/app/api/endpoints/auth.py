# apps/backend/app/api/endpoints/auth.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    revoke_refresh_token,
    store_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.db.postgres import get_postgres_session
from app.models.user import User, UserRole
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_postgres_session)],
) -> UserResponse:
    result = await session.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive JWT access and refresh tokens",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_postgres_session)],
) -> Token:
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role.value,
    )
    refresh_token = create_refresh_token()
    await store_refresh_token(str(user.id), refresh_token)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using a valid refresh token",
)
async def refresh(
    refresh_request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_postgres_session)],
) -> Token:
    user_id = await verify_refresh_token(refresh_request.refresh_token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
        )

    access_token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role.value,
    )
    new_refresh_token = create_refresh_token()

    # Revoke old refresh token and store new one
    await revoke_refresh_token(refresh_request.refresh_token)
    await store_refresh_token(str(user.id), new_refresh_token)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout by revoking the refresh token",
)
async def logout(
    refresh_request: RefreshTokenRequest,
) -> None:
    await revoke_refresh_token(refresh_request.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
