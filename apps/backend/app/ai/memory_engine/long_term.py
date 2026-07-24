import logging
import uuid
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_long_term_memory"
DEFAULT_VECTOR_SIZE = 768  # Default for Gemini; can be 1536 for OpenAI


class LongTermMemory:
    """Manages long-term memory using Qdrant vector database."""

    def __init__(self, qdrant_client: AsyncQdrantClient, vector_size: int = DEFAULT_VECTOR_SIZE):
        self.qdrant = qdrant_client
        self.vector_size = vector_size
        self.collection_name = COLLECTION_NAME

    async def _ensure_collection_exists(self) -> None:
        """Ensures the collection exists, creating it if necessary."""
        try:
            collections = await self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection {self.collection_name} with vector size {self.vector_size}")
                await self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise

    async def save_memory(
        self,
        user_id: str,
        text: str,
        vector: list[float],
        category: str = "general"
    ) -> None:
        """
        Upserts a vector with payload to Qdrant.

        Args:
            user_id: Unique identifier for the user
            text: The text content to store
            vector: The vector embedding of the text
            category: Category for the memory (default: "general")
        """
        await self._ensure_collection_exists()

        # Generate a valid UUID v4 point ID required by Qdrant
        point_id = str(uuid.uuid4())

        try:
            await self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "user_id": user_id,
                            "text": text,
                            "category": category
                        }
                    )
                ]
            )
            logger.debug(f"Saved memory for user {user_id}, category: {category}")
        except Exception as e:
            logger.error(f"Failed to save memory for user {user_id}: {e}")
            raise

    async def retrieve_relevant(
        self,
        user_id: str,
        query_vector: list[float],
        top_k: int = 3
    ) -> list[str]:
        """
        Searches Qdrant for relevant memories, filtered by user_id.

        Args:
            user_id: Unique identifier for the user
            query_vector: The vector embedding of the query
            top_k: Number of results to return (default: 3)

        Returns:
            List of text strings from the most relevant memories
        """
        await self._ensure_collection_exists()

        try:
            filter_ = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

            search_result = await self.qdrant.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                query_filter=filter_,
                with_payload=True,
            )

            memories = []
            for point in search_result.points:
                payload = point.payload or {}
                text = payload.get("text")
                if isinstance(text, str) and text:
                    memories.append(text)

            logger.debug(f"Retrieved {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve memories for user {user_id}: {e}")
            return []
