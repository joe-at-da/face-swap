from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.api.deps import get_db, get_current_user, get_current_user_optional
from backend.db import models
from backend.db.models.user import UserRole, User as UserModel
from backend.schemas import video as schemas
from backend.core.security import has_permission
# Import ClipStatus from the enums.py file
from backend.db.models.enums import ClipStatus

router = APIRouter()

@router.get("/")
async def list_clips(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
):
    """List video clips with pagination and optional filtering."""
    # Completely bypass the database query and return a hardcoded response
    # This will help us determine if the issue is with the database schema or with something else
    print("Returning hardcoded clips response with frontend-compatible format")
    
    # Create a few sample clips
    clips = [
        {
            "id": 1,
            "title": "Sample Clip 1",
            "description": "This is a sample clip for testing",
            "duration": 120,
            "status": "ready",
            "user_id": 1,
            "created_at": "2025-04-26T14:00:00",
            "error_message": None,
            "capture_session_id": None,
            "updated_at": None,
            "start_time": None,
            "end_time": None,
            "storage_path": None,
            # Add fields expected by the frontend
            "file_path": "/path/to/sample1.mp4",
            "thumbnail_url": None,
            "created_by_id": 1,
            "has_transcription": False
        },
        {
            "id": 2,
            "title": "Sample Clip 2",
            "description": "Another sample clip for testing",
            "duration": 180,
            "status": "processing",
            "user_id": 1,
            "created_at": "2025-04-26T15:00:00",
            "error_message": None,
            "capture_session_id": None,
            "updated_at": None,
            "start_time": None,
            "end_time": None,
            "storage_path": None,
            # Add fields expected by the frontend
            "file_path": "/path/to/sample2.mp4",
            "thumbnail_url": None,
            "created_by_id": 1,
            "has_transcription": False
        }
    ]
    
    # Apply basic filtering if needed
    if status:
        clips = [clip for clip in clips if clip["status"] == status]
    
    # Apply basic pagination
    paginated_clips = clips[skip:skip+limit]
    
    # Return in the format expected by the frontend
    response = {
        "items": paginated_clips,
        "total": len(clips),
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": (len(clips) + limit - 1) // limit
    }
    
    return response

@router.post("/", response_model=schemas.VideoClipResponse, status_code=status.HTTP_201_CREATED)
async def create_clip(
    clip: schemas.VideoClipCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new video clip."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Calculate duration in seconds
    duration = int((clip.end_time - clip.start_time).total_seconds()) if hasattr(clip, 'end_time') and hasattr(clip, 'start_time') else 0
    
    # Generate a unique file path for the video
    file_path = f"/tmp/video_{current_user.id}_{int(datetime.utcnow().timestamp())}.mp4"
    
    # Create clip with required fields
    clip_data = clip.dict()
    
    # Create a new VideoClip instance manually without using **clip_data to have more control
    db_clip = models.VideoClip(
        title=clip_data.get('title', ''),
        description=clip_data.get('description', ''),
        user_id=current_user.id,  # Use user_id to match the model
        status=ClipStatus.PROCESSING,  # Use the enum directly
        source_url=file_path,  # Use source_url instead of storage_path
        duration=duration,
        start_time=clip_data.get('start_time'),
        end_time=clip_data.get('end_time')
    )
    
    # Set capture_session_id if it exists
    if 'capture_session_id' in clip_data:
        db_clip.capture_session_id = clip_data['capture_session_id']
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    return db_clip

@router.get("/{clip_id}", response_model=schemas.VideoClipResponse)
async def get_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    return clip

@router.put("/{clip_id}", response_model=schemas.VideoClipResponse)
async def update_clip(
    clip_id: int,
    clip_update: schemas.VideoClipUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update a video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    if clip.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this clip"
        )
    
    for field, value in clip_update.dict(exclude_unset=True).items():
        setattr(clip, field, value)
    
    db.commit()
    db.refresh(clip)
    return clip

@router.delete("/{clip_id}", status_code=status.HTTP_200_OK)
async def delete_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    if clip.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this clip"
        )
    
    db.delete(clip)
    db.commit()
    return {"status": "success", "message": "Clip deleted successfully"}

@router.get("/{clip_id}/status", response_model=schemas.VideoClipStatus)
async def get_clip_status(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
):
    """Get the processing status of a video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    return {"status": clip.status, "progress": clip.processing_progress}
