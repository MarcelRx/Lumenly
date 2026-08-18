# apps/backend/app/ai/memory/consolidation.py
"""
Memory Consolidation - Memory merging and summarization implementation.

This module implements background consolidation operations:
- Merge similar memories
- Create summarized memories
- Keep original references
- No information loss
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.ai.memory.interfaces import (
    IMemoryConsolidator,
    IMemoryStorage,
    IMemorySummarizer,
    MemoryConsolidationResult,
    MemoryImportance,
    MemoryMetadata,
    MemoryRecord,
    MemoryType,
)
from app.ai.memory.summary import MemorySummarizer
from app.db.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)


class MemoryConsolidator(IMemoryConsolidator):
    """
    Memory consolidation implementation.

    Performs background consolidation operations:
    - Similarity-based memory merging
    - Summarization of related memories
    - Archiving of consolidated memories
    - Reference tracking for consolidation lineage
    """

    def __init__(
        self,
        storage: IMemoryStorage,
        summarizer: Optional[IMemorySummarizer] = None,
        similarity_threshold: float = 0.85,
    ):
        """
        Initialize the memory consolidator.

        Args:
            storage: Memory storage implementation
            summarizer: Optional memory summarizer
            similarity_threshold: Threshold for considering memories similar (0-1)
        """
        self.storage = storage
        self.summarizer = summarizer or MemorySummarizer()
        self.similarity_threshold = similarity_threshold
        self.qdrant_client = None

        logger.info(
            f"Initialized MemoryConsolidator with similarity_threshold={similarity_threshold}"
        )

    def _get_qdrant(self):
        """Lazy load Qdrant client."""
        if self.qdrant_client is None:
            self.qdrant_client = get_qdrant_client()
        return self.qdrant_client

    async def consolidate_similar(
        self,
        user_id: str,
        memory_type: MemoryType,
        similarity_threshold: Optional[float] = None
    ) -> List[MemoryConsolidationResult]:
        """
        Consolidate similar memories of a given type.

        Finds semantically similar memories and merges them:
        1. Retrieve memories of the given type
        2. Calculate pairwise similarity
        3. Group similar memories
        4. Create consolidated memories
        5. Archive original memories

        Args:
            user_id: User ID for multi-tenant isolation
            memory_type: Type of memories to consolidate
            similarity_threshold: Override default similarity threshold

        Returns:
            List of consolidation results
        """
        threshold = similarity_threshold or self.similarity_threshold
        results = []

        try:
            # Retrieve memories of the given type
            memories = await self.storage.list_user_memories(
                user_id=user_id,
                memory_type=memory_type,
                limit=1000,  # Large limit for consolidation
                offset=0
            )

            if len(memories) < 2:
                logger.debug(f"Not enough memories to consolidate for user {user_id}")
                return results

            # Group similar memories
            similarity_groups = await self._group_similar_memories(memories, threshold)

            logger.info(
                f"Found {len(similarity_groups)} similarity groups for "
                f"{memory_type.value} memories of user {user_id}"
            )

            # Consolidate each group
            for group in similarity_groups:
                if len(group) > 1:  # Only consolidate groups with multiple memories
                    result = await self._consolidate_group(
                        user_id=user_id,
                        memories=group,
                        strategy="similarity_merge"
                    )
                    if result:
                        results.append(result)

            logger.info(
                f"Consolidated {len(results)} memory groups for user {user_id}"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to consolidate memories for user {user_id}: {e}")
            return results

    async def _group_similar_memories(
        self,
        memories: List[MemoryRecord],
        threshold: float
    ) -> List[List[MemoryRecord]]:
        """
        Group memories by semantic similarity using optimized clustering.

        Uses a scalable clustering approach:
        1. Sort memories by time for locality
        2. Use sliding window for similarity comparison
        3. Only compare nearby memories to reduce complexity
        4. Early termination when similarity drops below threshold
        """
        if not memories:
            return []

        # Sort by creation time for temporal locality
        sorted_memories = sorted(memories, key=lambda m: m.created_at, reverse=True)

        groups = []
        processed = set()
        window_size = 50  # Only compare within a window of 50 memories

        for i, memory in enumerate(sorted_memories):
            if memory.id in processed:
                continue

            group = [memory]
            processed.add(memory.id)

            # Only check memories within the window (O(n * window_size) instead of O(n²))
            window_end = min(i + window_size, len(sorted_memories))

            for j in range(i + 1, window_end):
                other_memory = sorted_memories[j]

                if other_memory.id in processed:
                    continue

                # Check semantic similarity if embeddings exist
                similarity = 0.0
                if memory.embedding_vector and other_memory.embedding_vector:
                    similarity = await self._calculate_cosine_similarity(
                        memory.embedding_vector,
                        other_memory.embedding_vector
                    )

                # If similar enough, add to group
                if similarity >= threshold:
                    group.append(other_memory)
                    processed.add(other_memory.id)
                else:
                    # Early termination if similarity drops below threshold
                    # (since memories are sorted by time, later ones are less likely to be similar)
                    if similarity < threshold * 0.5:  # Allow some tolerance
                        break

            if len(group) > 1:
                groups.append(group)

        return groups

    async def _calculate_cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        cosine_sim = dot_product / (magnitude1 * magnitude2)
        return (cosine_sim + 1) / 2  # Normalize to [0, 1]

    async def _consolidate_group(
        self,
        user_id: str,
        memories: List[MemoryRecord],
        strategy: str
    ) -> Optional[MemoryConsolidationResult]:
        """
        Consolidate a group of memories.

        Creates a consolidated memory from a group of similar memories.
        """
        try:
            # Generate summary of the group
            summary = await self.summarizer.summarize_memories_batch(memories)

            if not summary:
                logger.warning("Failed to generate summary for memory group")
                return None

            # Determine consolidated memory type
            memory_type = memories[0].memory_type

            # Determine importance (max of group)
            importance_scores = {
                MemoryImportance.CRITICAL: 5,
                MemoryImportance.HIGH: 4,
                MemoryImportance.MEDIUM: 3,
                MemoryImportance.LOW: 2,
                MemoryImportance.TEMPORARY: 1,
            }
            max_importance = max(
                memories,
                key=lambda m: importance_scores.get(m.metadata.importance, 0)
            )

            # Create consolidated memory
            consolidated_id = str(uuid.uuid4())
            metadata = MemoryMetadata(
                user_id=user_id,
                memory_type=memory_type,
                importance=max_importance.metadata.importance,
                source="system_consolidated",
                tags=list(set(
                    tag for mem in memories for tag in mem.metadata.tags
                )),
                related_memories=[m.id for m in memories],
                confidence=sum(m.metadata.confidence for m in memories) / len(memories),
            )

            # Combine embeddings (average)
            consolidated_embedding = None
            if all(m.embedding_vector for m in memories):
                vectors = [m.embedding_vector for m in memories]
                consolidated_embedding = [
                    sum(v[i] for v in vectors) / len(vectors)
                    for i in range(len(vectors[0]))
                ]

            consolidated_memory = MemoryRecord(
                id=consolidated_id,
                user_id=user_id,
                memory_type=memory_type,
                content=summary,
                metadata=metadata,
                embedding_vector=consolidated_embedding,
                created_at=datetime.now(timezone.utc),
            )

            # Store consolidated memory
            await self.storage.store(consolidated_memory)

            # Archive original memories
            for memory in memories:
                await self.storage.update(
                    memory_id=memory.id,
                    user_id=user_id,
                    updates={
                        "consolidated_into": consolidated_id,
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            result = MemoryConsolidationResult(
                consolidated_memory=consolidated_memory,
                source_memory_ids=[m.id for m in memories],
                consolidation_strategy=strategy,
                timestamp=datetime.now(timezone.utc),
            )

            logger.info(
                f"Consolidated {len(memories)} memories into {consolidated_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to consolidate memory group: {e}")
            return None

    async def summarize_memories(
        self,
        memory_ids: List[str],
        user_id: str
    ) -> Optional[MemoryRecord]:
        """
        Create a summary memory from multiple memories.

        Creates a high-level summary that captures the essence of
        multiple related memories without losing key information.
        """
        try:
            # Retrieve the memories
            memories = []
            for memory_id in memory_ids:
                memory = await self.storage.retrieve(memory_id, user_id)
                if memory:
                    memories.append(memory)

            if not memories:
                logger.warning("No valid memories found for summarization")
                return None

            # Generate summary
            summary = await self.summarizer.summarize_memories_batch(memories)

            if not summary:
                return None

            # Create summary memory
            summary_id = str(uuid.uuid4())
            memory_type = MemoryType.EPISODIC  # Summaries become episodic memories

            metadata = MemoryMetadata(
                user_id=user_id,
                memory_type=memory_type,
                importance=MemoryImportance.HIGH,
                source="system_summary",
                tags=["summary", "consolidated"],
                related_memories=memory_ids,
                confidence=0.9,
            )

            summary_memory = MemoryRecord(
                id=summary_id,
                user_id=user_id,
                memory_type=memory_type,
                content=summary,
                metadata=metadata,
                created_at=datetime.now(timezone.utc),
            )

            # Store summary memory
            await self.storage.store(summary_memory)

            logger.info(
                f"Created summary memory {summary_id} from {len(memories)} memories"
            )
            return summary_memory

        except Exception as e:
            logger.error(f"Failed to summarize memories: {e}")
            return None

    async def merge_memories(
        self,
        memory_ids: List[str],
        user_id: str
    ) -> Optional[MemoryRecord]:
        """
        Merge multiple memories into a single comprehensive memory.

        Unlike summarization, merging preserves all important information
        while removing redundancy.
        """
        try:
            # Retrieve the memories
            memories = []
            for memory_id in memory_ids:
                memory = await self.storage.retrieve(memory_id, user_id)
                if memory:
                    memories.append(memory)

            if not memories:
                logger.warning("No valid memories found for merging")
                return None

            # Merge content (combine with deduplication)
            merged_content = await self._merge_content(memories)

            # Create merged memory
            merged_id = str(uuid.uuid4())
            memory_type = memories[0].memory_type

            # Use highest importance
            importance_scores = {
                MemoryImportance.CRITICAL: 5,
                MemoryImportance.HIGH: 4,
                MemoryImportance.MEDIUM: 3,
                MemoryImportance.LOW: 2,
                MemoryImportance.TEMPORARY: 1,
            }
            max_importance = max(
                memories,
                key=lambda m: importance_scores.get(m.metadata.importance, 0)
            )

            metadata = MemoryMetadata(
                user_id=user_id,
                memory_type=memory_type,
                importance=max_importance.metadata.importance,
                source="system_merged",
                tags=list(set(
                    tag for mem in memories for tag in mem.metadata.tags
                )),
                related_memories=memory_ids,
                confidence=sum(m.metadata.confidence for m in memories) / len(memories),
            )

            # Combine embeddings (average)
            merged_embedding = None
            if all(m.embedding_vector for m in memories):
                vectors = [m.embedding_vector for m in memories]
                merged_embedding = [
                    sum(v[i] for v in vectors) / len(vectors)
                    for i in range(len(vectors[0]))
                ]

            merged_memory = MemoryRecord(
                id=merged_id,
                user_id=user_id,
                memory_type=memory_type,
                content=merged_content,
                metadata=metadata,
                embedding_vector=merged_embedding,
                created_at=datetime.now(timezone.utc),
            )

            # Store merged memory
            await self.storage.store(merged_memory)

            # Archive original memories
            for memory in memories:
                await self.storage.update(
                    memory_id=memory.id,
                    user_id=user_id,
                    updates={
                        "merged_into": merged_id,
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            logger.info(
                f"Merged {len(memories)} memories into {merged_id}"
            )
            return merged_memory

        except Exception as e:
            logger.error(f"Failed to merge memories: {e}")
            return None

    async def _merge_content(self, memories: List[MemoryRecord]) -> str:
        """
        Merge content from multiple memories.

        Combines content while removing redundancy and preserving structure.
        """
        # Simple concatenation with deduplication
        seen_content = set()
        merged_parts = []

        for memory in memories:
            content = memory.content.strip()
            if content and content not in seen_content:
                seen_content.add(content)
                merged_parts.append(content)

        # Join with appropriate separators
        if len(merged_parts) == 1:
            return merged_parts[0]
        else:
            return "\n\n".join(merged_parts)

    async def cleanup_archived_memories(
        self,
        user_id: str,
        days_old: int = 30
    ) -> int:
        """
        Clean up archived memories older than specified days.

        Args:
            user_id: User ID for multi-tenant isolation
            days_old: Age threshold in days

        Returns:
            Number of memories cleaned up
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            # Get all memories for user
            memories = await self.storage.list_user_memories(
                user_id=user_id,
                limit=10000,
                offset=0
            )

            # Find archived memories older than threshold
            old_archived = []
            for memory in memories:
                # Check if memory is archived
                if hasattr(memory.metadata, 'archived') and memory.metadata.archived:
                    if memory.created_at < cutoff_date:
                        old_archived.append(memory.id)

            # Delete old archived memories
            deleted_count = 0
            for memory_id in old_archived:
                if await self.storage.delete(memory_id, user_id):
                    deleted_count += 1

            logger.info(
                f"Cleaned up {deleted_count} archived memories for user {user_id}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup archived memories: {e}")
            return 0
