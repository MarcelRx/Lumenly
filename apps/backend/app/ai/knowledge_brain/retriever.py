from typing import Callable, Awaitable, List, Dict
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


class KnowledgeRetriever:
    """Handles retrieval of knowledge from the knowledge base."""

    def __init__(
        self, qdrant_client: AsyncQdrantClient, embed_func: Callable[[str], Awaitable[list[float]]]
    ):
        """
        Initialize the KnowledgeRetriever.

        Args:
            qdrant_client: AsyncQdrantClient instance
            embed_func: Async function that takes text and returns embedding vector
        """
        self.qdrant_client = qdrant_client
        self.embed_func = embed_func
        self.collection_name = "knowledge_base"

    async def search_knowledge(self, user_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search the knowledge base for relevant chunks.

        Args:
            user_id: User identifier to filter results
            query: Search query text
            top_k: Number of top results to return

        Returns:
            List of dictionaries containing document_title and chunk_text
        """
        # Embed the query
        query_embedding = await self.embed_func(query)

        # Create filter for user_id
        query_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])

        # Search Qdrant using query_points (compatible with qdrant-client >= 1.16.0)
        response = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        # Extract points from the query response
        search_results = response.points

        # Format results
        results = []
        for result in search_results:
            payload = result.payload or {}
            results.append(
                {
                    "document_title": payload.get("document_title", ""),
                    "chunk_text": payload.get("chunk_text", ""),
                    "score": result.score,
                }
            )

        return results
