# tests/test_ai_memory_schema.py
"""
Tests for Memory Schema - No external dependencies, deterministic tests.
"""

from app.ai.memory.schema import (
    QDRANT_COLLECTIONS,
    RETENTION_POLICY,
    BehavioralMemory,
    ConversationMemory,
    GoalMemory,
    HabitMemory,
    JournalMemory,
    MemoryImportance,
    MemoryMetadata,
    MemoryType,
    PreferenceMemory,
)


class TestMemoryType:
    """Test memory type enum."""

    def test_memory_type_values(self):
        assert MemoryType.CONVERSATION == "conversation"
        assert MemoryType.JOURNAL == "journal"
        assert MemoryType.GOAL == "goal"
        assert MemoryType.HABIT == "habit"
        assert MemoryType.PREFERENCE == "preference"
        assert MemoryType.BEHAVIORAL == "behavioral"
        assert MemoryType.KNOWLEDGE == "knowledge"
        assert MemoryType.EPISODIC == "episodic"


class TestMemoryImportance:
    """Test memory importance enum."""

    def test_memory_importance_values(self):
        assert MemoryImportance.CRITICAL == "critical"
        assert MemoryImportance.HIGH == "high"
        assert MemoryImportance.MEDIUM == "medium"
        assert MemoryImportance.LOW == "low"
        assert MemoryImportance.TEMPORARY == "temporary"


class TestMemoryMetadata:
    """Test memory metadata structure."""

    def test_memory_metadata_creation(self):
        metadata = MemoryMetadata(
            user_id="user123",
            memory_type=MemoryType.JOURNAL,
            importance=MemoryImportance.HIGH,
        )
        assert metadata.user_id == "user123"
        assert metadata.memory_type == MemoryType.JOURNAL
        assert metadata.importance == MemoryImportance.HIGH
        assert metadata.created_at is not None
        assert metadata.access_count == 0

    def test_memory_metadata_with_tags(self):
        metadata = MemoryMetadata(
            user_id="user123",
            memory_type=MemoryType.JOURNAL,
            tags=["health", "fitness"],
        )
        assert len(metadata.tags) == 2
        assert "health" in metadata.tags


class TestConversationMemory:
    """Test conversation memory structure."""

    def test_conversation_memory_creation(self):
        memory = ConversationMemory(
            user_id="user123",
            role="user",
            content="Hello",
        )
        assert memory.user_id == "user123"
        assert memory.role == "user"
        assert memory.content == "Hello"
        assert memory.turn_id is not None

    def test_conversation_memory_to_dict(self):
        memory = ConversationMemory(
            user_id="user123",
            role="assistant",
            content="Hi there!",
        )
        result = memory.to_dict()
        assert result["role"] == "assistant"
        assert result["content"] == "Hi there!"
        assert "timestamp" in result
        assert "turn_id" in result


class TestJournalMemory:
    """Test journal memory structure."""

    def test_journal_memory_creation(self):
        memory = JournalMemory(
            user_id="user123",
            content="Today was a good day",
            mood_score=8,
        )
        assert memory.user_id == "user123"
        assert memory.content == "Today was a good day"
        assert memory.mood_score == 8
        assert memory.entry_id is not None

    def test_journal_memory_to_mongo_doc(self):
        memory = JournalMemory(
            user_id="user123",
            content="Test entry",
            topics=["work", "productivity"],
        )
        doc = memory.to_mongo_doc()
        assert doc["user_id"] == "user123"
        assert doc["content"] == "Test entry"
        assert doc["topics"] == ["work", "productivity"]

    def test_journal_memory_to_qdrant_payload(self):
        memory = JournalMemory(
            user_id="user123",
            content="Test entry",
            mood_score=7,
        )
        payload = memory.to_qdrant_payload()
        assert payload["user_id"] == "user123"
        assert payload["memory_type"] == MemoryType.JOURNAL.value
        assert payload["mood_score"] == 7


class TestGoalMemory:
    """Test goal memory structure."""

    def test_goal_memory_creation(self):
        memory = GoalMemory(
            user_id="user123",
            title="Exercise daily",
            description="Go to the gym every day",
        )
        assert memory.user_id == "user123"
        assert memory.title == "Exercise daily"
        assert memory.is_completed is False
        assert memory.progress == 0.0

    def test_goal_memory_to_mongo_doc(self):
        memory = GoalMemory(
            user_id="user123",
            title="Learn Python",
            description="Complete a Python course",
            category="learning",
        )
        doc = memory.to_mongo_doc()
        assert doc["title"] == "Learn Python"
        assert doc["category"] == "learning"
        assert doc["is_completed"] is False

    def test_goal_memory_to_qdrant_payload(self):
        memory = GoalMemory(
            user_id="user123",
            title="Read more books",
            description="Read 12 books this year",
            progress=0.5,
        )
        payload = memory.to_qdrant_payload()
        assert payload["memory_type"] == MemoryType.GOAL.value
        assert payload["progress"] == 0.5


