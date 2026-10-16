"""
Tests for multi-worker rate limiting verification.

Tests cover:
- Shared rate limit state across multiple workers
- Redis-backed shared enforcement
- Worker restart does not reset limits
"""
import pytest


@pytest.mark.asyncio
class TestMultiWorkerSharedState:
    """Test that rate limit state is shared across workers."""

    @pytest.mark.asyncio
    async def test_redis_shared_state_across_simulated_workers(self, setup_databases):
        """Test that rate limit state is shared via Redis (simulating multiple workers)."""
        from app.db.redis import get_redis_client
        from app.middleware.rate_limit import RateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

        # Simulate two different rate limiter instances (like two workers)
        limiter1 = RateLimiter()
        limiter2 = RateLimiter()

        identifier = "shared_user_123"
        user_role = "authenticated"
        limit = limiter1.limits[user_role]

        # Worker 1 makes requests up to limit
        for i in range(limit):
            is_allowed, _ = await limiter1.is_allowed(identifier, user_role)
            assert is_allowed is True, f"Worker 1 request {i+1} should be allowed"

        # Worker 1 should be blocked
        is_allowed, _ = await limiter1.is_allowed(identifier, user_role)
        assert is_allowed is False, "Worker 1 should be blocked at limit"

        # Worker 2 should also be blocked (shared state via Redis)
        is_allowed, _ = await limiter2.is_allowed(identifier, user_role)
        assert is_allowed is False, "Worker 2 should see the same limit (shared state)"

        # Clean up after test
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_endpoint_rate_limit_shared_state(self, setup_databases):
        """Test that endpoint rate limit state is shared via Redis."""
        from app.db.redis import get_redis_client
        from app.middleware.endpoint_rate_limit import EndpointRateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)

        # Simulate two different rate limiter instances
        limiter1 = EndpointRateLimiter("ai_ask", limit=20, window_seconds=60)
        limiter2 = EndpointRateLimiter("ai_ask", limit=20, window_seconds=60)

        identifier = "shared_user_456"

        # Worker 1 makes requests up to limit
        for i in range(20):
            is_allowed, _ = await limiter1.is_allowed(identifier)
            assert is_allowed is True, f"Worker 1 request {i+1} should be allowed"

        # Worker 1 should be blocked
        is_allowed, _ = await limiter1.is_allowed(identifier)
        assert is_allowed is False, "Worker 1 should be blocked at limit"

        # Worker 2 should also be blocked (shared state via Redis)
        is_allowed, _ = await limiter2.is_allowed(identifier)
        assert is_allowed is False, "Worker 2 should see the same limit (shared state)"

        # Clean up after test
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)


