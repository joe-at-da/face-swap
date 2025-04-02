from celery import Celery
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "parliament_clips",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.video_tasks",
        "workers.transcription_tasks",
        "workers.social_tasks"
    ]
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/London",
    enable_utc=True,
)
