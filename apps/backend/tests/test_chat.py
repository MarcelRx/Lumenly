# apps/backend/tests/test_chat.py

import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest_asyncio.fixture
async def test_user(setup_databases, db_session):
    """Create a test user for authentication."""
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$test_hashed_password",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user
    await db_session.delete(user)
    await db_session.commit()


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Generate authentication headers for the test user."""
    token = create_access_token(str(test_user.id), email=test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chat_ask_endpoint_with_mocked_gemini(auth_headers, test_user):
    """
    Integration test for POST /v1/ai/ask endpoint (canonical RAG endpoint).
    Tests the actual RAG orchestrator with mock providers.
    """
    import httpx

    # The test now uses the actual RAG orchestrator with mock providers configured in deps.py
    # This tests the full integration path through the canonical architecture

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/ai/ask",
            json={"query": "What is the context about?"},
            headers=auth_headers
        )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    # With mock provider, we should get a mock response
    assert "Mock response to:" in data["answer"]
    assert "context_used" in data
    assert "retrieval_stats" in data


@pytest.mark.asyncio
async def test_chat_ask_endpoint_unauthorized():
    """Test that the endpoint returns 401 without authentication."""
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/ai/ask",
            json={"query": "Test query"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_ask_endpoint_invalid_query(auth_headers):
    """Test that the endpoint validates query length."""
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/ai/ask",
            json={"query": ""},  # Empty query should fail validation
            headers=auth_headers
        )

    assert response.status_code == 422  # Validation error
