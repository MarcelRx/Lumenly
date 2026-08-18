# apps/backend/tests/test_vectors.py
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest_asyncio.fixture
async def test_user(setup_databases, db_session):
    """Create a test user for authentication."""
    user = User(
        email="test_vectors@example.com",
        hashed_password="$2b$12$test_hashed_password",
        full_name="Test Vectors User",
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
async def test_vectors_search_endpoint_success(auth_headers):
    """Test successful search request returning results."""
    from qdrant_client.models import ScoredPoint

    from app.core.config import settings

    # Use the configured vector dimension (1536 by default)
    vector_dimension = settings.VECTOR_DIMENSION
    mock_embedding = [0.1] * vector_dimension

    mock_search_results = [
        ScoredPoint(
            id="1",
            version=1,
            score=0.95,
            payload={"chunk_text": "This is a document", "user_id": "test_user_id"},
            vector=mock_embedding
        )
    ]

    with patch('app.api.endpoints.vectors.get_qdrant_client') as mock_get_qdrant, \
         patch('app.api.endpoints.vectors.generate_embedding') as mock_generate_embedding:

        mock_qdrant_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.points = mock_search_results
        mock_qdrant_client.query_points = AsyncMock(return_value=mock_result)
        mock_qdrant_client.collection_exists = AsyncMock(return_value=True)
        mock_get_qdrant.return_value = mock_qdrant_client

        mock_generate_embedding.return_value = mock_embedding

        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/vectors/search",
                json={"query": "test query", "collection_name": "my_collection", "limit": 5},
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        # The actual endpoint returns "text" field from chunk_text in payload
        assert data["results"][0]["text"] == "This is a document"


@pytest.mark.asyncio
async def test_vectors_search_validation_errors(auth_headers):
    """Test various validation errors that produce 422 Unprocessable Entity."""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Missing query
        response1 = await client.post(
            "/api/v1/vectors/search",
            json={"collection_name": "my_collection", "limit": 5},
            headers=auth_headers
        )
        assert response1.status_code == 422

        # 2. Empty query
        response2 = await client.post(
            "/api/v1/vectors/search",
            json={"query": "", "collection_name": "my_collection", "limit": 5},
            headers=auth_headers
        )
        assert response2.status_code == 422

        # 3. Empty collection name
        response3 = await client.post(
            "/api/v1/vectors/search",
            json={"query": "test", "collection_name": "", "limit": 5},
            headers=auth_headers
        )
        assert response3.status_code == 422

        # 4. Limit less than 1
        response4 = await client.post(
            "/api/v1/vectors/search",
            json={"query": "test", "limit": 0},
            headers=auth_headers
        )
        assert response4.status_code == 422

        # 5. Limit greater than 100
        response5 = await client.post(
            "/api/v1/vectors/search",
            json={"query": "test", "limit": 101},
            headers=auth_headers
        )
        assert response5.status_code == 422
