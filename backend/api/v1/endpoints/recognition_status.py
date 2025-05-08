"""
API endpoints for retrieving recognition status.
"""

import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/recognition-status/{video_id}", response_model=Dict)
async def get_recognition_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the recognition status and progress for a specific video.
    """
    logger.info(f"Getting recognition status for video ID: {video_id}")
    
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found for video ID {video_id}"
        )
    
    # Check if recognition status exists
    recognition_status = getattr(video, 'recognition_status', None)
    recognition_progress = getattr(video, 'recognition_progress', None)
    
    # Parse progress if it exists
    progress_data = None
    if recognition_progress:
        try:
            progress_data = json.loads(recognition_progress)
        except Exception as e:
            logger.error(f"Error parsing recognition progress for video ID {video_id}: {str(e)}")
            progress_data = {"steps": []}
    
    # Check if we have results
    recognition_results = getattr(video, 'recognition_results', None)
    has_results = recognition_results is not None and recognition_results != ''
    
    # Format response to match frontend expectations
    status_data = {
        "status": recognition_status or "not_started",
        "progress": progress_data or {"steps": []},
        "video_id": video_id,
        "started_at": video.recognition_started_at.isoformat() if hasattr(video, 'recognition_started_at') and video.recognition_started_at else None,
        "completed_at": video.recognition_completed_at.isoformat() if hasattr(video, 'recognition_completed_at') and video.recognition_completed_at else None,
        "has_results": has_results
    }
    
    # Return the status in the format expected by the frontend
    return {
        "success": True,
        "status": status_data,
        "error": None
    }
