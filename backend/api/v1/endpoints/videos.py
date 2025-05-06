from typing import List, Dict, Optional
import os
import glob
import tempfile
import subprocess
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import logging
from datetime import datetime

from backend.db.session import get_db
from backend.core.security import get_current_active_user, has_permission
from backend.core.config import settings
from backend.db import models
from backend.db.models.user import UserRole
from backend.services.video.processor import VideoProcessor
from backend.services.parliament_tv import ParliamentTVCapture

# Custom dependency for token authentication via query parameter
async def get_current_user_from_token_param(token: Optional[str] = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.email == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

router = APIRouter()

# Initialize the video processor and Parliament TV capture service
video_processor = VideoProcessor()
parliament_tv_capture = ParliamentTVCapture()

# Create a static file route for audio files
@router.get("/static/audio/{filename}")
async def get_static_audio_file(filename: str):
    """Serve a static audio file directly.
    
    This endpoint is for direct access to audio files for debugging purposes.
    """
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    
    # Add debug logging
    print(f"DEBUG: Requested audio file: {filename}")
    print(f"DEBUG: Data directory: {data_dir}")
    
    # Look for the audio file in common locations
    possible_locations = [
        os.path.join(data_dir, "temp", "audio_extracts", filename),
        os.path.join(data_dir, filename),
        os.path.join(data_dir, "**", filename)
    ]
    
    # Try to find the file
    for location in possible_locations:
        print(f"DEBUG: Checking location: {location}")
        
        # For the wildcard path, use glob
        if "**" in location:
            print(f"DEBUG: Using glob to search recursively")
            matching_files = glob.glob(location, recursive=True)
            if matching_files:
                print(f"DEBUG: Found files with glob: {matching_files}")
                return FileResponse(
                    path=matching_files[0],
                    media_type="audio/mpeg",
                    filename=filename
                )
            else:
                print("DEBUG: No files found with glob")
        elif os.path.exists(location):
            print(f"DEBUG: File exists at: {location}")
            return FileResponse(
                path=location,
                media_type="audio/mpeg",
                filename=filename
            )
        else:
            print(f"DEBUG: File does not exist at: {location}")
    
    # List all files in the audio_extracts directory
    audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
    if os.path.exists(audio_extracts_dir):
        print(f"DEBUG: Listing all files in {audio_extracts_dir}:")
        for file in os.listdir(audio_extracts_dir):
            print(f"DEBUG:   - {file}")
    
    # If we couldn't find the file
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Audio file {filename} not found"
    )

@router.get("", response_model=List[Dict])
async def get_all_videos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all video files available in the system."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    
    # Find all MP4 files in the data directory and its subdirectories
    video_files = []
    
    # Search in the main data directory
    main_mp4_files = glob.glob(os.path.join(data_dir, "**/*.mp4"), recursive=True)
    for file_path in main_mp4_files:
        if os.path.isfile(file_path):
            # Get file stats
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            file_mtime = file_stats.st_mtime
            
            # Get relative path for display
            rel_path = os.path.relpath(file_path, data_dir)
            
            # Try to find a corresponding capture in the database
            filename = os.path.basename(file_path)
            capture = None
            
            # Extract capture ID from filename if possible
            capture_id = None
            if "_" in filename:
                parts = filename.split("_")
                for part in parts:
                    if part.isdigit():
                        capture_id = int(part)
                        break
            
            if capture_id:
                capture = db.query(models.CaptureSession).filter(
                    models.CaptureSession.id == capture_id
                ).first()
            
            # Add to the list
            video_files.append({
                "path": file_path,
                "relative_path": rel_path,
                "filename": filename,
                "size": file_size,
                "modified_time": file_mtime,
                "capture_id": capture.id if capture else None,
                "title": capture.title if capture else filename,
                "status": capture.status if capture else "unknown",
                "duration": capture.duration if capture else None,
                "created_by": capture.created_by.full_name if capture and capture.created_by else "Unknown",
                "stream_url": f"/api/v1/videos/stream/{os.path.basename(file_path)}"
            })
    
    # Sort by modified time, newest first
    video_files.sort(key=lambda x: x["modified_time"], reverse=True)
    
    return video_files

