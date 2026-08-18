import pytest


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Test the /health endpoint returns correct response."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "lumenly-api"
    }
