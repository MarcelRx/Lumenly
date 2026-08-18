# apps/backend/app/db/mongo.py
import logging
from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.domain import (
    AIInsight,
    CoachingSession,
    ComplianceEvent,
    Goal,
    Habit,
    JournalEntry,
    UserDocument,
)

logger = logging.getLogger(__name__)

mongo_client: Optional[AsyncIOMotorClient] = None


async def init_mongo() -> None:
    """
    Initialize the MongoDB connection pool and Beanie ODM.
    """
    global mongo_client

    try:
        logger.info("Initializing connection to MongoDB...")
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)

        # Initialize Beanie with document models (User is now in PostgreSQL, not MongoDB)
        await init_beanie(
            database=mongo_client.get_default_database(),
            document_models=[
                JournalEntry,
                Goal,
                Habit,
                UserDocument,
                CoachingSession,
                AIInsight,
                ComplianceEvent,
            ],
        )
        logger.info("MongoDB and Beanie ODM successfully initialized.")
    except Exception as e:
        logger.critical(f"MongoDB initialization failed: {e}")
        raise e


async def close_mongo() -> None:
    """Close the MongoDB client connection on application shutdown."""
    global mongo_client

    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
        logger.info("MongoDB client connection closed.")


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the initialized MongoDB client for use in services and endpoints."""
    if mongo_client is None:
        raise RuntimeError(
            "MongoDB client is not initialized or the connection failed at startup."
        )
    return mongo_client
