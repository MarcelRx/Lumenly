# apps/backend/app/schemas/coaching.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.domain import InsightType, SessionType


class CoachingSessionRequest(BaseModel):
    """Request schema for creating a coaching session."""
    session_type: SessionType = Field(..., description="Type of coaching session")
    agent_id: Optional[str] = Field(None, description="Specific agent ID to use")
    title: Optional[str] = Field(None, max_length=200, description="Session title")
    context_ids: Optional[list[str]] = Field(
        default_factory=list,
        description="IDs of related context items (goals, habits, etc.)"
    )
    metadata: dict = Field(default_factory=dict, description="Additional session metadata")


class CoachingSessionResponse(BaseModel):
    """Response schema for coaching session."""
    id: str  # Changed from UUID to str to accommodate MongoDB ObjectId
    user_id: str  # Changed from UUID to str to accommodate PostgreSQL UUID
    session_type: SessionType
    agent_id: Optional[str] = None
    title: Optional[str] = None
    status: str
    metadata: dict
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    websocket_url: Optional[str] = Field(None, description="WebSocket URL for real-time coaching")


class CoachingHistoryRequest(BaseModel):
    """Request schema for coaching history."""
    session_type: Optional[SessionType] = Field(None, description="Filter by session type")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class CoachingHistoryResponse(BaseModel):
    """Response schema for coaching history."""
    sessions: list[CoachingSessionResponse]
    next_cursor: Optional[str] = None
    total_count: int


class CoachingInsightsRequest(BaseModel):
    """Request schema for coaching insights."""
    insight_type: Optional[InsightType] = Field(None, description="Filter by insight type")
    pillar: Optional[str] = Field(None, description="Filter by life pillar")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results to return")


class InsightResponse(BaseModel):
    """Response schema for a single insight."""
    id: str  # Changed from UUID to str to accommodate MongoDB ObjectId
    user_id: str  # Changed from UUID to str to accommodate PostgreSQL UUID
    insight_type: InsightType
    pillar: Optional[str] = None
    payload: dict
    confidence: Optional[float] = None
    session_id: Optional[str] = None  # Changed from UUID to str
    generated_at: datetime
    expires_at: Optional[datetime] = None


class CoachingInsightsResponse(BaseModel):
    """Response schema for coaching insights."""
    insights: list[InsightResponse]
    total_count: int
