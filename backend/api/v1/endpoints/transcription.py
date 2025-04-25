from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole
from backend.schemas import transcription as schemas
from backend.services.tasks import transcription_tasks

router = APIRouter()

@router.post("/", response_model=schemas.TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    transcription: schemas.TranscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new transcription for a video clip.
    This will start a background task to process the transcription.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Check if video clip exists
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == transcription.video_clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    # Check if transcription already exists
    existing = db.query(models.Transcription).filter(
        models.Transcription.video_clip_id == transcription.video_clip_id
    ).first()
    
    if existing:
        # If it exists but failed, we can retry
        if existing.status == "failed":
            existing.status = "processing"
            existing.error_message = None
            db.commit()
            db.refresh(existing)
            
            # Start transcription task
            transcription_tasks.transcribe_video_clip.delay(
                clip_id=transcription.video_clip_id,
                language=transcription.language
            )
            
            return existing
        else:
            # If it's already processing or ready, return it
            return existing
    
    # Create new transcription record
    db_transcription = models.Transcription(
        video_clip_id=transcription.video_clip_id,
        language=transcription.language,
        status="processing",
        text="",
        segments=[]
    )
    db.add(db_transcription)
    db.commit()
    db.refresh(db_transcription)
    
    # Start transcription task
    transcription_tasks.transcribe_video_clip.delay(
        clip_id=transcription.video_clip_id,
        language=transcription.language
    )
    
    return db_transcription

@router.get("/{transcription_id}", response_model=schemas.TranscriptionResponse)
async def get_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific transcription by ID."""
    transcription = db.query(models.Transcription).filter(
        models.Transcription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    return transcription

@router.get("/clip/{clip_id}", response_model=schemas.TranscriptionResponse)
async def get_transcription_by_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get the transcription for a specific video clip."""
    transcription = db.query(models.Transcription).filter(
        models.Transcription.video_clip_id == clip_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found for this clip"
        )
    
    return transcription

@router.post("/search", response_model=List[schemas.TranscriptionSearchResult])
async def search_transcriptions(
    search: schemas.TranscriptionSearch,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Search for text within transcriptions.
    If video_clip_id is provided, search only within that clip.
    """
    query = search.query.lower()
    
    # Build query for transcriptions
    transcription_query = db.query(models.Transcription, models.VideoClip).join(
        models.VideoClip, models.Transcription.video_clip_id == models.VideoClip.id
    ).filter(
        models.Transcription.status == "ready"
    )
    
    # Filter by clip ID if provided
    if search.video_clip_id:
        transcription_query = transcription_query.filter(
            models.Transcription.video_clip_id == search.video_clip_id
        )
    
    results = []
    for transcription, clip in transcription_query.all():
        # Search within transcription text
        if query in transcription.text.lower():
            # Find matching segments
            matches = []
            for segment in transcription.segments:
                if query in segment.get("text", "").lower():
                    matches.append(schemas.TranscriptionSegment(**segment))
            
            if matches:
                results.append(schemas.TranscriptionSearchResult(
                    video_clip_id=clip.id,
                    clip_title=clip.title,
                    matches=matches
                ))
    
    return results
