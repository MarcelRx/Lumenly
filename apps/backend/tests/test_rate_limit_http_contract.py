"""
Tests for rate limiting HTTP contract.

Tests cover:
- HTTP status codes (429)
- Response body structure
- Retry-After header
- No sensitive information leakage
- No internal implementation details
"""
import pytest


@pytest.mark.asyncio
class TestRateLimitHTTPContract:
    """Test the HTTP contract for rate limiting responses."""

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429_status(self, async_client, cleanup_redis):
        """Test that rate limited requests return HTTP 429."""
        # Make 11 login attempts to trigger rate limit
        for i in range(11):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"test{i}@example.com",
                    "password": "WrongPassword123!",
                },
            )

            if i >= 5:  # After 5 attempts, should be rate limited
                assert response.status_code == 429, f"Request {i+1} should return 429"

    @pytest.mark.asyncio
    async def test_rate_limit_response_body_structure(self, async_client, cleanup_redis):
        """Test that rate limit response has correct structure."""
        # Trigger rate limit
        for i in range(6):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"contract{i}@example.com",
                    "password": "WrongPassword123!",
                },
            )

            if i == 5:  # 6th request should be rate limited
                data = response.json()
                assert "success" in data
                assert data["success"] is False
                assert "error" in data
                assert "code" in data["error"]
                assert "message" in data["error"]
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                assert "Too many requests" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_rate_limit_retry_after_header(self, async_client, cleanup_redis):
        """Test that rate limit response includes Retry-After header."""
        # Trigger rate limit
        for i in range(6):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"retry{i}@example.com",
                    "password": "WrongPassword123!",
                },
            )

            if i == 5:  # 6th request should be rate limited
                assert "Retry-After" in response.headers
                retry_after = int(response.headers["Retry-After"])
                assert retry_after > 0
                assert retry_after <= 60  # Should be within window

    @pytest.mark.asyncio
    async def test_rate_limit_no_sensitive_data_leakage(self, async_client, cleanup_redis):
        """Test that rate limit response does not leak sensitive information."""
        # Trigger rate limit
        for i in range(6):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"leak{i}@example.com",
                    "password": "WrongPassword123!",
                },
            )

            if i == 5:  # 6th request should be rate limited
                data = response.json()
                response_str = str(data)

                # Should not contain sensitive information
                assert "password" not in response_str.lower()
                assert "token" not in response_str.lower()
                assert "secret" not in response_str.lower()
                assert "redis" not in response_str.lower()
                assert "internal" not in response_str.lower()
                assert "stack" not in response_str.lower()
                assert "trace" not in response_str.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_no_implementation_details(self, async_client, cleanup_redis):
        """Test that rate limit response does not expose implementation details."""
        # Trigger rate limit
        for i in range(6):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": f"impl{i}@example.com",
                    "password": "WrongPassword123!",
                },
            )

            if i == 5:  # 6th request should be rate limited
                data = response.json()
                response_str = str(data)

                # Should not contain implementation details
                assert "zadd" not in response_str.lower()
                assert "zcard" not in response_str.lower()
                assert "sorted set" not in response_str.lower()
                assert "pipeline" not in response_str.lower()
                assert "database" not in response_str.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_headers_on_success(self, async_client, cleanup_redis):
        """Test that rate limit headers are present on successful requests."""
        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "headers@example.com",
                "password": "TestPassword123!",
                "full_name": "Headers User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "headers@example.com",
                "password": "TestPassword123!",
            },
        )

        # Should have rate limit headers
        assert "X-RateLimit-Limit" in login_response.headers
        assert "X-RateLimit-Remaining" in login_response.headers
        assert "X-RateLimit-Reset" in login_response.headers

        # Verify header values are valid
        limit = int(login_response.headers["X-RateLimit-Limit"])
        remaining = int(login_response.headers["X-RateLimit-Remaining"])
        reset = int(login_response.headers["X-RateLimit-Reset"])

        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
        assert reset > 0

    @pytest.mark.asyncio
    async def test_endpoint_rate_limit_http_contract(self, async_client, cleanup_redis):
        """Test HTTP contract for endpoint-specific rate limiting."""
        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "endpoint_contract@example.com",
                "password": "TestPassword123!",
                "full_name": "Endpoint Contract User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "endpoint_contract@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]

        # Make 21 AI requests to trigger endpoint rate limit
        for i in range(21):
            response = await async_client.post(
                "/v1/ai/ask",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"query": f"Test query {i}"},
            )

            if i == 20:  # 21st request should be rate limited
                assert response.status_code == 429
                data = response.json()
                assert "success" in data
                assert data["success"] is False
                assert "error" in data
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                assert "Retry-After" in response.headers


@pytest.mark.asyncio
class TestRateLimitResponseHeaders:
    """Test rate limit response headers."""

    @pytest.mark.asyncio
    async def test_rate_limit_remaining_decrements(self, async_client, cleanup_redis):
        """Test that X-RateLimit-Remaining decreases with each request."""
        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "decrement@example.com",
                "password": "TestPassword123!",
                "full_name": "Decrement User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "decrement@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]

        # Make a few requests and verify remaining decreases
        previous_remaining = None
        for i in range(5):
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            current_remaining = int(response.headers["X-RateLimit-Remaining"])

            if previous_remaining is not None:
                # Remaining should decrease or stay same (might fluctuate with timing)
                assert current_remaining <= previous_remaining

            previous_remaining = current_remaining

    @pytest.mark.asyncio
    async def test_rate_limit_reset_timestamp_is_future(self, async_client, cleanup_redis):
        """Test that X-RateLimit-Reset is a future timestamp."""
        import time

        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset@example.com",
                "password": "TestPassword123!",
                "full_name": "Reset User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "reset@example.com",
                "password": "TestPassword123!",
            },
        )

        reset_timestamp = int(login_response.headers["X-RateLimit-Reset"])
        current_timestamp = int(time.time())

        # Reset should be in the future
        assert reset_timestamp > current_timestamp
        # Reset should be within ~60 seconds
        assert reset_timestamp - current_timestamp <= 70
