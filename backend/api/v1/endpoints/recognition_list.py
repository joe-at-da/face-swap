"""
API endpoints for listing recognition results.
"""

import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/list/{source_type}", response_model=List[Dict])
async def list_recognition_results(
    source_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all recognition results for a specific source type.
    """
    logger.info(f"Listing recognition results for source type: {source_type}")
    
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get all videos with recognition results
    # For parliament-tv, we'll just return all captures with recognition status
    # In a real implementation, you might want to filter by source_url or metadata
    query = db.query(models.CaptureSession).filter(
        models.CaptureSession.recognition_status.isnot(None)
    ).order_by(models.CaptureSession.created_at.desc())
    
    # Limit to 50 results to avoid performance issues
    videos = query.limit(50).all()
    
    # Format the results
    results = []
    for video in videos:
        recognition_status = getattr(video, 'recognition_status', None)
        recognition_results = getattr(video, 'recognition_results', None)
        
        # Parse results if they exist
        parsed_results = None
        if recognition_results:
            try:
                parsed_results = json.loads(recognition_results)
            except Exception as e:
                logger.error(f"Error parsing recognition results for video ID {video.id}: {str(e)}")
                parsed_results = None
        
        # Create a result object
        result = {
            "id": video.id,
            "title": getattr(video, 'title', f"Capture {video.id}"),
            "status": recognition_status or "not_started",
            "created_at": video.created_at.isoformat() if hasattr(video, 'created_at') and video.created_at else None,
            "started_at": video.recognition_started_at.isoformat() if hasattr(video, 'recognition_started_at') and video.recognition_started_at else None,
            "completed_at": video.recognition_completed_at.isoformat() if hasattr(video, 'recognition_completed_at') and video.recognition_completed_at else None,
            "has_results": recognition_results is not None and recognition_results != '',
            "source_type": source_type,
            "thumbnail_url": getattr(video, 'thumbnail_url', None),
            "video_path": getattr(video, 'video_path', None),
            "audio_path": getattr(video, 'audio_path', None),
        }
        
        results.append(result)
    
    return results
