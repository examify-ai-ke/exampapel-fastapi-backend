# Celery is good for data-intensive application or some long-running tasks in other simple cases use Fastapi background tasks
# Reference https://towardsdatascience.com/deploying-ml-models-in-production-with-fastapi-and-celery-7063e539a5db
from celery import Celery
from app.core.config import settings
import os
import pytz  # Add this import

# Define the Celery instance with the name "celery" to match imports
celery_app = Celery(
    "worker",
    # Use Redis as both broker and result backend
    backend=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD and settings.REDIS_USE_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    broker=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD and settings.REDIS_USE_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
)

# For backward compatibility - existing code is importing 'celery'
celery = celery_app  # Add this alias for backward compatibility

# Configure Celery - use pytz.timezone instead of zoneinfo
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",  # Use string instead of zoneinfo
    enable_utc=True,
    worker_concurrency=os.cpu_count() or 2,
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.tasks.*": {"queue": "main-queue"}
    }
)

# Disable the default backend_cleanup task that's causing issues
celery_app.conf.beat_schedule = {}

# Optional: Set up task error handling
@celery_app.task
def debug_task():
    print("Hello from Celery!")
