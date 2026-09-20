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

# Select appropriate key based on algorithm
def get_signing_key():
    """Get the appropriate signing key based on JWT algorithm."""
    if JWT_ALGORITHM == "RS256":
        if not settings.JWT_SECRET_RS256_PRIVATE:
            raise ValueError("JWT_SECRET_RS256_PRIVATE is required when JWT_ALGORITHM=RS256")
        return settings.JWT_SECRET_RS256_PRIVATE
    return JWT_SECRET

def get_verification_key():
    """Get the appropriate verification key based on JWT algorithm."""
    if JWT_ALGORITHM == "RS256":
        if not settings.JWT_SECRET_RS256_PUBLIC:
            raise ValueError("JWT_SECRET_RS256_PUBLIC is required when JWT_ALGORITHM=RS256")
        return settings.JWT_SECRET_RS256_PUBLIC
    return JWT_SECRET


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
    signing_key = get_signing_key()
    return jwt.encode(payload, signing_key, algorithm=JWT_ALGORITHM)


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


async def verify_and_consume_refresh_token(refresh_token: str) -> str | None:
    """
    Atomically verify and consume (delete) a refresh token.
    Returns user_id if token was valid and consumed, None otherwise.
    This prevents race conditions where concurrent refresh requests could both succeed.
    """
    redis_client = get_redis_client()
    key = f"refresh_token:{refresh_token}"

    # Use Lua script for atomic get-and-delete
    # This ensures only one request can successfully consume the token
    lua_script = """
    local value = redis.call('GET', KEYS[1])
    if value then
        redis.call('DEL', KEYS[1])
        return value
    else
        return nil
    end
    """

    result = await redis_client.eval(lua_script, 1, key)
    return result.decode("utf-8") if result else None


async def verify_refresh_token(refresh_token: str) -> str | None:
    """Verify refresh token exists in Redis and return user_id (non-consuming)."""
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
    verification_key = get_verification_key()
    return jwt.decode(token, verification_key, algorithms=[JWT_ALGORITHM])
