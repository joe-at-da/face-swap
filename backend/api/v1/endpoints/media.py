"""
API endpoints for media streaming.
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.db import models

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/stream/{video_id}", response_model=None)
async def stream_media(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Stream media file for a capture session by ID.
    This endpoint serves the video file associated with a capture session.
    """
    try:
        logger.info(f"Streaming media for capture ID: {video_id}")
        
        # Get the capture session from the database
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture session not found with ID: {video_id}")
        
        # Get the file path from the capture session
        file_path = capture.file_path
        
        if not file_path or not os.path.exists(file_path):
            # Try to find the file using a pattern
            possible_paths = [
                f"/app/data/temp/capture_{str(video_id).zfill(4)}.mp4",
                f"/app/data/temp/capture_{video_id}.mp4",
                f"/app/data/captures/capture_{str(video_id).zfill(4)}.mp4",
                f"/app/data/captures/capture_{video_id}.mp4"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    break
            
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Media file not found for capture ID: {video_id}")
        
        # Determine content type based on file extension
        content_type = "video/mp4"  # Default to MP4
        if file_path.lower().endswith(".webm"):
            content_type = "video/webm"
        elif file_path.lower().endswith(".mov"):
            content_type = "video/quicktime"
        
        # Return the file as a streaming response
        return FileResponse(
            path=file_path,
            media_type=content_type,
            filename=os.path.basename(file_path)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error streaming media: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error streaming media: {str(e)}")