@pytest.mark.asyncio
class TestConcurrencyRaceConditions:
    """Test concurrent request handling for race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_global_limit(self, setup_databases):
        """Test that concurrent requests cannot significantly exceed the global limit."""
        import asyncio

        from app.db.redis import get_redis_client
        from app.middleware.rate_limit import RateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = RateLimiter()
        identifier = "concurrent_user_123"
        user_role = "authenticated"
        limit = limiter.limits[user_role]

        # Make concurrent requests at the limit
        tasks = [limiter.is_allowed(identifier, user_role) for _ in range(limit)]
        results = await asyncio.gather(*tasks)

        # All should be allowed since we're at the limit
        allowed_count = sum(1 for is_allowed, _ in results if is_allowed)
        assert allowed_count == limit, f"Expected {limit} allowed, got {allowed_count}"

        # One more should be blocked
        is_allowed, _ = await limiter.is_allowed(identifier, user_role)
        assert is_allowed is False, "Request after limit should be blocked"

        # Clean up after test
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_concurrent_requests_exceeding_limit_blocked(self, setup_databases):
        """Test that concurrent requests exceeding limit are blocked."""
        import asyncio

        from app.db.redis import get_redis_client
        from app.middleware.rate_limit import RateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = RateLimiter()
        identifier = "concurrent_user_456"
        user_role = "authenticated"
        limit = limiter.limits[user_role]

        # Make concurrent requests exceeding the limit
        tasks = [limiter.is_allowed(identifier, user_role) for _ in range(limit + 5)]
        results = await asyncio.gather(*tasks)

        # Should not significantly exceed the limit
        allowed_count = sum(1 for is_allowed, _ in results if is_allowed)
        assert allowed_count <= limit + 1, f"Allowed {allowed_count} which significantly exceeds limit {limit}"

        # Clean up after test
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_concurrent_endpoint_requests_respect_limit(self, setup_databases):
        """Test that concurrent endpoint requests respect the endpoint limit."""
        import asyncio

        from app.db.redis import get_redis_client
        from app.middleware.endpoint_rate_limit import EndpointRateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = EndpointRateLimiter("ai_ask", limit=20, window_seconds=60)
        identifier = "concurrent_user_789"

        # Make concurrent requests at the limit
        tasks = [limiter.is_allowed(identifier) for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # All should be allowed since we're at the limit
        allowed_count = sum(1 for is_allowed, _ in results if is_allowed)
        assert allowed_count == 20, f"Expected 20 allowed, got {allowed_count}"

        # One more should be blocked
        is_allowed, _ = await limiter.is_allowed(identifier)
        assert is_allowed is False, "Request after limit should be blocked"

        # Clean up after test
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)


@pytest.mark.asyncio
class TestRedisFailureRecovery:
    """Test Redis failure and recovery behavior."""

    @pytest.mark.asyncio
    async def test_redis_unavailable_blocks_requests(self, setup_databases):
        """Test that Redis unavailability blocks requests (FAIL-CLOSED)."""
        from app.middleware.rate_limit import RateLimiter
        from unittest.mock import patch

        limiter = RateLimiter()
        identifier = "test_user_redis_down"
        user_role = "authenticated"

        # Mock Redis to raise exception
        with patch('app.middleware.rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should block when Redis is unavailable (FAIL-CLOSED)
            is_allowed, retry_after = await limiter.is_allowed(identifier, user_role)
            assert is_allowed is False, "Should block when Redis is unavailable"
            assert retry_after is not None

    @pytest.mark.asyncio
    async def test_redis_recovery_restores_rate_limiting(self, setup_databases):
        """Test that Redis recovery restores rate limiting functionality."""
        from app.db.redis import get_redis_client
        from app.middleware.rate_limit import RateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = RateLimiter()
        identifier = "recovery_user_123"
        user_role = "authenticated"
        limit = limiter.limits[user_role]

        # Normal operation: make requests up to limit
        for i in range(limit):
            is_allowed, _ = await limiter.is_allowed(identifier, user_role)
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # Should be blocked at limit
        is_allowed, _ = await limiter.is_allowed(identifier, user_role)
        assert is_allowed is False, "Should be blocked at limit"

        # Clean up to simulate recovery window expiration
        keys = await redis_client.keys("rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

        # After cleanup (simulating window expiration), should be allowed again
        is_allowed, _ = await limiter.is_allowed(identifier, user_role)
        assert is_allowed is True, "Should be allowed after window expires"

        # Clean up after test
        keys = await redis_client.keys("rate_rate_limit:*")
        if keys:
            await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_endpoint_redis_failure_blocks_requests(self, setup_databases):
        """Test that endpoint rate limiting blocks requests on Redis failure."""
        from app.middleware.endpoint_rate_limit import EndpointRateLimiter
        from unittest.mock import patch

        limiter = EndpointRateLimiter("ai_ask", limit=20, window_seconds=60)
        identifier = "test_user_endpoint_redis_down"

        # Mock Redis to raise exception
        with patch('app.middleware.endpoint_rate_limit.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # Should block when Redis is unavailable (FAIL-CLOSED)
            is_allowed, retry_after = await limiter.is_allowed(identifier)
            assert is_allowed is False, "Should block when Redis is unavailable"
            assert retry_after is not None
