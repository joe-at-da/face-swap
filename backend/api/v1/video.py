from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.api.deps import get_db
from backend.schemas.video import VideoClip, VideoClipCreate, VideoClipUpdate
from backend.db import models

router = APIRouter()

@router.post("/", response_model=VideoClip, status_code=status.HTTP_201_CREATED)
def create_video_clip(
    *,
    db: Session = Depends(get_db),
    video_clip_in: VideoClipCreate
) -> VideoClip:
    """Create a new video clip."""
    video_clip = models.VideoClip(
        title=video_clip_in.title,
        description=video_clip_in.description,
        source_url=video_clip_in.source_url,
        start_time=video_clip_in.start_time,
        end_time=video_clip_in.end_time,
        clip_metadata=video_clip_in.clip_metadata,
        status="processing"
    )
    db.add(video_clip)
    db.commit()
    db.refresh(video_clip)
    return video_clip

@router.get("/", response_model=List[VideoClip])
def list_video_clips(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[VideoClip]:
    """Retrieve video clips."""
    return db.query(models.VideoClip).offset(skip).limit(limit).all()

@router.get("/{clip_id}", response_model=VideoClip)
def get_video_clip(
    *,
    db: Session = Depends(get_db),
    clip_id: int
) -> VideoClip:
    """Get a specific video clip by ID."""
    video_clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not video_clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    return video_clip

@router.patch("/{clip_id}", response_model=VideoClip)
def update_video_clip(
    *,
    db: Session = Depends(get_db),
    clip_id: int,
    video_clip_in: VideoClipUpdate
) -> VideoClip:
    """Update a video clip."""
    video_clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not video_clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    update_data = video_clip_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video_clip, field, value)
    
    db.add(video_clip)
    db.commit()
    db.refresh(video_clip)
    return video_clip

@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_clip(
    *,
    db: Session = Depends(get_db),
    clip_id: int
):
    """Delete a video clip."""
    video_clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
    if not video_clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    db.delete(video_clip)
    db.commit()
    return None
