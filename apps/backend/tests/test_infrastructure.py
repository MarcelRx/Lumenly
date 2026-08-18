#!/usr/bin/env python3
"""
Test infrastructure connectivity for Lumenly backend.
Tests PostgreSQL, MongoDB, Redis, and Qdrant connections.
"""
import asyncio
import sys
import os

# Set test environment before imports
os.environ["APP_ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["POSTGRES_URL"] = "postgresql+asyncpg://lumenly:lumenly@localhost:5433/lumenly_test"
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/lumenly_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["QDRANT_URL"] = "http://localhost:6333"

from app.db.postgres import engine
from app.db.mongo import init_mongo, close_mongo
from app.db.redis import init_redis, close_redis
from app.db.qdrant import init_qdrant, close_qdrant
from sqlalchemy import text


async def test_postgres():
    """Test PostgreSQL connection."""
    print("Testing PostgreSQL connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result = result.scalar()
            assert result == 1
        print("✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False


async def test_mongodb():
    """Test MongoDB connection."""
    print("Testing MongoDB connection...")
    try:
        await init_mongo()
        print("✓ MongoDB connection successful")
        await close_mongo()
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        return False


async def test_redis():
    """Test Redis connection."""
    print("Testing Redis connection...")
    try:
        result = await init_redis()
        if result:
            print("✓ Redis connection successful")
            await close_redis()
            return True
        else:
            print("✗ Redis connection failed")
            await close_redis()
            return False
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


async def test_qdrant():
    """Test Qdrant connection."""
    print("Testing Qdrant connection...")
    try:
        result = await init_qdrant()
        if result:
            print("✓ Qdrant connection successful")
            await close_qdrant()
            return True
        else:
            print("✗ Qdrant connection failed")
            await close_qdrant()
            return False
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        return False


async def main():
    """Run all infrastructure tests."""
    print("=" * 60)
    print("Lumenly Infrastructure Connectivity Test")
    print("=" * 60)
    
    results = {
        "PostgreSQL": await test_postgres(),
        "MongoDB": await test_mongodb(),
        "Redis": await test_redis(),
        "Qdrant": await test_qdrant(),
    }
    
    print("=" * 60)
    print("Summary:")
    for service, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {service}: {status}")
    print("=" * 60)
    
    all_passed = all(results.values())
    if all_passed:
        print("All infrastructure tests passed!")
        return 0
    else:
        print("Some infrastructure tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)