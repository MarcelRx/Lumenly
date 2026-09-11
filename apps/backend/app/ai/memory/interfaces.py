# apps/backend/app/ai/memory/interfaces.py
"""
Memory Interfaces - Base interfaces for the Memory Intelligence Core.

This module defines the abstract interfaces that all memory components must implement,
ensuring provider-independent operation and clean separation of concerns.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from app.ai.memory.schema import (
    MemoryType,
    MemoryImportance,
    MemoryMetadata,
)


@dataclass
class MemoryRecord:
    """Unified memory record representation."""
    id: str
    user_id: str
    memory_type: MemoryType
    content: str
    metadata: MemoryMetadata
    embedding_id: Optional[str] = None
    embedding_vector: Optional[List[float]] = None
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = self.metadata.created_at


@dataclass
class MemorySearchResult:
    """Result from memory search with ranking information."""
    memory: MemoryRecord
    score: float
    rank: int
    relevance_factors: Dict[str, float]


@dataclass
class MemoryConsolidationResult:
    """Result from memory consolidation operation."""
    consolidated_memory: MemoryRecord
    source_memory_ids: List[str]
    consolidation_strategy: str
    timestamp: datetime


@dataclass
class MemoryRetrievalConfig:
    """Configuration for memory retrieval operations."""
    max_results: int = 10
    min_score: float = 0.0
    memory_types: Optional[List[MemoryType]] = None
    date_range: Optional[tuple[datetime, datetime]] = None
    importance_filter: Optional[List[MemoryImportance]] = None
    source_filter: Optional[List[str]] = None
    enable_ranking: bool = True
    enable_semantic_search: bool = True


class IMemoryStorage(ABC):
    """Interface for memory storage operations."""
    
    @abstractmethod
    async def store(self, memory: MemoryRecord) -> str:
        """Store a memory record and return its ID."""
        pass
    
    @abstractmethod
    async def retrieve(self, memory_id: str, user_id: str) -> Optional[MemoryRecord]:
        """Retrieve a memory record by ID for a specific user."""
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory record."""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory record."""
        pass
    
    @abstractmethod
    async def list_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryRecord]:
        """List memories for a user with optional filtering."""
        pass
    
    @abstractmethod
    async def count_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> int:
        """Count memories for a user with optional filtering."""
        pass


class IMemoryRetriever(ABC):
    """Interface for memory retrieval operations."""
    
    @abstractmethod
    async def search(
        self,
        user_id: str,
        query: str,
        config: MemoryRetrievalConfig
    ) -> List[MemorySearchResult]:
        """Search for memories based on a query."""
        pass
    
    @abstractmethod
    async def retrieve_by_id(
        self,
        memory_id: str,
        user_id: str
    ) -> Optional[MemoryRecord]:
        """Retrieve a specific memory by ID."""
        pass
    
    @abstractmethod
    async def retrieve_recent(
        self,
        user_id: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryRecord]:
        """Retrieve recent memories for a user."""
        pass
    
    @abstractmethod
    async def retrieve_by_type(
        self,
        user_id: str,
        memory_type: MemoryType,
        limit: int = 100
    ) -> List[MemoryRecord]:
        """Retrieve memories of a specific type."""
        pass


class IMemoryRanker(ABC):
    """Interface for memory ranking operations."""
    
    @abstractmethod
    async def rank(
        self,
        memories: List[MemoryRecord],
        query: str,
        query_vector: Optional[List[float]] = None
    ) -> List[MemorySearchResult]:
        """Rank memories based on relevance to the query."""
        pass
    
    @abstractmethod
    async def calculate_importance_score(self, memory: MemoryRecord) -> float:
        """Calculate importance score for a memory."""
        pass
    
    @abstractmethod
    async def calculate_recency_score(self, memory: MemoryRecord) -> float:
        """Calculate recency score for a memory."""
        pass
    
    @abstractmethod
    async def calculate_frequency_score(self, memory: MemoryRecord) -> float:
        """Calculate frequency score based on access patterns."""
        pass
    
    @abstractmethod
    async def calculate_semantic_similarity(
        self,
        memory: MemoryRecord,
        query_vector: List[float]
    ) -> float:
        """Calculate semantic similarity between memory and query."""
        pass


class IMemoryConsolidator(ABC):
    """Interface for memory consolidation operations."""
    
    @abstractmethod
    async def consolidate_similar(
        self,
        user_id: str,
        memory_type: MemoryType,
        similarity_threshold: float = 0.85
    ) -> List[MemoryConsolidationResult]:
        """Consolidate similar memories of a given type."""
        pass
    
    @abstractmethod
    async def summarize_memories(
        self,
        memory_ids: List[str],
        user_id: str
    ) -> Optional[MemoryRecord]:
        """Create a summary memory from multiple memories."""
        pass
    
    @abstractmethod
    async def merge_memories(
        self,
        memory_ids: List[str],
        user_id: str
    ) -> Optional[MemoryRecord]:
        """Merge multiple memories into a single comprehensive memory."""
        pass


class IMemoryForgetting(ABC):
    """Interface for memory forgetting operations."""
    
    @abstractmethod
    async def should_forget(self, memory: MemoryRecord) -> bool:
        """Determine if a memory should be forgotten based on policy."""
        pass
    
    @abstractmethod
    async def archive_memory(self, memory_id: str, user_id: str) -> bool:
        """Archive a memory instead of deleting it."""
        pass
    
    @abstractmethod
    async def compress_memory(self, memory_id: str, user_id: str) -> bool:
        """Compress a memory to reduce storage while preserving core information."""
        pass
    
    @abstractmethod
    async def apply_forgetting_policy(
        self,
        user_id: str,
        policy_name: str = "default"
    ) -> Dict[str, int]:
        """Apply forgetting policy to user's memories."""
        pass


