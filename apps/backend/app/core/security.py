# apps/backend/app/core/security.py
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.db.redis import get_redis_client

JWT_SECRET = settings.JWT_SECRET or settings.SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    subject: str,
    *,
    email: str | None = None,
    role: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }
    if email is not None:
        payload["email"] = email
    if role is not None:
        payload["role"] = role
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token."""
    return secrets.token_urlsafe(32)


async def store_refresh_token(
    user_id: str,
    refresh_token: str,
) -> None:
    """Store refresh token in Redis with expiration."""
    redis_client = get_redis_client()
    key = f"refresh_token:{refresh_token}"
    await redis_client.set(
        key,
        user_id,
        ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


async def verify_refresh_token(refresh_token: str) -> str | None:
    """Verify refresh token exists in Redis and return user_id."""
    redis_client = get_redis_client()
    key = f"refresh_token:{refresh_token}"
    user_id = await redis_client.get(key)
    return user_id.decode("utf-8") if user_id else None


async def revoke_refresh_token(refresh_token: str) -> bool:
    """Revoke/delete refresh token from Redis."""
    redis_client = get_redis_client()
    key = f"refresh_token:{refresh_token}"
    result = await redis_client.delete(key)
    return result > 0


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
