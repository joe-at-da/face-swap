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
            logger.error(f"Capture session not found with ID: {video_id}")
            raise HTTPException(status_code=404, detail=f"Capture session not found with ID: {video_id}")
        
        # Get the file path from the capture session
        file_path = capture.file_path
        logger.info(f"Original file path from database: {file_path}")
        
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"File path not found in database or does not exist: {file_path}")
            # Try to find the file using a pattern
            possible_paths = [
                f"/app/data/temp/capture_{str(video_id).zfill(4)}.mp4",
                f"/app/data/temp/capture_{video_id}.mp4",
                f"/app/data/captures/capture_{str(video_id).zfill(4)}.mp4",
                f"/app/data/captures/capture_{video_id}.mp4"
            ]
            
            logger.info(f"Trying possible paths: {possible_paths}")
            found = False
            for path in possible_paths:
                logger.info(f"Checking path: {path}")
                if os.path.exists(path):
                    file_path = path
                    found = True
                    logger.info(f"Found file at: {file_path}")
                    break
            
            if not found or not os.path.exists(file_path):
                logger.error(f"Media file not found for capture ID: {video_id} after trying all possible paths")
                raise HTTPException(status_code=404, detail=f"Media file not found for capture ID: {video_id}")
        
        # Determine content type based on file extension
        content_type = "video/mp4"  # Default to MP4
        if file_path.lower().endswith(".webm"):
            content_type = "video/webm"
        elif file_path.lower().endswith(".mov"):
            content_type = "video/quicktime"
        
        logger.info(f"Serving file: {file_path} with content type: {content_type}")
        
        # Return the file as a streaming response with appropriate headers
        response = FileResponse(
            path=file_path,
            media_type=content_type,
            filename=os.path.basename(file_path)
        )
        
        # Add headers to prevent caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error streaming media: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error streaming media: {str(e)}")
