"""
Endpoint-specific rate limiting for sensitive operations.

Provides fine-grained rate limiting for high-cost or security-sensitive endpoints
with stricter limits than the global middleware.
"""
import ipaddress
import logging
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.metrics import (
    rate_limit_violations_total,
    security_rate_limit_exceeded_total,
)
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)


class EndpointRateLimiter:
    """
    Redis-based endpoint-specific rate limiter.

    Tracks requests per endpoint/user with custom limits.
    """

    def __init__(self, endpoint_name: str, limit: int, window_seconds: int = 60):
        """
        Initialize endpoint-specific rate limiter.

        Args:
            endpoint_name: Unique identifier for the endpoint
            limit: Maximum requests per window
            window_seconds: Time window in seconds (default: 60)
        """
        self.endpoint_name = endpoint_name
        self.limit = limit
        self.window_seconds = window_seconds
        import os
        self.enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.fail_open = settings.RATE_LIMIT_FAIL_OPEN
        self.redis_prefix = "endpoint_rate_limit"

    async def is_allowed(
        self, identifier: str
    ) -> tuple[bool, int | None]:
        """
        Check if request is allowed for this endpoint.

        Args:
            identifier: User ID or IP address

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not self.enabled:
            return True, None

        current_time = int(time.time())
        window_start = current_time - self.window_seconds
        key = f"{self.redis_prefix}:{self.endpoint_name}:{identifier}"

        try:
            redis_client = get_redis_client()
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Remove entries outside the current window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current entries in window
            pipe.zcard(key)

            # Add current request
            import uuid as uuid_lib

            member_id = f"{current_time}_{uuid_lib.uuid4().hex}"
            pipe.zadd(key, {member_id: current_time})

            # Set expiration on the key
            pipe.expire(key, self.window_seconds + 10)

            results = await pipe.execute()

            current_count = results[1]

            if current_count >= self.limit:
                # Calculate retry after (when oldest entry will expire)
                oldest_entry = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_entry:
                    retry_after = int(oldest_entry[0][1] + self.window_seconds - current_time)
                    return False, max(1, retry_after)
                return False, self.window_seconds

            return True, None

        except Exception as e:
            logger.error(f"Endpoint rate limiting error for {self.endpoint_name}: {e}")
            # Fail closed by default for security
            if self.fail_open:
                logger.warning(
                    f"Endpoint rate limiting failing open for {self.endpoint_name} (allowing requests due to Redis failure)"
                )
                return True, None
            else:
                logger.error(
                    f"Endpoint rate limiting failing closed for {self.endpoint_name} (blocking requests due to Redis failure)"
                )
                return False, self.window_seconds


def rate_limit_endpoint(
    endpoint_name: str,
    limit: int,
    window_seconds: int = 60,
) -> Callable:
    """
    Create a FastAPI dependency for endpoint-specific rate limiting.

    Args:
        endpoint_name: Unique identifier for the endpoint
        limit: Maximum requests per window
        window_seconds: Time window in seconds (default: 60)

    Returns:
        FastAPI dependency function
    """

    async def check_rate_limit(request: Request) -> None:
        # Get user_id from JWT if authenticated, otherwise use IP
        user_id = getattr(request.state, "user_id", None)

        # If user_id not in state (authentication runs after rate limit), try to extract from token
        if not user_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from app.core.security import decode_access_token
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    payload = decode_access_token(token)
                    user_id = payload.get("sub")
                except Exception:
                    pass  # Invalid token, fall back to IP

        if user_id:
            identifier = str(user_id)
        else:
            # Use IP for anonymous requests with trusted proxy validation
            client_ip = request.client.host if request.client else "unknown"

            # Check if we have trusted proxies configured
            trusted_proxies_str = settings.RATE_LIMIT_TRUSTED_PROXIES
            if trusted_proxies_str:
                trusted_proxies = [p.strip() for p in trusted_proxies_str.split(",") if p.strip()]

                # Simple CIDR check for trusted proxies
                def is_trusted_proxy(ip: str) -> bool:
                    """Check if IP is in trusted proxy list."""
                    for trusted in trusted_proxies:
                        if "/" in trusted:
                            # CIDR range
                            try:
                                network = ipaddress.ip_network(trusted, strict=False)
                                return ipaddress.ip_address(ip) in network
                            except ValueError:
                                continue
                        else:
                            # Exact match
                            if ip == trusted:
                                return True
                    return False

                # Only use X-Forwarded-For if the direct client is trusted
                if is_trusted_proxy(client_ip):
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        # Use the leftmost (original) IP from X-Forwarded-For
                        identifier = forwarded.split(",")[0].strip()
                    else:
                        identifier = client_ip
                else:
                    # Not a trusted proxy, ignore X-Forwarded-For
                    identifier = client_ip
            else:
                # No trusted proxies configured, ignore X-Forwarded-For
                identifier = client_ip

        limiter = EndpointRateLimiter(endpoint_name, limit, window_seconds)
        is_allowed, retry_after = await limiter.is_allowed(identifier)

        if not is_allowed:
            logger.warning(
                f"Endpoint rate limit exceeded for {endpoint_name}",
                extra={
                    "endpoint": endpoint_name,
                    "identifier": identifier,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # Record rate limit violation metrics
            security_rate_limit_exceeded_total.labels(
                endpoint=endpoint_name, user_role="authenticated" if user_id else "anonymous"
            ).inc()

            rate_limit_violations_total.labels(
                limit_type=f"endpoint_{endpoint_name}",
                user_role="authenticated" if user_id else "anonymous",
            ).inc()

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests for this endpoint. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return check_rate_limit


def get_ai_rate_limit():
    """Rate limiter for AI/LLM endpoints (expensive operations)."""
    return rate_limit_endpoint("ai_ask", limit=20, window_seconds=60)


def get_document_upload_rate_limit():
    """Rate limiter for document upload (triggers expensive Celery tasks)."""
    return rate_limit_endpoint("document_upload", limit=10, window_seconds=60)


def get_login_rate_limit():
    """Rate limiter for login endpoint (authentication attacks)."""
    return rate_limit_endpoint("auth_login", limit=5, window_seconds=60)


def get_refresh_rate_limit():
    """Rate limiter for token refresh endpoint (token abuse)."""
    return rate_limit_endpoint("auth_refresh", limit=10, window_seconds=60)


def get_register_rate_limit():
    """Rate limiter for registration endpoint (account creation abuse)."""
    return rate_limit_endpoint("auth_register", limit=5, window_seconds=3600)  # 5 per hour


async def endpoint_rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for endpoint-specific rate limiting.

    This middleware checks for endpoint-specific rate limits BEFORE the global rate limiter.
    It handles endpoints that need stricter limits than the global default.
    """
    # Skip endpoint rate limiting if disabled (check env var directly for test isolation)
    import os
    if os.environ.get("RATE_LIMIT_ENABLED", "true").lower() != "true":
        return await call_next(request)

    # Map paths to their specific limits
    endpoint_limits = {
        "/v1/ai/ask": ("ai_ask", 20, 60),
        "/api/v1/documents/": ("document_upload", 10, 60),
        "/api/v1/auth/login": ("auth_login", 5, 60),
        "/api/v1/auth/refresh": ("auth_refresh", 10, 60),
        "/api/v1/auth/register": ("auth_register", 5, 3600),
    }

    path = request.url.path
    if path in endpoint_limits:
        endpoint_name, limit, window = endpoint_limits[path]

        # Get user_id from JWT if authenticated, otherwise use IP
        user_id = getattr(request.state, "user_id", None)

        # If user_id not in state (authentication runs after rate limit), try to extract from token
        if not user_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from app.core.security import decode_access_token
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    payload = decode_access_token(token)
                    user_id = payload.get("sub")
                except Exception:
                    pass  # Invalid token, fall back to IP

        if user_id:
            identifier = str(user_id)
        else:
            # Use IP for anonymous requests with trusted proxy validation
            client_ip = request.client.host if request.client else "unknown"

            # Check if we have trusted proxies configured
            trusted_proxies_str = settings.RATE_LIMIT_TRUSTED_PROXIES
            if trusted_proxies_str:
                trusted_proxies = [p.strip() for p in trusted_proxies_str.split(",") if p.strip()]

                # Simple CIDR check for trusted proxies
                def is_trusted_proxy(ip: str) -> bool:
                    """Check if IP is in trusted proxy list."""
                    for trusted in trusted_proxies:
                        if "/" in trusted:
                            # CIDR range
                            try:
                                network = ipaddress.ip_network(trusted, strict=False)
                                return ipaddress.ip_address(ip) in network
                            except ValueError:
                                continue
                        else:
                            # Exact match
                            if ip == trusted:
                                return True
                    return False

                # Only use X-Forwarded-For if the direct client is trusted
                if is_trusted_proxy(client_ip):
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        # Use the leftmost (original) IP from X-Forwarded-For
                        identifier = forwarded.split(",")[0].strip()
                    else:
                        identifier = client_ip
                else:
                    # Not a trusted proxy, ignore X-Forwarded-For
                    identifier = client_ip
            else:
                # No trusted proxies configured, ignore X-Forwarded-For
                identifier = client_ip

        limiter = EndpointRateLimiter(endpoint_name, limit, window)
        is_allowed, retry_after = await limiter.is_allowed(identifier)

        if not is_allowed:
            logger.warning(
                f"Endpoint rate limit exceeded for {endpoint_name}",
                extra={
                    "endpoint": endpoint_name,
                    "identifier": identifier,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            # Record rate limit violation metrics
            security_rate_limit_exceeded_total.labels(
                endpoint=endpoint_name, user_role="authenticated" if user_id else "anonymous"
            ).inc()

            rate_limit_violations_total.labels(
                limit_type=f"endpoint_{endpoint_name}",
                user_role="authenticated" if user_id else "anonymous",
            ).inc()

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests for this endpoint. Please try again later.",
                    },
                    "meta": {
                        "retryAfter": retry_after,
                    },
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Add rate limit headers for successful requests
        current_time = int(time.time())
        window_start = current_time - window
        redis_client = get_redis_client()
        key = f"endpoint_rate_limit:{endpoint_name}:{identifier}"

        try:
            await redis_client.zremrangebyscore(key, 0, window_start)
            current_count = await redis_client.zcard(key)

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
            response.headers["X-RateLimit-Reset"] = str(current_time + window)
            return response
        except Exception:
            # If we can't get current count, just proceed without headers
            return await call_next(request)

    # Process request
    return await call_next(request)