# Create a custom dependency for token authentication that doesn't raise exceptions
def get_user_from_token(token: str = None, db: Session = Depends(get_db)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        user = db.query(models.User).filter(models.User.email == username).first()
        return user
    except JWTError:
        return None

@router.get("/stream/{filename}", response_model=None)
async def stream_video(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Stream a video file by filename.
    
    Supports authentication via standard authentication.
    """
    # Check user permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    return stream_video_file(filename, db)

@router.get("/stream-with-token/{filename}", response_model=None)
async def stream_video_with_token(
    filename: str,
    token: str,
    db: Session = Depends(get_db),
):
    """Stream a video file by filename using token authentication.
    
    This endpoint is specifically for clients that can't use cookie-based authentication.
    """
    # Validate token and get user
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        # Get user from database
        user = db.query(models.User).filter(models.User.email == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
            
        # Check user permissions
        has_permission(user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
        
        return stream_video_file(filename, db)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

def stream_video_file(filename: str, db: Session):
    """Helper function to stream a video file."""
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    
    # Construct the full path, ensuring we don't allow directory traversal
    # Strip any leading slashes or path components to ensure we stay within data_dir
    safe_filename = filename.lstrip("/").replace("../", "")
    
    # Search for the file in the data directory and its subdirectories
    found_files = glob.glob(os.path.join(data_dir, "**", safe_filename), recursive=True)
    
    if not found_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file {filename} not found"
        )
    
    # Use the first match
    video_path = found_files[0]
    
    # Return the file as a streaming response
    return FileResponse(
        path=video_path,
        media_type="video/mp4"
    )

# This function has been removed as part of the audio/video extraction cleanup
    
    # Step 4: Handle Parliament TV captures differently
    if is_parliament_tv:
        logger.warning("This is a Parliament TV capture - audio must be extracted from the dedicated audio URL")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parliament TV captures require using the dedicated audio extraction endpoint: /api/v1/audio-extraction/{capture_id}"
        )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Could not find or create audio for {filename}"
    )

@router.post("/combine-audio-video", response_model=None)
async def combine_audio_video(
    video_filename: str = Form(...),
    audio_filename: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Combine separate audio and video files into a single file and return the combined file.
    
    This endpoint requires both video and audio filenames that exist in the data directory.
    """
    # Check user permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    print(f"Received request to combine video: {video_filename} with audio: {audio_filename}")
    
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    temp_dir = os.path.join(data_dir, "temp")
    media_dir = os.path.join(data_dir, "media")
    
    # Search in multiple directories
    search_dirs = [temp_dir, media_dir, data_dir]
    
    # Find the video file
    video_files = []
    for search_dir in search_dirs:
        found_files = glob.glob(os.path.join(search_dir, "**", video_filename), recursive=True)
        video_files.extend(found_files)
    
    if not video_files:
        print(f"Video file {video_filename} not found in search directories")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file {video_filename} not found"
        )
    
    # Find the audio file
    audio_files = []
    for search_dir in search_dirs:
        found_files = glob.glob(os.path.join(search_dir, "**", audio_filename), recursive=True)
        audio_files.extend(found_files)
    
    if not audio_files:
        print(f"Audio file {audio_filename} not found in search directories")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file {audio_filename} not found"
        )
    
    print(f"Found video file: {video_files[0]}")
    print(f"Found audio file: {audio_files[0]}")
    
    try:
        # Combine the audio and video files
        combined_file_path = video_processor.combine_audio_video(
            video_files[0],
            audio_files[0]
        )
        
        print(f"Successfully combined files, result: {combined_file_path}")
        
        # Return the filename instead of the file content
        return {
            "status": "success",
            "filename": os.path.basename(combined_file_path),
            "path": combined_file_path
        }
    except Exception as e:
        print(f"Error combining files: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to combine audio and video: {str(e)}"
        )

