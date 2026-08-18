# apps/backend/app/main.py
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.db.mongo import close_mongo, init_mongo
from app.db.postgres import close_postgres
from app.db.qdrant import close_qdrant, init_qdrant
from app.db.redis import close_redis, init_redis
from app.middleware.rate_limit import rate_limit_middleware


def parse_cors_origins(origins_string: str) -> list[str]:
    """Parse comma-separated origins string into list."""
    if not origins_string:
        return []
    return [origin.strip() for origin in origins_string.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup operations
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=[method.strip() for method in settings.ALLOW_METHODS.split(",")],
    allow_headers=[header.strip() for header in settings.ALLOW_HEADERS.split(",")],
)

# Rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# میان‌افزار مدیریت هویت درخواست (Request-ID) و زمان‌سنجی
@app.middleware("http")
async def add_process_time_and_uuid_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()

    # ذخیره در context ناهمگام برای لاگرها
    request.state.request_id = request_id

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    return response

# مدیریت خطاهای پیش‌بینی نشده سراسری طبق قرارداد api_contracts.md
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred on the server.",
                "details": str(exc) if settings.ENVIRONMENT == "development" else None
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

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "lumenly-api"
    }
