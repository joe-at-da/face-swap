from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.db.models.user import UserRole, User as UserModel
from backend.schemas import video as schemas
from backend.core.security import has_permission

router = APIRouter()

@router.get("/", response_model=List[schemas.VideoClipResponse])
async def list_clips(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """List video clips with pagination."""
    clips = db.query(models.VideoClip).offset(skip).limit(limit).all()
    return clips

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
    current_user: UserModel = Depends(get_current_user)
):
    """Get the processing status of a video clip."""
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    return {"status": clip.status, "progress": clip.processing_progress}