class IMemorySummarizer(ABC):
    """Interface for memory summarization operations."""
    
    @abstractmethod
    async def summarize_memory(self, memory: MemoryRecord) -> str:
        """Generate a summary of a single memory."""
        pass
    
    @abstractmethod
    async def summarize_memories_batch(
        self,
        memories: List[MemoryRecord]
    ) -> List[str]:
        """Generate summaries for multiple memories."""
        pass
    
    @abstractmethod
    async def extract_key_insights(
        self,
        memories: List[MemoryRecord]
    ) -> List[str]:
        """Extract key insights from a set of memories."""
        pass


class IBehaviorTracker(ABC):
    """Interface for behavior tracking operations."""
    
    @abstractmethod
    async def track_conversation_frequency(
        self,
        user_id: str,
        timestamp: datetime
    ) -> None:
        """Track conversation frequency for behavior analysis."""
        pass
    
    @abstractmethod
    async def track_goal_completion(
        self,
        user_id: str,
        goal_id: str,
        completed: bool
    ) -> None:
        """Track goal completion events."""
        pass
    
    @abstractmethod
    async def track_habit_streak(
        self,
        user_id: str,
        habit_id: str,
        completed: bool
    ) -> None:
        """Track habit streak information."""
        pass
    
    @abstractmethod
    async def track_journal_statistics(
        self,
        user_id: str,
        entry_id: str,
        mood_score: Optional[int]
    ) -> None:
        """Track journal entry statistics."""
        pass
    
    @abstractmethod
    async def get_behavior_summary(
        self,
        user_id: str,
        time_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get behavioral summary for a user."""
        pass


class IMemoryManager(ABC):
    """Main interface for the Memory Manager orchestrator."""
    
    @abstractmethod
    async def store_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[MemoryMetadata] = None
    ) -> str:
        """Store a memory with automatic type handling."""
        pass
    
    @abstractmethod
    async def retrieve_memories(
        self,
        user_id: str,
        query: str,
        config: Optional[MemoryRetrievalConfig] = None
    ) -> List[MemorySearchResult]:
        """Retrieve memories based on query with ranking."""
        pass
    
    @abstractmethod
    async def consolidate_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryConsolidationResult]:
        """Consolidate memories for a user."""
        pass
    
    @abstractmethod
    async def cleanup_user_memories(
        self,
        user_id: str,
        policy_name: str = "default"
    ) -> Dict[str, int]:
        """Clean up memories using forgetting policy."""
        pass
    
    @abstractmethod
    async def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get statistics about user's memories."""
        pass
