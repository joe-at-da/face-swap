import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import psutil
import json
from datetime import datetime

from backend.api import deps
from backend.db.models.user import User, UserRole
from backend.services.system.docker_metrics import DockerMetrics

router = APIRouter()

@router.get("/", response_class=PlainTextResponse)
async def get_metrics():
    """
    Get system metrics for Prometheus.
    This endpoint returns basic system metrics in a format Prometheus can scrape.
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Format metrics for Prometheus
        metrics = []
        
        # CPU metrics
        metrics.append(f'# HELP cpu_usage_percent CPU usage percentage')
        metrics.append(f'# TYPE cpu_usage_percent gauge')
        metrics.append(f'cpu_usage_percent {cpu_percent}')
        
        # Memory metrics
        metrics.append(f'# HELP memory_usage_percent Memory usage percentage')
        metrics.append(f'# TYPE memory_usage_percent gauge')
        metrics.append(f'memory_usage_percent {memory_percent}')
        
        # Disk metrics
        metrics.append(f'# HELP disk_usage_percent Disk usage percentage')
        metrics.append(f'# TYPE disk_usage_percent gauge')
        metrics.append(f'disk_usage_percent {disk_percent}')
        
        # Try to get Docker metrics if available
        try:
            containers = DockerMetrics.get_container_stats()
            for container in containers:
                name = container.get('name', 'unknown').replace('-', '_')
                
                # Container CPU metrics
                cpu = container.get('cpu_percent', 0)
                metrics.append(f'# HELP container_{name}_cpu_percent CPU usage percentage for container {name}')
                metrics.append(f'# TYPE container_{name}_cpu_percent gauge')
                metrics.append(f'container_{name}_cpu_percent {cpu}')
                
                # Container memory metrics
                memory = container.get('memory_percent', 0)
                metrics.append(f'# HELP container_{name}_memory_percent Memory usage percentage for container {name}')
                metrics.append(f'# TYPE container_{name}_memory_percent gauge')
                metrics.append(f'container_{name}_memory_percent {memory}')
        except Exception as e:
            # Just log the error and continue without Docker metrics
            logging.error(f"Error getting Docker metrics: {str(e)}")
        
        return '\n'.join(metrics)
    except Exception as e:
        logging.error(f"Error generating metrics: {str(e)}")
        return f"# Error generating metrics: {str(e)}"
