# apps/backend/app/core/database.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """
    Initializes the MongoDB connection pool and Beanie ODM.
    """
    try:
        logger.info("Initializing connection to MongoDB Atlas Local...")
        client = AsyncIOMotorClient(settings.MONGODB_URL)

        # معرفی مدل‌ها به Beanie برای ساخت خودکار کالکشن‌ها و ایندکس‌ها
        await init_beanie(
            database=client.get_default_database(),
            document_models=[
                User,
            ]
        )
        logger.info("MongoDB and Beanie ODM successfully initialized.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        raise e
