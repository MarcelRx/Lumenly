# apps/backend/app/ai/memory/behavior.py
"""
Behavior Tracking - User behavior tracking implementation.

This module implements behavior tracking for:
- Conversation frequency
- Goal completion
- Habit streaks
- Journal statistics
- Interaction timestamps
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ai.memory.interfaces import (
    IBehaviorTracker,
    IMemoryStorage,
    MemoryType,
)

logger = logging.getLogger(__name__)


class BehaviorTracker(IBehaviorTracker):
    """
    Behavior tracking implementation.

    Tracks user behavior patterns across different memory types:
    - Conversation frequency and timing
    - Goal completion rates
    - Habit streak tracking
    - Journal mood patterns
    - General interaction statistics
    """

    def __init__(self, storage: IMemoryStorage):
        """
        Initialize the behavior tracker.

        Args:
            storage: Memory storage implementation
        """
        self.storage = storage
        logger.info("Initialized BehaviorTracker")

    async def track_conversation_frequency(self, user_id: str, timestamp: datetime) -> None:
        """
        Track conversation frequency for behavior analysis.

        Records conversation events to analyze usage patterns over time.
        """
        try:
            # Create a behavioral memory for conversation tracking
            from app.ai.memory.interfaces import MemoryImportance, MemoryMetadata, MemoryRecord

            behavior_memory = MemoryRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                memory_type=MemoryType.BEHAVIORAL,
                content=f"Conversation interaction at {timestamp.isoformat()}",
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=MemoryType.BEHAVIORAL,
                    importance=MemoryImportance.LOW,
                    source="system_tracking",
                    tags=["conversation", "frequency"],
                ),
                created_at=timestamp,
            )

            await self.storage.store(behavior_memory)

            logger.debug(f"Tracked conversation frequency for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to track conversation frequency: {e}")

    async def track_goal_completion(self, user_id: str, goal_id: str, completed: bool) -> None:
        """
        Track goal completion events.

        Records goal completion events to analyze achievement patterns.
        """
        try:
            from app.ai.memory.interfaces import MemoryImportance, MemoryMetadata, MemoryRecord

            status = "completed" if completed else "not_completed"
            content = f"Goal {goal_id} marked as {status}"

            behavior_memory = MemoryRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                memory_type=MemoryType.BEHAVIORAL,
                content=content,
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=MemoryType.BEHAVIORAL,
                    importance=MemoryImportance.MEDIUM if completed else MemoryImportance.LOW,
                    source="system_tracking",
                    tags=["goal", "completion", status],
                ),
                created_at=datetime.now(timezone.utc),
            )

            await self.storage.store(behavior_memory)

            logger.debug(f"Tracked goal completion for user {user_id}: {status}")

        except Exception as e:
            logger.error(f"Failed to track goal completion: {e}")

    async def track_habit_streak(self, user_id: str, habit_id: str, completed: bool) -> None:
        """
        Track habit streak information.

        Records habit completion events to analyze streak patterns.
        """
        try:
            from app.ai.memory.interfaces import MemoryImportance, MemoryMetadata, MemoryRecord

            status = "completed" if completed else "missed"
            content = f"Habit {habit_id} {status}"

            behavior_memory = MemoryRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                memory_type=MemoryType.BEHAVIORAL,
                content=content,
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=MemoryType.BEHAVIORAL,
                    importance=MemoryImportance.MEDIUM if completed else MemoryImportance.LOW,
                    source="system_tracking",
                    tags=["habit", "streak", status],
                ),
                created_at=datetime.now(timezone.utc),
            )

            await self.storage.store(behavior_memory)

            logger.debug(f"Tracked habit streak for user {user_id}: {status}")

        except Exception as e:
            logger.error(f"Failed to track habit streak: {e}")

    async def track_journal_statistics(
        self, user_id: str, entry_id: str, mood_score: Optional[int]
    ) -> None:
        """
        Track journal entry statistics.

        Records journal entries to analyze mood patterns and journaling frequency.
        """
        try:
            from app.ai.memory.interfaces import MemoryImportance, MemoryMetadata, MemoryRecord

            mood_text = f"with mood score {mood_score}" if mood_score else "without mood score"
            content = f"Journal entry {entry_id} {mood_text}"

            behavior_memory = MemoryRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                memory_type=MemoryType.BEHAVIORAL,
                content=content,
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=MemoryType.BEHAVIORAL,
                    importance=MemoryImportance.MEDIUM,
                    source="system_tracking",
                    tags=["journal", "mood"] + ([f"mood_{mood_score}"] if mood_score else []),
                ),
                created_at=datetime.now(timezone.utc),
            )

            await self.storage.store(behavior_memory)

            logger.debug(f"Tracked journal statistics for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to track journal statistics: {e}")

    async def get_behavior_summary(
        self, user_id: str, time_range: Optional[tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get behavioral summary for a user.

        Analyzes behavioral memories to provide insights about:
        - Conversation patterns
        - Goal completion rates
        - Habit streaks
        - Journal frequency and mood trends
        - Overall engagement levels
        """
        try:
            # Get behavioral memories
            if time_range:
                # Apply time range filtering (would need storage support)
                memories = await self.storage.list_user_memories(
                    user_id=user_id, memory_type=MemoryType.BEHAVIORAL, limit=10000, offset=0
                )
                memories = [m for m in memories if time_range[0] <= m.created_at <= time_range[1]]
            else:
                memories = await self.storage.list_user_memories(
                    user_id=user_id, memory_type=MemoryType.BEHAVIORAL, limit=10000, offset=0
                )

            # Analyze patterns
            summary = {
                "total_behavioral_events": len(memories),
                "conversation_frequency": self._analyze_conversation_frequency(memories),
                "goal_completion_rate": self._analyze_goal_completion(memories),
                "habit_streak_summary": self._analyze_habit_streaks(memories),
                "journal_statistics": self._analyze_journal_patterns(memories),
                "overall_engagement": self._calculate_engagement_score(memories),
                "time_range": {
                    "start": time_range[0].isoformat() if time_range else None,
                    "end": time_range[1].isoformat() if time_range else None,
                }
                if time_range
                else "all_time",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Generated behavior summary for user {user_id}")
            return summary

        except Exception as e:
            logger.error(f"Failed to get behavior summary for user {user_id}: {e}")
            return {}

    def _analyze_conversation_frequency(self, memories: List) -> Dict[str, Any]:
        """Analyze conversation frequency patterns."""
        conversation_memories = [m for m in memories if "conversation" in m.metadata.tags]

        if not conversation_memories:
            return {"count": 0, "frequency": "none"}

        # Group by day
        daily_counts = defaultdict(int)
        for memory in conversation_memories:
            date = memory.created_at.date()
            daily_counts[date] += 1

        # Calculate average daily frequency
        if daily_counts:
            avg_daily = sum(daily_counts.values()) / len(daily_counts)
            frequency_level = "high" if avg_daily > 5 else "medium" if avg_daily > 2 else "low"
        else:
            avg_daily = 0
            frequency_level = "none"

        return {
            "count": len(conversation_memories),
            "frequency": frequency_level,
            "average_daily": round(avg_daily, 2),
            "active_days": len(daily_counts),
        }

    def _analyze_goal_completion(self, memories: List) -> Dict[str, Any]:
        """Analyze goal completion patterns."""
        goal_memories = [
            m for m in memories if "goal" in m.metadata.tags and "completion" in m.metadata.tags
        ]

        if not goal_memories:
            return {"total": 0, "completed": 0, "rate": 0.0}

        completed = sum(1 for m in goal_memories if "completed" in m.metadata.tags)

        completion_rate = completed / len(goal_memories) if goal_memories else 0.0

        return {
            "total": len(goal_memories),
            "completed": completed,
            "not_completed": len(goal_memories) - completed,
            "rate": round(completion_rate, 2),
        }

    def _analyze_habit_streaks(self, memories: List) -> Dict[str, Any]:
        """Analyze habit streak patterns."""
        habit_memories = [
            m for m in memories if "habit" in m.metadata.tags and "streak" in m.metadata.tags
        ]

        if not habit_memories:
            return {"total": 0, "completed": 0, "missed": 0}

        completed = sum(1 for m in habit_memories if "completed" in m.metadata.tags)

        return {
            "total": len(habit_memories),
            "completed": completed,
            "missed": len(habit_memories) - completed,
            "completion_rate": round(completed / len(habit_memories), 2) if habit_memories else 0.0,
        }

    def _analyze_journal_patterns(self, memories: List) -> Dict[str, Any]:
        """Analyze journal patterns and mood trends."""
        journal_memories = [m for m in memories if "journal" in m.metadata.tags]

        if not journal_memories:
            return {"total": 0, "with_mood": 0, "average_mood": None}

        # Extract mood scores
        mood_scores = []
        for memory in journal_memories:
            for tag in memory.metadata.tags:
                if tag.startswith("mood_"):
                    try:
                        mood = int(tag.split("_")[1])
                        mood_scores.append(mood)
                    except (ValueError, IndexError):
                        pass

        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else None

        return {
            "total": len(journal_memories),
            "with_mood": len(mood_scores),
            "average_mood": round(avg_mood, 2) if avg_mood else None,
            "mood_distribution": self._get_mood_distribution(mood_scores) if mood_scores else {},
        }

    def _get_mood_distribution(self, mood_scores: List[int]) -> Dict[str, int]:
        """Get distribution of mood scores."""
        distribution = defaultdict(int)
        for mood in mood_scores:
            if mood >= 8:
                distribution["high"] += 1
            elif mood >= 5:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return dict(distribution)

    def _calculate_engagement_score(self, memories: List) -> Dict[str, Any]:
        """Calculate overall engagement score."""
        if not memories:
            return {"score": 0.0, "level": "none"}

        # Calculate based on total events and recency
        total_events = len(memories)

        # Get most recent event
        most_recent = max(memories, key=lambda m: m.created_at)
        days_since_last = (datetime.now(timezone.utc) - most_recent.created_at).days

        # Engagement score calculation
        recency_score = max(0, 1 - (days_since_last / 30))  # Decay over 30 days
        volume_score = min(total_events / 100, 1.0)  # Cap at 100 events

        engagement_score = (recency_score * 0.7) + (volume_score * 0.3)

        engagement_level = (
            "high" if engagement_score > 0.7 else "medium" if engagement_score > 0.4 else "low"
        )

        return {
            "score": round(engagement_score, 2),
            "level": engagement_level,
            "total_events": total_events,
            "days_since_last": days_since_last,
        }
