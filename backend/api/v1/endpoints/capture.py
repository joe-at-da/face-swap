from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from jose import jwt, JWTError

from backend.api.deps import get_db
from backend.core.security import has_permission, get_current_user, get_current_active_user
from backend.db import models
from backend.core.security import UserRole
from backend.services.video.capture import StreamCapture
from backend.core.config import settings
import threading

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

@router.get("", response_model=List[Dict])
async def get_captures(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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
        # Handle missing fields gracefully
        title = getattr(capture, 'title', None) or f"Capture Session {capture.id}"
        end_time = getattr(capture, 'end_time', None)
        file_path = getattr(capture, 'file_path', None)
        file_size = getattr(capture, 'file_size', None)
        duration = getattr(capture, 'duration', None)
        
        result.append({
            "id": capture.id,
            "title": title,
            "status": capture.status,
            "start_time": capture.created_at,
            "end_time": end_time,
            "file_path": file_path,
            "file_size": file_size,
            "duration": duration,
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

@router.post("", response_model=Dict)
async def start_capture(
    capture: CaptureCreate = Body(...),
    draft: bool = Query(False, description="Save as draft without starting capture"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Start capturing the Parliament TV stream or save as draft."""
    # Debug information
    print(f"DEBUG - Capture request received from user: {current_user.email}, role: {current_user.role}")
    
    # Check if user has required permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Check if capture is already running
    active_capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.status == "active"
    ).first()
    
    # If trying to start a new active capture when one is already running
    if active_capture and not draft:
        # Get user who started the active capture
        active_user = db.query(models.User).filter(models.User.id == active_capture.user_id).first()
        user_info = f"{active_user.full_name} ({active_user.email})" if active_user else "Unknown user"
        
        # Calculate how long the capture has been running
        start_time = active_capture.created_at
        current_time = datetime.utcnow()
        duration_seconds = int((current_time - start_time).total_seconds())
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m {seconds}s"
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "A capture session is already running",
                "active_capture": {
                    "id": active_capture.id,
                    "title": getattr(active_capture, 'title', f"Capture Session {active_capture.id}"),
                    "started_by": user_info,
                    "started_at": active_capture.created_at.isoformat(),
                    "duration": duration_str,
                    "url": f"/capture/{active_capture.id}"
                }
            }
        )
    
    # Create new capture session with basic fields
    status_value = "draft" if draft else "active"
    capture_session = models.CaptureSession(
        user_id=current_user.id,
        status=status_value
    )
    
    # Try to set additional fields if they exist in the model
    try:
        if hasattr(models.CaptureSession, 'title'):
            capture_session.title = capture.title
        if hasattr(models.CaptureSession, 'description'):
            capture_session.description = capture.description
        if hasattr(models.CaptureSession, 'source_url'):
            capture_session.source_url = capture.source_url
        if hasattr(models.CaptureSession, 'scheduled_start'):
            capture_session.scheduled_start = capture.scheduled_start
            if capture.scheduled_start and hasattr(models.CaptureSession, 'status'):
                capture_session.status = "scheduled"
        if hasattr(models.CaptureSession, 'scheduled_end'):
            capture_session.scheduled_end = capture.scheduled_end
    except Exception as e:
        # If setting additional fields fails, continue with basic fields
        print(f"Warning: Could not set additional fields: {str(e)}")
    
    db.add(capture_session)
    db.commit()
    db.refresh(capture_session)
    
    # Start capture in background if not scheduled and not a draft
    scheduled_start = getattr(capture, 'scheduled_start', None)
    if not scheduled_start and not draft:
        # Start the actual video capture process directly
        def start_capture_thread():
            try:
                stream_capture = StreamCapture()
                output_file = stream_capture.start_capture()
                print(f"DEBUG - Started direct capture to file: {output_file}")
                
                # Store the output file path in the database
                if hasattr(capture_session, 'file_path'):
                    capture_session.file_path = output_file
                    db.commit()
            except Exception as e:
                print(f"ERROR - Failed to start capture: {str(e)}")
        
        # Start capture in a separate thread
        capture_thread = threading.Thread(target=start_capture_thread)
        capture_thread.daemon = True
        capture_thread.start()
        print(f"DEBUG - Started capture thread")
    elif draft:
        print("DEBUG - Saving as draft, no capture started")
    
    # Format response to match frontend expectations
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    # Build response with basic fields
    response = {
        "id": capture_session.id,
        "status": capture_session.status,
        "start_time": capture_session.created_at,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture_session.created_at,
        "updated_at": capture_session.updated_at
    }
    
    # Add additional fields if they exist
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration']:
        if hasattr(capture_session, field):
            response[field] = getattr(capture_session, field)
        else:
            response[field] = None

@router.post("/{capture_id}/stop", response_model=Dict)
async def stop_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Stop a specific capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
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
    
    # Update capture status
    capture.status = "completed"
    capture.end_time = datetime.utcnow()
    db.commit()
    
    # Stop the actual video capture process directly
    try:
        stream_capture = StreamCapture()
        stream_capture.stop_capture()
        print(f"DEBUG - Stopped capture process directly")
    except Exception as e:
        print(f"ERROR - Failed to stop capture: {str(e)}")
    
    # Format response to match frontend expectations
    user = db.query(models.User).filter(models.User.id == capture.user_id).first()
    
    # Build response with basic fields
    response = {
        "id": capture.id,
        "status": capture.status,
        "start_time": capture.created_at,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture.created_at,
        "updated_at": capture.updated_at
    }
    
    # Add additional fields if they exist
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration']:
        if hasattr(capture, field):
            response[field] = getattr(capture, field)
        else:
            response[field] = None
    
    if 'title' not in response or not response['title']:
        response['title'] = f"Capture Session {capture.id}"
    
    return response

@router.get("/status", response_model=Dict)
async def get_capture_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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

@router.get("/{capture_id}", response_model=Dict)
async def get_capture_by_id(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific capture session by ID."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # Format response to match frontend expectations
    user = db.query(models.User).filter(models.User.id == capture.user_id).first()
    
    # Build response with basic fields
    response = {
        "id": capture.id,
        "status": capture.status,
        "start_time": capture.created_at,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture.created_at,
        "updated_at": capture.updated_at
    }
    
    # Add additional fields if they exist
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration']:
        if hasattr(capture, field):
            response[field] = getattr(capture, field)
        else:
            response[field] = None
    
    if 'title' not in response or not response['title']:
        response['title'] = f"Capture Session {capture.id}"
    
    return response

@router.get("/{capture_id}/logs", response_model=Dict)
async def get_capture_logs(
    capture_id: int,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get logs for a specific capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # For now, return a placeholder response since we don't have actual logs
    return {
        "logs": [],
        "total": 0,
        "page": page,
        "per_page": per_page,
        "total_pages": 0
    }
