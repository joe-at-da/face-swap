from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole
from backend.services.tasks import video_tasks
from backend.core.config import settings

router = APIRouter()


class CaptureCreate(BaseModel):
    title: str
    description: Optional[str] = None
    source_url: str
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class CaptureResponse(BaseModel):
    id: int
    title: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    created_by_id: int
    created_by: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

@router.get("", response_model=List[CaptureResponse])
async def get_captures(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all capture sessions with optional filtering by status."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    query = db.query(models.CaptureSession)
    
    if status:
        query = query.filter(models.CaptureSession.status == status)
    
    captures = query.order_by(models.CaptureSession.created_at.desc()).all()
    
    # Format response to match frontend expectations
    result = []
    for capture in captures:
        user = db.query(models.User).filter(models.User.id == capture.user_id).first()
        result.append({
            "id": capture.id,
            "title": capture.title or f"Capture Session {capture.id}",
            "status": capture.status,
            "start_time": capture.created_at,
            "end_time": capture.end_time,
            "file_path": capture.file_path,
            "file_size": capture.file_size,
            "duration": capture.duration,
            "created_by_id": user.id,
            "created_by": {
                "id": user.id,
                "name": user.full_name,
                "email": user.email
            },
            "created_at": capture.created_at,
            "updated_at": capture.updated_at
        })
    
    return result

@router.post("", response_model=CaptureResponse)
async def start_capture(
    capture: CaptureCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Start capturing the Parliament TV stream."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Check if capture is already running
    active_capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.status == "active"
    ).first()
    
    if active_capture:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A capture session is already running"
        )
    
    # Create new capture session
    capture_session = models.CaptureSession(
        user_id=current_user.id,
        title=capture.title,
        description=capture.description,
        source_url=capture.source_url,
        scheduled_start=capture.scheduled_start,
        scheduled_end=capture.scheduled_end,
        status="active" if not capture.scheduled_start else "scheduled"
    )
    db.add(capture_session)
    db.commit()
    db.refresh(capture_session)
    
    # Start capture in background if not scheduled
    if not capture.scheduled_start:
        task = video_tasks.start_stream_capture.delay()
    
    # Format response to match frontend expectations
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    return {
        "id": capture_session.id,
        "title": capture_session.title,
        "status": capture_session.status,
        "start_time": capture_session.created_at,
        "end_time": capture_session.end_time,
        "file_path": capture_session.file_path,
        "file_size": capture_session.file_size,
        "duration": capture_session.duration,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture_session.created_at,
        "updated_at": capture_session.updated_at
    }

@router.post("/{capture_id}/stop", response_model=CaptureResponse)
async def stop_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Stop a specific capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    if capture.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capture session with ID {capture_id} is not active"
        )
    
    # Update capture session status
    capture.status = "completed"
    capture.end_time = datetime.now()
    db.commit()
    db.refresh(capture)
    
    # Stop capture in background
    task = video_tasks.stop_stream_capture.delay()
    
    # Format response to match frontend expectations
    user = db.query(models.User).filter(models.User.id == capture.user_id).first()
    return {
        "id": capture.id,
        "title": capture.title or f"Capture Session {capture.id}",
        "status": capture.status,
        "start_time": capture.created_at,
        "end_time": capture.end_time,
        "file_path": capture.file_path,
        "file_size": capture.file_size,
        "duration": capture.duration,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture.created_at,
        "updated_at": capture.updated_at
    }

@router.get("/status", response_model=Dict)
async def get_capture_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get the current capture status."""
    active_capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.status == "active"
    ).first()
    
    return {
        "is_capturing": active_capture is not None,
        "capture_id": active_capture.id if active_capture else None,
        "start_time": active_capture.created_at if active_capture else None
    }
