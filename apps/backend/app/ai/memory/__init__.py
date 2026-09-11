# apps/backend/app/ai/memory/__init__.py
"""
Memory Intelligence Core - Main package initialization.

This package provides the Memory Intelligence Core for Lumenly:
- Multi-backend memory storage (Redis, MongoDB, Qdrant)
- Memory ranking with multi-factor scoring
- Memory retrieval with filtering and ranking
- Memory consolidation and summarization
- Configurable forgetting policies
- Behavior tracking and analysis
"""

from app.ai.memory.behavior import BehaviorTracker
from app.ai.memory.consolidation import MemoryConsolidator
from app.ai.memory.forgetting import ForgettingAction, ForgettingPolicy, MemoryForgetting
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
    MemoryRecord,
    MemoryRetrievalConfig,
    MemorySearchResult,
)
from app.ai.memory.manager import MemoryManager
from app.ai.memory.ranking import MemoryRanker
from app.ai.memory.retriever import MemoryRetriever
from app.ai.memory.schema import (
    QDRANT_COLLECTIONS,
    RETENTION_POLICY,
    BehavioralMemory,
    ConversationMemory,
    EpisodicMemory,
    GoalMemory,
    HabitMemory,
    JournalMemory,
    KnowledgeMemory,
    MemoryImportance,
    MemoryMetadata,
    MemoryType,
    PreferenceMemory,
)
from app.ai.memory.security import MemorySecurityContext, MemorySecurityValidator
from app.ai.memory.storage import MultiBackendMemoryStorage
from app.ai.memory.summary import MemorySummarizer
from app.ai.memory.validation import (
    ChunkCountExceededError,
    InvalidEmbeddingDimensionsError,
    InvalidUTF8Error,
    MalformedMetadataError,
    MemorySizeExceededError,
    MemoryValidationError,
    MemoryValidator,
    MetadataSizeExceededError,
    OversizedJSONError,
    PayloadSizeExceededError,
    TokenLimitExceededError,
    default_validator,
)

__all__ = [
    # Interfaces
    "IMemoryStorage",
    "IMemoryRetriever",
    "IMemoryRanker",
    "IMemoryConsolidator",
    "IMemoryForgetting",
    "IMemorySummarizer",
    "IBehaviorTracker",
    "IMemoryManager",
    "MemoryRecord",
    "MemorySearchResult",
    "MemoryConsolidationResult",
    "MemoryRetrievalConfig",
    # Implementations
    "MultiBackendMemoryStorage",
    "MemoryRetriever",
    "MemoryRanker",
    "MemoryConsolidator",
    "MemoryForgetting",
    "ForgettingPolicy",
    "ForgettingAction",
    "MemorySummarizer",
    "BehaviorTracker",
    "MemoryManager",
    "MemorySecurityValidator",
    "MemorySecurityContext",
    # Schema
    "MemoryType",
    "MemoryImportance",
    "MemoryMetadata",
    "ConversationMemory",
    "JournalMemory",
    "GoalMemory",
    "HabitMemory",
    "PreferenceMemory",
    "BehavioralMemory",
    "KnowledgeMemory",
    "EpisodicMemory",
    "QDRANT_COLLECTIONS",
    "RETENTION_POLICY",
    # Validation
    "MemoryValidator",
    "MemoryValidationError",
    "MemorySizeExceededError",
    "MetadataSizeExceededError",
    "InvalidEmbeddingDimensionsError",
    "ChunkCountExceededError",
    "TokenLimitExceededError",
    "PayloadSizeExceededError",
    "InvalidUTF8Error",
    "MalformedMetadataError",
    "OversizedJSONError",
    "default_validator",
]

__version__ = "1.0.0"
