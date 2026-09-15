
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

# Set required environment variables for testing before importing app modules
os.environ.setdefault("APP_ENV", "development")  # Use development for testing
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("RATE_LIMIT_ENABLED", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-32bytes-min")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-32bytes-min")
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://lumenly:lumenly_secure_password_32chars@localhost:5433/lumenly_test")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/lumenly_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
# Ensure no real API keys are set for testing - force mock providers
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("COHERE_API_KEY", "")

from app.db.base_class import Base
from app.db.mongo import close_mongo, init_mongo
from app.db.postgres import AsyncSessionLocal, close_postgres, engine
from app.db.qdrant import close_qdrant, init_qdrant
from app.db.redis import close_redis, init_redis
from app.models.user import User


async def create_tables():
    """Create all database tables for testing."""
    async with engine.begin() as conn:
        # Drop tables first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Then create tables
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables after testing."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session():
    """Create a database session for each test."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_databases():
    """Setup all databases for testing."""
    # Ensure tables are created before any test runs
    await create_tables()
    await init_redis()
    await init_mongo()
    await init_qdrant()

    # Yield control to the test
    yield

    # Cleanup after test
    await drop_tables()
    await close_postgres()
    await close_redis()
    await close_mongo()
    await close_qdrant()


@pytest.fixture(scope="function")
async def cleanup_redis(setup_databases):
    """Clean up Redis after each test."""
    from app.db.redis import get_redis_client
    yield
    try:
        redis_client = get_redis_client()
        keys = await redis_client.keys("refresh_token:*")
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        pass  # Redis might not be available


@pytest.fixture(scope="function")
async def cleanup_users(db_session):
    """Clean up test users after each test."""
    yield
    try:
        result = await db_session.execute(
            select(User).where(User.email.like("%@example.com"))
        )
        users = result.scalars().all()
        for user in users:
            await db_session.delete(user)
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.fixture(scope="function")
async def cleanup_mongo(setup_databases):
    """Clean up MongoDB collections after each test."""
    from app.db.mongo import get_mongo_client
    from app.models.domain import (
        AIInsight,
        CoachingSession,
        ComplianceEvent,
        Goal,
        Habit,
        JournalEntry,
        UserDocument,
    )

    yield
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()

        # Clean up all domain collections
        await db.drop_collection(JournalEntry.get_collection_name())
        await db.drop_collection(Goal.get_collection_name())
        await db.drop_collection(Habit.get_collection_name())
        await db.drop_collection(UserDocument.get_collection_name())
        await db.drop_collection(CoachingSession.get_collection_name())
        await db.drop_collection(AIInsight.get_collection_name())
        await db.drop_collection(ComplianceEvent.get_collection_name())
    except Exception:
        pass  # MongoDB might not be available


@pytest.fixture(scope="function")
async def cleanup_qdrant(setup_databases):
    """Clean up Qdrant collection after each test."""
    from app.db.qdrant import get_qdrant_client
    from app.services.vector import COLLECTION_NAME

    yield
    try:
        qdrant_client = get_qdrant_client()
        # Only delete collection if it exists
        try:
            await qdrant_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # Collection might not exist
    except Exception:
        pass  # Qdrant might not be available


@pytest.fixture(scope="function")
async def async_client(setup_databases):
    """Create an async HTTP client using the test app with pre-initialized databases."""
    # Create a test app without lifespan (databases already initialized by setup_databases)
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.endpoints.ai import router as ai_router
    from app.api.endpoints.auth import router as auth_router
    from app.api.endpoints.coaching import router as coaching_router
    from app.api.endpoints.documents import router as documents_router
    from app.api.endpoints.journals import router as journals_router

    # from app.api.endpoints.memory import router as memory_router  # Temporarily disabled
    from app.api.endpoints.metrics import router as metrics_router
    from app.api.endpoints.users import router as users_router
    from app.api.endpoints.vectors import router as vectors_router
    from app.core.config import settings

    test_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        lifespan=None  # No lifespan - databases managed by setup_databases
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    test_app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    test_app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    test_app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    test_app.include_router(journals_router, prefix="/api/v1/journals", tags=["journals"])
    # test_app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])  # Temporarily disabled
    test_app.include_router(vectors_router, prefix="/api/v1/vectors", tags=["vectors"])
    test_app.include_router(ai_router, prefix="/v1/ai", tags=["ai"])
    test_app.include_router(coaching_router, prefix="/v1/coaching", tags=["coaching"])
    test_app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])

    # Add health endpoints
    @test_app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok",
            "service": "lumenly-api"
        }

    @test_app.get("/health/live", tags=["Health"])
    async def liveness_check():
        return {
            "status": "alive",
            "service": "lumenly-api"
        }

    @test_app.get("/health/ready", tags=["Health"])
    async def readiness_check():
        from asyncio import timeout

        from fastapi import HTTPException
        from sqlalchemy import text

        from app.db.mongo import get_mongo_client
        from app.db.postgres import AsyncSessionLocal
        from app.db.qdrant import get_qdrant_client
        from app.db.redis import get_redis_client

        health_status = {
            "status": "ready",
            "service": "lumenly-api",
            "checks": {}
        }

        overall_healthy = True

        # Check PostgreSQL with timeout
        try:
            async with timeout(5.0):
                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
            health_status["checks"]["postgres"] = {"status": "healthy"}
        except Exception:
            health_status["checks"]["postgres"] = {"status": "unhealthy", "error": "connection_failed"}
            overall_healthy = False

        # Check MongoDB with timeout
        try:
            async with timeout(5.0):
                mongo_client = get_mongo_client()
                await mongo_client.admin.command('ping')
            health_status["checks"]["mongodb"] = {"status": "healthy"}
        except Exception:
            health_status["checks"]["mongodb"] = {"status": "unhealthy", "error": "connection_failed"}
            overall_healthy = False

        # Check Redis with timeout
        try:
            async with timeout(5.0):
                redis_client = get_redis_client()
                await redis_client.ping()
            health_status["checks"]["redis"] = {"status": "healthy"}
        except Exception:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": "connection_failed"}
            overall_healthy = False

        # Check Qdrant with timeout
        try:
            async with timeout(5.0):
                qdrant_client = get_qdrant_client()
                await qdrant_client.get_collections()
            health_status["checks"]["qdrant"] = {"status": "healthy"}
        except Exception:
            health_status["checks"]["qdrant"] = {"status": "unhealthy", "error": "connection_failed"}
            overall_healthy = False

        if not overall_healthy:
            health_status["status"] = "not_ready"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )

        return health_status

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def client(setup_databases):
    """Create a synchronous test client for non-WebSocket testing."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    from app.api.endpoints.ai import router as ai_router
    from app.api.endpoints.auth import router as auth_router
    from app.api.endpoints.coaching import router as coaching_router
    from app.api.endpoints.documents import router as documents_router
    from app.api.endpoints.journals import router as journals_router
    from app.api.endpoints.metrics import router as metrics_router
    from app.api.endpoints.users import router as users_router
    from app.api.endpoints.vectors import router as vectors_router
    from app.core.config import settings

    test_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        lifespan=None  # No lifespan - databases managed by setup_databases
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    test_app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    test_app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    test_app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    test_app.include_router(journals_router, prefix="/api/v1/journals", tags=["journals"])
    # test_app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])  # Temporarily disabled
    test_app.include_router(vectors_router, prefix="/api/v1/vectors", tags=["vectors"])
    test_app.include_router(ai_router, prefix="/v1/ai", tags=["ai"])
    test_app.include_router(coaching_router, prefix="/v1/coaching", tags=["coaching"])
    test_app.include_router(metrics_router, prefix="/v1", tags=["metrics"])

    # Add health endpoint
    @test_app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok",
            "service": "lumenly-api"
        }

    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_websocket_client(setup_databases):
    """Create an async WebSocket client for WebSocket testing with proper async database access."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from httpx import ASGITransport, AsyncClient

    from app.api.endpoints.ai import router as ai_router
    from app.api.endpoints.auth import router as auth_router
    from app.api.endpoints.coaching import router as coaching_router
    from app.api.endpoints.documents import router as documents_router
    from app.api.endpoints.journals import router as journals_router
    from app.api.endpoints.metrics import router as metrics_router
    from app.api.endpoints.users import router as users_router
    from app.api.endpoints.vectors import router as vectors_router
    from app.core.config import settings

    test_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        lifespan=None  # No lifespan - databases managed by setup_databases
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    test_app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    test_app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    test_app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
    test_app.include_router(journals_router, prefix="/api/v1/journals", tags=["journals"])
    # test_app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])  # Temporarily disabled
    test_app.include_router(vectors_router, prefix="/api/v1/vectors", tags=["vectors"])
    test_app.include_router(ai_router, prefix="/v1/ai", tags=["ai"])
    test_app.include_router(coaching_router, prefix="/v1/coaching", tags=["coaching"])
    test_app.include_router(metrics_router, prefix="/v1", tags=["metrics"])

    # Add health endpoint
    @test_app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok",
            "service": "lumenly-api"
        }

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def create_test_user(db_session):
    """Helper fixture to create a test user with proper async database operations."""
    async def _create_user(email: str, password: str = "TestPassword123!", is_active: bool = True):
        from app.core.security import get_password_hash
        from app.models.user import User

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture(scope="function")
async def create_test_user_with_token(async_websocket_client, create_test_user):
    """Helper fixture to create a test user and return their JWT token."""
    async def _create_user_with_token(email: str, password: str = "TestPassword123!", is_active: bool = True):
        # Create user
        user = await create_test_user(email, password, is_active)

        # Login to get token
        login_response = await async_websocket_client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        return user, token_data["access_token"]

    return _create_user_with_token


@pytest.fixture(scope="function")
async def create_coaching_session(create_test_user):
    """Helper fixture to create a coaching session with proper async MongoDB operations."""
    async def _create_session(user_id, session_type="assessment", title="Test Session"):
        from app.models.domain import CoachingSession, SessionType

        # Convert string to enum if needed
        if isinstance(session_type, str):
            session_type = SessionType(session_type)

        session = CoachingSession(
            user_id=user_id,
            session_type=session_type,
            agent_id="test_agent",
            title=title,
            metadata={"test": True},
        )
        await session.insert()
        return session

    return _create_session
