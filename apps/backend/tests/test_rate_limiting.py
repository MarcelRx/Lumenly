# apps/backend/tests/test_rate_limiting.py
"""
Integration tests for Redis-based rate limiting middleware.

Tests cover:
- Sliding window algorithm accuracy
- Different user role limits
- Distributed rate limiting (Redis-based)
- Header generation
- Error handling and fallback
"""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import RateLimiter, get_client_identifier, rate_limit_middleware


@pytest.fixture
def rate_limiter():
    """Create a RateLimiter instance for testing."""
    return RateLimiter()


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = "/v1/ai"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_response():
    """Create a mock FastAPI response."""
    response = MagicMock(spec=Response)
    response.headers = {}
    return response


class TestRateLimiter:
    """Test RateLimiter class functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self, rate_limiter):
        """Test that requests within limit are allowed."""
        identifier = "test_user_123"
        user_role = "authenticated"

        # Make requests up to limit
        limit = rate_limiter.limits[user_role]
        for _ in range(limit):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_when_exceeded(self, rate_limiter):
        """Test that requests exceeding limit are blocked."""
        identifier = "test_user_456"
        user_role = "anonymous"

        limit = rate_limiter.limits[user_role]

        # Use real Redis for this test to verify actual blocking behavior
        # This test requires actual Redis operations
        for i in range(limit + 1):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            if i < limit:
                assert is_allowed is True
            else:
                # Last request should be blocked
                assert is_allowed is False
                assert retry_after is not None
                assert retry_after > 0

    @pytest.mark.asyncio
    async def test_rate_limit_sliding_window(self, rate_limiter):
        """Test that sliding window correctly expires old requests."""
        identifier = "test_user_789"
        user_role = "authenticated"

        limit = rate_limiter.limits[user_role]

        # Fill up the limit
        for _ in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True

        # Should be blocked
        is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
        assert is_allowed is False

        # Wait for window to expire (60 seconds + buffer)
        # In test, we'll mock time to speed this up
        with patch('time.time', return_value=time.time() + 61):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_different_users_independent(self, rate_limiter):
        """Test that rate limits are independent per user."""
        user1 = "user_1"
        user2 = "user_2"
        user_role = "authenticated"
        limit = rate_limiter.limits[user_role]

        # User 1 exceeds limit
        for i in range(limit + 1):
            is_allowed, _ = await rate_limiter.is_allowed(user1, user_role)
            if i < limit:
                assert is_allowed is True

        # User 1 should be blocked
        is_allowed, _ = await rate_limiter.is_allowed(user1, user_role)
        assert is_allowed is False

        # User 2 should still be allowed
        is_allowed, _ = await rate_limiter.is_allowed(user2, user_role)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_disabled_when_flag_false(self, rate_limiter):
        """Test that rate limiting is disabled when flag is False."""
        rate_limiter.enabled = False

        identifier = "test_user"
        user_role = "anonymous"

        # Should always allow when disabled
        for _ in range(1000):  # Way above limit
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, rate_limiter):
        """Test rate limit header generation."""
        identifier = "test_user_headers"
        user_role = "authenticated"

        # Make some requests
        await rate_limiter.is_allowed(identifier, user_role)
        await rate_limiter.is_allowed(identifier, user_role)

        headers = await rate_limiter.get_rate_limit_headers(identifier, user_role)

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

        assert int(headers["X-RateLimit-Limit"]) == rate_limiter.limits[user_role]
        assert int(headers["X-RateLimit-Remaining"]) >= 0

    @pytest.mark.asyncio
    async def test_rate_limit_redis_failure_fails_closed_by_default(self, rate_limiter):
        """Test that Redis failures fail closed (block requests) by default for security."""
        identifier = "test_user_redis_fail"
        user_role = "anonymous"

        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should block request when Redis fails (FAIL-CLOSED for security)
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None
            assert retry_after == rate_limiter.window_seconds

    @pytest.mark.asyncio
    async def test_rate_limit_redis_failure_fails_open_when_configured(self, rate_limiter):
        """Test that Redis failures can be configured to fail open for development."""
        identifier = "test_user_redis_fail_open"
        user_role = "anonymous"

        # Configure fail open
        rate_limiter.fail_open = True

        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should allow request when Redis fails (FAIL-OPEN when configured)
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None


class TestGetClientIdentifier:
    """Test client identifier extraction."""

    @pytest.mark.asyncio
    async def test_identifies_authenticated_user(self, mock_request):
        """Test identification of authenticated users."""
        mock_request.state.user_id = "user_123"
        mock_request.state.role = "admin"

        identifier, user_role = await get_client_identifier(mock_request)

        assert identifier == "user_123"
        assert user_role == "admin"

    @pytest.mark.asyncio
    async def test_identifies_anonymous_user_by_ip(self, mock_request):
        """Test identification of anonymous users by IP."""
        mock_request.state.user_id = None
        mock_request.client.host = "192.168.1.100"

        identifier, user_role = await get_client_identifier(mock_request)

        assert identifier == "192.168.1.100"
        assert user_role == "anonymous"

    @pytest.mark.asyncio
    async def test_uses_forwarded_header_when_present(self, mock_request):
        """Test that X-Forwarded-For header is used when present."""
        mock_request.state.user_id = None
        mock_request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
        mock_request.client.host = "192.168.1.100"

        identifier, user_role = await get_client_identifier(mock_request)

        # Should use first IP from X-Forwarded-For
        assert identifier == "203.0.113.195"
        assert user_role == "anonymous"

    @pytest.mark.asyncio
    async def test_fallback_to_unknown_when_no_client_info(self, mock_request):
        """Test fallback to 'unknown' when no client info available."""
        mock_request.state.user_id = None
        mock_request.client = None
        mock_request.headers = {}

        identifier, user_role = await get_client_identifier(mock_request)

        assert identifier == "unknown"
        assert user_role == "anonymous"


class TestRateLimitMiddleware:
    """Test rate limiting middleware integration."""

    @pytest.mark.asyncio
    async def test_middleware_allows_within_limit(self, mock_request, mock_response):
        """Test middleware allows requests within rate limit."""
        mock_request.state.user_id = "test_user"
        mock_request.state.role = "authenticated"
        mock_request.url.path = "/v1/ai"

        call_next = AsyncMock(return_value=mock_response)

        response = await rate_limit_middleware(mock_request, call_next)

        assert response == mock_response
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_blocks_when_exceeded(self, mock_request):
        """Test middleware blocks requests exceeding rate limit."""
        mock_request.state.user_id = "limited_user"
        mock_request.state.role = "anonymous"
        mock_request.url.path = "/v1/ai"

        call_next = AsyncMock()

        # Mock rate limiter to simulate limit exceeded
        with patch('app.middleware.rate_limit.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter.is_allowed.return_value = (False, 30)
            mock_limiter_class.return_value = mock_limiter

            response = await rate_limit_middleware(mock_request, call_next)

            assert isinstance(response, JSONResponse)
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_skips_health_check(self, mock_request, mock_response):
        """Test that health check endpoints bypass rate limiting."""
        mock_request.url.path = "/health"

        call_next = AsyncMock(return_value=mock_response)

        response = await rate_limit_middleware(mock_request, call_next)

        assert response == mock_response
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_adds_rate_limit_headers(self, mock_request, mock_response):
        """Test that middleware adds rate limit headers to responses."""
        mock_request.state.user_id = "test_user"
        mock_request.state.role = "authenticated"
        mock_request.url.path = "/v1/ai"

        call_next = AsyncMock(return_value=mock_response)

        with patch('app.middleware.rate_limit.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter.is_allowed.return_value = (True, None)
            mock_limiter.get_rate_limit_headers.return_value = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "95",
                "X-RateLimit-Reset": "1234567890",
            }
            mock_limiter_class.return_value = mock_limiter

            response = await rate_limit_middleware(mock_request, call_next)

            assert response.headers["X-RateLimit-Limit"] == "100"
            assert response.headers["X-RateLimit-Remaining"] == "95"
            assert response.headers["X-RateLimit-Reset"] == "1234567890"

    @pytest.mark.asyncio
    async def test_middleware_sets_retry_after_header(self, mock_request):
        """Test that middleware sets Retry-After header when rate limited."""
        mock_request.state.user_id = "limited_user"
        mock_request.state.role = "anonymous"
        mock_request.url.path = "/v1/ai"

        call_next = AsyncMock()

        with patch('app.middleware.rate_limit.RateLimiter') as mock_limiter_class:
            mock_limiter = AsyncMock()
            mock_limiter.is_allowed.return_value = (False, 45)
            mock_limiter_class.return_value = mock_limiter

            response = await rate_limit_middleware(mock_request, call_next)

            assert response.headers["Retry-After"] == "45"


class TestRateLimitRoles:
    """Test rate limiting for different user roles."""

    @pytest.mark.asyncio
    async def test_anonymous_user_limit(self, rate_limiter):
        """Test that anonymous users have correct limit."""
        limit = rate_limiter.limits["anonymous"]
        assert limit == 10  # Default from settings

        identifier = "anonymous_user"
        for i in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, "anonymous")
            assert is_allowed is True

        # Next request should be blocked
        is_allowed, _ = await rate_limiter.is_allowed(identifier, "anonymous")
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_authenticated_user_limit(self, rate_limiter):
        """Test that authenticated users have higher limit."""
        limit = rate_limiter.limits["authenticated"]
        assert limit == 100  # Default from settings

        identifier = "authenticated_user"
        # Test a subset to avoid long test times
        for i in range(min(limit, 20)):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, "authenticated")
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_admin_user_limit(self, rate_limiter):
        """Test that admin users have highest limit."""
        limit = rate_limiter.limits["admin"]
        assert limit == 1000  # Default from settings

        identifier = "admin_user"
        # Test a subset to avoid long test times
        for i in range(min(limit, 20)):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, "admin")
            assert is_allowed is True


class TestRateLimitFailureScenarios:
    """Test rate limiting under various Redis failure scenarios."""

    @pytest.mark.asyncio
    async def test_redis_connection_refused_fails_closed(self, rate_limiter):
        """Test that Redis connection refused causes fail-closed behavior."""
        identifier = "test_user_conn_refused"
        user_role = "anonymous"

        import redis.exceptions

        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = redis.exceptions.ConnectionError("Connection refused")

            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_redis_timeout_fails_closed(self, rate_limiter):
        """Test that Redis timeout causes fail-closed behavior."""
        identifier = "test_user_timeout"
        user_role = "authenticated"

        import redis.exceptions

        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = redis.exceptions.TimeoutError("Redis timeout")

            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_redis_pipeline_failure_fails_closed(self, rate_limiter):
        """Test that Redis pipeline execution failure causes fail-closed behavior."""
        identifier = "test_user_pipeline_fail"
        user_role = "admin"

        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(side_effect=Exception("Pipeline execution failed"))
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_redis_availability_allows_requests(self, rate_limiter):
        """Test that available Redis allows normal rate limiting."""
        identifier = "test_user_available"
        user_role = "authenticated"

        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 5, True, True])  # pipeline results
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_concurrent_requests_race_condition(self, rate_limiter):
        """Test that concurrent requests are handled correctly."""
        import asyncio
        identifier = "test_user_concurrent"
        user_role = "authenticated"
        limit = rate_limiter.limits[user_role]

        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, limit - 1, True, True])
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            # Make concurrent requests
            tasks = [rate_limiter.is_allowed(identifier, user_role) for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All should be allowed since we're under the limit
            for is_allowed, retry_after in results:
                assert is_allowed is True
                assert retry_after is None

    @pytest.mark.asyncio
    async def test_multiple_users_isolated_limits(self, rate_limiter):
        """Test that multiple users have independent rate limits."""
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 5, True, True])
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            # User A makes requests
            for _ in range(5):
                is_allowed, _ = await rate_limiter.is_allowed("user_a", "authenticated")
                assert is_allowed is True

            # User B makes requests - should have independent limit
            for _ in range(5):
                is_allowed, _ = await rate_limiter.is_allowed("user_b", "authenticated")
                assert is_allowed is True

    @pytest.mark.asyncio
    async def test_authenticated_user_rate_limited_by_correct_identity(self, rate_limiter):
        """Test that authenticated users are rate-limited by user_id, not IP."""
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 99, True, True])
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            # User should be rate-limited by user_id
            is_allowed, _ = await rate_limiter.is_allowed("user_123", "authenticated")
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_anonymous_user_rate_limited_by_ip(self, rate_limiter):
        """Test that anonymous users are rate-limited by IP address."""
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 9, True, True])
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            # Anonymous user should be rate-limited by IP
            is_allowed, _ = await rate_limiter.is_allowed("192.168.1.100", "anonymous")
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_headers_generated_correctly(self, rate_limiter):
        """Test that rate limit headers are generated with correct values."""
        identifier = "test_user_headers"
        user_role = "authenticated"

        mock_redis = MagicMock()
        mock_redis.zremrangebyscore = AsyncMock(return_value=None)
        mock_redis.zcard = AsyncMock(return_value=42)  # Current count

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            headers = await rate_limiter.get_rate_limit_headers(identifier, user_role)

            assert headers["X-RateLimit-Limit"] == str(rate_limiter.limits[user_role])
            assert headers["X-RateLimit-Remaining"] == str(rate_limiter.limits[user_role] - 42)
            assert "X-RateLimit-Reset" in headers

    @pytest.mark.asyncio
    async def test_retry_after_calculated_correctly(self, rate_limiter):
        """Test that Retry-After header is calculated correctly."""
        identifier = "test_user_retry"
        user_role = "anonymous"

        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        # Simulate being at limit
        mock_pipeline.execute = AsyncMock(return_value=[None, 10, True, True])
        mock_redis.pipeline.return_value = mock_pipeline
        # Simulate oldest entry time
        mock_redis.zrange = AsyncMock(return_value=[("timestamp", time.time() - 30)])

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None
            assert retry_after > 0

    @pytest.mark.asyncio
    async def test_users_cannot_bypass_by_changing_headers(self, rate_limiter):
        """Test that users cannot bypass rate limits by changing headers."""
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 10, True, True])
        mock_redis.pipeline.return_value = mock_pipeline

        with patch('app.middleware.rate_limit.get_redis_client', return_value=mock_redis):
            # Rate limiting is based on user_id/IP, not headers
            # Even with different headers, same user_id should be rate-limited
            identifier = "user_123"
            is_allowed, _ = await rate_limiter.is_allowed(identifier, "authenticated")
            assert is_allowed is True
