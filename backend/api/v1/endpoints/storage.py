from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole
from backend.services.video.storage import StorageManager
from backend.services.tasks import storage_tasks

router = APIRouter()

@router.get("/stats", response_model=Dict)
async def get_storage_stats(
    current_user: models.User = Depends(get_current_user)
):
    """Get detailed storage usage statistics."""
    has_permission(current_user, [UserRole.ADMIN])
    
    storage = StorageManager()
    return storage.get_storage_stats()

@router.post("/cleanup", response_model=Dict)
async def cleanup_storage(
    background_tasks: BackgroundTasks,
    max_age_hours: int = 24,
    current_user: models.User = Depends(get_current_user)
):
    """
    Clean up temporary storage by removing old files.
    This operation runs in the background.
    """
    has_permission(current_user, [UserRole.ADMIN])
    
    # Start cleanup task in the background
    task = storage_tasks.cleanup_temp_storage.delay(max_age_hours=max_age_hours)
    
    return {
        "status": "started",
        "task_id": task.id,
        "message": f"Storage cleanup started for files older than {max_age_hours} hours"
    }

@router.post("/archive", response_model=Dict)
async def archive_media(
    max_age_days: int = 90,
    current_user: models.User = Depends(get_current_user)
):
    """
    Archive old media files to the archive directory.
    This operation runs in the background.
    """
    has_permission(current_user, [UserRole.ADMIN])
    
    # Start archive task in the background
    task = storage_tasks.archive_old_media.delay(max_age_days=max_age_days)
    
    return {
        "status": "started",
        "task_id": task.id,
        "message": f"Archiving media files older than {max_age_days} days"
    }

@router.post("/compress", response_model=Dict)
async def compress_videos(
    min_size_mb: int = 500,
    quality: str = "medium",
    current_user: models.User = Depends(get_current_user)
):
    """
    Compress large video files to save storage space.
    This operation runs in the background.
    
    Args:
        min_size_mb: Minimum size in MB to consider a video for compression
        quality: Compression quality ('low', 'medium', 'high')
    """
    has_permission(current_user, [UserRole.ADMIN])
    
    # Validate quality parameter
    if quality not in ["low", "medium", "high"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quality must be one of: low, medium, high"
        )
    
    # Start compression task in the background
    task = storage_tasks.compress_large_videos.delay(
        min_size_mb=min_size_mb,
        quality=quality
    )
    
    return {
        "status": "started",
        "task_id": task.id,
        "message": f"Compressing videos larger than {min_size_mb} MB with {quality} quality"
    }

@router.post("/backup", response_model=Dict)
async def create_backup(
    include_media: bool = False,
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a system backup.
    This operation runs in the background.
    
    Args:
        include_media: Whether to include media files in the backup
    """
    has_permission(current_user, [UserRole.ADMIN])
    
    # Start backup task in the background
    task = storage_tasks.create_system_backup.delay(include_media=include_media)
    
    return {
        "status": "started",
        "task_id": task.id,
        "message": f"Creating system backup {'with' if include_media else 'without'} media files"
    }
