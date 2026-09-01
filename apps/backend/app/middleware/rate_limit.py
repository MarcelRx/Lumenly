# apps/backend/app/middleware/rate_limit.py
"""
Redis-based rate limiting middleware using sliding window algorithm.

Provides production-grade rate limiting for API endpoints with:
- Sliding window algorithm for accurate rate limiting
- Configurable limits per user role
- Redis-based storage for distributed systems
- Automatic cleanup of expired entries
"""
import logging
import time
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.metrics import (
    rate_limit_violations_total,
    security_rate_limit_exceeded_total,
)
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Tracks requests per user/IP within a time window and enforces limits.
    """

    def __init__(self):
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.redis_prefix = settings.RATE_LIMIT_REDIS_PREFIX
        self.window_seconds = 60  # 1-minute sliding window
        self.fail_open = settings.RATE_LIMIT_FAIL_OPEN
        self.limits = {
            "anonymous": settings.RATE_LIMIT_ANONYMOUS_REQUESTS,
            "authenticated": settings.RATE_LIMIT_AUTHENTICATED_REQUESTS,
            "admin": settings.RATE_LIMIT_ADMIN_REQUESTS,
        }

    async def is_allowed(
        self,
        identifier: str,
        user_role: str = "anonymous"
    ) -> tuple[bool, Optional[int]]:
        if not self.enabled:
            return True, None

        limit = self.limits.get(user_role, self.limits["anonymous"])
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        key = f"{self.redis_prefix}:{identifier}"

        try:
            redis_client = get_redis_client()
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Remove entries outside the current window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current entries in window
            pipe.zcard(key)

            # Add current request
            import uuid
            member_id = f"{current_time}_{uuid.uuid4().hex}"
            pipe.zadd(key, {member_id: current_time})

            # Set expiration on the key
            pipe.expire(key, self.window_seconds + 10)

            results = await pipe.execute()

            current_count = results[1]

            if current_count >= limit:
                # Calculate retry after (when oldest entry will expire)
                oldest_entry = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_entry:
                    retry_after = int(oldest_entry[0][1] + self.window_seconds - current_time)
                    return False, max(1, retry_after)
                return False, self.window_seconds

            return True, None

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail closed by default for security - block request if Redis fails
            # Can be configured to fail open in development/low-risk scenarios
            if self.fail_open:
                logger.warning("Rate limiting failing open (allowing requests due to Redis failure)")
                return True, None
            else:
                logger.error("Rate limiting failing closed (blocking requests due to Redis failure)")
                return False, self.window_seconds

    async def get_rate_limit_headers(
        self,
        identifier: str,
        user_role: str = "anonymous"
    ) -> dict[str, str]:
        if not self.enabled:
            return {}

        limit = self.limits.get(user_role, self.limits["anonymous"])
        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        key = f"{self.redis_prefix}:{identifier}"

        try:
            redis_client = get_redis_client()
            # Count current requests in window
            await redis_client.zremrangebyscore(key, 0, window_start)
            current_count = await redis_client.zcard(key)

            return {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - current_count)),
                "X-RateLimit-Reset": str(current_time + self.window_seconds),
            }
        except Exception as e:
            logger.error(f"Rate limit headers error: {e}")
            return {}


async def get_client_identifier(request: Request) -> tuple[str, str]:
    """
    Extract client identifier and user role from request.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (identifier, user_role)
    """
    # Try to get user_id from JWT token
    user_id = getattr(request.state, "user_id", None)

    if user_id:
        # Get user role if available
        user_role = getattr(request.state, "role", "authenticated")
        return str(user_id), user_role

    # Fall back to IP address for anonymous users
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        identifier = forwarded.split(",")[0].strip()
    else:
        identifier = request.client.host if request.client else "unknown"

    return identifier, "anonymous"


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Rate limiting middleware for FastAPI.

    Enforces rate limits based on user role and returns 429 if exceeded.
    """
    # Skip rate limiting for health checks and metrics
    if request.url.path in ["/health", "/health/live", "/health/ready", "/api/v1/metrics", "/metrics", "/v1/metrics"]:
        return await call_next(request)

    # Get client identifier and role
    identifier, user_role = await get_client_identifier(request)

    # Initialize rate limiter
    rate_limiter = RateLimiter()

    # Check if request is allowed
    is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)

    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for {identifier} (role: {user_role})",
            extra={
                "identifier": identifier,
                "user_role": user_role,
                "path": request.url.path,
                "method": request.method,
            }
        )

        # Record rate limit violation metrics
        security_rate_limit_exceeded_total.labels(
            endpoint=request.url.path,
            user_role=user_role
        ).inc()

        rate_limit_violations_total.labels(
            limit_type="http_request",
            user_role=user_role
        ).inc()

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                },
                "meta": {
                    "retryAfter": retry_after,
                }
            },
            headers={"Retry-After": str(retry_after)}
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers
    rate_limit_headers = await rate_limiter.get_rate_limit_headers(identifier, user_role)
    for header_name, header_value in rate_limit_headers.items():
        response.headers[header_name] = header_value

    return response
