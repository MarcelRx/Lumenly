# apps/backend/app/ai/memory/schema.py
"""
Memory Schema Design - Comprehensive memory architecture for Lumenly.

This module defines the schema and metadata structure for different memory types:
- Short-term: Current conversation context (Redis)
- Medium-term: Recent goals, habits, journal entries (MongoDB + Qdrant)
- Long-term: User preferences, personality patterns, life history (Qdrant)
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings


class MemoryType(str, Enum):
    """Types of memory stored in the system."""
    CONVERSATION = "conversation"  # Short-term chat history
    JOURNAL = "journal"  # Journal entries and reflections
    GOAL = "goal"  # User goals and progress
    HABIT = "habit"  # Habit tracking and patterns
    PREFERENCE = "preference"  # User preferences and settings
    BEHAVIORAL = "behavioral"  # Behavioral patterns and insights
    KNOWLEDGE = "knowledge"  # Document knowledge base
    EPISODIC = "episodic"  # Specific life events and memories


class MemoryImportance(str, Enum):
    """Importance level for long-term memory retention."""
    CRITICAL = "critical"  # Never forget
    HIGH = "high"  # Long-term retention
    MEDIUM = "medium"  # Medium-term retention
    LOW = "low"  # Short-term retention
    TEMPORARY = "temporary"  # May be forgotten


@dataclass
class MemoryMetadata:
    """Standardized metadata for all memory entries."""
    user_id: str
    memory_type: MemoryType
    importance: MemoryImportance = MemoryImportance.MEDIUM
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    source: Optional[str] = None  # "user_input", "system_inferred", "document", etc.
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0  # Confidence score for inferred memories
    expires_at: Optional[datetime] = None  # For temporary memories
    related_memories: List[str] = field(default_factory=list)  # IDs of related memories
    version: int = 1  # Memory version for tracking changes


@dataclass
class ConversationMemory:
    """Short-term conversation memory (stored in Redis)."""
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "turn_id": self.turn_id,
        }


@dataclass
class JournalMemory:
    """Journal entry memory (stored in MongoDB + Qdrant)."""
    user_id: str
    content: str
    mood_score: Optional[int] = None  # 1-10
    topics: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_mongo_doc(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "content": self.content,
            "mood_score": self.mood_score,
            "topics": self.topics,
            "created_at": self.created_at,
            "entry_id": self.entry_id,
        }

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.JOURNAL.value,
            "content": self.content,
            "mood_score": self.mood_score,
            "topics": self.topics,
            "created_at": self.created_at.isoformat(),
            "entry_id": self.entry_id,
        }


@dataclass
class GoalMemory:
    """Goal tracking memory (stored in MongoDB + Qdrant)."""
    user_id: str
    title: str
    description: str
    target_date: Optional[datetime] = None
    is_completed: bool = False
    progress: float = 0.0  # 0.0 to 1.0
    category: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_mongo_doc(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "target_date": self.target_date,
            "is_completed": self.is_completed,
            "progress": self.progress,
            "category": self.category,
            "created_at": self.created_at,
            "goal_id": self.goal_id,
        }

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.GOAL.value,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "progress": self.progress,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat(),
            "goal_id": self.goal_id,
        }


@dataclass
class HabitMemory:
    """Habit tracking memory (stored in MongoDB + Qdrant)."""
    user_id: str
    title: str
    frequency: str  # "daily", "weekly", etc.
    streak_count: int = 0
    best_streak: int = 0
    completion_rate: float = 0.0
    category: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    habit_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_mongo_doc(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "title": self.title,
            "frequency": self.frequency,
            "streak_count": self.streak_count,
            "best_streak": self.best_streak,
            "completion_rate": self.completion_rate,
            "category": self.category,
            "created_at": self.created_at,
            "habit_id": self.habit_id,
        }

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.HABIT.value,
            "title": self.title,
            "frequency": self.frequency,
            "streak_count": self.streak_count,
            "completion_rate": self.completion_rate,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "habit_id": self.habit_id,
        }


@dataclass
class PreferenceMemory:
    """User preference memory (stored in Qdrant for vector search)."""
    user_id: str
    preference_key: str
    preference_value: str
    context: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pref_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.PREFERENCE.value,
            "preference_key": self.preference_key,
            "preference_value": self.preference_value,
            "context": self.context,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "pref_id": self.pref_id,
        }


@dataclass
class BehavioralMemory:
    """Behavioral pattern memory (stored in Qdrant)."""
    user_id: str
    pattern_type: str  # "time_of_day", "day_of_week", "response_pattern", etc.
    pattern_description: str
    strength: float  # 0.0 to 1.0, how strong the pattern is
    evidence_count: int = 0
    last_observed: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.BEHAVIORAL.value,
            "pattern_type": self.pattern_type,
            "pattern_description": self.pattern_description,
            "strength": self.strength,
            "evidence_count": self.evidence_count,
            "last_observed": self.last_observed.isoformat() if self.last_observed else None,
            "created_at": self.created_at.isoformat(),
            "pattern_id": self.pattern_id,
        }


@dataclass
class KnowledgeMemory:
    """Document knowledge memory (stored in Qdrant)."""
    user_id: str
    content: str
    document_id: str
    chunk_index: int
    source: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    knowledge_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.KNOWLEDGE.value,
            "content": self.content,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "knowledge_id": self.knowledge_id,
        }


@dataclass
class EpisodicMemory:
    """Specific life event memory (stored in Qdrant)."""
    user_id: str
    event_description: str
    event_date: Optional[datetime] = None
    emotional_significance: Optional[float] = None  # 0.0 to 1.0
    participants: List[str] = field(default_factory=list)
    location: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    episodic_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_qdrant_payload(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "memory_type": MemoryType.EPISODIC.value,
            "event_description": self.event_description,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "emotional_significance": self.emotional_significance,
            "participants": self.participants,
            "location": self.location,
            "created_at": self.created_at.isoformat(),
            "episodic_id": self.episodic_id,
        }


# Qdrant Collection Configuration
def get_qdrant_collections_config():
    """Get Qdrant collection configuration with centralized settings."""
    vector_size = settings.VECTOR_DIMENSION
    distance_metric = settings.DISTANCE_METRIC

    return {
        "short_term_memory": {
            "vector_size": vector_size,
            "distance": distance_metric,
            "payload_fields": ["user_id", "turn_id", "role", "timestamp"],
        },
        "medium_term_memory": {
            "vector_size": vector_size,
            "distance": distance_metric,
            "payload_fields": [
                "user_id",
                "memory_type",
                "entry_id",
                "goal_id",
                "habit_id",
                "mood_score",
                "topics",
                "category",
                "created_at",
            ],
        },
        "long_term_memory": {
            "vector_size": vector_size,
            "distance": distance_metric,
            "payload_fields": [
                "user_id",
                "memory_type",
                "importance",
                "pref_id",
                "pattern_id",
                "confidence",
                "access_count",
                "last_accessed",
                "created_at",
            ],
        },
    }

# Backward compatibility - expose as function result
QDRANT_COLLECTIONS = get_qdrant_collections_config()


# Memory Retention Policy
RETENTION_POLICY = {
    MemoryType.CONVERSATION: {"ttl_days": 1, "max_entries": 100},
    MemoryType.JOURNAL: {"ttl_days": 365, "max_entries": 1000},
    MemoryType.GOAL: {"ttl_days": 1825, "max_entries": 100},  # 5 years
    MemoryType.HABIT: {"ttl_days": 1825, "max_entries": 50},
    MemoryType.PREFERENCE: {"ttl_days": None, "max_entries": 500},  # Never expire
    MemoryType.BEHAVIORAL: {"ttl_days": 365, "max_entries": 200},
    MemoryType.KNOWLEDGE: {"ttl_days": None, "max_entries": None},  # Never expire
    MemoryType.EPISODIC: {"ttl_days": 3650, "max_entries": 500},  # 10 years
}
