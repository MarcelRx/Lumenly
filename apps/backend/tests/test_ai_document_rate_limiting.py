"""
Integration tests for AI and document upload endpoint rate limiting.

Tests cover:
- AI ask endpoint rate limiting (20 req/min per user)
- Document upload endpoint rate limiting (10 req/min per user)
- Real Redis-backed enforcement
- User-based isolation
"""
import pytest


@pytest.mark.asyncio
class TestAIEndpointRateLimiting:
    """Test AI endpoint rate limiting."""

    @pytest.mark.asyncio
    async def test_ai_ask_blocks_after_limit(self, async_client, cleanup_redis):
        """Test that AI ask requests are blocked after 20 attempts per minute per user."""
        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "ai_limit@example.com",
                "password": "TestPassword123!",
                "full_name": "AI Limit User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "ai_limit@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try 21 AI ask requests
        for i in range(21):
            response = await async_client.post(
                "/v1/ai/ask",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"query": f"Test query {i}"},
            )

            if i < 20:
                # First 20 should succeed (or fail for other reasons, but not rate limit)
                assert response.status_code in [200, 503]  # 200 or service unavailable
            else:
                # 21st should get 429 (rate limited)
                assert response.status_code == 429
                response_data = response.json()
                # Endpoint rate limit middleware returns nested structure
                if "error" in response_data:
                    assert "Too many requests" in response_data["error"]["message"]
                else:
                    assert "Too many requests" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ai_different_users_independent(self, async_client, cleanup_redis):
        """Test that AI rate limits are independent per user."""
        # Register and login user 1
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "ai_user1@example.com",
                "password": "TestPassword123!",
                "full_name": "AI User 1",
            },
        )

        login_response_1 = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "ai_user1@example.com",
                "password": "TestPassword123!",
            },
        )
        token_1 = login_response_1.json()["access_token"]

        # Register and login user 2
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "ai_user2@example.com",
                "password": "TestPassword123!",
                "full_name": "AI User 2",
            },
        )

        login_response_2 = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "ai_user2@example.com",
                "password": "TestPassword123!",
            },
        )
        token_2 = login_response_2.json()["access_token"]

        # User 1 makes 20 requests (at limit)
        for i in range(20):
            response = await async_client.post(
                "/v1/ai/ask",
                headers={"Authorization": f"Bearer {token_1}"},
                json={"query": f"User 1 query {i}"},
            )
            assert response.status_code in [200, 503]

        # User 1 should be rate limited
        response = await async_client.post(
            "/v1/ai/ask",
            headers={"Authorization": f"Bearer {token_1}"},
            json={"query": "User 1 query 21"},
        )
        assert response.status_code == 429

        # User 2 should still be allowed (independent limit)
        response = await async_client.post(
            "/v1/ai/ask",
            headers={"Authorization": f"Bearer {token_2}"},
            json={"query": "User 2 query 1"},
        )
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
class TestDocumentUploadRateLimiting:
    """Test document upload endpoint rate limiting."""

    @pytest.mark.asyncio
    async def test_document_upload_blocks_after_limit(self, async_client, cleanup_redis):
        """Test that document upload requests are blocked after 10 attempts per minute per user."""
        # Register and login
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "doc_limit@example.com",
                "password": "TestPassword123!",
                "full_name": "Doc Limit User",
            },
        )

        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "doc_limit@example.com",
                "password": "TestPassword123!",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try 11 document upload requests
        for i in range(11):
            response = await async_client.post(
                "/api/v1/documents/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "filename": f"test{i}.txt",
                    "content": "Test document content " * 10,
                },
            )

            if i < 10:
                # First 10 should succeed (202 accepted)
                assert response.status_code == 202
            else:
                # 11th should get 429 (rate limited)
                assert response.status_code == 429
                response_data = response.json()
                if "error" in response_data:
                    assert "Too many requests" in response_data["error"]["message"]
                else:
                    assert "Too many requests" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_document_upload_different_users_independent(self, async_client, cleanup_redis):
        """Test that document upload rate limits are independent per user."""
        # Register and login user 1
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "doc_user1@example.com",
                "password": "TestPassword123!",
                "full_name": "Doc User 1",
            },
        )

        login_response_1 = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "doc_user1@example.com",
                "password": "TestPassword123!",
            },
        )
        token_1 = login_response_1.json()["access_token"]

        # Register and login user 2
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "doc_user2@example.com",
                "password": "TestPassword123!",
                "full_name": "Doc User 2",
            },
        )

        login_response_2 = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "doc_user2@example.com",
                "password": "TestPassword123!",
            },
        )
        token_2 = login_response_2.json()["access_token"]

        # User 1 makes 10 uploads (at limit)
        for i in range(10):
            response = await async_client.post(
                "/api/v1/documents/",
                headers={"Authorization": f"Bearer {token_1}"},
                json={
                    "filename": f"user1_doc{i}.txt",
                    "content": "Test content " * 10,
                },
            )
            assert response.status_code == 202

        # User 1 should be rate limited
        response = await async_client.post(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {token_1}"},
            json={
                "filename": "user1_doc_11.txt",
                "content": "Test content " * 10,
            },
        )
        assert response.status_code == 429

        # User 2 should still be allowed (independent limit)
        response = await async_client.post(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {token_2}"},
            json={
                "filename": "user2_doc_1.txt",
                "content": "Test content " * 10,
            },
        )
        assert response.status_code == 202


@pytest.mark.asyncio
class TestRealRedisAIAndDocumentRateLimiting:
    """Integration tests using real Redis for AI and document rate limiting."""

    @pytest.mark.asyncio
    async def test_real_redis_ai_limit_enforcement(self, setup_databases):
        """Test AI limit with real Redis."""
        from app.db.redis import get_redis_client
        from app.middleware.endpoint_rate_limit import EndpointRateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = EndpointRateLimiter("ai_ask", limit=20, window_seconds=60)
        identifier = "user_123"  # Simulated user ID

        # Make 20 requests (at limit)
        for i in range(20):
            is_allowed, _ = await limiter.is_allowed(identifier)
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # 21st request should be blocked
        is_allowed, retry_after = await limiter.is_allowed(identifier)
        assert is_allowed is False, "Request exceeding limit should be blocked"
        assert retry_after is not None

        # Clean up after test
        keys = await redis_client.keys("endpoint_rate_limit:ai_ask:*")
        if keys:
            await redis_client.delete(*keys)

    @pytest.mark.asyncio
    async def test_real_redis_document_upload_limit_enforcement(self, setup_databases):
        """Test document upload limit with real Redis."""
        from app.db.redis import get_redis_client
        from app.middleware.endpoint_rate_limit import EndpointRateLimiter

        # Clean up before test
        redis_client = get_redis_client()
        keys = await redis_client.keys("endpoint_rate_limit:document_upload:*")
        if keys:
            await redis_client.delete(*keys)

        limiter = EndpointRateLimiter("document_upload", limit=10, window_seconds=60)
        identifier = "user_456"  # Simulated user ID

        # Make 10 requests (at limit)
        for i in range(10):
            is_allowed, _ = await limiter.is_allowed(identifier)
            assert is_allowed is True, f"Request {i+1} should be allowed"

        # 11th request should be blocked
        is_allowed, retry_after = await limiter.is_allowed(identifier)
        assert is_allowed is False, "Request exceeding limit should be blocked"
        assert retry_after is not None

        # Clean up after test
        keys = await redis_client.keys("endpoint_rate_limit:document_upload:*")
        if keys:
            await redis_client.delete(*keys)
