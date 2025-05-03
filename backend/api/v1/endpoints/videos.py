from typing import List, Dict, Optional
import os
import glob
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.security import get_current_active_user, has_permission
from backend.core.config import settings
from backend.db import models
from backend.db.models.user import UserRole

router = APIRouter()

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

@router.get("/stream/{filename}")
async def stream_video(
    filename: str,
    current_user: models.User = Depends(get_current_active_user)
):
    """Stream a video file by filename."""
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
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
    
    # Return the file as a streaming response
    from fastapi.responses import FileResponse
    return FileResponse(video_path, media_type="video/mp4")


@router.delete("/delete/{filename}")
async def delete_video(
    filename: str,
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
