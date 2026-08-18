import uuid
from typing import Awaitable, Callable

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from .chunker import DocumentChunker


class KnowledgeIngestor:
    """Handles ingestion of documents into the knowledge base."""

    def __init__(self, qdrant_client: AsyncQdrantClient, embed_func: Callable[[str], Awaitable[list[float]]]):
        """
        Initialize the KnowledgeIngestor.

        Args:
            qdrant_client: Async Qdrant client instance
            embed_func: Async function that takes text and returns embedding vector
        """
        self.qdrant_client = qdrant_client
        self.embed_func = embed_func
        self.collection_name = "knowledge_base"
        self.vector_size = settings.VECTOR_DIMENSION

        # Ensure collection exists will be called lazily when needed
        # to avoid async issues in __init__

    async def _ensure_collection_exists(self) -> None:
        """Create the knowledge_base collection if it doesn't exist."""
        collections_result = await self.qdrant_client.get_collections()
        collections = collections_result.collections
        collection_names = [col.name for col in collections]

        if self.collection_name not in collection_names:
            # FIX: Added 'await' here
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=getattr(Distance, settings.DISTANCE_METRIC.upper(), Distance.COSINE)
                )
            )

    async def process_and_store_document(
        self,
        user_id: str,
        document_title: str,
        text: str
    ) -> None:
        """
        Process a document and store its chunks in the knowledge base.

        Args:
            user_id: User identifier for the document
            document_title: Title of the document
            text: Full text content of the document
        """
        # Ensure collection exists
        await self._ensure_collection_exists()

        # Chunk the text
        chunks = DocumentChunker.chunk_text(text)

        # Prepare points for upsert
        points = []

        for i, chunk in enumerate(chunks):
            # Embed the chunk
            embedding = await self.embed_func(chunk)

            # Create point with UUID
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "document_title": document_title,
                    "chunk_text": chunk,
                    "chunk_index": i
                }
            )
            points.append(point)

        # Upsert all points
        if points:
            # FIX: Added 'await' here
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
