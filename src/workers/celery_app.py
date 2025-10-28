"""
Celery application configuration.
"""
from celery import Celery
from src.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "excel_differ",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.EXTRACTION_TIMEOUT_SECONDS,
    result_expires=settings.RESULT_TTL_SECONDS,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["src.workers"])
