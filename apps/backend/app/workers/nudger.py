# apps/backend/app/workers/nudger.py
import logging
import uuid
from datetime import datetime, timedelta

from celery import shared_task
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


@shared_task(
    name="app.workers.nudger.proactive_nudger_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def proactive_nudger_task(self):
    """
    Proactive Nudger Celery worker - runs every 15 minutes.

    Queries users with:
    - Missed habits
    - Wellness score drops
    - Upcoming goal deadlines

    Generates personalized nudges via Nudge agent and delivers as in-app messages.

    Uses synchronous providers only (no async/await in Celery).
    """
    logger.info("Starting Proactive Nudger task")

    try:
        # Query users with missed habits (placeholder - actual implementation would query MongoDB)
        users_with_missed_habits = _get_users_with_missed_habits()
        logger.info(f"Found {len(users_with_missed_habits)} users with missed habits")

        # Query users with wellness score drops (placeholder)
        users_with_wellness_drops = _get_users_with_wellness_drops()
        logger.info(f"Found {len(users_with_wellness_drops)} users with wellness drops")

        # Query users with upcoming deadlines (placeholder)
        users_with_upcoming_deadlines = _get_users_with_upcoming_deadlines()
        logger.info(f"Found {len(users_with_upcoming_deadlines)} users with upcoming deadlines")

        # Combine unique users who need nudges
        all_users_needing_nudges = set(
            users_with_missed_habits + users_with_wellness_drops + users_with_upcoming_deadlines
        )

        logger.info(f"Total unique users needing nudges: {len(all_users_needing_nudges)}")

        # Generate and deliver nudges for each user
        nudges_delivered = 0
        for user_id in all_users_needing_nudges:
            try:
                # Generate personalized nudge
                nudge_content = _generate_personalized_nudge(user_id)

                if nudge_content:
                    # Deliver as in-app message (placeholder - would write to messages table)
                    _deliver_nudge(user_id, nudge_content)
                    nudges_delivered += 1
                    logger.info(f"Delivered nudge to user {user_id}")

            except Exception as e:
                logger.error(f"Failed to deliver nudge to user {user_id}: {e}")
                continue

        logger.info(f"Proactive Nudger task completed. Delivered {nudges_delivered} nudges")
        return {
            "status": "success",
            "users_processed": len(all_users_needing_nudges),
            "nudges_delivered": nudges_delivered,
        }

    except Exception as e:
        logger.error(f"Proactive Nudger task failed: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries))


def _get_users_with_missed_habits() -> list[uuid.UUID]:
    """
    Query users with missed habits.

    Uses synchronous MongoDB client (no async/await).
    Returns users who have habits with streak_count < 3 (indicating missed check-ins).
    """
    try:
        # Initialize synchronous MongoDB client
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        # Test connection
        mongo_client.admin.command("ping")

        # Get database name from URL
        db_name = settings.MONGODB_URL.split("/")[-1] if "/" in settings.MONGODB_URL else "lumenly"
        db = mongo_client[db_name]
        habits_collection = db["habits"]

        # Query for habits with low streak counts (indicating missed habits)
        # Aggregate to get unique user_ids
        pipeline = [
            {"$match": {"streak_count": {"$lt": 3}}},
            {"$group": {"_id": "$user_id"}},
            {"$project": {"user_id": "$_id", "_id": 0}},
        ]

        results = list(habits_collection.aggregate(pipeline))

        # Convert to UUID list
        user_ids = [uuid.UUID(result["user_id"]) for result in results]

        mongo_client.close()

        logger.info(f"Found {len(user_ids)} users with missed habits")
        return user_ids

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in nudger: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to query users with missed habits: {e}")
        return []


def _get_users_with_wellness_drops() -> list[uuid.UUID]:
    """
    Query users with wellness score drops.

    Uses synchronous MongoDB client (no async/await).
    Returns users whose journal mood scores dropped by more than 1.5 points in the last 7 days.
    """
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command("ping")

        db_name = settings.MONGODB_URL.split("/")[-1] if "/" in settings.MONGODB_URL else "lumenly"
        db = mongo_client[db_name]
        journal_collection = db["journal_entries"]

        # Calculate date threshold (7 days ago)
        week_ago = datetime.now() - timedelta(days=7)

        # Aggregate to find users with declining mood scores
        pipeline = [
            {"$match": {"created_at": {"$gte": week_ago}, "mood_score": {"$ne": None}}},
            {"$sort": {"created_at": 1}},
            {
                "$group": {
                    "_id": "$user_id",
                    "first_score": {"$first": "$mood_score"},
                    "last_score": {"$last": "$mood_score"},
                    "entry_count": {"$sum": 1},
                }
            },
            {
                "$match": {
                    "entry_count": {"$gte": 2},  # Need at least 2 entries to calculate trend
                    "$expr": {"$lt": ["$last_score", "$first_score"]},  # Declining
                }
            },
            {
                "$project": {
                    "user_id": "$_id",
                    "score_drop": {"$subtract": ["$first_score", "$last_score"]},
                    "_id": 0,
                }
            },
            {"$match": {"score_drop": {"$gte": 1.5}}},  # Significant drop
        ]

        results = list(journal_collection.aggregate(pipeline))

        user_ids = [uuid.UUID(result["user_id"]) for result in results]

        mongo_client.close()

        logger.info(f"Found {len(user_ids)} users with wellness drops")
        return user_ids

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in nudger wellness query: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to query users with wellness drops: {e}")
        return []


def _get_users_with_upcoming_deadlines() -> list[uuid.UUID]:
    """
    Query users with upcoming goal deadlines.

    Uses synchronous MongoDB client (no async/await).
    Returns users with uncompleted goals due within the next 7 days.
    """
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command("ping")

        db_name = settings.MONGODB_URL.split("/")[-1] if "/" in settings.MONGODB_URL else "lumenly"
        db = mongo_client[db_name]
        goals_collection = db["goals"]

        # Calculate date threshold (7 days from now)
        upcoming_deadline = datetime.now() + timedelta(days=7)

        # Query for uncompleted goals with upcoming deadlines
        query = {"is_completed": False, "target_date": {"$lte": upcoming_deadline}}

        # Get unique user_ids
        results = list(goals_collection.find(query, {"user_id": 1}).distinct("user_id"))

        user_ids = [uuid.UUID(user_id) for user_id in results]

        mongo_client.close()

        logger.info(f"Found {len(user_ids)} users with upcoming deadlines")
        return user_ids

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in nudger deadline query: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to query users with upcoming deadlines: {e}")
        return []


def _generate_personalized_nudge(user_id: uuid.UUID) -> str:
    """
    Generate a personalized nudge for a user.

    Uses synchronous approach for Celery compatibility.
    Generates context-aware nudges based on the user's actual state.
    """
    try:
        # Gather user context
        context = _gather_user_context(user_id)

        # For Celery compatibility, we'll use a simple template-based approach
        # In production, this would use a synchronous LLM provider or call an API
        # that doesn't require async/await

        missed_habits = context.get("missed_habits", 0)
        wellness_score = context.get("wellness_score", 70)
        upcoming_deadlines = context.get("upcoming_deadlines", 0)

        # Generate personalized nudge based on context
        if missed_habits > 0:
            nudge = f"Hi! I noticed you missed {missed_habits} habit check-in(s) recently. Would you like to reschedule or adjust your routine?"
        elif upcoming_deadlines > 0:
            nudge = f"You have {upcoming_deadlines} goal(s) coming up soon. How can I help you stay on track?"
        elif wellness_score < 60:
            nudge = "I've noticed your wellness score has been lower lately. Remember to be kind to yourself - small steps forward still count!"
        elif wellness_score > 80:
            nudge = "You're doing great! Your consistency is really paying off. Keep up the excellent work!"
        else:
            nudge = "Just checking in - how are you feeling about your progress today?"

        return nudge

    except Exception as e:
        logger.error(f"Failed to generate personalized nudge for user {user_id}: {e}")
        # Fallback to generic nudge
        return "Hi! Just checking in - how are you doing with your goals today?"


def _gather_user_context(user_id: uuid.UUID) -> dict:
    """Gather context about a user for personalized nudges."""
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command("ping")

        db_name = settings.MONGODB_URL.split("/")[-1] if "/" in settings.MONGODB_URL else "lumenly"
        db = mongo_client[db_name]

        # Get habit streak info
        habits_collection = db["habits"]
        habit_info = list(habits_collection.find({"user_id": user_id}, {"streak_count": 1}))
        avg_streak = (
            sum(h.get("streak_count", 0) for h in habit_info) / len(habit_info) if habit_info else 0
        )

        # Get wellness info (average recent mood score)
        journal_collection = db["journal_entries"]
        week_ago = datetime.now() - timedelta(days=7)
        recent_journals = list(
            journal_collection.find(
                {"user_id": user_id, "created_at": {"$gte": week_ago}, "mood_score": {"$ne": None}},
                {"mood_score": 1},
            )
        )
        avg_mood = (
            sum(j.get("mood_score", 5) for j in recent_journals) / len(recent_journals)
            if recent_journals
            else 70
        )

        # Get upcoming goals
        goals_collection = db["goals"]
        upcoming_deadline = datetime.now() + timedelta(days=7)
        upcoming_goals = goals_collection.count_documents(
            {"user_id": user_id, "is_completed": False, "target_date": {"$lte": upcoming_deadline}}
        )

        mongo_client.close()

        return {
            "missed_habits": sum(1 for h in habit_info if h.get("streak_count", 0) < 3),
            "wellness_score": avg_mood * 10,  # Convert to 0-100 scale
            "upcoming_deadlines": upcoming_goals,
            "average_streak": avg_streak,
        }

    except Exception as e:
        logger.error(f"Failed to gather user context for {user_id}: {e}")
        return {
            "missed_habits": 0,
            "wellness_score": 70,
            "upcoming_deadlines": 0,
            "average_streak": 0,
        }


def _deliver_nudge(user_id: uuid.UUID, nudge_content: str) -> None:
    """
    Deliver a nudge as an in-app message with persistent storage.

    Uses synchronous MongoDB client (no async/await).
    Stores the nudge in the messages collection for the user.
    """
    try:
        mongo_client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=30000,
            connectTimeoutMS=5000,
        )

        mongo_client.admin.command("ping")

        db_name = settings.MONGODB_URL.split("/")[-1] if "/" in settings.MONGODB_URL else "lumenly"
        db = mongo_client[db_name]
        messages_collection = db["in_app_messages"]

        # Create message document
        message_document = {
            "user_id": user_id,
            "message_type": "nudge",
            "content": nudge_content,
            "created_at": datetime.now(),
            "read": False,
            "metadata": {"source": "proactive_nudger", "priority": "normal"},
        }

        # Insert message
        result = messages_collection.insert_one(message_document)

        mongo_client.close()

        logger.info(
            f"Nudge delivered to user {user_id} (message_id: {result.inserted_id}): "
            f"{nudge_content[:50]}..."
        )

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection failed in nudge delivery: {e}")
    except Exception as e:
        logger.error(f"Failed to deliver nudge to user {user_id}: {e}")
