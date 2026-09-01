# apps/backend/app/main.py
import time
import uuid
from asyncio import timeout
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.endpoints.ai import router as ai_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.coaching import router as coaching_router
from app.api.endpoints.documents import router as documents_router
from app.api.endpoints.journals import router as journals_router
from app.api.endpoints.memory import router as memory_router
from app.api.endpoints.metrics import router as metrics_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.vectors import router as vectors_router
from app.core.config import settings
from app.core.logging_config import (
    get_logger,
    get_request_id,
    set_request_id,
    setup_logging,
    validate_request_id,
)
from app.core.metrics import (
    database_health_status,
    initialize_metrics,
)
from app.db.mongo import close_mongo, get_mongo_client, init_mongo
from app.db.postgres import AsyncSessionLocal, close_postgres
from app.db.qdrant import close_qdrant, get_qdrant_client, init_qdrant
from app.db.redis import close_redis, get_redis_client, init_redis
from app.middleware.metrics import metrics_middleware
from app.middleware.rate_limit import rate_limit_middleware

# Setup logging based on environment
setup_logging(settings.APP_ENV)
logger = get_logger(__name__)


def parse_cors_origins(origins_string: str) -> list[str]:
    """Parse comma-separated origins string into list."""
    if not origins_string:
        return []
    return [origin.strip() for origin in origins_string.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup operations
    initialize_metrics()  # Initialize Prometheus metrics
    await init_mongo()
    await init_qdrant()
    await init_redis()
    yield
    # Shutdown operations - close connection pools
    await close_postgres()
    await close_mongo()
    await close_qdrant()
    await close_redis()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Production-safe CORS configuration
allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)

# Security check: reject wildcard with credentials (browsers will reject this anyway)
if "*" in allowed_origins and settings.ALLOW_CREDENTIALS:
    raise ValueError(
        "Wildcard CORS origins with credentials are not allowed. "
        "Set ALLOW_CREDENTIALS=false or use specific origins in ALLOW_ORIGINS."
    )

# Security check: reject wildcard origins in production
if settings.APP_ENV == "production" and "*" in allowed_origins:
    raise ValueError(
        "Wildcard CORS origins are not allowed in production. "
        "Set ALLOW_ORIGINS environment variable to specific domains."
    )

# Security check: staging should also use restrictive CORS by default
if settings.APP_ENV == "staging" and "*" in allowed_origins:
    import warnings
    warnings.warn(
        "Wildcard CORS origins in staging environment. "
        "Consider using specific origins for better security.",
        RuntimeWarning
    )

# Fallback to localhost for development if no origins specified
if not allowed_origins and settings.APP_ENV == "development":
    allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

# Security validation: validate embedding configuration
try:
    settings.validate_embedding_config()
except ValueError as e:
    if settings.APP_ENV == "production":
        raise ValueError(f"Embedding configuration validation failed: {e}")
    else:
        import warnings
        warnings.warn(f"Embedding configuration validation failed: {e}", RuntimeWarning)

