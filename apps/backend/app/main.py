# apps/backend/app/main.py
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.chat import router as fusion_chat_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.metrics import router as metrics_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.vectors import router as vectors_router
from app.core.config import settings
from app.core.database import init_db
from app.core.qdrant import close_qdrant, init_qdrant
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # عملیات زمان راه‌اندازی (Startup)
    await init_db()
    await init_qdrant()
    await init_redis()
    yield
    await close_qdrant()
    await close_redis()
    # عملیات زمان خاموش شدن (Shutdown) - در صورت نیاز برای بستن کانکشن‌پول‌ها

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# تنظیم CORS بر اساس نیازهای فرانت‌اند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در محیط پروداکشن محدود شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(vectors_router, prefix="/api/v1/vectors", tags=["vectors"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(fusion_chat_router)
app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "success": True,
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }
