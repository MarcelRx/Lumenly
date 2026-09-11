# apps/backend/app/workers/reflection.py
import logging
import uuid
from datetime import datetime, timedelta

from celery import shared_task
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.reflection.end_day_reflection_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def end_day_reflection_task(self, user_id: str, time_zone: str):
    """
    End-Day Reflection Loop Celery task.

    Scheduled at user's local midnight to:
    - Analyze journal sentiment trends
    - Generate action recommendations
    - Store insights to ai_insights table

    Uses synchronous providers only (no async/await in Celery).

    Args:
        user_id: User ID (as string for Celery serialization)
        time_zone: User's time zone (e.g., "America/New_York")
    """
    logger.info(f"Starting End-Day Reflection task for user {user_id} in {time_zone}")

    try:
        user_uuid = uuid.UUID(user_id)

        # Analyze journal sentiment trends
        sentiment_analysis = _analyze_journal_sentiment(user_uuid)
        logger.info(f"Sentiment analysis for user {user_id}: {sentiment_analysis}")

        # Generate action recommendations
        recommendations = _generate_recommendations(user_uuid, sentiment_analysis)
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")

        # Store insights to ai_insights table
        insights_stored = _store_reflection_insights(
            user_uuid,
            sentiment_analysis,
            recommendations
        )
        logger.info(f"Stored {insights_stored} insights for user {user_id}")

        logger.info(f"End-Day Reflection task completed for user {user_id}")
        return {
            "status": "success",
            "user_id": user_id,
            "insights_stored": insights_stored,
            "sentiment_trend": sentiment_analysis.get("trend", "unknown")
        }

    except Exception as e:
        logger.error(f"End-Day Reflection task failed for user {user_id}: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


def _analyze_journal_sentiment(user_id: uuid.UUID) -> dict:
    """
    Analyze journal sentiment trends for a user.

    Uses synchronous MongoDB client (no async/await).
    Queries actual journal entries and calculates sentiment trends.
    """
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command('ping')

        db_name = settings.MONGODB_URL.split('/')[-1] if '/' in settings.MONGODB_URL else 'lumenly'
        db = mongo_client[db_name]
        journal_collection = db["journal_entries"]

        # Get journal entries from the last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        journal_entries = list(journal_collection.find(
            {
                "user_id": user_id,
                "created_at": {"$gte": week_ago}
            }
        ).sort("created_at", 1))

        if not journal_entries:
            return {
                "trend": "insufficient_data",
                "average_sentiment": 0.5,
                "sentiment_change": 0.0,
                "journal_entries_analyzed": 0,
                "time_period": "last_7_days"
            }

        # Analyze mood scores (normalize to 0-1 range)
        mood_scores = []
        for entry in journal_entries:
            if entry.get("mood_score") is not None:
                # Normalize 1-10 to 0-1
                normalized_score = (entry["mood_score"] - 1) / 9
                mood_scores.append(normalized_score)

        if not mood_scores:
            return {
                "trend": "no_mood_data",
                "average_sentiment": 0.5,
                "sentiment_change": 0.0,
                "journal_entries_analyzed": len(journal_entries),
                "time_period": "last_7_days"
            }

        # Calculate average sentiment
        average_sentiment = sum(mood_scores) / len(mood_scores)

        # Calculate trend (compare first half with second half)
        mid_point = len(mood_scores) // 2
        if mid_point > 0:
            first_half_avg = sum(mood_scores[:mid_point]) / mid_point
            second_half_avg = sum(mood_scores[mid_point:]) / (len(mood_scores) - mid_point)
            sentiment_change = second_half_avg - first_half_avg

            if sentiment_change > 0.1:
                trend = "improving"
            elif sentiment_change < -0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            sentiment_change = 0.0
            trend = "stable"

        mongo_client.close()

        return {
            "trend": trend,
            "average_sentiment": average_sentiment,
            "sentiment_change": sentiment_change,
            "journal_entries_analyzed": len(journal_entries),
            "time_period": "last_7_days"
        }

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in reflection analysis: {e}")
        return {
            "trend": "error",
            "average_sentiment": 0.5,
            "sentiment_change": 0.0,
            "journal_entries_analyzed": 0,
            "time_period": "last_7_days"
        }
    except Exception as e:
        logger.error(f"Failed to analyze journal sentiment for user {user_id}: {e}")
        return {
            "trend": "error",
            "average_sentiment": 0.5,
            "sentiment_change": 0.0,
            "journal_entries_analyzed": 0,
            "time_period": "last_7_days"
        }


def _generate_recommendations(user_id: uuid.UUID, sentiment_analysis: dict) -> list[str]:
    """
    Generate action recommendations based on sentiment analysis.

    Uses synchronous approach for Celery compatibility.
    Generates personalized recommendations based on actual sentiment trends.
    """
    trend = sentiment_analysis.get("trend", "stable")
    average_sentiment = sentiment_analysis.get("average_sentiment", 0.5)
    journal_count = sentiment_analysis.get("journal_entries_analyzed", 0)

    recommendations = []

    # Base recommendations on trend and sentiment
    if trend == "improving":
        recommendations.extend([
            "Continue your current journaling practice - it's working well!",
            "Consider sharing your progress with a trusted friend or family member",
            "Try adding a gratitude component to your routine to amplify positivity"
        ])
    elif trend == "declining":
        recommendations.extend([
            "Remember that it's okay to have difficult days - self-compassion is important",
            "Try a brief meditation or breathing exercise before journaling",
            "Focus on small, achievable goals for tomorrow rather than overwhelming yourself"
        ])
    else:  # stable
        recommendations.extend([
            "Maintain your current routine - consistency is key",
            "Try varying your journaling prompts to gain fresh perspectives",
            "Consider tracking additional metrics like sleep quality or energy levels"
        ])

    # Add sentiment-specific recommendations
    if average_sentiment < 0.4:  # Low sentiment
        recommendations.append("If you're feeling persistently low, consider reaching out to a mental health professional")
    elif average_sentiment > 0.7:  # High sentiment
        recommendations.append("Your positive outlook is great - consider setting slightly more challenging goals")

    # Add journaling frequency recommendations
    if journal_count < 3:
        recommendations.append("Try to journal more frequently - even brief entries can be valuable")
    elif journal_count > 7:
        recommendations.append("Your consistent journaling is excellent - consider exploring deeper reflection prompts")

    return recommendations[:5]  # Limit to top 5 recommendations


def _store_reflection_insights(
    user_id: uuid.UUID,
    sentiment_analysis: dict,
    recommendations: list[str]
) -> int:
    """
    Store reflection insights to ai_insights table.

    Uses synchronous MongoDB client (no async/await).
    Creates AIInsight documents with proper TTL and multi-tenant isolation.
    """
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command('ping')

        db_name = settings.MONGODB_URL.split('/')[-1] if '/' in settings.MONGODB_URL else 'lumenly'
        db = mongo_client[db_name]
        insights_collection = db["ai_insights"]

        # Calculate expiration (30 days from now)
        expires_at = datetime.now() + timedelta(days=30)

        # Create wellness trend insight
        trend_insight = {
            "user_id": user_id,
            "insight_type": "wellness_trend",
            "pillar": "mental_health",
            "payload": {
                "trend": sentiment_analysis.get("trend", "unknown"),
                "average_sentiment": sentiment_analysis.get("average_sentiment", 0.5),
                "sentiment_change": sentiment_analysis.get("sentiment_change", 0.0),
                "journal_entries_analyzed": sentiment_analysis.get("journal_entries_analyzed", 0),
                "time_period": sentiment_analysis.get("time_period", "last_7_days")
            },
            "confidence": 0.8 if sentiment_analysis.get("journal_entries_analyzed", 0) >= 3 else 0.5,
            "session_id": None,
            "generated_at": datetime.now(),
            "expires_at": expires_at,
            "created_at": datetime.now()
        }

        # Create recommendations insight
        recommendations_insight = {
            "user_id": user_id,
            "insight_type": "habit_recommendation",
            "pillar": "self_care",
            "payload": {
                "recommendations": recommendations,
                "trend_context": sentiment_analysis.get("trend", "unknown"),
                "priority": "high" if sentiment_analysis.get("trend") == "declining" else "normal"
            },
            "confidence": 0.7,
            "session_id": None,
            "generated_at": datetime.now(),
            "expires_at": expires_at,
            "created_at": datetime.now()
        }

        # Insert insights
        insights_collection.insert_one(trend_insight)
        insights_collection.insert_one(recommendations_insight)

        mongo_client.close()

        logger.info(
            f"Stored 2 reflection insights for user {user_id}: "
            f"trend={sentiment_analysis.get('trend')}, "
            f"recommendations={len(recommendations)}"
        )

        return 2  # Return count of insights stored

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in reflection insight storage: {e}")
        return 0
    except Exception as e:
        logger.error(f"Failed to store reflection insights for user {user_id}: {e}")
        return 0


@shared_task(
    name="app.workers.reflection.schedule_reflection_tasks",
)
def schedule_reflection_tasks():
    """
    Schedule reflection tasks for all users at their local midnight.

    This task runs periodically (e.g., every hour) to check which users
    need their reflection task scheduled based on their time zone.

    Uses synchronous MongoDB client (no async/await).
    """
    logger.info("Scheduling reflection tasks for all users")

    try:
        # Get all users with their time zones (placeholder)
        # Actual implementation would query MongoDB for users
        users = _get_all_users_with_time_zones()

        tasks_scheduled = 0
        for user_id, time_zone in users:
            # Check if user's local midnight is approaching
            if _is_local_midnight_approaching(time_zone):
                # Schedule reflection task
                end_day_reflection_task.delay(str(user_id), time_zone)
                tasks_scheduled += 1
                logger.info(f"Scheduled reflection task for user {user_id} in {time_zone}")

        logger.info(f"Scheduled {tasks_scheduled} reflection tasks")
        return {
            "status": "success",
            "tasks_scheduled": tasks_scheduled
        }

    except Exception as e:
        logger.error(f"Failed to schedule reflection tasks: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def _get_all_users_with_time_zones() -> list[tuple[uuid.UUID, str]]:
    """
    Get all users with their time zones.

    Uses synchronous PostgreSQL client (no async/await).
    Queries PostgreSQL users table for timezone information.
    """
    try:
        from sqlalchemy import create_engine, text

        from app.core.config import settings

        # Create synchronous PostgreSQL engine
        engine = create_engine(settings.POSTGRES_URL.replace("+asyncpg", ""))

        with engine.connect() as connection:
            # Query for users with their time zones
            # Assuming there's a profiles table with timezone info
            query = text("""
                SELECT u.id, p.time_zone
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                WHERE u.is_active = true
                AND p.time_zone IS NOT NULL
            """)

            result = connection.execute(query)
            users = [(row[0], row[1]) for row in result]

            logger.info(f"Retrieved {len(users)} users with time zones")
            return users

    except Exception as e:
        logger.error(f"Failed to get users with time zones: {e}")
        return []


def _is_local_midnight_approaching(time_zone: str) -> bool:
    """
    Check if local midnight is approaching for a given time zone.

    Uses timezone-aware datetime comparison.
    Returns True if the user's local midnight is within the next hour.
    """
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        # Get current UTC time
        utc_now = datetime.now()

        # Convert to user's local timezone
        user_tz = ZoneInfo(time_zone)
        local_now = utc_now.replace(tzinfo=ZoneInfo("UTC")).astimezone(user_tz)

        # Calculate local midnight for today
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

        # If we've passed midnight today, use tomorrow's midnight
        if local_now >= local_midnight:
            from datetime import timedelta
            local_midnight += timedelta(days=1)

        # Check if midnight is within the next hour
        time_until_midnight = (local_midnight - local_now).total_seconds()

        return 0 <= time_until_midnight <= 3600  # Within next hour

    except Exception as e:
        logger.error(f"Failed to check local midnight for timezone {time_zone}: {e}")
        return False
