"""
API endpoints for retrieving recognition results.
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

@router.get("/results/{video_id}", response_model=Dict)
async def get_recognition_results(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the recognition results for a specific video.
    """
    logger.info(f"Getting recognition results for video ID: {video_id}")
    
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found for video ID {video_id}"
        )
    
    # Check if recognition results exist
    if not video.recognition_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recognition results found for video ID {video_id}"
        )
    
    # Parse and return the recognition results
    try:
        # If the results are stored as a JSON string, parse them
        if isinstance(video.recognition_results, str):
            results = json.loads(video.recognition_results)
        else:
            results = video.recognition_results
            
        # Return the results directly as the frontend expects
        # The frontend is looking for speakers and segments
        if isinstance(results, dict) and ('speakers' in results or 'segments' in results):
            return results
        elif isinstance(results, dict) and 'results' in results:
            return results['results']
        else:
            # Fallback to the original format
            return {
                "success": True,
                "video_id": video_id,
                "speakers": results.get('speakers', []),
                "segments": results.get('segments', [])
            }
    except Exception as e:
        logger.error(f"Error parsing recognition results for video ID {video_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing recognition results: {str(e)}"
        )
