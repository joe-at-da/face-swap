import os
from celery import Celery
from celery.schedules import crontab

from backend.core.config import settings

# Set environment variables for Celery
os.environ.setdefault('CELERY_CONFIG_MODULE', 'backend.celeryconfig')

# Create Celery app
celery_app = Celery('backend')

# Configure Celery
celery_app.conf.broker_url = settings.REDIS_URL
celery_app.conf.result_backend = settings.REDIS_URL
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.task_track_started = True
celery_app.conf.task_time_limit = 30 * 60  # 30 minutes
celery_app.conf.worker_prefetch_multiplier = 1

# Import tasks so they are registered with Celery
import backend.services.tasks.video_tasks
import backend.services.tasks.transcription_tasks
import backend.services.tasks.storage_tasks

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    # Daily cleanup of temporary files (run at 3:00 AM)
    'cleanup-temp-storage-daily': {
        'task': 'backend.services.tasks.storage_tasks.cleanup_temp_storage',
        'schedule': crontab(hour=3, minute=0),
        'args': (24,),  # max_age_hours
    },
    
    # Weekly archive of old media files (run on Sunday at 4:00 AM)
    'archive-old-media-weekly': {
        'task': 'backend.services.tasks.storage_tasks.archive_old_media',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        'args': (90,),  # max_age_days
    },
    
    # Weekly compression of large videos (run on Saturday at 2:00 AM)
    'compress-large-videos-weekly': {
        'task': 'backend.services.tasks.storage_tasks.compress_large_videos',
        'schedule': crontab(hour=2, minute=0, day_of_week=6),
        'args': (500, 'medium'),  # min_size_mb, quality
    },
    
    # Weekly system backup (run on Monday at 1:00 AM)
    'create-system-backup-weekly': {
        'task': 'backend.services.tasks.storage_tasks.create_system_backup',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),
        'kwargs': {'include_media': False},
    },
}

# Start Celery worker
if __name__ == '__main__':
    celery_app.start()
