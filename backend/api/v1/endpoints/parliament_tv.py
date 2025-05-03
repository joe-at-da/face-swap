from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Response, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import glob
import subprocess
from pathlib import Path

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission, get_current_active_user
from backend.core.security import UserRole
from backend.db import models
from backend.schemas.parliament_tv import ParliamentTVCaptureRequest, ParliamentTVCaptureResponse
from backend.services.parliament_tv import ParliamentTVCapture

router = APIRouter()

# Initialize the Parliament TV capture service
parliament_tv_service = ParliamentTVCapture()

# Define the data directory where videos are stored
DATA_DIR = os.environ.get('DATA_DIR', '/app/data/temp')

# Helper function to make objects JSON serializable
def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON serializable format"""
    try:
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ attribute (like MetaData)
            return make_json_serializable(obj.__dict__)
        elif hasattr(obj, 'keys') and callable(getattr(obj, 'keys', None)):
            # Handle dictionary-like objects
            return {k: make_json_serializable(obj[k]) for k in obj.keys()}
        elif hasattr(obj, '__iter__') and callable(getattr(obj, '__iter__', None)) and not isinstance(obj, (str, bytes)):
            # Handle iterable objects
            return [make_json_serializable(item) for item in obj]
        return obj
    except Exception as e:
        print(f"Error serializing object: {str(e)}")
        return str(obj)  # Fallback to string representation

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
        print(f"Extracting stream URL from: {capture_request.url}")
        stream_info = parliament_tv_service.extract_stream_url(capture_request.url)
        print(f"Stream info: {stream_info}")
        
        # Ensure stream_info is a dictionary
        if not stream_info:
            stream_info = {}
            
        # Ensure direct_stream exists and is a string
        direct_stream = stream_info.get("direct_stream")
        if not direct_stream:
            print("No direct_stream found in stream_info, using original URL")
            direct_stream = capture_request.url
            stream_info["direct_stream"] = direct_stream
        
        print(f"Direct stream URL: {direct_stream}")
        
        # Validate the direct stream URL
        if not isinstance(direct_stream, str):
            print(f"Direct stream URL is not a string: {direct_stream}, type: {type(direct_stream)}")
            direct_stream = str(direct_stream) if direct_stream is not None else capture_request.url
            stream_info["direct_stream"] = direct_stream
            
        # Test if the direct stream URL is valid
        is_valid = parliament_tv_service.test_stream_url(direct_stream)
        if not is_valid:
            print(f"Direct stream URL is not valid: {direct_stream}")
            # Update the capture session status to failed
            db_capture.status = "failed"
            db_capture.metadata = {
                **db_capture.metadata,
                "error": "Failed to extract valid stream URL"
            }
            db.commit()
            
            # Create a serializable error response
            error_detail = make_json_serializable({
                "message": "Failed to extract valid stream URL from Parliament TV page",
                "capture_id": db_capture.id
            })
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        
        # Start the capture process asynchronously
        def capture_callback(result):
            try:
                # Process result to ensure it's JSON serializable
                serializable_result = {}
                for key, value in result.items():
                    if isinstance(value, datetime):
                        serializable_result[key] = value.isoformat()
                    else:
                        serializable_result[key] = value
                
                # Log the result for debugging
                print(f"Capture callback received result: {serializable_result}")
                
                # Create a new database session for the callback
                from backend.db.session import SessionLocal
                callback_db = SessionLocal()
                
                try:
                    # Update the capture session with the result
                    capture_session = callback_db.query(models.CaptureSession).filter(
                        models.CaptureSession.id == db_capture.id
                    ).first()
                    
                    if not capture_session:
                        print(f"Error: Capture session {db_capture.id} not found in callback")
                        return
                    
                    if result.get("success", False):
                        capture_session.status = "completed"
                        
                        # Get the output file path from the result
                        output_file = result.get("output_file")
                        print(f"Output file from result: {output_file}")
                        
                        # If no output file in result, try to find it based on capture ID
                        if not output_file or not os.path.exists(output_file):
                            print(f"Output file not found in result or doesn't exist: {output_file}")
                            print(f"Searching for file with capture ID: {capture_session.id}")
                            
                            # Search in multiple directories for files with the capture ID
                            search_dirs = [
                                '/app/data/temp',
                                '/app/data/media/parliament_captures',
                                '/app/data/media',
                                '/app/data'
                            ]
                            
                            file_patterns = [
                                f"parliament_stream_*_{capture_session.id}.mp4",
                                f"parliament_capture_*_{capture_session.id}.mp4",
                                f"capture_*_{capture_session.id}.mp4",
                                f"*_{capture_session.id}.mp4"
                            ]
                            
                            # Search in all directories with all patterns
                            found_file = False
                            for search_dir in search_dirs:
                                if not os.path.exists(search_dir):
                                    print(f"Search directory does not exist: {search_dir}")
                                    continue
                                    
                                print(f"Searching in directory: {search_dir}")
                                for pattern in file_patterns:
                                    full_pattern = os.path.join(search_dir, pattern)
                                    print(f"Searching with pattern: {full_pattern}")
                                    matching_files = glob.glob(full_pattern)
                                    
                                    if matching_files:
                                        # Sort by modification time, newest first
                                        matching_files.sort(key=os.path.getmtime, reverse=True)
                                        output_file = matching_files[0]  # Use the newest match
                                        print(f"Found matching file: {output_file}")
                                        found_file = True
                                        break
                                
                                if found_file:
                                    break
                        
                        # Update the file path in the database
                        if output_file and os.path.exists(output_file):
                            print(f"Setting file path in database to: {output_file}")
                            capture_session.file_path = output_file
                            capture_session.file_size = os.path.getsize(output_file)
                            print(f"File size: {capture_session.file_size} bytes")
                        else:
                            print(f"Warning: No valid output file found for capture {capture_session.id}")
                        
                        capture_session.end_time = datetime.now()
                        capture_session.metadata = {
                            **(capture_session.metadata or {}),
                            "capture_result": serializable_result,
                            "output_file": output_file if output_file and os.path.exists(output_file) else None
                        }
                    else:
                        capture_session.status = "failed"
                        capture_session.end_time = datetime.now()
                        capture_session.metadata = {
                            **(capture_session.metadata or {}),
                            "error": result.get("error", "Unknown error")
                        }
                    
                    # Commit changes with the new session
                    callback_db.commit()
                    print(f"Capture session {db_capture.id} updated successfully in callback")
                    print(f"Final file path in database: {capture_session.file_path}")
                except Exception as e:
                    callback_db.rollback()
                    print(f"Error updating capture session in callback: {str(e)}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # Always close the new session
                    callback_db.close()
            except Exception as e:
                print(f"Unexpected error in capture callback: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Start the capture process asynchronously
        print(f"Starting capture with direct_stream: {direct_stream}")
        print(f"Capture ID: {db_capture.id}, Duration: {capture_request.duration}")
        
        try:
            parliament_tv_service.start_capture_async(
                url=direct_stream,  # Use the validated direct_stream variable
                capture_id=db_capture.id,  # Pass the capture ID for proper file naming
                duration=capture_request.duration,
                callback=capture_callback
            )
            print(f"Capture process started successfully for ID: {db_capture.id}")
        except Exception as e:
            print(f"Error starting capture process: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            # Update the capture session status to failed
            db_capture.status = "failed"
            db_capture.metadata = {
                **db_capture.metadata,
                "error": f"Failed to start capture: {str(e)}"
            }
            db.commit()
            
            # Return error response but don't raise exception
            response_data = {
                "id": db_capture.id,
                "title": db_capture.title,
                "status": db_capture.status,
                "created_at": make_json_serializable(db_capture.created_at),
                "message": f"Failed to start capture: {str(e)}"
            }
            return make_json_serializable(response_data)
        
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
    url: Optional[str] = None,
    video_url: Optional[str] = None,
    audio_url: Optional[str] = None,
    current_user: models.User = Depends(get_current_active_user)
):
    """Test if a stream URL is valid by downloading a small segment.
    
    Can accept either a single 'url' parameter or separate 'video_url' and 'audio_url' parameters.
    When both video and audio URLs are provided, only the video URL is tested for validity.
    """
    # Check if user has required permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Determine which URL to test
    test_url = None
    if url:
        test_url = url
    elif video_url:
        test_url = video_url
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'url' or 'video_url' must be provided"
        )
    
    # Test the stream URL
    is_valid = parliament_tv_service.test_stream_url(test_url)
    
    return {
        "url": test_url,
        "is_valid": is_valid,
        "video_url": video_url,
        "audio_url": audio_url
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

@router.get("/{capture_id}/stream")
async def stream_parliament_tv_video(
    capture_id: int,
    db: Session = Depends(get_db)
):
    """Stream a Parliament TV video file. This endpoint is publicly accessible."""
    # No authentication required for video streaming
    
    # Get the specified capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # Log capture details for debugging
    print(f"Streaming video for capture {capture_id}")
    print(f"Capture status: {capture.status}")
    print(f"Capture file path: {capture.file_path}")
    if hasattr(capture, 'metadata') and capture.metadata:
        try:
            metadata_dict = dict(capture.metadata) if hasattr(capture.metadata, '__dict__') else capture.metadata
            print(f"Capture metadata: {metadata_dict}")
        except Exception as e:
            print(f"Error serializing metadata: {str(e)}")
            # Continue without printing metadata
    
    # Try multiple approaches to find the video file
    video_file_paths = []
    
    # Print the DATA_DIR for debugging
    print(f"Looking for video files in DATA_DIR: {DATA_DIR}")
    print(f"DATA_DIR exists: {os.path.exists(DATA_DIR)}")
    
    # 1. Check if the file path in the database exists
    if capture.file_path:
        print(f"Database file path: {capture.file_path}")
        print(f"Database file path exists: {os.path.exists(capture.file_path)}")
        if os.path.exists(capture.file_path):
            video_file_paths.append(capture.file_path)
            print(f"Found video file in database path: {capture.file_path}")
    
    # 2. Try to find by creation time - get files created around the time this capture was started
    if not video_file_paths and capture.created_at:
        # Get all mp4 files in the temp directory
        all_mp4_files = glob.glob(os.path.join(DATA_DIR, "*.mp4"))
        
        # Sort files by modification time, newest first
        sorted_files = sorted(all_mp4_files, key=os.path.getmtime, reverse=True)
        
        # Print the creation times for debugging
        print(f"Capture created at: {capture.created_at}")
        print(f"Looking for files created after the capture started")
        
        # Find files created after the capture started
        capture_time = capture.created_at.timestamp()
        for file_path in sorted_files:
            file_time = os.path.getmtime(file_path)
            # If file was created after the capture started and within 10 minutes
            if file_time >= capture_time and file_time <= capture_time + 600:
                print(f"Found file created after capture: {file_path}")
                video_file_paths.append(file_path)
                break
    
    # 3. Try to find by parliament_stream pattern with capture ID - ONLY use patterns with the capture ID
    parliament_patterns = [
        # ONLY look for files with the exact capture ID
        f"parliament_stream_*_{capture_id}.mp4",
        f"parliament_capture_*_{capture_id}.mp4",
        f"capture_*_{capture_id}.mp4",
        f"*_{capture_id}.mp4"
        # NO FALLBACK to random videos
    ]
    
    for pattern in parliament_patterns:
        full_pattern = os.path.join(DATA_DIR, pattern)
        print(f"Searching with pattern: {full_pattern}")
        matching_files = glob.glob(full_pattern)
        print(f"Found {len(matching_files)} files with pattern {pattern}")
        for file_path in matching_files:
            if file_path not in video_file_paths:
                video_file_paths.append(file_path)
                print(f"Found video file with pattern {pattern}: {file_path}")
    
    # 3. Try to find in other common directories - ONLY look for files with the capture ID
    other_dirs = [
        "/app/data/media",
        "/app/data/temp",
        "/app/data"
    ]
    
    for directory in other_dirs:
        if directory != DATA_DIR and os.path.exists(directory):
            print(f"Searching in alternative directory: {directory}")
            # ONLY search for files with the capture ID
            pattern = f"*_{capture_id}.mp4"
            full_pattern = os.path.join(directory, pattern)
            matching_files = glob.glob(full_pattern)
            print(f"Found {len(matching_files)} files with pattern {pattern} in {directory}")
            for file_path in matching_files:
                if file_path not in video_file_paths:
                    video_file_paths.append(file_path)
                    print(f"Found video file in {directory}: {file_path}")
    
    # If no video file found or if we found files but none match the capture ID, return 404
    if not video_file_paths:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No video file found for capture session {capture_id}"
        )
    
    # Before serving, verify that the file belongs to this capture
    video_file = video_file_paths[0]
    
    # Extract timestamp from filename to verify it was created after the capture started
    if capture.created_at:
        try:
            # Check if the file was actually created after the capture started
            file_time = os.path.getmtime(video_file)
            capture_time = capture.created_at.timestamp()
            
            # If file was created before the capture started, it's probably not the right file
            if file_time < capture_time - 60:  # Allow 1 minute clock difference
                print(f"WARNING: File {video_file} was created before the capture started")
                print(f"File time: {datetime.fromtimestamp(file_time)}")
                print(f"Capture time: {capture.created_at}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No valid video file found for capture {capture_id}"
                )
        except Exception as e:
            print(f"Error checking file creation time: {str(e)}")
    
    print(f"Serving video file: {video_file}")
    
    # Check if the video file has audio
    try:
        probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "json", video_file]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        audio_info = json.loads(probe_result.stdout)
        if not audio_info.get("streams"):
            print(f"WARNING: Video file does not have audio: {video_file}")
    except Exception as e:
        print(f"Error checking audio streams: {str(e)}")
    
    # Update the file path in the database if it's different
    if capture.file_path != video_file:
        capture.file_path = video_file
        db.commit()
        print(f"Updated file path in database for capture {capture_id}")
    
    # Return the video file as a streaming response
    # Use StreamingResponse instead of FileResponse to avoid content length mismatch errors
    def iterfile():
        with open(video_file, 'rb') as f:
            while chunk := f.read(8192):  # Read in 8KB chunks
                yield chunk
    
    headers = {
        'Content-Disposition': f'attachment; filename="parliament_capture_{capture_id}.mp4"',
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-cache',
    }
    
    return StreamingResponse(
        iterfile(),
        media_type="video/mp4",
        headers=headers
    )

@router.delete("/{capture_id}")
async def delete_parliament_tv_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a Parliament TV capture session and its associated files."""
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
    
    # If the capture is active, stop it first
    if capture.status == "active":
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
            
            # Attempt to stop the actual capture process
            try:
                parliament_tv_service.stop_capture(capture_id)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Error stopping capture process: {str(e)}")
        except Exception as e:
            print(f"Error stopping active capture: {str(e)}")
    
    # Delete associated files
    files_deleted = []
    
    # Try to delete the main video file
    if capture.file_path and os.path.exists(capture.file_path):
        try:
            os.remove(capture.file_path)
            files_deleted.append(os.path.basename(capture.file_path))
        except Exception as e:
            print(f"Error deleting file {capture.file_path}: {str(e)}")
    
    # Try to find and delete other associated files
    file_patterns = [
        f"parliament_stream_*_{capture_id}.mp4",
        f"parliament_capture_log_*_{capture_id}.json",
        f"stream_info_*_{capture_id}.json"
    ]
    
    for pattern in file_patterns:
        matching_files = glob.glob(os.path.join(DATA_DIR, pattern))
        for file_path in matching_files:
            try:
                os.remove(file_path)
                files_deleted.append(os.path.basename(file_path))
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")
    
    # Delete the database record
    db.delete(capture)
    db.commit()
    
    return {
        "message": f"Capture session {capture_id} deleted successfully",
        "files_deleted": files_deleted
    }

@router.post("/cleanup")
async def cleanup_temporary_files(
    current_user: models.User = Depends(get_current_active_user)
):
    """Clean up temporary files from Parliament TV captures."""
    has_permission(current_user, [UserRole.ADMIN])
    
    # Define file patterns to clean up
    patterns = [
        "test_stream_*.mp4",
        "stream_info_*.json"
    ]
    
    files_deleted = []
    
    for pattern in patterns:
        matching_files = glob.glob(os.path.join(DATA_DIR, pattern))
        for file_path in matching_files:
            try:
                os.remove(file_path)
                files_deleted.append(os.path.basename(file_path))
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")
    
    return {
        "message": "Temporary files cleaned up successfully",
        "files_deleted": files_deleted,
        "count": len(files_deleted)
    }
