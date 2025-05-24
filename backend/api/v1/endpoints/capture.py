from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from jose import jwt, JWTError
import os
import subprocess
import json
import glob

from backend.api.deps import get_db
from backend.core.security import has_permission, get_current_user, get_current_active_user
from backend.db import models
from backend.core.security import UserRole
from backend.services.video.capture import StreamCapture
from backend.core.config import settings
import threading
import subprocess

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
        # Make sure both datetimes are timezone-aware or timezone-naive
        if start_time.tzinfo is not None:
            # If start_time is timezone-aware, make current_time timezone-aware too
            current_time = datetime.utcnow().replace(tzinfo=start_time.tzinfo)
        else:
            # If start_time is timezone-naive, use naive current_time
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
        # Start the actual video capture process directly using ffmpeg
        try:
            # Get the source URL from the capture request
            source_url = capture.source_url if hasattr(capture, 'source_url') and capture.source_url else None
            print(f"DEBUG - Source URL from capture request: {source_url}")
            
            # Extract the direct stream URL if it's a Parliament TV URL
            direct_stream_url = None
            if source_url and ('parliamentlive.tv' in source_url or 'parliament.tv' in source_url):
                try:
                    # Import the Parliament TV service
                    from backend.services.parliament_tv import parliament_tv_service
                    
                    # Extract the direct stream URL
                    print(f"DEBUG - Extracting direct stream URL from: {source_url}")
                    stream_info = parliament_tv_service.extract_stream_url(source_url)
                    
                    if stream_info and 'direct_stream' in stream_info:
                        direct_stream_url = stream_info['direct_stream']
                        print(f"DEBUG - Extracted direct stream URL: {direct_stream_url}")
                    else:
                        print(f"DEBUG - Failed to extract direct stream URL from: {source_url}")
                except Exception as extract_error:
                    print(f"ERROR - Failed to extract direct stream URL: {str(extract_error)}")
            
            # Use the direct stream URL if available, otherwise fall back to the original URL
            final_url = direct_stream_url if direct_stream_url else source_url
            print(f"DEBUG - Final URL for capture: {final_url}")
            
            # Create a StreamCapture instance with the final URL
            stream_capture = StreamCapture(stream_url=final_url)
            print(f"DEBUG - Created StreamCapture instance with stream_url: {stream_capture.stream_url}")
            print(f"DEBUG - temp_dir: {stream_capture.temp_dir}, exists: {stream_capture.temp_dir.exists()}")
            
            # Start the capture directly
            output_file = stream_capture.start_capture()
            print(f"DEBUG - Started direct capture to file: {output_file}")
            
            # Store the output file path in the database
            if hasattr(capture_session, 'file_path'):
                capture_session.file_path = output_file
                print(f"DEBUG - Updated file_path in database: {output_file}")
            
            # Also set video_path to ensure recognition works properly
            if hasattr(capture_session, 'video_path'):
                capture_session.video_path = output_file
                print(f"DEBUG - Updated video_path in database: {output_file}")
                
            db.commit()
        except Exception as e:
            print(f"ERROR - Failed to start capture: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            
            # Update the capture session status to failed
            capture_session.status = "failed"
            
            # Safely handle metadata - check if it's a dict-like object
            try:
                if hasattr(capture_session, 'metadata'):
                    # Check if metadata is a dict-like object
                    if hasattr(capture_session.metadata, 'items') and callable(getattr(capture_session.metadata, 'items', None)):
                        # It's a dict-like object, update it
                        capture_session.metadata = {
                            **dict(capture_session.metadata),
                            "error": f"Failed to start capture: {str(e)}"
                        }
                    else:
                        # Not a dict-like object, create a new dict
                        print(f"WARNING: metadata is not a dict-like object: {type(capture_session.metadata)}")
                        capture_session.metadata = {
                            "error": f"Failed to start capture: {str(e)}"
                        }
            except Exception as metadata_error:
                print(f"ERROR: Failed to update metadata: {str(metadata_error)}")
                # Create a new metadata dict
                try:
                    capture_session.metadata = {
                        "error": f"Failed to start capture: {str(e)}"
                    }
                except:
                    # Last resort - if we can't set metadata at all, just log the error
                    print(f"CRITICAL ERROR: Cannot set metadata on capture_session")
            
            # Save changes
            try:
                db.commit()
            except Exception as commit_error:
                print(f"ERROR: Failed to commit changes: {str(commit_error)}")
                db.rollback()
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
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration', 'recognition_results', 'recognition_status', 'recognition_started_at', 'recognition_completed_at', 'recognition_progress']:
        if hasattr(capture_session, field):
            response[field] = getattr(capture_session, field)
        else:
            response[field] = None
            
    return response

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
        # Pass the capture_id to the stop_capture method
        success = stream_capture.stop_capture(capture_id=capture_id)
        if success:
            print(f"DEBUG - Successfully stopped capture process for ID {capture_id}")
        else:
            print(f"WARNING - No active process found for capture ID {capture_id}")
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
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration', 'recognition_results', 'recognition_status', 'recognition_started_at', 'recognition_completed_at', 'recognition_progress']:
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
    for field in ['title', 'end_time', 'file_path', 'file_size', 'duration', 'recognition_results', 'recognition_status', 'recognition_started_at', 'recognition_completed_at', 'recognition_progress']:
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
    
    # Get logs from various sources
    logs = []
    
    # 1. Add logs from capture metadata if available
    if capture.metadata and isinstance(capture.metadata, dict):
        for key, value in capture.metadata.items():
            if key not in ['parliament_tv_url', 'duration', 'enable_facial_recognition']:
                timestamp = datetime.now().isoformat()
                if key == 'capture_completed_at' and isinstance(value, str):
                    timestamp = value
                elif key == 'capture_started_at' and isinstance(value, str):
                    timestamp = value
                
                logs.append({
                    "timestamp": timestamp,
                    "level": "INFO",
                    "message": f"{key}: {value}"
                })
    
    # 2. Check for log files in the data directory
    data_dir = os.environ.get('DATA_DIR', '/app/data/temp')
    log_patterns = [
        f"parliament_capture_*_{capture_id}.log",
        f"parliament_capture_log_*_{capture_id}.json",
        f"capture_{capture_id}_*.log"
    ]
    
    for pattern in log_patterns:
        matching_files = glob.glob(os.path.join(data_dir, pattern))
        for log_file in matching_files:
            try:
                with open(log_file, 'r') as f:
                    file_logs = f.readlines()
                    for line in file_logs:
                        line = line.strip()
                        if line:
                            # Try to parse log line
                            timestamp = datetime.now().isoformat()
                            level = "INFO"
                            message = line
                            
                            # Try to extract timestamp and level
                            parts = line.split(' - ', 2)
                            if len(parts) >= 3:
                                try:
                                    timestamp_str = parts[0]
                                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').isoformat()
                                    level = parts[1].upper()
                                    message = parts[2]
                                except:
                                    pass
                            
                            logs.append({
                                "timestamp": timestamp,
                                "level": level,
                                "message": message
                            })
            except Exception as e:
                print(f"Error reading log file {log_file}: {str(e)}")
    
    # 3. Add system logs for this capture
    system_logs = [
        {
            "timestamp": capture.created_at.isoformat() if capture.created_at else datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Capture session created with ID {capture.id}"
        }
    ]
    
    if capture.status == "active":
        system_logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Capture is currently active"
        })
    elif capture.status == "completed":
        system_logs.append({
            "timestamp": capture.updated_at.isoformat() if capture.updated_at else datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Capture completed"
        })
    
    if capture.file_path:
        system_logs.append({
            "timestamp": capture.updated_at.isoformat() if capture.updated_at else datetime.now().isoformat(),
            "level": "INFO",
            "message": f"Video saved to {capture.file_path}"
        })
        
        # Check if the file exists and has audio
        if os.path.exists(capture.file_path):
            try:
                # Use ffprobe to check for audio streams
                probe_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", 
                    "stream=codec_type", "-of", "json", capture.file_path
                ]
                probe_result = subprocess.run(
                    probe_cmd, 
                    capture_output=True, 
                    text=True
                )
                
                if probe_result.returncode == 0:
                    # Parse the probe result
                    probe_data = json.loads(probe_result.stdout)
                    streams = probe_data.get('streams', [])
                    has_audio = False
                    has_video = False
                    
                    for stream in streams:
                        if stream.get('codec_type') == 'audio':
                            has_audio = True
                        elif stream.get('codec_type') == 'video':
                            has_video = True
                    
                    system_logs.append({
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO" if has_audio else "WARNING",
                        "message": f"Video file has {'audio and video' if has_audio and has_video else 'video only' if has_video else 'audio only' if has_audio else 'no audio or video'} streams"
                    })
            except Exception as e:
                system_logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "message": f"Error checking video file: {str(e)}"
                })
    
    # Add system logs to the logs list
    logs.extend(system_logs)
    
    # Sort logs by timestamp (newest first)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Paginate logs
    total_logs = len(logs)
    total_pages = (total_logs + per_page - 1) // per_page if total_logs > 0 else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_logs = logs[start_idx:end_idx] if start_idx < total_logs else []
    
    return {
        "logs": paginated_logs,
        "total": total_logs,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }

