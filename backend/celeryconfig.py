"""
Celery configuration file.
This file is required for Celery to start properly.
"""
from backend.core.config import settings

# Broker settings
broker_url = settings.REDIS_URL
result_backend = settings.REDIS_URL

# Task serialization format
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# Time zone settings
timezone = 'Europe/London'
enable_utc = True

# Task routes
task_routes = {
    'backend.services.tasks.*': {'queue': 'default'},
}

# Task execution settings
task_acks_late = True
worker_prefetch_multiplier = 1

# Task result settings
task_ignore_result = False
task_store_errors_even_if_ignored = True

# Logging
worker_redirect_stdouts = False
worker_log_format = '%(asctime)s [%(process)d] [%(levelname)s] %(message)s'
worker_task_log_format = '%(asctime)s [%(process)d] [%(levelname)s] [%(task_name)s(%(task_id)s)] %(message)s'
