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
    try:
        # Start with a base query
        query = db.query(models.VideoClip)
        
        # Apply status filter if provided
        if status:
            query = query.filter(models.VideoClip.status == status)
        
        # Apply sorting if provided
        if sort:
            if sort == "newest":
                query = query.order_by(models.VideoClip.created_at.desc())
            elif sort == "oldest":
                query = query.order_by(models.VideoClip.created_at.asc())
            elif sort == "title_asc":
                query = query.order_by(models.VideoClip.title.asc())
            elif sort == "title_desc":
                query = query.order_by(models.VideoClip.title.desc())
            elif sort == "duration_asc":
                query = query.order_by(models.VideoClip.duration.asc())
            elif sort == "duration_desc":
                query = query.order_by(models.VideoClip.duration.desc())
        else:
            # Default sorting is by newest first
            query = query.order_by(models.VideoClip.created_at.desc())
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query and get results
        db_clips = query.all()
        
        # Convert to response format
        clips = []
        for clip in db_clips:
            # Check if the clip has a transcription
            has_transcription = False
            if hasattr(clip, 'transcription') and clip.transcription is not None:
                has_transcription = True
            
            # Create a dictionary with all the fields from the database model
            clip_dict = {
                "id": clip.id,
                "title": clip.title,
                "description": clip.description,
                "duration": clip.duration,
                "status": clip.status.value if hasattr(clip.status, 'value') else str(clip.status),
                "user_id": clip.owner_id,  # Map owner_id to user_id for frontend compatibility
                "created_at": clip.created_at.isoformat() if clip.created_at else None,
                "updated_at": clip.updated_at.isoformat() if clip.updated_at else None,
                "error_message": clip.error_message,
                "capture_session_id": clip.capture_session_id,
                "start_time": clip.start_time.isoformat() if clip.start_time else None,
                "end_time": clip.end_time.isoformat() if clip.end_time else None,
                "storage_path": clip.source_url,  # Map source_url to storage_path for frontend compatibility
                "file_path": clip.source_url,  # For frontend compatibility
                "thumbnail_url": getattr(clip, 'thumbnail_url', None),
                "created_by_id": clip.owner_id,
                "has_transcription": has_transcription
            }
            
            clips.append(clip_dict)
        
        # Return in the format expected by the frontend
        response = {
            "items": clips,
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "size": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1
        }
        
        return response
    
    except Exception as e:
        # Log the error
        print(f"Error listing video clips: {str(e)}")
        
        # Return an empty response in case of error
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": limit,
            "pages": 0
        }

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
        owner_id=current_user.id,  # Use owner_id to match the database schema
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