@router.get("/{capture_id}/metadata", response_model=Dict[str, Any])
async def get_capture_metadata(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get metadata for a specific capture session."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # Initialize metadata
    metadata = {
        "id": capture.id,
        "title": getattr(capture, 'title', None) or f"Capture Session {capture.id}",
        "status": capture.status,
        "duration": getattr(capture, 'duration', None),
        "file_path": getattr(capture, 'file_path', None),
        "file_size": getattr(capture, 'file_size', None),
        "created_at": capture.created_at.isoformat() if capture.created_at else None,
        "updated_at": capture.updated_at.isoformat() if capture.updated_at else None
    }
    
    # If the file exists, try to get more detailed metadata using ffprobe
    if metadata["file_path"] and os.path.exists(metadata["file_path"]):
        try:
            # Use ffprobe to get video metadata
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_format", "-show_streams",
                "-of", "json", metadata["file_path"]
            ]
            probe_result = subprocess.run(
                probe_cmd, 
                capture_output=True, 
                text=True
            )
            
            if probe_result.returncode == 0:
                # Parse the probe result
                probe_data = json.loads(probe_result.stdout)
                
                # Extract format information
                if "format" in probe_data:
                    format_data = probe_data["format"]
                    metadata["format"] = format_data.get("format_name")
                    metadata["duration"] = float(format_data.get("duration", 0)) if "duration" in format_data else None
                    metadata["bit_rate"] = int(format_data.get("bit_rate", 0)) if "bit_rate" in format_data else None
                    metadata["size"] = int(format_data.get("size", 0)) if "size" in format_data else None
                
                # Extract stream information
                if "streams" in probe_data:
                    streams = probe_data["streams"]
                    video_streams = [s for s in streams if s.get("codec_type") == "video"]
                    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
                    
                    if video_streams:
                        video_stream = video_streams[0]  # Use the first video stream
                        metadata["width"] = video_stream.get("width")
                        metadata["height"] = video_stream.get("height")
                        metadata["fps"] = eval(video_stream.get("r_frame_rate", "0/1")) if "r_frame_rate" in video_stream else None
                        metadata["video_codec"] = video_stream.get("codec_name")
                    
                    if audio_streams:
                        audio_stream = audio_streams[0]  # Use the first audio stream
                        metadata["audio_codec"] = audio_stream.get("codec_name")
                        metadata["sample_rate"] = audio_stream.get("sample_rate")
                        metadata["channels"] = audio_stream.get("channels")
                    
                    metadata["has_video"] = len(video_streams) > 0
                    metadata["has_audio"] = len(audio_streams) > 0
        except Exception as e:
            metadata["probe_error"] = str(e)
    
    return metadata
