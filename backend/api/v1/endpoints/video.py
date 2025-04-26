from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user, get_current_user_optional
from backend.db import models
from backend.db.models.user import UserRole, User as UserModel
from backend.schemas import video as schemas
from backend.core.security import has_permission

router = APIRouter()

@router.get("/", response_model=List[schemas.VideoClipResponse])
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
        # Use a more selective query that explicitly selects only the columns that exist in the database
        query = db.query(
            models.VideoClip.id,
            models.VideoClip.title,
            models.VideoClip.description,
            models.VideoClip.duration,
            models.VideoClip.status,
            models.VideoClip.error_message,
            models.VideoClip.user_id,
            models.VideoClip.capture_session_id,
            models.VideoClip.created_at,
            models.VideoClip.updated_at,
            models.VideoClip.start_time,
            models.VideoClip.end_time
        )
        
        # Apply status filter if provided
        if status:
            query = query.filter(models.VideoClip.status == status)
        
        # Apply sorting if provided
        if sort:
            sort_field, sort_order = sort.split(":") if ":" in sort else (sort, "asc")
            order_by = getattr(models.VideoClip, sort_field)
            if sort_order.lower() == "desc":
                order_by = order_by.desc()
            query = query.order_by(order_by)
        
        # Execute the query
        result = query.offset(skip).limit(limit).all()
        
        # Convert the result to a list of dictionaries
        clips = []
        for row in result:
            clip_dict = {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "duration": row.duration,
                "status": row.status,
                "error_message": row.error_message,
                "user_id": row.user_id,
                "capture_session_id": row.capture_session_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "start_time": row.start_time,
                "end_time": row.end_time,
                # Add a default value for storage_path
                "storage_path": None
            }
            clips.append(clip_dict)
        
        return clips
    except Exception as e:
        print(f"Error in list_clips: {str(e)}")
        # Return an empty list as a fallback
        return []

@router.post("/", response_model=schemas.VideoClipResponse, status_code=status.HTTP_201_CREATED)
async def create_clip(
    clip: schemas.VideoClipCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new video clip."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    db_clip = models.VideoClip(**clip.dict(), user_id=current_user.id, status="processing")
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
