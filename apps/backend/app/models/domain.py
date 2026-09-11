# apps/backend/app/models/domain.py
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field


def utc_now():
    return datetime.now(timezone.utc)


class DocumentStatus(str, Enum):
    """Status of document processing."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class SessionType(str, Enum):
    """Coaching session types."""

    ASSESSMENT = "assessment"
    NUDGE = "nudge"
    REFLECTION = "reflection"
    ESCALATION = "escalation"


class InsightType(str, Enum):
    """AI insight types."""

    WELLNESS_TREND = "wellness_trend"
    RISK_ALERT = "risk_alert"
    GOAL_SUGGESTION = "goal_suggestion"
    HABIT_RECOMMENDATION = "habit_recommendation"
    BURNOUT_WARNING = "burnout_warning"
    LEARNING_INSIGHT = "learning_insight"


class JournalEntry(Document):
    """Journal entry document for user reflections and thoughts."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    content: str = Field(..., description="Journal entry content")
    mood_score: Optional[int] = Field(None, ge=1, le=10, description="Mood score from 1-10")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "journal_entries"
        indexes = [
            "user_id",
            "created_at",
            [("user_id", 1), ("created_at", -1)],  # Compound index for efficient queries
        ]


class Goal(Document):
    """Goal document for user objectives and targets."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    title: str = Field(..., description="Goal title")
    description: str = Field(..., description="Goal description")
    target_date: datetime = Field(..., description="Target completion date")
    is_completed: bool = Field(default=False, description="Goal completion status")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "goals"
        indexes = [
            "user_id",
            "target_date",
            "is_completed",
            [
                ("user_id", 1),
                ("is_completed", 1),
                ("target_date", -1),
            ],  # Compound index for user's active goals
        ]


class Habit(Document):
    """Habit document for user recurring activities."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    title: str = Field(..., description="Habit title")
    frequency: str = Field(..., description="Habit frequency (e.g., daily, weekly)")
    streak_count: int = Field(default=0, ge=0, description="Current streak count")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "habits"
        indexes = [
            "user_id",
            "frequency",
            [
                ("user_id", 1),
                ("frequency", 1),
                ("streak_count", -1),
            ],  # Compound index for habit tracking
        ]


class UserDocument(Document):
    """User document for storing uploaded files and their vector embeddings."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    filename: str = Field(..., description="Original filename")
    content: str = Field(..., description="Document text content")
    vector_ids: list[str] = Field(
        default_factory=list, description="Qdrant vector IDs for this document"
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING, description="Document processing status"
    )
    chunk_count: int = Field(default=0, description="Number of chunks created from this document")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "user_documents"
        indexes = [
            "user_id",
            "filename",
            "status",
        ]


class CoachingSession(Document):
    """Coaching session document for AI coaching interactions."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    session_type: SessionType = Field(..., description="Type of coaching session")
    agent_id: Optional[str] = Field(None, description="Agent ID that handled this session")
    title: Optional[str] = Field(None, max_length=200, description="Session title")
    status: str = Field(
        default="active", description="Session status (active, completed, cancelled)"
    )
    metadata: dict = Field(default_factory=dict, description="Session metadata and context")
    started_at: datetime = Field(default_factory=utc_now, description="Session start time")
    ended_at: Optional[datetime] = Field(None, description="Session end time")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "coaching_sessions"
        indexes = [
            "user_id",
            "session_type",
            "status",
            [("user_id", 1), ("started_at", -1)],  # Compound index for user's session history
            [("user_id", 1), ("status", 1)],  # Compound index for user's active sessions
        ]

    def validate_status_transition(self, new_status: str) -> bool:
        """Validate that status transition is allowed."""
        valid_transitions = {
            "active": ["completed", "cancelled"],
            "completed": [],  # Terminal state
            "cancelled": [],  # Terminal state
        }

        if self.status not in valid_transitions:
            return False

        if new_status not in valid_transitions[self.status]:
            return False

        return True


class AIInsight(Document):
    """AI insight document for coaching-derived insights."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    insight_type: InsightType = Field(..., description="Type of insight")
    pillar: Optional[str] = Field(
        None, max_length=50, description="Life pillar (mental_health, fitness, etc.)"
    )
    payload: dict = Field(..., description="Insight data and recommendations")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    session_id: Optional[uuid.UUID] = Field(None, description="Related coaching session ID")
    generated_at: datetime = Field(default_factory=utc_now, description="Generation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp for TTL")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "ai_insights"
        indexes = [
            "user_id",
            "insight_type",
            "pillar",
            [
                ("user_id", 1),
                ("insight_type", 1),
                ("generated_at", -1),
            ],  # Compound index for user insights
            [("expires_at", 1)],  # TTL index
        ]

    def validate_payload(self) -> bool:
        """Validate insight payload structure."""
        if not isinstance(self.payload, dict):
            return False

        # Check for required fields based on insight type
        if self.insight_type == InsightType.WELLNESS_TREND:
            required_fields = ["trend", "average_sentiment"]
            return all(field in self.payload for field in required_fields)

        return True

    def is_expired(self) -> bool:
        """Check if insight has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class ComplianceEvent(Document):
    """Compliance event document for audit logging and security events."""

    user_id: uuid.UUID = Field(..., description="Reference to PostgreSQL User.id")
    event_type: str = Field(
        ..., description="Type of compliance event (escalation, security, etc.)"
    )
    severity_level: float = Field(..., ge=0.0, le=1.0, description="Severity level (0.0 to 1.0)")
    session_id: Optional[uuid.UUID] = Field(None, description="Related coaching session ID")
    details: dict = Field(..., description="Event details and context")
    created_at: datetime = Field(default_factory=utc_now, description="Creation timestamp")

    class Settings:
        collection_name = "compliance_events"
        indexes = [
            "user_id",
            "event_type",
            "severity_level",
            [
                ("user_id", 1),
                ("event_type", 1),
                ("created_at", -1),
            ],  # Compound index for user events
            [("created_at", -1)],  # For time-based queries
        ]
