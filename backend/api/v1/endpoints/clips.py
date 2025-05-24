from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.schemas.video import VideoClipCreate, VideoClipUpdate, VideoClipResponse
from backend.services.tasks import video_tasks
from backend.core.config import settings
from backend.services.video.storage import StorageManager

router = APIRouter()

@router.post("/", response_model=VideoClipResponse)
async def create_clip(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    clip_data: VideoClipCreate
):
    """Create a new video clip from an active or completed capture."""
    has_permission(current_user, ["ADMIN", "MP", "STAFF"])
    
    # Validate time range
    if clip_data.end_time <= clip_data.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    duration = (clip_data.end_time - clip_data.start_time).total_seconds() / 60
    if duration > settings.MAX_CLIP_DURATION_MINUTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clip duration cannot exceed {settings.MAX_CLIP_DURATION_MINUTES} minutes"
        )
    
    # Get capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == clip_data.capture_session_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture session not found"
        )
    
    # Create clip record
    clip = models.VideoClip(
        title=clip_data.title,
        description=clip_data.description,
        user_id=current_user.id,
        capture_session_id=capture.id,
        start_time=clip_data.start_time,
        end_time=clip_data.end_time,
        status=models.ClipStatus.PROCESSING
    )
    
    db.add(clip)
    db.commit()
    db.refresh(clip)
    
    # Start clip creation task
    video_tasks.create_video_clip.delay(
        source_file=f"{settings.TEMP_STORAGE_PATH}/capture_{capture.id}.mp4",
        clip_id=clip.id,
        start_time=clip_data.start_time.isoformat(),
        end_time=clip_data.end_time.isoformat()
    )
    
    return clip

@router.get("/{clip_id}", response_model=VideoClipResponse)
async def get_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    # Check permissions
    if clip.user_id != current_user.id and current_user.role not in ["ADMIN", "MP"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return clip

@router.get("/", response_model=List[VideoClipResponse])
async def list_clips(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List video clips."""
    query = db.query(models.VideoClip)
    
    # Filter by status if provided
    if status:
        query = query.filter(models.VideoClip.status == status)
    
    # Filter by user unless admin
    if current_user.role not in ["ADMIN", "MP"]:
        query = query.filter(models.VideoClip.user_id == current_user.id)
    
    clips = query.offset(skip).limit(limit).all()
    return clips

@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    # Check permissions
    if clip.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Delete file if it exists
    if clip.storage_path:
        storage = StorageManager()
        try:
            storage.delete_file(clip.storage_path)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Error deleting file {clip.storage_path}: {e}")
    
    db.delete(clip)
    db.commit()
    
    return None
