# apps/backend/app/ai/memory/retriever.py
"""
Memory Retriever - Query pipeline and filtering implementation.

This module implements the memory retrieval pipeline:
Query → Embedding → Qdrant Search → Memory Ranking → Context Selection → LLM
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

from app.ai.embeddings.interface import EmbeddingProviderInterface
from app.ai.memory.interfaces import (
    IMemoryRanker,
    IMemoryRetriever,
    IMemoryStorage,
    MemoryRecord,
    MemoryRetrievalConfig,
    MemorySearchResult,
    MemoryType,
)
from app.db.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)


class MemoryRetriever(IMemoryRetriever):
    """
    Memory retrieval pipeline implementation.

    Implements the full retrieval pipeline:
    1. Query processing and embedding
    2. Vector search in Qdrant
    3. Memory ranking with multi-factor scoring
    4. Context selection and filtering
    5. LLM-ready context preparation
    """

    def __init__(
        self,
        storage: IMemoryStorage,
        ranker: IMemoryRanker,
        embedding_model: Optional[EmbeddingProviderInterface] = None,
    ):
        """
        Initialize the memory retriever.

        Args:
            storage: Memory storage implementation
            ranker: Memory ranking implementation
            embedding_model: Optional embedding model for semantic search
        """
        self.storage = storage
        self.ranker = ranker
        self.embedding_model = embedding_model
        self.qdrant_client = None

        logger.info("Initialized MemoryRetriever")

    def _get_qdrant(self):
        """Lazy load Qdrant client."""
        if self.qdrant_client is None:
            self.qdrant_client = get_qdrant_client()
        return self.qdrant_client

    async def search(
        self,
        user_id: str,
        query: str,
        config: MemoryRetrievalConfig
    ) -> List[MemorySearchResult]:
        """
        Search for memories based on a query.

        Implements the full retrieval pipeline:
        1. Generate query embedding if semantic search enabled
        2. Search Qdrant for similar memories
        3. Apply filters (type, date, importance, source)
        4. Rank results with multi-factor scoring
        5. Return top-k results

        Args:
            user_id: User ID for multi-tenant isolation
            query: Search query string
            config: Retrieval configuration

        Returns:
            List of ranked memory search results
        """
        try:
            # Step 1: Generate query embedding if semantic search enabled
            query_vector = None
            if config.enable_semantic_search and self.embedding_model:
                try:
                    query_vector = await self.embedding_model.embed_text(query)
                    logger.debug(f"Generated query embedding for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate query embedding: {e}")

            # Step 2: Search memories from storage
            memories = await self._search_memories(
                user_id=user_id,
                query=query,
                query_vector=query_vector,
                config=config
            )

            if not memories:
                logger.debug(f"No memories found for user {user_id} with query: {query}")
                return []

            # Step 3: Apply ranking if enabled
            if config.enable_ranking:
                ranked_results = await self.ranker.rank(
                    memories=memories,
                    query=query,
                    query_vector=query_vector
                )

                # Filter by minimum score
                ranked_results = [
                    r for r in ranked_results
                    if r.score >= config.min_score
                ]

                # Limit to max results
                ranked_results = ranked_results[:config.max_results]

                logger.debug(
                    f"Ranked {len(ranked_results)} memories for user {user_id}, "
                    f"top score: {ranked_results[0].score if ranked_results else 0:.3f}"
                )

                return ranked_results
            else:
                # Return unranked results with default scores
                return [
                    MemorySearchResult(
                        memory=mem,
                        score=1.0,
                        rank=idx + 1,
                        relevance_factors={}
                    )
                    for idx, mem in enumerate(memories[:config.max_results])
                ]

        except Exception as e:
            logger.error(f"Failed to search memories for user {user_id}: {e}")
            return []

    async def _search_memories(
        self,
        user_id: str,
        query: str,
        query_vector: Optional[List[float]],
        config: MemoryRetrievalConfig
    ) -> List[MemoryRecord]:
        """
        Search memories from storage with filters.

        Handles both vector search (Qdrant) and metadata-based search.
        """
        memories = []

        # If we have a query vector, perform semantic search in Qdrant
        if query_vector and config.enable_semantic_search:
            memories.extend(await self._semantic_search(user_id, query_vector, config))

        # Always perform metadata-based search as fallback/complement
        memories.extend(await self._metadata_search(user_id, query, config))

        # Remove duplicates
        seen_ids = set()
        unique_memories = []
        for mem in memories:
            if mem.id not in seen_ids:
                seen_ids.add(mem.id)
                unique_memories.append(mem)

        return unique_memories

    async def _semantic_search(
        self,
        user_id: str,
        query_vector: List[float],
        config: MemoryRetrievalConfig
    ) -> List[MemoryRecord]:
        """
        Perform semantic search using Qdrant vector database.
        """
        memories = []
        qdrant = self._get_qdrant()

        # Build Qdrant filter
        filter_conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]

        # Add memory type filter
        if config.memory_types:
            type_values = [t.value for t in config.memory_types]
            filter_conditions.append(
                FieldCondition(key="memory_type", match=MatchAny(any=type_values))
            )

        # Add importance filter
        if config.importance_filter:
            importance_values = [i.value for i in config.importance_filter]
            filter_conditions.append(
                FieldCondition(key="importance", match=MatchAny(any=importance_values))
            )

        # Add source filter
        if config.source_filter:
            filter_conditions.append(
                FieldCondition(key="source", match=MatchAny(any=config.source_filter))
            )

        query_filter = Filter(must=filter_conditions)

        # Search across all memory collections
        collections = [
            "medium_term_journal_entries",
            "medium_term_goals",
            "medium_term_habits",
            "long_term_preference",
            "long_term_behavioral",
            "long_term_knowledge",
            "long_term_episodic",
        ]

        for collection_name in collections:
            try:
                search_result = await qdrant.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=config.max_results,
                    query_filter=query_filter,
                    with_payload=True,
                    with_vectors=True,
                )

                for point in search_result.points:
                    payload = point.payload or {}

                    # Apply date range filter
                    if config.date_range:
                        created_at = datetime.fromisoformat(payload.get("created_at", ""))
                        if not (config.date_range[0] <= created_at <= config.date_range[1]):
                            continue

                    # Convert to MemoryRecord
                    memory = self._qdrant_point_to_memory(point)
                    if memory:
                        memories.append(memory)

            except Exception as e:
                logger.debug(f"Collection {collection_name} not available or error: {e}")
                continue

        logger.debug(f"Semantic search found {len(memories)} memories for user {user_id}")
        return memories

    async def _metadata_search(
        self,
        user_id: str,
        query: str,
        config: MemoryRetrievalConfig
    ) -> List[MemoryRecord]:
        """
        Perform metadata-based search using storage.
        """
        # Get memories from storage with type filter
        memory_type = config.memory_types[0] if config.memory_types and len(config.memory_types) == 1 else None

        memories = await self.storage.list_user_memories(
            user_id=user_id,
            memory_type=memory_type,
            limit=config.max_results,
            offset=0
        )

        # Apply additional filters
        filtered_memories = []
        for memory in memories:
            # Apply type filter if multiple types specified
            if config.memory_types and memory.memory_type not in config.memory_types:
                continue

            # Apply importance filter
            if config.importance_filter and memory.metadata.importance not in config.importance_filter:
                continue

            # Apply source filter
            if config.source_filter and memory.metadata.source not in config.source_filter:
                continue

            # Apply date range filter
            if config.date_range:
                if not (config.date_range[0] <= memory.created_at <= config.date_range[1]):
                    continue

            # Apply simple text matching to query
            if query and query.lower() not in memory.content.lower():
                # Also check tags
                tag_match = any(
                    query.lower() in tag.lower()
                    for tag in memory.metadata.tags
                )
                if not tag_match:
                    continue

            filtered_memories.append(memory)

        logger.debug(f"Metadata search found {len(filtered_memories)} memories for user {user_id}")
        return filtered_memories

    def _qdrant_point_to_memory(self, point) -> Optional[MemoryRecord]:
        """Convert Qdrant point to MemoryRecord."""
        try:
            from app.ai.memory.schema import MemoryImportance, MemoryMetadata, MemoryType

            payload = point.payload or {}

            memory_type = MemoryType(payload.get("memory_type", "knowledge"))
            importance = MemoryImportance(payload.get("importance", "medium"))

            metadata = MemoryMetadata(
                user_id=payload.get("user_id", ""),
                memory_type=memory_type,
                importance=importance,
                source=payload.get("source"),
                tags=payload.get("tags", []),
                access_count=payload.get("access_count", 0),
                created_at=datetime.fromisoformat(payload.get("created_at", datetime.now(timezone.utc).isoformat())),
            )

            return MemoryRecord(
                id=payload.get("memory_id", ""),
                user_id=payload.get("user_id", ""),
                memory_type=memory_type,
                content=payload.get("content", ""),
                metadata=metadata,
                embedding_vector=point.vector,
                created_at=metadata.created_at,
            )

        except Exception as e:
            logger.error(f"Failed to convert Qdrant point to MemoryRecord: {e}")
            return None

    async def retrieve_by_id(
        self,
        memory_id: str,
        user_id: str
    ) -> Optional[MemoryRecord]:
        """
        Retrieve a specific memory by ID.

        Ensures multi-tenant isolation by verifying user_id.
        """
        try:
            memory = await self.storage.retrieve(memory_id, user_id)

            if memory and memory.user_id != user_id:
                logger.warning(
                    f"Security violation: User {user_id} attempted to access "
                    f"memory {memory_id} owned by {memory.user_id}"
                )
                return None

            # Update access count
            if memory:
                await self.storage.update(
                    memory_id=memory_id,
                    user_id=user_id,
                    updates={
                        "access_count": memory.metadata.access_count + 1,
                        "last_accessed": datetime.now(timezone.utc).isoformat(),
                    }
                )

            return memory

        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def retrieve_recent(
        self,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryRecord]:
        """
        Retrieve recent memories for a user.

        Returns most recently created memories, optionally filtered by type.
        """
        try:
            memories = await self.storage.list_user_memories(
                user_id=user_id,
                memory_type=memory_type,
                limit=limit * 2,  # Get more to allow for filtering
                offset=0
            )

            # Sort by creation time descending
            memories.sort(key=lambda m: m.created_at, reverse=True)

            # Limit to requested number
            recent_memories = memories[:limit]

            logger.debug(f"Retrieved {len(recent_memories)} recent memories for user {user_id}")
            return recent_memories

        except Exception as e:
            logger.error(f"Failed to retrieve recent memories for user {user_id}: {e}")
            return []

    async def retrieve_by_type(
        self,
        user_id: str,
        memory_type: MemoryType,
        limit: int = 100
    ) -> List[MemoryRecord]:
        """
        Retrieve memories of a specific type.

        Returns all memories of the given type for a user.
        """
        try:
            memories = await self.storage.list_user_memories(
                user_id=user_id,
                memory_type=memory_type,
                limit=limit,
                offset=0
            )

            logger.debug(
                f"Retrieved {len(memories)} {memory_type.value} memories "
                f"for user {user_id}"
            )
            return memories

        except Exception as e:
            logger.error(
                f"Failed to retrieve {memory_type.value} memories "
                f"for user {user_id}: {e}"
            )
            return []

    async def build_context(
        self,
        user_id: str,
        query: str,
        max_memories: int = 5
    ) -> Dict[str, Any]:
        """
        Build LLM context from retrieved memories.

        Formats retrieved memories into a context structure suitable for LLM prompts.
        """
        config = MemoryRetrievalConfig(
            max_results=max_memories,
            enable_ranking=True,
            enable_semantic_search=True,
        )

        search_results = await self.search(user_id, query, config)

        # Format memories for LLM context
        formatted_memories = []
        for result in search_results:
            memory = result.memory
            formatted_memories.append({
                "type": memory.memory_type.value,
                "content": memory.content,
                "importance": memory.metadata.importance.value,
                "relevance_score": result.score,
                "created_at": memory.created_at.isoformat(),
            })

        context = {
            "query": query,
            "memory_count": len(formatted_memories),
            "memories": formatted_memories,
            "total_relevance": sum(r.score for r in search_results),
        }

        logger.debug(f"Built context with {len(formatted_memories)} memories for user {user_id}")
        return context
