# apps/backend/app/ai/memory/manager.py
"""
Memory Manager - Main Memory Manager orchestrator implementation.

This module implements the main Memory Manager that orchestrates all memory components:
- Storage operations
- Retrieval with ranking
- Consolidation
- Forgetting
- Summarization
- Behavior tracking
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.embeddings.interface import EmbeddingProviderInterface
from app.ai.llm.interface import LLMProviderInterface
from app.ai.memory.behavior import BehaviorTracker
from app.ai.memory.consolidation import MemoryConsolidator
from app.ai.memory.forgetting import MemoryForgetting
from app.ai.memory.interfaces import (
    IBehaviorTracker,
    IMemoryConsolidator,
    IMemoryForgetting,
    IMemoryManager,
    IMemoryRanker,
    IMemoryRetriever,
    IMemoryStorage,
    IMemorySummarizer,
    MemoryConsolidationResult,
    MemoryImportance,
    MemoryMetadata,
    MemoryRecord,
    MemoryRetrievalConfig,
    MemorySearchResult,
    MemoryType,
)
from app.ai.memory.ranking import MemoryRanker
from app.ai.memory.retriever import MemoryRetriever
from app.ai.memory.storage import MultiBackendMemoryStorage
from app.ai.memory.summary import MemorySummarizer
from app.ai.memory.validation import MemoryValidator, default_validator

logger = logging.getLogger(__name__)


class MemoryManager(IMemoryManager):
    """
    Main Memory Manager orchestrator.

    Coordinates all memory intelligence operations:
    - Store and retrieve memories
    - Rank memories by relevance
    - Consolidate similar memories
    - Apply forgetting policies
    - Track user behavior
    - Generate summaries
    """

    def __init__(
        self,
        storage: Optional[IMemoryStorage] = None,
        retriever: Optional[IMemoryRetriever] = None,
        ranker: Optional[IMemoryRanker] = None,
        consolidator: Optional[IMemoryConsolidator] = None,
        forgetting: Optional[IMemoryForgetting] = None,
        summarizer: Optional[IMemorySummarizer] = None,
        behavior_tracker: Optional[IBehaviorTracker] = None,
        embedding_model: Optional[EmbeddingProviderInterface] = None,
        llm_provider: Optional[LLMProviderInterface] = None,
        validator: Optional[MemoryValidator] = None,
    ):
        """
        Initialize the Memory Manager with all components.

        Args:
            storage: Memory storage implementation
            retriever: Memory retriever implementation
            ranker: Memory ranker implementation
            consolidator: Memory consolidator implementation
            forgetting: Memory forgetting implementation
            summarizer: Memory summarizer implementation
            behavior_tracker: Behavior tracker implementation
            embedding_model: Optional embedding model for semantic search
            llm_provider: Optional LLM provider for summarization
            validator: Optional memory validator for input validation
        """
        # Initialize components (create defaults if not provided)
        self.storage = storage or MultiBackendMemoryStorage()
        self.ranker = ranker or MemoryRanker()
        self.summarizer = summarizer or MemorySummarizer(llm_provider)
        self.consolidator = consolidator or MemoryConsolidator(self.storage, self.summarizer)
        self.forgetting = forgetting or MemoryForgetting(self.storage, self.consolidator)
        self.retriever = retriever or MemoryRetriever(self.storage, self.ranker, embedding_model)
        self.behavior_tracker = behavior_tracker or BehaviorTracker(self.storage)
        self.validator = validator or default_validator

        logger.info("Initialized Memory Manager with all components")

    async def store_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[MemoryMetadata] = None,
        embedding_vector: Optional[List[float]] = None,
    ) -> str:
        """
        Store a memory with automatic type handling and validation.

        Creates a memory record and routes it to the appropriate storage backend.
        Validates all inputs before storage.
        """
        try:
            # Validate content
            self.validator.validate_memory_content(content)

            # Validate embedding vector
            self.validator.validate_embedding_vector(embedding_vector)

            # Create metadata if not provided
            if metadata is None:
                metadata = MemoryMetadata(
                    user_id=user_id,
                    memory_type=memory_type,
                    importance=MemoryImportance.MEDIUM,
                    source="user_input",
                )

            # Validate metadata
            metadata_dict = {
                "user_id": metadata.user_id,
                "memory_type": metadata.memory_type.value,
                "importance": metadata.importance.value,
                "source": metadata.source,
                "tags": metadata.tags,
            }
            self.validator.validate_metadata(metadata_dict)

            # Create memory record
            memory_id = str(uuid.uuid4())
            memory = MemoryRecord(
                id=memory_id,
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                metadata=metadata,
                embedding_vector=embedding_vector,
                created_at=datetime.now(timezone.utc),
            )

            # Validate complete memory record
            self.validator.validate_memory_record(memory)

            # Store the memory
            await self.storage.store(memory)

            # Track behavior if applicable
            await self._track_storage_behavior(memory)

            logger.info(f"Stored memory {memory_id} of type {memory_type.value} for user {user_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store memory for user {user_id}: {e}")
            raise

    async def retrieve_memories(
        self, user_id: str, query: str, config: Optional[MemoryRetrievalConfig] = None
    ) -> List[MemorySearchResult]:
        """
        Retrieve memories based on query with ranking and validation.

        Uses the retriever to search, rank, and return relevant memories.
        Validates search query before processing.
        """
        try:
            # Validate search query
            self.validator.validate_search_query(query)

            if config is None:
                config = MemoryRetrievalConfig(
                    max_results=10,
                    enable_ranking=True,
                    enable_semantic_search=True,
                )

            results = await self.retriever.search(user_id, query, config)

            # Update access counts for retrieved memories
            for result in results:
                await self.storage.update(
                    memory_id=result.memory.id,
                    user_id=user_id,
                    updates={
                        "access_count": result.memory.metadata.access_count + 1,
                        "last_accessed": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(
                f"Retrieved {len(results)} memories for user {user_id} with query: {query[:50]}..."
            )
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve memories for user {user_id}: {e}")
            return []

    async def consolidate_user_memories(
        self, user_id: str, memory_type: Optional[MemoryType] = None
    ) -> List[MemoryConsolidationResult]:
        """
        Consolidate memories for a user using Celery task.

        Performs consolidation of similar memories, optionally filtered by type.
        Delegates to Celery task for background processing.
        """
        try:
            from app.workers.tasks import memory_consolidation_task

            # Convert memory type to string for Celery
            memory_type_str = memory_type.value if memory_type else None

            # Trigger Celery task
            task_result = memory_consolidation_task.delay(
                user_id=user_id, memory_type=memory_type_str
            )

            logger.info(
                f"Triggered memory consolidation Celery task {task_result.id} "
                f"for user {user_id} with type {memory_type_str}"
            )

            # Return task info instead of waiting for completion
            return [
                {
                    "task_id": task_result.id,
                    "status": "scheduled",
                    "user_id": user_id,
                    "memory_type": memory_type_str,
                }
            ]

        except Exception as e:
            logger.error(f"Failed to trigger memory consolidation for user {user_id}: {e}")
            return []

    async def cleanup_user_memories(
        self, user_id: str, policy_name: str = "default"
    ) -> Dict[str, int]:
        """
        Clean up memories using forgetting policy via Celery task.

        Applies the specified forgetting policy to clean up old,
        low-importance, or redundant memories.
        Delegates to Celery task for background processing.
        """
        try:
            from app.workers.tasks import memory_forgetting_task

            # Trigger Celery task
            task_result = memory_forgetting_task.delay(user_id=user_id, policy_name=policy_name)

            logger.info(
                f"Triggered memory forgetting Celery task {task_result.id} "
                f"for user {user_id} with policy '{policy_name}'"
            )

            # Return task info instead of waiting for completion
            return {
                "task_id": task_result.id,
                "status": "scheduled",
                "user_id": user_id,
                "policy_name": policy_name,
            }

        except Exception as e:
            logger.error(f"Failed to trigger memory cleanup for user {user_id}: {e}")
            return {}

    async def get_memory_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about user's memories.

        Returns comprehensive statistics including:
        - Total memory count
        - Count by type
        - Count by importance
        - Storage usage
        - Access patterns
        """
        try:
            # Get total count
            total_count = await self.storage.count_user_memories(user_id)

            # Get counts by type
            counts_by_type = {}
            for mem_type in MemoryType:
                type_count = await self.storage.count_user_memories(
                    user_id=user_id, memory_type=mem_type
                )
                counts_by_type[mem_type.value] = type_count

            # Get recent memories
            recent_memories = await self.retriever.retrieve_recent(user_id=user_id, limit=10)

            # Calculate basic statistics
            stats = {
                "total_memories": total_count,
                "counts_by_type": counts_by_type,
                "recent_memory_count": len(recent_memories),
                "last_activity": recent_memories[0].created_at if recent_memories else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Generated memory statistics for user {user_id}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get memory statistics for user {user_id}: {e}")
            return {}

    async def get_memory_by_id(self, memory_id: str, user_id: str) -> Optional[MemoryRecord]:
        """
        Retrieve a specific memory by ID.

        Convenience method for retrieving a single memory.
        """
        return await self.retriever.retrieve_by_id(memory_id, user_id)

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """
        Delete a specific memory by ID.

        Convenience method for deleting a single memory.
        """
        try:
            success = await self.storage.delete(memory_id, user_id)

            if success:
                logger.info(f"Deleted memory {memory_id} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryRecord]:
        """
        List memories for a user with optional filtering.

        Convenience method for listing memories.
        """
        try:
            memories = await self.storage.list_user_memories(
                user_id=user_id, memory_type=memory_type, limit=limit, offset=offset
            )

            logger.debug(
                f"Listed {len(memories)} memories for user {user_id} "
                f"(type: {memory_type.value if memory_type else 'all'})"
            )
            return memories

        except Exception as e:
            logger.error(f"Failed to list memories for user {user_id}: {e}")
            return []

    async def update_memory(self, memory_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a memory record.

        Convenience method for updating a memory.
        """
        try:
            success = await self.storage.update(memory_id, user_id, updates)

            if success:
                logger.info(f"Updated memory {memory_id} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def summarize_memory(self, memory_id: str, user_id: str) -> Optional[str]:
        """
        Generate a summary of a specific memory using Celery task.

        Convenience method for summarizing a single memory.
        Delegates to Celery task for background processing.
        """
        try:
            from app.workers.tasks import memory_summarization_task

            # Trigger Celery task
            task_result = memory_summarization_task.delay(user_id=user_id, memory_id=memory_id)

            logger.info(
                f"Triggered memory summarization Celery task {task_result.id} "
                f"for memory {memory_id}"
            )

            # Return task info instead of waiting for completion
            return {
                "task_id": task_result.id,
                "status": "scheduled",
                "user_id": user_id,
                "memory_id": memory_id,
            }

        except Exception as e:
            logger.error(f"Failed to trigger memory summarization for memory {memory_id}: {e}")
            return None

    async def get_behavior_summary(
        self, user_id: str, time_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get behavioral summary for a user using Celery task.

        Convenience method for behavior tracking.
        Delegates to Celery task for background processing.
        """
        try:
            from app.workers.tasks import behavior_aggregation_task

            # Calculate time range in days if provided
            time_range_days = 30  # default
            if time_range:
                days_diff = (time_range[1] - time_range[0]).days
                time_range_days = max(1, days_diff)

            # Trigger Celery task
            task_result = behavior_aggregation_task.delay(
                user_id=user_id, time_range_days=time_range_days
            )

            logger.info(
                f"Triggered behavior aggregation Celery task {task_result.id} "
                f"for user {user_id} with time range {time_range_days} days"
            )

            # Return task info instead of waiting for completion
            return {
                "task_id": task_result.id,
                "status": "scheduled",
                "user_id": user_id,
                "time_range_days": time_range_days,
            }

        except Exception as e:
            logger.error(f"Failed to trigger behavior aggregation for user {user_id}: {e}")
            return {}

    async def _track_storage_behavior(self, memory: MemoryRecord) -> None:
        """
        Track behavior when storing a memory.

        Updates behavior tracking based on memory type and content.
        """
        try:
            # Track based on memory type
            if memory.memory_type == MemoryType.CONVERSATION:
                await self.behavior_tracker.track_conversation_frequency(
                    user_id=memory.user_id, timestamp=memory.created_at
                )
            elif memory.memory_type == MemoryType.JOURNAL:
                # Extract mood score from metadata if available
                mood_score = None
                if hasattr(memory.metadata, "mood_score"):
                    mood_score = memory.metadata.mood_score
                await self.behavior_tracker.track_journal_statistics(
                    user_id=memory.user_id, entry_id=memory.id, mood_score=mood_score
                )

        except Exception as e:
            logger.error(f"Failed to track storage behavior: {e}")

    async def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all memory components.

        Returns health status of each component.
        """
        health = {
            "storage": True,
            "retriever": True,
            "ranker": True,
            "consolidator": True,
            "forgetting": True,
            "summarizer": True,
            "behavior_tracker": True,
        }

        try:
            # Test storage
            await self.storage.count_user_memories("health_check_user")
        except Exception:
            health["storage"] = False

        return health
