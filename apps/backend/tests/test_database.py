# apps/backend/tests/test_database.py
import pytest
from sqlalchemy import text

from app.db.mongo import get_mongo_client
from app.db.postgres import AsyncSessionLocal
from app.db.qdrant import get_qdrant_client
from app.db.redis import get_redis_client


@pytest.mark.asyncio
async def test_postgres_connection(setup_databases):
    """Test PostgreSQL connection by executing SELECT 1 via an async session."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_mongodb_connection(setup_databases):
    """Test MongoDB connection by performing a ping command."""
    mongo_client = get_mongo_client()
    # Test connection with ping
    await mongo_client.admin.command('ping')


@pytest.mark.asyncio
async def test_redis_connection(setup_databases):
    """Test Redis connection by performing an async SET and GET."""
    redis_client = get_redis_client()

    # Test SET and GET
    await redis_client.set("test_key", "test_value")
    retrieved_value = await redis_client.get("test_key")

    assert retrieved_value.decode("utf-8") == "test_value"

    # Clean up
    await redis_client.delete("test_key")


@pytest.mark.asyncio
async def test_qdrant_connection(setup_databases):
    """Test Qdrant connection by querying the cluster/collection status."""
    qdrant_client = get_qdrant_client()

    # Test connection by getting collections
    collections = await qdrant_client.get_collections()
    assert collections is not None
