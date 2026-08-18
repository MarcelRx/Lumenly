# apps/backend/app/db/qdrant.py
import logging
from typing import Optional

from qdrant_client import AsyncQdrantClient

from app.core.config import settings

logger = logging.getLogger(__name__)

qdrant_client: Optional[AsyncQdrantClient] = None


async def init_qdrant() -> bool:
    """
    Initialize the async Qdrant client and verify connectivity.
    Returns True on success; logs a warning and returns False if unreachable.
    """
    global qdrant_client

    try:
        logger.info(
            "Initializing connection to Qdrant at %s:%s...",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
        )
        protocol = "https" if settings.QDRANT_USE_HTTPS else "http"
        client = AsyncQdrantClient(
            url=f"{protocol}://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            api_key=settings.QDRANT_API_KEY or None,
        )
        await client.get_collections()
        qdrant_client = client
        logger.info("Qdrant Vector Database successfully initialized")
        return True
    except Exception as exc:
        logger.warning(
            "Failed to connect to Qdrant at %s:%s — %s. "
            "Vector search features will be unavailable until Qdrant is reachable.",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
            exc,
        )
        qdrant_client = None
        return False


async def close_qdrant() -> None:
    """Close the Qdrant client connection on application shutdown."""
    global qdrant_client

    if qdrant_client is not None:
        await qdrant_client.close()
        qdrant_client = None
        logger.info("Qdrant client connection closed.")


def get_qdrant_client() -> AsyncQdrantClient:
    """Return the initialized Qdrant client for use in services and endpoints."""
    if qdrant_client is None:
        raise RuntimeError(
            "Qdrant client is not initialized or the connection failed at startup."
        )
    return qdrant_client
