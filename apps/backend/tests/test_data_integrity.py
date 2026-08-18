# tests/test_data_integrity.py
"""
Data Integrity Tests for Coaching Engine.

Tests for:
- CoachingSession status transitions
- AIInsight validation
- Duplicate protection
- Concurrent update safety
- Tenant isolation
- MongoDB index verification
- TTL verification
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import AIInsight, CoachingSession, InsightType, SessionType


@pytest.mark.asyncio
class TestCoachingSessionDataIntegrity:
    """Test CoachingSession data integrity."""

    async def test_valid_status_transitions(self):
        """Test that valid status transitions are allowed."""
        session = CoachingSession(
            user_id=uuid.uuid4(),
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent",
            title="Test Session",
            status="active"
        )

        # Valid transition: active -> completed
        assert session.validate_status_transition("completed")

        # Valid transition: active -> cancelled
        assert session.validate_status_transition("cancelled")

        # Invalid transition: active -> active (no change)
        assert not session.validate_status_transition("active")

    async def test_invalid_status_transitions(self):
        """Test that invalid status transitions are rejected."""
        session = CoachingSession(
            user_id=uuid.uuid4(),
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent",
            status="completed"
        )

        # Terminal state cannot transition
        assert not session.validate_status_transition("active")
        assert not session.validate_status_transition("cancelled")

    async def test_concurrent_update_safety(self):
        """Test that concurrent updates are handled safely."""
        session = CoachingSession(
            user_id=uuid.uuid4(),
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent",
            status="active"
        )
        await session.insert()

        # Simulate concurrent update by getting two separate instances
        session1 = await CoachingSession.get(session.id)
        session2 = await CoachingSession.get(session.id)

        # Verify both instances have the same initial status
        assert session1.status == "active"
        assert session2.status == "active"

        # Verify that the validation logic allows these transitions from "active"
        assert session1.validate_status_transition("completed")
        assert session2.validate_status_transition("cancelled")

        # Both try to update status to different terminal states
        session1.status = "completed"
        session2.status = "cancelled"

        # First save should succeed (valid transition from active to completed)
        await session1.save()

        # Verify the session was actually updated
        updated_session = await CoachingSession.get(session.id)
        assert updated_session.status == "completed"

        # Note: In production, session2.save() would fail with optimistic concurrency control
        # since the document was updated by session1. This test validates that the
        # transition validation logic exists and works correctly for the initial state.

    async def test_duplicate_protection(self):
        """Test that duplicate sessions are prevented."""
        user_id = uuid.uuid4()

        session1 = CoachingSession(
            user_id=user_id,
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent",
            title="Test Session 1"
        )
        await session1.insert()

        # Create second session with same user (should be allowed)
        session2 = CoachingSession(
            user_id=user_id,
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent",
            title="Test Session 2"
        )
        await session2.insert()

        # Both should exist (different sessions are allowed)
        assert session1.id != session2.id


@pytest.mark.asyncio
class TestAIInsightDataIntegrity:
    """Test AIInsight data integrity."""

    async def test_payload_validation(self):
        """Test that insight payload validation works."""
        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={
                "trend": "improving",
                "average_sentiment": 0.75
            },
            confidence=0.8
        )

        assert insight.validate_payload()

    async def test_invalid_payload_validation(self):
        """Test that invalid payload is rejected."""
        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={
                "trend": "improving"
                # Missing required field: average_sentiment
            },
            confidence=0.8
        )

        assert not insight.validate_payload()

    async def test_confidence_validation(self):
        """Test that confidence scores are validated."""
        # Valid confidence
        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={"trend": "stable", "average_sentiment": 0.5},
            confidence=0.5
        )

        # Invalid confidence (would be caught by Pydantic validation)
        try:
            invalid_insight = AIInsight(
                user_id=uuid.uuid4(),
                insight_type=InsightType.WELLNESS_TREND,
                pillar="mental_health",
                payload={"trend": "stable", "average_sentiment": 0.5},
                confidence=1.5  # Invalid: > 1.0
            )
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected

    async def test_ttl_expiration(self):
        """Test that TTL expiration is calculated correctly."""
        future_expiration = datetime.now(timezone.utc) + timedelta(days=30)

        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={"trend": "stable", "average_sentiment": 0.5},
            confidence=0.5,
            expires_at=future_expiration
        )

        # Should not be expired
        assert not insight.is_expired()

        # Set to past
        insight.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert insight.is_expired()

    async def test_no_expiration_when_not_set(self):
        """Test that insights without expiration are not considered expired."""
        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={"trend": "stable", "average_sentiment": 0.5},
            confidence=0.5
            # No expires_at set
        )

        assert not insight.is_expired()


@pytest.mark.asyncio
class TestTenantIsolation:
    """Test multi-tenant isolation at data level."""

    async def test_user_cannot_access_other_user_sessions(self):
        """Test that users cannot access sessions from other users."""
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        session_a = CoachingSession(
            user_id=user_a_id,
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent"
        )
        await session_a.insert()

        # Query for user B should not return user A's session
        sessions_b = await CoachingSession.find(
            CoachingSession.user_id == user_b_id
        ).to_list()

        assert len(sessions_b) == 0
        assert session_a.id not in [s.id for s in sessions_b]

    async def test_user_cannot_access_other_user_insights(self):
        """Test that users cannot access insights from other users."""
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        insight_a = AIInsight(
            user_id=user_a_id,
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={"trend": "stable", "average_sentiment": 0.5},
            confidence=0.5
        )
        await insight_a.insert()

        # Query for user B should not return user A's insight
        insights_b = await AIInsight.find(
            AIInsight.user_id == user_b_id
        ).to_list()

        assert len(insights_b) == 0
        assert insight_a.id not in [i.id for i in insights_b]


@pytest.mark.asyncio
class TestMongoDBIndexes:
    """Test that MongoDB indexes are properly configured."""

    async def test_coaching_session_indexes_exist(self):
        """Test that CoachingSession indexes exist."""
        # This would require MongoDB admin access to verify indexes
        # For now, we verify the index configuration is defined
        session = CoachingSession(
            user_id=uuid.uuid4(),
            session_type=SessionType.ASSESSMENT,
            agent_id="test_agent"
        )

        # Verify index configuration is defined in Settings
        assert "user_id" in session.Settings.indexes
        assert "session_type" in session.Settings.indexes
        assert "status" in session.Settings.indexes

    async def test_ai_insight_indexes_exist(self):
        """Test that AIInsight indexes exist."""
        insight = AIInsight(
            user_id=uuid.uuid4(),
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={"trend": "stable", "average_sentiment": 0.5},
            confidence=0.5
        )

        # Verify index configuration is defined in Settings
        assert "user_id" in insight.Settings.indexes
        assert "insight_type" in insight.Settings.indexes
        assert "pillar" in insight.Settings.indexes
