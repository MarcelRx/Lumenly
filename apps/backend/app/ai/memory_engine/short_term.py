# apps/backend/app/ai/memory_engine/short_term.py
import json
import logging

from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Manages short-term conversation history stored in Redis."""

    def __init__(self, redis_client: AsyncRedis):
        self.redis = redis_client

    async def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        limit: int = 20
    ) -> None:
        """
        Pushes a message to the user's chat history in Redis.

        Args:
            user_id: Unique identifier for the user
            role: Message role (e.g., "user", "assistant")
            content: Message content
            limit: Maximum number of messages to keep (default: 20)
        """
        key = f"chat_history:{user_id}"
        message = {"role": role, "content": content}

        try:
            # Push message to the list
            await self.redis.rpush(key, json.dumps(message))

            # Trim list to keep only the last `limit` items
            await self.redis.ltrim(key, -limit, -1)

            # Set TTL to 24 hours (86400 seconds)
            await self.redis.expire(key, 86400)

            logger.debug(f"Added message for user {user_id}, role: {role}")
        except Exception as e:
            logger.error(f"Failed to add message for user {user_id}: {e}")
            raise

    async def get_history(self, user_id: str) -> list[dict]:
        """
        Retrieves and parses the chat history for a user from Redis.

        Args:
            user_id: Unique identifier for the user

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        key = f"chat_history:{user_id}"

        try:
            # Retrieve all messages from the list
            messages = await self.redis.lrange(key, 0, -1)

            # Parse JSON strings into dictionaries
            history = []
            for msg in messages:
                try:
                    parsed = json.loads(msg)
                    if isinstance(parsed, dict):
                        history.append(parsed)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message for user {user_id}")
                    continue

            logger.debug(f"Retrieved {len(history)} messages for user {user_id}")
            return history

        except Exception as e:
            logger.error(f"Failed to retrieve history for user {user_id}: {e}")
            return []
