# apps/backend/app/core/beat_config.py
"""
Celery Beat Configuration for Lumenly Coaching Engine.

This module configures the Celery Beat scheduler for periodic tasks:
- Proactive nudger: Every 15 minutes
- Reflection scheduler: Every hour
- Additional periodic tasks as needed
"""

from celery.schedules import crontab

beat_schedule = {
    # Proactive nudger - runs every 15 minutes
    "proactive-nudger-every-15-minutes": {
        "task": "app.workers.nudger.proactive_nudger_task",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {
            "queue": "coaching_operations",
        },
    },
    # Reflection scheduler - runs every hour to check for users due for reflection
    "reflection-scheduler-every-hour": {
        "task": "app.workers.reflection.schedule_reflection_tasks",
        "schedule": crontab(minute=0),  # Every hour at minute 0
        "options": {
            "queue": "coaching_operations",
        },
    },
}
