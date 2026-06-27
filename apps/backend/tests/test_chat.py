# apps/backend/tests/test_chat.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest.fixture
async def test_user():
    """Create a test user for authentication."""
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$test_hashed_password",
        full_name="Test User",
        is_active=True
    )
    await user.insert()
    yield user
    await user.delete()


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers for the test user."""
    token = create_access_token(str(test_user.id), email=test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_ask_endpoint_with_mocked_gemini(auth_headers):
    """
    Integration test for POST /api/v1/chat/ask endpoint.
    Mocks Gemini API and verifies Qdrant context retrieval is called.
    """
    from qdrant_client.models import ScoredPoint

    # Mock Qdrant search response
    mock_search_results = [
        ScoredPoint(
            id="1",
            version=1,
            score=0.95,
            payload={"text": "This is context chunk 1", "user_id": "test_user_id"},
            vector=[0.1, 0.2, 0.3]
        ),
        ScoredPoint(
            id="2",
            version=1,
            score=0.85,
            payload={"text": "This is context chunk 2", "user_id": "test_user_id"},
            vector=[0.4, 0.5, 0.6]
        )
    ]

    # Mock Gemini API response
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "This is a mocked AI response based on the context."}
                    ]
                }
            }
        ]
    }

    from httpx import AsyncClient
    original_post = AsyncClient.post

    mock_http_post = MagicMock()

    async def mock_post_side_effect(self, url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in str(url):
            mock_http_post(url, *args, **kwargs)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_gemini_response
            mock_resp.raise_for_status = MagicMock()
            return mock_resp
        return await original_post(self, url, *args, **kwargs)

    with patch('app.services.chat_service.get_qdrant_client') as mock_get_qdrant, \
         patch('app.services.chat_service.TextEmbedding') as mock_embedding_class, \
         patch('httpx.AsyncClient.post', new=mock_post_side_effect):

        # Setup Qdrant mock
        mock_qdrant_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.points = mock_search_results
        mock_qdrant_client.query_points = AsyncMock(return_value=mock_result)
        mock_get_qdrant.return_value = mock_qdrant_client

        # Setup embedding mock
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_embedding_class.return_value = mock_embedding_instance

        # Make request using httpx AsyncClient
        import httpx

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/ask",
                json={"query": "What is the context about?"},
                headers=auth_headers
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "This is a mocked AI response based on the context."
        assert "context" in data
        assert len(data["context"]) == 2
        assert "This is context chunk 1" in data["context"]
        assert "This is context chunk 2" in data["context"]

        # Verify Qdrant query_points was called with correct filter
        mock_qdrant_client.query_points.assert_called_once()
        call_args = mock_qdrant_client.query_points.call_args
        assert call_args[1]["query_filter"] is not None
        assert call_args[1]["limit"] == 5

        # Verify Gemini API was called
        mock_http_post.assert_called_once()
        http_call_args = mock_http_post.call_args
        assert "generativelanguage.googleapis.com" in http_call_args[0][0]


@pytest.mark.asyncio
async def test_chat_ask_endpoint_unauthorized():
    """Test that the endpoint returns 401 without authentication."""
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/ask",
            json={"query": "Test query"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_ask_endpoint_invalid_query(auth_headers):
    """Test that the endpoint validates query length."""
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/ask",
            json={"query": ""},  # Empty query should fail validation
            headers=auth_headers
        )

    assert response.status_code == 422  # Validation error