class TestHabitMemory:
    """Test habit memory structure."""

    def test_habit_memory_creation(self):
        memory = HabitMemory(
            user_id="user123",
            title="Morning meditation",
            frequency="daily",
        )
        assert memory.user_id == "user123"
        assert memory.title == "Morning meditation"
        assert memory.frequency == "daily"
        assert memory.streak_count == 0

    def test_habit_memory_to_mongo_doc(self):
        memory = HabitMemory(
            user_id="user123",
            title="Evening walk",
            frequency="daily",
            streak_count=7,
        )
        doc = memory.to_mongo_doc()
        assert doc["title"] == "Evening walk"
        assert doc["streak_count"] == 7

    def test_habit_memory_to_qdrant_payload(self):
        memory = HabitMemory(
            user_id="user123",
            title="Drink water",
            frequency="daily",
            completion_rate=0.8,
        )
        payload = memory.to_qdrant_payload()
        assert payload["memory_type"] == MemoryType.HABIT.value
        assert payload["completion_rate"] == 0.8


class TestPreferenceMemory:
    """Test preference memory structure."""

    def test_preference_memory_creation(self):
        memory = PreferenceMemory(
            user_id="user123",
            preference_key="communication_style",
            preference_value="direct",
        )
        assert memory.user_id == "user123"
        assert memory.preference_key == "communication_style"
        assert memory.preference_value == "direct"

    def test_preference_memory_to_qdrant_payload(self):
        memory = PreferenceMemory(
            user_id="user123",
            preference_key="meeting_time",
            preference_value="morning",
            context="Work meetings",
        )
        payload = memory.to_qdrant_payload()
        assert payload["memory_type"] == MemoryType.PREFERENCE.value
        assert payload["preference_key"] == "meeting_time"
        assert payload["context"] == "Work meetings"


class TestBehavioralMemory:
    """Test behavioral memory structure."""

    def test_behavioral_memory_creation(self):
        memory = BehavioralMemory(
            user_id="user123",
            pattern_type="time_of_day",
            pattern_description="Most active in the morning",
            strength=0.8,
        )
        assert memory.user_id == "user123"
        assert memory.pattern_type == "time_of_day"
        assert memory.strength == 0.8

    def test_behavioral_memory_to_qdrant_payload(self):
        memory = BehavioralMemory(
            user_id="user123",
            pattern_type="day_of_week",
            pattern_description="More productive on weekdays",
            strength=0.9,
            evidence_count=50,
        )
        payload = memory.to_qdrant_payload()
        assert payload["memory_type"] == MemoryType.BEHAVIORAL.value
        assert payload["strength"] == 0.9
        assert payload["evidence_count"] == 50


class TestQdrantCollections:
    """Test Qdrant collection configuration."""

    def test_qdrant_collections_config(self):
        from app.core.config import settings
        assert "short_term_memory" in QDRANT_COLLECTIONS
        assert "medium_term_memory" in QDRANT_COLLECTIONS
        assert "long_term_memory" in QDRANT_COLLECTIONS

        short_term = QDRANT_COLLECTIONS["short_term_memory"]
        assert short_term["vector_size"] == settings.VECTOR_DIMENSION
        assert short_term["distance"] == settings.DISTANCE_METRIC
        assert "user_id" in short_term["payload_fields"]


class TestRetentionPolicy:
    """Test memory retention policy."""

    def test_retention_policy_exists(self):
        assert MemoryType.CONVERSATION in RETENTION_POLICY
        assert MemoryType.JOURNAL in RETENTION_POLICY
        assert MemoryType.GOAL in RETENTION_POLICY

    def test_conversation_retention_policy(self):
        policy = RETENTION_POLICY[MemoryType.CONVERSATION]
        assert policy["ttl_days"] == 1
        assert policy["max_entries"] == 100

    def test_preference_retention_policy(self):
        policy = RETENTION_POLICY[MemoryType.PREFERENCE]
        assert policy["ttl_days"] is None  # Never expire
        assert policy["max_entries"] == 500
