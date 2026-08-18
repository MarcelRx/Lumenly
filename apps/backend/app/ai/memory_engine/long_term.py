# apps/backend/app/ai/memory_engine/long_term.py
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

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_long_term_memory"
# Standard dimension from configuration
DEFAULT_VECTOR_SIZE = settings.VECTOR_DIMENSION


class LongTermMemory:
    """Manages long-term memory using Qdrant vector database."""

    def __init__(self, qdrant_client: AsyncQdrantClient, vector_size: int = DEFAULT_VECTOR_SIZE):
        self.qdrant = qdrant_client
        self.vector_size = vector_size
        self.collection_name = COLLECTION_NAME
        logger.info(f"Initialized LongTermMemory with vector size: {self.vector_size}")

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
                        distance=getattr(Distance, settings.DISTANCE_METRIC.upper(), Distance.COSINE)
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully with dimension {self.vector_size}")
            else:
                # Optionally check existing collection info to verify dimensions match
                # This helps prevent silent mismatches if the file is changed but collection persists
                collection_info = await self.qdrant.get_collection(collection_name=self.collection_name)
                # The config path can vary by qdrant version, this is basic check
                try:
                    current_dim = collection_info.config.params.vectors.size
                    if current_dim != self.vector_size:
                        logger.error(
                            f"DIMENSION MISMATCH DETECTED for {self.collection_name}! "
                            f"Code expects {self.vector_size}, but Qdrant has {current_dim}. "
                            f"PLEASE DELETE THE COLLECTION manually."
                        )
                except AttributeError:
                    # In some qdrant client versions access might be different
                    pass

        except Exception as e:
            logger.error(f"Failed to ensure collection exists for {self.collection_name}: {e}")
            raise

    async def save_memory(
        self,
        user_id: str,
        text: str,
        vector: list[float],
        category: str = "general"
    ) -> None:
        """Upserts a vector with payload to Qdrant."""
        await self._ensure_collection_exists()

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
        """Searches Qdrant for relevant memories, filtered by user_id."""
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
            # If the backend terminal shows the 400 error again, it means the old collection persists
            return []
