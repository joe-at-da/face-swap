"""
Integration endpoints for external systems like Supabase.

These endpoints provide secure access to Parliament TV data for external systems.
"""

from fastapi import APIRouter, Depends, HTTPException, Security, Query, Path
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import os
import logging
import json
from datetime import datetime

from backend.db.session import get_db
from backend.db.models import CaptureSession, RecognitionProcess
from backend.core.security import get_api_key
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recognition/{video_id}", dependencies=[Security(get_api_key)])
def get_recognition_results(
    video_id: int = Path(..., description="ID of the video to get recognition results for"),
    db: Session = Depends(get_db)
):
    """
    Get recognition results for integration with external systems like Supabase.
    
    This endpoint provides access to the recognition results for a specific video,
    including speaker identification data and timestamps.
    
    Authentication is required via API key.
    """
    logger.info(f"Integration API: Getting recognition results for video ID {video_id}")
    
    # Find the recognition process for this video
    process = db.query(RecognitionProcess).filter(
        RecognitionProcess.video_id == video_id
    ).first()
    
    if not process:
        logger.warning(f"Integration API: Recognition process not found for video ID {video_id}")
        raise HTTPException(status_code=404, detail="Recognition process not found")
    
    # Get the capture session for additional metadata
    capture = db.query(CaptureSession).filter(
        CaptureSession.id == video_id
    ).first()
    
    if not capture:
        logger.warning(f"Integration API: Capture session not found for video ID {video_id}")
        raise HTTPException(status_code=404, detail="Capture session not found")
    
    # Prepare the response with recognition results and metadata
    response = {
        "success": True,
        "video_id": video_id,
        "title": capture.title,
        "description": capture.description,
        "capture_date": capture.start_time,
        "duration": capture.duration,
        "status": process.status,
        "results": process.results,
        "audio_url": capture.capture_metadata.get("audio_url", "") if capture.capture_metadata else "",
        "video_url": capture.capture_metadata.get("video_url", "") if capture.capture_metadata else "",
        "combined_av_url": json.loads(process.process_metadata).get("combined_av_url", "") if process.process_metadata and isinstance(process.process_metadata, str) else \
                          process.process_metadata.get("combined_av_url", "") if process.process_metadata else ""
    }
    
    # Make the response JSON serializable (handle datetime objects)
    serializable_response = make_json_serializable(response)
    
    return serializable_response


@router.get("/videos", dependencies=[Security(get_api_key)])
def list_videos(
    limit: int = Query(10, description="Maximum number of videos to return"),
    offset: int = Query(0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Filter by recognition status"),
    db: Session = Depends(get_db)
):
    """
    List videos with recognition data for integration with external systems.
    
    This endpoint provides a paginated list of videos with recognition data,
    including metadata and status information.
    
    Authentication is required via API key.
    """
    logger.info(f"Integration API: Listing videos with limit {limit}, offset {offset}")
    
    # Build the query for recognition processes
    query = db.query(RecognitionProcess)
    
    # Apply status filter if provided
    if status:
        query = query.filter(RecognitionProcess.status == status)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    processes = query.offset(offset).limit(limit).all()
    
    # Prepare the response with video list
    videos = []
    for process in processes:
        # Get the capture session for additional metadata
        capture = db.query(CaptureSession).filter(
            CaptureSession.id == process.video_id
        ).first()
        
        if capture:
            video_data = {
                "video_id": process.video_id,
                "title": capture.title,
                "description": capture.description,
                "capture_date": capture.start_time,
                "duration": capture.duration,
                "status": process.status,
                "has_results": process.results is not None,
                "audio_url": capture.capture_metadata.get("audio_url", "") if capture.capture_metadata else "",
                "video_url": capture.capture_metadata.get("video_url", "") if capture.capture_metadata else "",
                "combined_av_url": json.loads(process.process_metadata).get("combined_av_url", "") if process.process_metadata and isinstance(process.process_metadata, str) else \
                                  process.process_metadata.get("combined_av_url", "") if process.process_metadata else ""
            }
            videos.append(video_data)
    
    # Make the response JSON serializable (handle datetime objects)
    serializable_videos = make_json_serializable(videos)
    
    return {
        "success": True,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "videos": serializable_videos
    }
