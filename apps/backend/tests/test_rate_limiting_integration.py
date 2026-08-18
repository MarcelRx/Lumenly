# apps/backend/tests/test_rate_limiting_integration.py
"""
Integration tests for Redis-based rate limiting using real Redis.

These tests verify the actual Redis-backed rate limiting behavior
without mocking, ensuring production-safe behavior.
"""
import time

import pytest

from app.db.redis import get_redis_client
from app.middleware.rate_limit import RateLimiter


@pytest.fixture
async def cleanup_rate_limit_keys(setup_databases):
    """Clean up rate limit keys before and after each test."""
    redis_client = get_redis_client()
    # Clean up before test
    keys = await redis_client.keys("rate_limit:*")
    if keys:
        await redis_client.delete(*keys)
    yield
    # Clean up after test
    keys = await redis_client.keys("rate_limit:*")
    if keys:
        await redis_client.delete(*keys)


class TestRateLimitingRealRedis:
    """Integration tests using real Redis instance."""

    @pytest.mark.asyncio
    async def test_real_redis_blocks_when_limit_exceeded(self, cleanup_rate_limit_keys):
        """Test that real Redis blocks requests when limit is exceeded."""
        rate_limiter = RateLimiter()
        identifier = "test_user_real_1"
        user_role = "anonymous"
        limit = rate_limiter.limits[user_role]

        # Make requests up to limit
        for i in range(limit):
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True, f"Request {i+1} should be allowed"
            assert retry_after is None

        # Next request should be blocked
        is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
        assert is_allowed is False, "Request exceeding limit should be blocked"
        assert retry_after is not None
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_real_redis_different_users_independent(self, cleanup_rate_limit_keys):
        """Test that rate limits are independent per user in real Redis."""
        rate_limiter = RateLimiter()
        user1 = "real_user_1"
        user2 = "real_user_2"
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

        # User 2 should still be allowed (independent limit)
        is_allowed, _ = await rate_limiter.is_allowed(user2, user_role)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_real_redis_sliding_window_expires(self, cleanup_rate_limit_keys):
        """Test that sliding window correctly expires old requests in real Redis."""
        rate_limiter = RateLimiter()
        identifier = "real_user_sliding"
        user_role = "authenticated"
        limit = rate_limiter.limits[user_role]

        # Fill up the limit
        for _ in range(limit):
            is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True

        # Should be blocked
        is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
        assert is_allowed is False

        # Wait for window to expire (61 seconds to be safe)
        time.sleep(61)

        # Should be allowed again after window expires
        is_allowed, _ = await rate_limiter.is_allowed(identifier, user_role)
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_real_redis_headers_accurate(self, cleanup_rate_limit_keys):
        """Test that rate limit headers are accurate with real Redis."""
        rate_limiter = RateLimiter()
        identifier = "real_user_headers"
        user_role = "authenticated"

        # Make some requests
        for _ in range(5):
            await rate_limiter.is_allowed(identifier, user_role)

        headers = await rate_limiter.get_rate_limit_headers(identifier, user_role)

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

        assert int(headers["X-RateLimit-Limit"]) == rate_limiter.limits[user_role]
        assert int(headers["X-RateLimit-Remaining"]) >= 0
        assert int(headers["X-RateLimit-Remaining"]) <= rate_limiter.limits[user_role]

    @pytest.mark.asyncio
    async def test_real_redis_fail_closed_on_error(self, cleanup_rate_limit_keys):
        """Test FAIL-CLOSED behavior when Redis is unavailable."""
        from unittest.mock import patch
        rate_limiter = RateLimiter()
        rate_limiter.fail_open = False  # Ensure FAIL-CLOSED

        identifier = "real_user_fail_closed"
        user_role = "anonymous"

        # Mock Redis client to raise an exception
        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should block when Redis is unavailable (FAIL-CLOSED)
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is False
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_real_redis_fail_open_when_configured(self, cleanup_rate_limit_keys):
        """Test FAIL-OPEN behavior when configured."""
        from unittest.mock import patch
        rate_limiter = RateLimiter()
        rate_limiter.fail_open = True  # Configure FAIL-OPEN

        identifier = "real_user_fail_open"
        user_role = "anonymous"

        # Mock Redis client to raise an exception
        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should allow when Redis is unavailable (FAIL-OPEN)
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_real_redis_concurrent_requests(self, cleanup_rate_limit_keys):
        """Test that concurrent requests are handled correctly with real Redis."""
        import asyncio
        rate_limiter = RateLimiter()
        identifier = "real_user_concurrent"
        user_role = "authenticated"

        # Make concurrent requests under the limit
        tasks = [rate_limiter.is_allowed(identifier, user_role) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should be allowed since we're under the limit
        for is_allowed, retry_after in results:
            assert is_allowed is True
            assert retry_after is None

    @pytest.mark.asyncio
    async def test_real_redis_role_based_limits(self, cleanup_rate_limit_keys):
        """Test that different roles have different limits in real Redis."""
        rate_limiter = RateLimiter()

        anonymous_limit = rate_limiter.limits["anonymous"]
        authenticated_limit = rate_limiter.limits["authenticated"]
        admin_limit = rate_limiter.limits["admin"]

        # Verify limits are correctly configured
        assert anonymous_limit < authenticated_limit < admin_limit

        # Test anonymous limit
        anon_id = "real_anon"
        for i in range(anonymous_limit):
            is_allowed, _ = await rate_limiter.is_allowed(anon_id, "anonymous")
            assert is_allowed is True

        is_allowed, _ = await rate_limiter.is_allowed(anon_id, "anonymous")
        assert is_allowed is False

        # Test authenticated limit (higher)
        auth_id = "real_auth"
        for i in range(min(authenticated_limit, 20)):  # Test subset for speed
            is_allowed, _ = await rate_limiter.is_allowed(auth_id, "authenticated")
            assert is_allowed is True

    @pytest.mark.asyncio
    async def test_real_redis_disabled_flag(self, cleanup_rate_limit_keys):
        """Test that rate limiting can be disabled."""
        rate_limiter = RateLimiter()
        rate_limiter.enabled = False

        identifier = "real_user_disabled"
        user_role = "anonymous"

        # Should always allow when disabled
        for _ in range(100):  # Way above normal limit
            is_allowed, retry_after = await rate_limiter.is_allowed(identifier, user_role)
            assert is_allowed is True
            assert retry_after is None