# Production configuration validation
if settings.APP_ENV == "production":
    # Validate critical security settings
    if len(settings.SECRET_KEY) < 32:
        raise ValueError(
            "SECRET_KEY is too short for production. "
            "Use a strong secret key with at least 32 characters."
        )

    if len(settings.JWT_SECRET) < 32:
        raise ValueError(
            "JWT_SECRET is too short for production. "
            "Use a strong JWT secret with at least 32 characters."
        )

    if settings.SECRET_KEY == settings.JWT_SECRET:
        raise ValueError(
            "SECRET_KEY and JWT_SECRET must be different for security."
        )

    if settings.RATE_LIMIT_ENABLED and settings.RATE_LIMIT_FAIL_OPEN:
        raise ValueError(
            "RATE_LIMIT_FAIL_OPEN is True in production. "
            "This allows requests when Redis is unavailable, which violates security requirements. "
            "Set RATE_LIMIT_FAIL_OPEN=False for fail-closed behavior."
        )

    # Validate required infrastructure URLs
    if not settings.POSTGRES_URL or "localhost" in settings.POSTGRES_URL:
        raise ValueError(
            "POSTGRES_URL must be configured for production without localhost."
        )

    if not settings.MONGODB_URL or "localhost" in settings.MONGODB_URL:
        raise ValueError(
            "MONGODB_URL must be configured for production without localhost."
        )

    if not settings.REDIS_URL or "localhost" in settings.REDIS_URL:
        raise ValueError(
            "REDIS_URL must be configured for production without localhost."
        )

    if not settings.QDRANT_URL or "localhost" in settings.QDRANT_URL:
        raise ValueError(
            "QDRANT_URL must be configured for production without localhost."
        )

    # Validate API keys are set for production
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        raise ValueError(
            "At least one LLM API key (GROQ_API_KEY or GEMINI_API_KEY) must be set for production."
        )

    # Validate that API keys are not placeholder values (config.py handles this, but double-check)
    groq_key = settings.GROQ_API_KEY.strip() if settings.GROQ_API_KEY else ""
    gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""

    if "test_" in groq_key.lower() or "replace_before_production" in groq_key.lower():
        raise ValueError(
            "GROQ_API_KEY appears to be a test/placeholder value. Use a real production API key."
        )

    if "test_" in gemini_key.lower() or "replace_before_production" in gemini_key.lower():
        raise ValueError(
            "GEMINI_API_KEY appears to be a test/placeholder value. Use a real production API key."
        )

    # Run the comprehensive production secrets validation from config
    settings._validate_production_secrets()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=[method.strip() for method in settings.ALLOW_METHODS.split(",")],
    allow_headers=[header.strip() for header in settings.ALLOW_HEADERS.split(",")],
)

# Metrics middleware (must be before rate limiting to track all requests)
app.middleware("http")(metrics_middleware)

# Rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Request correlation middleware with validation and context propagation
@app.middleware("http")
async def add_process_time_and_uuid_middleware(request: Request, call_next):
    """
    Enhanced request correlation middleware.

    - Validates incoming X-Request-ID header
    - Generates UUID v4 if missing or invalid
    - Propagates request ID via contextvars for async-safe logging
    - Adds timing information
    """
    # Get or generate request ID with validation
    incoming_request_id = request.headers.get("X-Request-ID")

    if incoming_request_id and validate_request_id(incoming_request_id):
        request_id = incoming_request_id
    else:
        # Generate new UUID if header missing or invalid
        request_id = str(uuid.uuid4())
        if incoming_request_id:
            logger.warning(
                f"Rejected invalid request ID: {incoming_request_id[:50]}... (generated new ID)"
            )

    start_time = time.time()

    # Store in request.state for existing code compatibility
    request.state.request_id = request_id

    # Store in contextvars for async-safe logger access
    set_request_id(request_id)

    # Log request start (skip health probes to reduce noise)
    if request.url.path not in ["/health", "/health/live", "/health/ready", "/metrics"]:
        logger.info(
            "HTTP request started",
            extra={
                "event": "http_request_start",
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id

    # Log request completion (skip health probes to reduce noise)
    if request.url.path not in ["/health", "/health/live", "/health/ready", "/metrics"]:
        extra_data = {
            "event": "http_request_end",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time * 1000, 2)
        }

        if response.status_code < 400:
            logger.info("HTTP request completed", extra=extra_data)
        elif response.status_code < 500:
            logger.warning("HTTP request completed with warning", extra=extra_data)
        else:
            logger.error("HTTP request completed with error", extra=extra_data)

    return response

# Global exception handler with enhanced observability
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Enhanced global exception handler with proper observability.

    - Logs exceptions server-side with full context
    - Includes request ID from contextvars
    - Returns safe error messages to clients
    - Only exposes stack traces in development
    """
    # Get request ID from contextvars (fallback to request.state)
    request_id = get_request_id() or getattr(request.state, "request_id", "unknown")

    # Log the exception server-side with full context
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "event": "exception",
            "request_id": request_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "method": request.method,
            "path": request.url.path,
            "error_category": "unexpected_error"
        }
    )

    # Return safe error response to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server.",
                "details": str(exc) if settings.APP_ENV == "development" else None
            },
            "meta": {
                "requestId": request_id,
                "timestamp": int(time.time())
            }
        }
    )

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(journals_router, prefix="/api/v1/journals", tags=["journals"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(vectors_router, prefix="/api/v1/vectors", tags=["vectors"])
app.include_router(ai_router, prefix="/v1/ai", tags=["ai"])
app.include_router(coaching_router, prefix="/v1/coaching", tags=["coaching"])
app.include_router(metrics_router, prefix="/v1", tags=["metrics"])

@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Liveness probe - confirms the application process is alive.
    Does NOT depend on external databases.
    """
    return {
        "status": "alive",
        "service": "lumenly-api"
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness probe - determines whether the application can safely receive traffic.
    Verifies actual configured dependencies: PostgreSQL, MongoDB, Redis, Qdrant.
    """
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
        database_health_status.labels(database='postgresql').set(1)
    except TimeoutError:
        health_status["checks"]["postgres"] = {"status": "unhealthy", "error": "timeout"}
        database_health_status.labels(database='postgresql').set(0)
        overall_healthy = False
    except Exception:
        health_status["checks"]["postgres"] = {"status": "unhealthy", "error": "connection_failed"}
        database_health_status.labels(database='postgresql').set(0)
        overall_healthy = False

    # Check MongoDB with timeout
    try:
        async with timeout(5.0):
            mongo_client = get_mongo_client()
            await mongo_client.admin.command('ping')
        health_status["checks"]["mongodb"] = {"status": "healthy"}
        database_health_status.labels(database='mongodb').set(1)
    except TimeoutError:
        health_status["checks"]["mongodb"] = {"status": "unhealthy", "error": "timeout"}
        database_health_status.labels(database='mongodb').set(0)
        overall_healthy = False
    except Exception:
        health_status["checks"]["mongodb"] = {"status": "unhealthy", "error": "connection_failed"}
        database_health_status.labels(database='mongodb').set(0)
        overall_healthy = False

    # Check Redis with timeout
    try:
        async with timeout(5.0):
            redis_client = get_redis_client()
            await redis_client.ping()
        health_status["checks"]["redis"] = {"status": "healthy"}
        database_health_status.labels(database='redis').set(1)
    except TimeoutError:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": "timeout"}
        database_health_status.labels(database='redis').set(0)
        overall_healthy = False
    except Exception:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": "connection_failed"}
        database_health_status.labels(database='redis').set(0)
        overall_healthy = False

    # Check Qdrant with timeout
    try:
        async with timeout(5.0):
            qdrant_client = get_qdrant_client()
            await qdrant_client.get_collections()
        health_status["checks"]["qdrant"] = {"status": "healthy"}
        database_health_status.labels(database='qdrant').set(1)
    except TimeoutError:
        health_status["checks"]["qdrant"] = {"status": "unhealthy", "error": "timeout"}
        database_health_status.labels(database='qdrant').set(0)
        overall_healthy = False
    except Exception:
        health_status["checks"]["qdrant"] = {"status": "unhealthy", "error": "connection_failed"}
        database_health_status.labels(database='qdrant').set(0)
        overall_healthy = False

    if not overall_healthy:
        health_status["status"] = "not_ready"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )

    return health_status


# Keep legacy /health endpoint for backward compatibility
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Legacy health check endpoint for backward compatibility.
    Returns basic status without dependency checks.
    """
    return {
        "status": "ok",
        "service": "lumenly-api"
    }
