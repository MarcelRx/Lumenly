# apps/backend/app/core/celery_app.py
from celery import Celery

from app.core.beat_config import beat_schedule
from app.core.config import settings

celery_app = Celery(
    "lumenly",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.nudger", "app.workers.reflection"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Only acknowledge task after completion to handle failures properly
    worker_prefetch_multiplier=1,  # Disable prefetch to ensure fair task distribution
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies unexpectedly
    task_default_routing_key="default",
    task_routes={
        "app.workers.tasks.process_document_task": {"queue": "document_processing"},
        "app.workers.tasks.memory_consolidation_task": {"queue": "memory_operations"},
        "app.workers.tasks.memory_cleanup_task": {"queue": "memory_operations"},
        "app.workers.tasks.behavior_aggregation_task": {"queue": "memory_operations"},
        "app.workers.tasks.memory_summarization_task": {"queue": "memory_operations"},
        "app.workers.tasks.memory_forgetting_task": {"queue": "memory_operations"},
        "app.workers.nudger.proactive_nudger_task": {"queue": "coaching_operations"},
        "app.workers.reflection.end_day_reflection_task": {"queue": "coaching_operations"},
        "app.workers.reflection.schedule_reflection_tasks": {"queue": "coaching_operations"},
    },
    # Import beat schedule from external config
    beat_schedule=beat_schedule,
)