@router.get("/stream-combined/{filename}", response_model=None)
async def stream_combined_video(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Stream a combined audio/video file by filename.
    
    This endpoint is for streaming files that have already been combined.
    """
    # Check user permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    return stream_video_file(filename, db)

@router.get("/stream-combined-with-token/{filename}", response_model=None)
async def stream_combined_video_with_token(
    filename: str,
    token: str,
    db: Session = Depends(get_db)
):
    """Stream a combined audio/video file by filename using token authentication.
    
    This endpoint is for streaming combined files with token authentication.
    """
    # Validate the token and get the user
    current_user = get_user_from_token(token, db)
    
    # Check user permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    return stream_video_file(filename, db)


@router.get("/stream-audio/{filename}")
async def stream_audio(
    filename: str,
    debug: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Stream just the audio track from a video file by filename.
    
    Extracts and streams only the audio track from the video file.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    return stream_audio_from_video(filename, db, debug=debug)


@router.get("/stream-audio-with-token/{filename}")
async def stream_audio_with_token(
    filename: str,
    token: str,
    debug: bool = False,
    db: Session = Depends(get_db)
):
    """Stream just the audio track from a video file using token authentication.
    
    This endpoint is for streaming just the audio with token authentication.
    """
    # Authenticate the user using the token
    user = get_user_from_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    # Check user permissions
    has_permission(user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    return stream_audio_from_video(filename, db, debug=debug)


@router.delete("/delete/{filename}")
async def delete_video(
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a video file by filename."""
    # Only admins can delete videos
    has_permission(current_user, [UserRole.ADMIN])
    
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    
    # Construct the full path, ensuring we don't allow directory traversal
    # Strip any leading slashes or path components to ensure we stay within data_dir
    safe_filename = filename.lstrip("/").replace("../", "").replace("..\\", "")
    
    # Search for the file in the data directory and its subdirectories
    found_files = glob.glob(os.path.join(data_dir, "**", safe_filename), recursive=True)
    
    if not found_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file {filename} not found"
        )
    
    # Use the first match
    video_path = found_files[0]
    
    try:
        # Delete the file
        os.remove(video_path)
        
        # Check if there's a corresponding capture session in the database
        capture_id = None
        if "_" in filename:
            parts = filename.split("_")
            for part in parts:
                if part.isdigit():
                    capture_id = int(part)
                    break
        
        # Update the database if a capture session was found
        if capture_id:
            capture = db.query(models.CaptureSession).filter(
                models.CaptureSession.id == capture_id
            ).first()
            
            if capture:
                # Update the capture status to indicate the video was deleted
                capture.status = "deleted"
                db.commit()
        
        return {"status": "success", "detail": f"Video file {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting video file: {str(e)}"
        )


@router.delete("/delete-all")
async def delete_all_videos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete all video files."""
    # Only admins can delete all videos
    has_permission(current_user, [UserRole.ADMIN])
    
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    
    # Find all MP4 files in the data directory and its subdirectories
    mp4_files = glob.glob(os.path.join(data_dir, "**/*.mp4"), recursive=True)
    
    deleted_count = 0
    errors = []
    
    for file_path in mp4_files:
        try:
            # Delete the file
            os.remove(file_path)
            deleted_count += 1
            
            # Try to find a corresponding capture in the database
            filename = os.path.basename(file_path)
            capture_id = None
            
            # Extract capture ID from filename if possible
            if "_" in filename:
                parts = filename.split("_")
                for part in parts:
                    if part.isdigit():
                        capture_id = int(part)
                        break
            
            # Update the database if a capture session was found
            if capture_id:
                capture = db.query(models.CaptureSession).filter(
                    models.CaptureSession.id == capture_id
                ).first()
                
                if capture:
                    # Update the capture status to indicate the video was deleted
                    capture.status = "deleted"
        except Exception as e:
            errors.append({"file": file_path, "error": str(e)})
    
    # Commit all database changes at once
    db.commit()
    
    return {
        "status": "success", 
        "deleted_count": deleted_count,
        "errors": errors
    }


# This endpoint has been removed as part of the audio/video extraction cleanup
