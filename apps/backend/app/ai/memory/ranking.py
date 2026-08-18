# apps/backend/app/ai/memory/ranking.py
"""
Memory Ranking - Multi-factor memory ranking implementation.

This module implements ranking algorithms based on:
- Importance score (based on memory importance level)
- Recency score (how recently the memory was created/accessed)
- Frequency score (how often the memory is accessed)
- Semantic similarity (vector similarity to query)
- User relevance (custom user-specific factors)
"""
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.ai.memory.interfaces import (
    IMemoryRanker,
    MemoryImportance,
    MemoryRecord,
    MemorySearchResult,
)

logger = logging.getLogger(__name__)


class MemoryRanker(IMemoryRanker):
    """
    Multi-factor memory ranking implementation.

    Combines multiple scoring factors to rank memories by relevance:
    - Importance: Weighted by memory importance level
    - Recency: Time-decay function based on creation/access time
    - Frequency: Access frequency tracking
    - Semantic: Vector similarity when available
    - User Relevance: Future extensibility for reinforcement learning
    """

    # Scoring weights (configurable)
    IMPORTANCE_WEIGHT = 0.25
    RECENCY_WEIGHT = 0.20
    FREQUENCY_WEIGHT = 0.15
    SEMANTIC_WEIGHT = 0.30
    USER_RELEVANCE_WEIGHT = 0.10

    # Importance score mappings
    IMPORTANCE_SCORES = {
        MemoryImportance.CRITICAL: 1.0,
        MemoryImportance.HIGH: 0.8,
        MemoryImportance.MEDIUM: 0.6,
        MemoryImportance.LOW: 0.4,
        MemoryImportance.TEMPORARY: 0.2,
    }

    # Time decay constants
    RECENCY_HALF_LIFE_DAYS = 30  # Half-life for recency scoring
    FREQUENCY_DECAY_DAYS = 7    # Decay for frequency scoring

    def __init__(
        self,
        importance_weight: float = IMPORTANCE_WEIGHT,
        recency_weight: float = RECENCY_WEIGHT,
        frequency_weight: float = FREQUENCY_WEIGHT,
        semantic_weight: float = SEMANTIC_WEIGHT,
        user_relevance_weight: float = USER_RELEVANCE_WEIGHT,
    ):
        """
        Initialize the memory ranker with custom weights.

        Args:
            importance_weight: Weight for importance scoring (0-1)
            recency_weight: Weight for recency scoring (0-1)
            frequency_weight: Weight for frequency scoring (0-1)
            semantic_weight: Weight for semantic similarity (0-1)
            user_relevance_weight: Weight for user relevance (0-1)
        """
        # Normalize weights to sum to 1
        total_weight = (
            importance_weight + recency_weight + frequency_weight +
            semantic_weight + user_relevance_weight
        )

        self.importance_weight = importance_weight / total_weight
        self.recency_weight = recency_weight / total_weight
        self.frequency_weight = frequency_weight / total_weight
        self.semantic_weight = semantic_weight / total_weight
        self.user_relevance_weight = user_relevance_weight / total_weight

        logger.info(
            f"Initialized MemoryRanker with weights: "
            f"importance={self.importance_weight:.2f}, "
            f"recency={self.recency_weight:.2f}, "
            f"frequency={self.frequency_weight:.2f}, "
            f"semantic={self.semantic_weight:.2f}, "
            f"user_relevance={self.user_relevance_weight:.2f}"
        )

    async def rank(
        self,
        memories: List[MemoryRecord],
        query: str,
        query_vector: Optional[List[float]] = None
    ) -> List[MemorySearchResult]:
        """
        Rank memories based on relevance to the query.

        Args:
            memories: List of memories to rank
            query: Search query string
            query_vector: Optional query embedding vector for semantic search

        Returns:
            List of MemorySearchResult with ranking information
        """
        if not memories:
            return []

        scored_memories = []

        # Pre-calculate query-related values to avoid repeated calculations
        query_has_vector = query_vector is not None

        for memory in memories:
            try:
                # Calculate individual scores (optimized to reduce overhead)
                importance_score = self._calculate_importance_score_sync(memory)
                recency_score = self._calculate_recency_score_sync(memory)
                frequency_score = self._calculate_frequency_score_sync(memory)

                # Calculate semantic similarity if query vector is available
                semantic_score = 0.0
                if query_has_vector and memory.embedding_vector:
                    semantic_score = self._calculate_semantic_similarity_sync(
                        memory, query_vector
                    )
                elif query_has_vector:
                    # If memory has no embedding but query does, use default low score
                    semantic_score = 0.1

                # User relevance score (placeholder for future reinforcement learning)
                user_relevance_score = self._calculate_user_relevance_score_sync(memory, query)

                # Calculate weighted composite score (optimized multiplication)
                composite_score = (
                    self.importance_weight * importance_score +
                    self.recency_weight * recency_score +
                    self.frequency_weight * frequency_score +
                    self.semantic_weight * semantic_score +
                    self.user_relevance_weight * user_relevance_score
                )

                # Create search result with relevance factors
                relevance_factors = {
                    "importance": importance_score,
                    "recency": recency_score,
                    "frequency": frequency_score,
                    "semantic": semantic_score,
                    "user_relevance": user_relevance_score,
                }

                scored_memories.append(
                    MemorySearchResult(
                        memory=memory,
                        score=composite_score,
                        rank=0,  # Will be assigned after sorting
                        relevance_factors=relevance_factors
                    )
                )

            except Exception as e:
                logger.error(f"Failed to rank memory {memory.id}: {e}")
                continue

        # Sort by score descending
        scored_memories.sort(key=lambda x: x.score, reverse=True)

        # Assign ranks
        for idx, result in enumerate(scored_memories):
            result.rank = idx + 1

        logger.debug(f"Ranked {len(scored_memories)} memories")
        return scored_memories

    def _calculate_importance_score_sync(self, memory: MemoryRecord) -> float:
        """
        Synchronous version of importance score calculation for performance.
        """
        base_score = self.IMPORTANCE_SCORES.get(
            memory.metadata.importance,
            self.IMPORTANCE_SCORES[MemoryImportance.MEDIUM]
        )

        # Boost for high access count (diminishing returns)
        access_boost = min(math.log(memory.metadata.access_count + 1) / 10, 0.2)

        # Boost for recent updates
        update_boost = 0.0
        if memory.metadata.updated_at:
            days_since_update = (datetime.now(timezone.utc) - memory.metadata.updated_at).days
            update_boost = max(0, 0.1 - (days_since_update / 365))  # Decay over a year

        # Combine scores
        importance_score = min(base_score + access_boost + update_boost, 1.0)

        logger.debug(f"Importance score for {memory.id}: {importance_score:.3f}")
        return importance_score

    def _calculate_recency_score_sync(self, memory: MemoryRecord) -> float:
        """
        Synchronous version of recency score calculation for performance.
        """
        # Use last_accessed if available, otherwise created_at
        reference_time = memory.metadata.last_accessed or memory.created_at
        days_ago = (datetime.now(timezone.utc) - reference_time).days

        # Exponential decay: score = 0.5^(days / half_life)
        recency_score = math.pow(0.5, days_ago / self.RECENCY_HALF_LIFE_DAYS)

        logger.debug(f"Recency score for {memory.id}: {recency_score:.3f}")
        return recency_score

    def _calculate_frequency_score_sync(self, memory: MemoryRecord) -> float:
        """
        Synchronous version of frequency score calculation for performance.
        """
        # Calculate access frequency score
        access_count = memory.metadata.access_count

        # Use logarithmic scaling to prevent unlimited growth
        frequency_score = min(math.log(access_count + 1) / math.log(100), 1.0)

        logger.debug(f"Frequency score for {memory.id}: {frequency_score:.3f}")
        return frequency_score

    def _calculate_semantic_similarity_sync(
        self,
        memory: MemoryRecord,
        query_vector: List[float]
    ) -> float:
        """
        Synchronous version of semantic similarity calculation for performance.
        """
        if not memory.embedding_vector:
            return 0.0

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(memory.embedding_vector, query_vector))
        magnitude_memory = math.sqrt(sum(a * a for a in memory.embedding_vector))
        magnitude_query = math.sqrt(sum(b * b for b in query_vector))

        if magnitude_memory == 0 or magnitude_query == 0:
            return 0.0

        cosine_sim = dot_product / (magnitude_memory * magnitude_query)

        # Normalize to [0, 1] range from [-1, 1]
        normalized_sim = (cosine_sim + 1) / 2

        logger.debug(f"Semantic similarity for {memory.id}: {normalized_sim:.3f}")
        return normalized_sim

    def _calculate_user_relevance_score_sync(self, memory: MemoryRecord, query: str) -> float:
        """
        Synchronous version of user relevance score calculation for performance.
        Placeholder for future reinforcement learning integration.
        """
        # For now, return a neutral score
        # In production, this would use user-specific models trained on interaction data
        return 0.5

    async def calculate_importance_score(self, memory: MemoryRecord) -> float:
        """
        Calculate importance score for a memory.

        Based on the memory's importance level with additional factors:
        - Base importance from importance level
        - Boost for high access count
        - Boost for recent updates
        """
        return self._calculate_importance_score_sync(memory)

    async def calculate_recency_score(self, memory: MemoryRecord) -> float:
        """
        Calculate recency score for a memory.

        Uses exponential decay based on time since last access or creation.
        More recent memories have higher scores.
        """
        return self._calculate_recency_score_sync(memory)

    async def calculate_frequency_score(self, memory: MemoryRecord) -> float:
        """
        Calculate frequency score based on access patterns.

        More frequently accessed memories have higher scores.
        Uses time-weighted frequency to account for access recency.
        """
        return self._calculate_frequency_score_sync(memory)

    async def calculate_semantic_similarity(
        self,
        memory: MemoryRecord,
        query_vector: List[float]
    ) -> float:
        """
        Calculate semantic similarity between memory and query.

        Uses cosine similarity between memory embedding and query vector.
        Returns 0.0 if either vector is missing.
        """
        return self._calculate_semantic_similarity_sync(memory, query_vector)

    async def _calculate_user_relevance_score(
        self,
        memory: MemoryRecord,
        query: str
    ) -> float:
        """
        Calculate user relevance score.

        Placeholder for future reinforcement learning integration.
        Currently uses simple heuristics:
        - Tag matching with query terms
        - Source preference
        """
        return self._calculate_user_relevance_score_sync(memory, query)

    async def calculate_composite_score(
        self,
        memory: MemoryRecord,
        query: str,
        query_vector: Optional[List[float]] = None
    ) -> float:
        """
        Calculate composite score for a single memory.

        Convenience method for scoring individual memories.
        """
        result = await self.rank([memory], query, query_vector)
        return result[0].score if result else 0.0

    def update_weights(
        self,
        importance_weight: Optional[float] = None,
        recency_weight: Optional[float] = None,
        frequency_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        user_relevance_weight: Optional[float] = None,
    ) -> None:
        """
        Update ranking weights dynamically.

        Useful for A/B testing or user personalization.
        """
        self.importance_weight = importance_weight if importance_weight is not None else self.importance_weight
        self.recency_weight = recency_weight if recency_weight is not None else self.recency_weight
        self.frequency_weight = frequency_weight if frequency_weight is not None else self.frequency_weight
        self.semantic_weight = semantic_weight if semantic_weight is not None else self.semantic_weight
        self.user_relevance_weight = user_relevance_weight if user_relevance_weight is not None else self.user_relevance_weight

        # Normalize weights
        total_weight = (
            self.importance_weight + self.recency_weight + self.frequency_weight +
            self.semantic_weight + self.user_relevance_weight
        )

        if total_weight > 0:
            self.importance_weight /= total_weight
            self.recency_weight /= total_weight
            self.frequency_weight /= total_weight
            self.semantic_weight /= total_weight
            self.user_relevance_weight /= total_weight

        logger.info(f"Updated MemoryRanker weights: {self._get_weights_dict()}")

    def _get_weights_dict(self) -> Dict[str, float]:
        """Get current weights as a dictionary."""
        return {
            "importance": self.importance_weight,
            "recency": self.recency_weight,
            "frequency": self.frequency_weight,
            "semantic": self.semantic_weight,
            "user_relevance": self.user_relevance_weight,
        }
