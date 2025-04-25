from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole
from backend.services.tasks import video_tasks
from backend.core.config import settings

router = APIRouter()

@router.post("/start", response_model=Dict)
async def start_capture(
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
        status="active"
    )
    db.add(capture_session)
    db.commit()
    
    # Start capture in background
    task = video_tasks.start_stream_capture.delay()
    
    return {
        "status": "started",
        "capture_id": capture_session.id,
        "task_id": task.id
    }

@router.post("/stop", response_model=Dict)
async def stop_capture(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Stop the current capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Get active capture session
    active_capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.status == "active"
    ).first()
    
    if not active_capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active capture session found"
        )
    
    # Update capture session status
    active_capture.status = "completed"
    db.commit()
    
    # Stop capture in background
    task = video_tasks.stop_stream_capture.delay()
    
    return {
        "status": "stopped",
        "capture_id": active_capture.id,
        "task_id": task.id
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
