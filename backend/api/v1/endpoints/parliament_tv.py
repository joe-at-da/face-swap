from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from backend.api.deps import get_db
from backend.core.security import has_permission, get_current_active_user
from backend.core.security import UserRole
from backend.db import models
from backend.schemas.parliament_tv import ParliamentTVCaptureRequest, ParliamentTVCaptureResponse
from backend.services.parliament_tv import ParliamentTVCapture

router = APIRouter()

# Initialize the Parliament TV capture service
parliament_tv_service = ParliamentTVCapture()

# Helper function to make objects JSON serializable
def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON serializable format"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    return obj

@router.post("", response_model=Dict)
async def start_parliament_tv_capture(
    capture_request: ParliamentTVCaptureRequest = Body(...),
    draft: bool = Query(False, description="Save as draft without starting capture"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Start capturing a Parliament TV stream with facial recognition."""
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
        
        # Create a serializable error response
        error_detail = make_json_serializable({
            "message": "A capture session is already in progress",
            "capture_id": active_capture.id,
            "started_by": active_user.full_name if active_user else "Unknown",
            "started_at": active_capture.created_at
        })
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_detail
        )
    
    # Create a new capture session in the database
    db_capture = models.CaptureSession(
        title=capture_request.title,
        description=capture_request.description,
        source_url=capture_request.url,
        status="draft" if draft else "active",
        user_id=current_user.id,
        scheduled_start=capture_request.scheduled_start,
        scheduled_end=capture_request.scheduled_end,
        # Store Parliament TV specific fields in metadata
        metadata={
            "parliament_tv_url": capture_request.url,
            "duration": capture_request.duration,
            "enable_facial_recognition": capture_request.enable_facial_recognition
        }
    )
    
    db.add(db_capture)
    db.commit()
    db.refresh(db_capture)
    
    # If not a draft, start the capture process
    if not draft:
        # Extract stream URL first to validate it
        stream_info = parliament_tv_service.extract_stream_url(capture_request.url)
        
        if not stream_info or not stream_info.get("direct_stream"):
            # Update the capture session status to failed
            db_capture.status = "failed"
            db_capture.metadata = {
                **db_capture.metadata,
                "error": "Failed to extract stream URL"
            }
            db.commit()
            
            # Create a serializable error response
            error_detail = make_json_serializable({
                "message": "Failed to extract stream URL from Parliament TV page",
                "capture_id": db_capture.id
            })
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        
        # Start the capture process asynchronously
        def capture_callback(result):
            # Process result to ensure it's JSON serializable
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, datetime):
                    serializable_result[key] = value.isoformat()
                else:
                    serializable_result[key] = value
            
            # Update the capture session with the result
            capture_session = db.query(models.CaptureSession).filter(
                models.CaptureSession.id == db_capture.id
            ).first()
            
            if result.get("success", False):
                capture_session.status = "completed"
                capture_session.file_path = result.get("output_file")
                capture_session.file_size = result.get("file_size")
                capture_session.end_time = datetime.now()
                capture_session.metadata = {
                    **capture_session.metadata,
                    "capture_result": serializable_result
                }
            else:
                capture_session.status = "failed"
                capture_session.end_time = datetime.now()
                capture_session.metadata = {
                    **capture_session.metadata,
                    "error": result.get("error", "Unknown error")
                }
            
            db.commit()
        
        # Start the capture process asynchronously
        parliament_tv_service.start_capture_async(
            url=stream_info["direct_stream"],
            duration=capture_request.duration,
            enable_facial_recognition=capture_request.enable_facial_recognition,
            callback=capture_callback
        )
        
        # Return the capture session information with serialized datetime
        response_data = {
            "id": db_capture.id,
            "title": db_capture.title,
            "status": db_capture.status,
            "created_at": make_json_serializable(db_capture.created_at),
            "message": "Capture started successfully"
        }
        
        # Make the response JSON serializable
        return make_json_serializable(response_data)
    
    # Format response
    user = db.query(models.User).filter(models.User.id == db_capture.user_id).first()
    metadata = db_capture.metadata or {}
    
    response = {
        "id": db_capture.id,
        "title": db_capture.title,
        "description": db_capture.description,
        "status": db_capture.status,
        "url": db_capture.source_url,
        "duration": metadata.get("duration"),
        "facial_recognition_enabled": metadata.get("enable_facial_recognition", False),
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": make_json_serializable(db_capture.created_at),
        "updated_at": make_json_serializable(db_capture.updated_at)
    }
    
    # Make the response JSON serializable
    return make_json_serializable(response)

@router.get("/extract-url", response_model=Dict)
async def extract_parliament_tv_url(
    url: str,
    current_user: models.User = Depends(get_current_active_user)
):
    """Extract the direct stream URL from a Parliament TV event page."""
    # Check if user has required permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Extract the stream URL
    stream_info = parliament_tv_service.extract_stream_url(url)
    
    if not stream_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract stream URL from Parliament TV page"
        )
    
    # Convert datetime objects to strings to ensure JSON serialization
    serializable_info = {}
    for key, value in stream_info.items():
        if isinstance(value, dict):
            serializable_info[key] = {}
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, datetime):
                    serializable_info[key][sub_key] = sub_value.isoformat()
                else:
                    serializable_info[key][sub_key] = sub_value
        elif isinstance(value, datetime):
            serializable_info[key] = value.isoformat()
        else:
            serializable_info[key] = value
    
    return serializable_info

@router.get("/test-url", response_model=Dict)
async def test_stream_url(
    url: str,
    current_user: models.User = Depends(get_current_active_user)
):
    """Test if a stream URL is valid by downloading a small segment."""
    # Check if user has required permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Test the stream URL
    is_valid = parliament_tv_service.test_stream_url(url)
    
    return {
        "url": url,
        "is_valid": is_valid
    }

@router.get("", response_model=List[Dict])
async def get_parliament_tv_captures(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all Parliament TV capture sessions with optional filtering by status."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Query capture sessions with Parliament TV metadata
    # First get all capture sessions
    query = db.query(models.CaptureSession)
    
    if status:
        query = query.filter(models.CaptureSession.status == status)
    
    # Get all captures and filter in Python for those with parliament_tv_url in metadata
    all_captures = query.order_by(models.CaptureSession.created_at.desc()).all()
    captures = []
    for capture in all_captures:
        try:
            # Check if metadata is a dictionary and has parliament_tv_url
            if capture.metadata and isinstance(capture.metadata, dict) and 'parliament_tv_url' in capture.metadata:
                captures.append(capture)
        except Exception as e:
            print(f"Error checking metadata for capture {capture.id}: {str(e)}")
    
    # Format response
    result = []
    for capture in captures:
        user = db.query(models.User).filter(models.User.id == capture.user_id).first()
        metadata = capture.metadata or {}
        
        result.append({
            "id": capture.id,
            "title": capture.title,
            "status": capture.status,
            "url": capture.source_url,
            "duration": metadata.get("duration"),
            "facial_recognition_enabled": metadata.get("enable_facial_recognition", False),
            "start_time": capture.created_at,
            "end_time": capture.end_time,
            "file_path": capture.file_path,
            "file_size": capture.file_size,
            "created_by_id": user.id,
            "created_by": {
                "id": user.id,
                "name": user.full_name,
                "email": user.email
            },
            "created_at": capture.created_at,
            "updated_at": capture.updated_at
        })
    
    # Make the response JSON serializable
    return make_json_serializable(result)

@router.get("/{capture_id}", response_model=Dict)
async def get_parliament_tv_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific Parliament TV capture session by ID."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    # Check if it's a Parliament TV capture
    try:
        if capture and (not capture.metadata or not isinstance(capture.metadata, dict) or 'parliament_tv_url' not in capture.metadata):
            capture = None
    except Exception as e:
        print(f"Error checking metadata for capture {capture_id}: {str(e)}")
        capture = None
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parliament TV capture session with ID {capture_id} not found"
        )
    
    # Format response
    user = db.query(models.User).filter(models.User.id == capture.user_id).first()
    metadata = capture.metadata or {}
    
    response = {
        "id": capture.id,
        "title": capture.title,
        "status": capture.status,
        "url": capture.source_url,
        "duration": metadata.get("duration"),
        "facial_recognition_enabled": metadata.get("enable_facial_recognition", False),
        "start_time": capture.created_at,
        "end_time": capture.end_time,
        "file_path": capture.file_path,
        "file_size": capture.file_size,
        "created_by_id": user.id,
        "created_by": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email
        },
        "created_at": capture.created_at,
        "updated_at": capture.updated_at
    }
    
    # Make the response JSON serializable
    return make_json_serializable(response)

@router.post("/{capture_id}/stop", response_model=Dict)
async def stop_parliament_tv_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Stop an active Parliament TV capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    # Check if it's a Parliament TV capture
    try:
        if capture and (not capture.metadata or not isinstance(capture.metadata, dict) or 'parliament_tv_url' not in capture.metadata):
            capture = None
    except Exception as e:
        print(f"Error checking metadata for capture {capture_id}: {str(e)}")
        capture = None
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parliament TV capture session with ID {capture_id} not found"
        )
    
    # Check if the capture is active
    if capture.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot stop capture session with status '{capture.status}'"
        )
    
    # Stop the capture process
    try:
        # Update the capture session status
        capture.status = "completed"
        capture.end_time = datetime.now()
        
        # Add metadata about who stopped the capture
        capture.metadata = {
            **(capture.metadata or {}),
            "stopped_by": current_user.id,
            "stopped_by_name": current_user.full_name,
            "stopped_at": datetime.now()
        }
        
        db.commit()
        db.refresh(capture)
        
        # Attempt to stop the actual capture process
        # This is implementation-dependent and may need to be adapted
        # to your specific capture service
        try:
            parliament_tv_service.stop_capture(capture_id)
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Error stopping capture process: {str(e)}")
        
        return make_json_serializable({
            "id": capture.id,
            "status": capture.status,
            "message": "Capture stopped successfully",
            "stopped_at": capture.end_time
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop capture: {str(e)}"
        )
