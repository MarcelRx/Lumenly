# apps/backend/app/services/vector.py
import logging
from typing import Optional

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.db.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "lumenly_vectors"

def get_vector_dimension() -> int:
    """Get the current vector dimension from settings."""
    return settings.VECTOR_DIMENSION


class VectorService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None

    async def _get_client(self) -> AsyncQdrantClient:
        """Get the Qdrant client, initializing if needed."""
        # Always get a fresh client to avoid closed client issues
        return get_qdrant_client()

    async def ensure_collection(self) -> None:
        """
        Create the Qdrant collection if it doesn't exist.
        Uses configured dimension and distance metric from settings.
        """
        client = await self._get_client()

        try:
            collections = await client.get_collections()
            existing_collections = [c.name for c in collections.collections]

            if COLLECTION_NAME not in existing_collections:
                vector_dim = get_vector_dimension()
                logger.info(f"Creating collection '{COLLECTION_NAME}' with {vector_dim} dimensions")
                distance_metric = models.Distance.COSINE if settings.DISTANCE_METRIC == "Cosine" else (
                    models.Distance.EUCLID if settings.DISTANCE_METRIC == "Euclid" else models.Distance.DOT
                )
                await client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=vector_dim,
                        distance=distance_metric,
                    ),
                )
                logger.info(f"Collection '{COLLECTION_NAME}' created successfully")
            else:
                logger.info(f"Collection '{COLLECTION_NAME}' already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def upsert_vector(
        self,
        vector_id: str,
        embedding: list[float],
        payload: dict,
    ) -> None:
        """
        Upsert a vector to the Qdrant collection.

        Args:
            vector_id: Unique identifier for the vector
            embedding: Vector embedding with configured dimension
            payload: Must include user_id and document_id
        """
        client = await self._get_client()

        # Validate required payload fields
        if "user_id" not in payload or "document_id" not in payload:
            raise ValueError("Payload must include 'user_id' and 'document_id'")

        try:
            await client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=vector_id,
                        vector=embedding,
                        payload=payload,
                    ),
                ],
            )
            logger.info(f"Vector {vector_id} upserted successfully for user {payload['user_id']}")
        except Exception as e:
            logger.error(f"Failed to upsert vector {vector_id}: {e}")
            raise

    async def search_vectors(
        self,
        user_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[models.ScoredPoint]:
        """
        Search for similar vectors filtered by user_id.

        Args:
            user_id: Filter results to only this user's vectors
            query_embedding: Query vector for similarity search
            limit: Maximum number of results to return

        Returns:
            List of scored points matching the query
        """
        client = await self._get_client()

        try:
            results = await client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id),
                        ),
                    ],
                ),
                limit=limit,
            )
            logger.info(f"Found {len(results.points)} vectors for user {user_id}")
            return results.points
        except Exception as e:
            logger.error(f"Failed to search vectors for user {user_id}: {e}")
            raise


# Global service instance
vector_service = VectorService()
