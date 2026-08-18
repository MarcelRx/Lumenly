# apps/backend/app/db/redis.py
import logging
from typing import Optional

from redis.asyncio import ConnectionPool
from redis.asyncio import Redis as AsyncRedis

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Optional[AsyncRedis] = None
_redis_pool: Optional[ConnectionPool] = None


async def init_redis() -> bool:
    """
    Initialize the async Redis client and verify connectivity.
    Returns True on success; logs a warning and returns False if unreachable.
    """
    global redis_client, _redis_pool

    try:
        logger.info("Initializing connection to Redis at %s...", settings.REDIS_URL)
        _redis_pool = ConnectionPool.from_url(settings.REDIS_URL)
        redis_client = AsyncRedis(connection_pool=_redis_pool)

        # Test connection
        await redis_client.ping()

        logger.info("Redis successfully initialized")
        return True
    except Exception as exc:
        logger.warning(
            "Failed to connect to Redis at %s — %s. "
            "Short-term memory features will be unavailable until Redis is reachable.",
            settings.REDIS_URL,
            exc,
        )
        redis_client = None
        _redis_pool = None
        return False


async def close_redis() -> None:
    """Close the Redis client connection on application shutdown."""
    global redis_client, _redis_pool

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis client connection closed.")

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


def get_redis_client() -> AsyncRedis:
    """Return the initialized Redis client for use in services and endpoints."""
    if redis_client is None:
        raise RuntimeError(
            "Redis client is not initialized or the connection failed at startup."
        )
    return redis_client
