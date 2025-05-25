"""
API endpoints for integrated transcription and recognition processing.

This module provides endpoints for processing videos with both transcription and
face recognition, and integrating the results for improved speaker identification.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, File, UploadFile
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db import models
from backend.api import deps
from backend.services.video.transcription_recognition_integrator import TranscriptionRecognitionIntegrator
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
integrator_service = TranscriptionRecognitionIntegrator()


@router.post("/{capture_id}/process")
async def process_transcription_recognition(
    capture_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Process a video with integrated transcription and face recognition.
    
    This endpoint will:
    1. Run transcription with speaker diarization
    2. Run face recognition
    3. Integrate the results for improved speaker identification
    4. Store the results in the database
    
    The processing is done in the background to avoid blocking the API.
    """
    logger.info(f"Starting integrated transcription and recognition processing for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Check if the video file exists
    if not capture.video_path or not os.path.exists(capture.video_path):
        raise HTTPException(status_code=400, detail="Video file not found")
    
    # Add the processing task to the background
    background_tasks.add_task(
        process_in_background,
        capture_id,
        current_user.id
    )
    
    return {
        "success": True,
        "message": f"Integrated transcription and recognition processing started for capture {capture_id}",
        "status": "processing"
    }


@router.get("/{capture_id}/status")
async def get_processing_status(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get the status of integrated transcription and recognition processing."""
    logger.info(f"Getting processing status for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Check if transcription results exist
    has_transcription = capture.transcription_results is not None
    
    # Check if face detection results exist
    has_face_detection = capture.face_detection_results is not None
    
    # Check if timeline data exists
    has_timeline = capture.timeline_data is not None
    
    # Get recognition events count
    events_count = db.query(models.RecognitionEvent).filter(
        models.RecognitionEvent.capture_session_id == capture_id
    ).count()
    
    # Determine the status
    status = "not_started"
    if has_transcription and has_face_detection and has_timeline:
        status = "completed"
    elif has_transcription or has_face_detection:
        status = "partially_completed"
    
    return {
        "success": True,
        "capture_id": capture_id,
        "status": status,
        "has_transcription": has_transcription,
        "has_face_detection": has_face_detection,
        "has_timeline": has_timeline,
        "events_count": events_count
    }


@router.post("/{capture_id}/integrate_existing")
async def integrate_existing_data(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Integrate existing transcription and recognition data.
    
    This endpoint will process existing transcription and recognition data
    for a capture session and integrate them for improved speaker identification.
    """
    logger.info(f"Integrating existing data for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Process existing data
    result = integrator_service.process_existing_data(db, capture_id)
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=400, 
            detail=result.get("error", "Failed to integrate existing data")
        )
    
    return result


@router.get("/{capture_id}/integrated_results")
async def get_integrated_results(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get the integrated transcription and recognition results."""
    logger.info(f"Getting integrated results for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Check if timeline data exists
    if not capture.timeline_data:
        raise HTTPException(status_code=404, detail="No integrated results found")
    
    try:
        # Parse timeline data
        timeline_data = json.loads(capture.timeline_data)
        return timeline_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid timeline data format")


async def process_in_background(capture_id: int, user_id: int):
    """
    Process integrated transcription and recognition in the background.
    
    This function is called by the background task system and should not be called directly.
    """
    logger.info(f"Processing integrated transcription and recognition in background for capture {capture_id}")
    
    # Create a new database session for the background task
    db = next(get_db())
    
    try:
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture not found: {capture_id}")
            return
        
        # Process the video
        result = integrator_service.process_video(capture.video_path, db, capture_id)
        
        if not result.get("success", False):
            logger.error(f"Processing failed: {result.get('error', 'Unknown error')}")
        else:
            logger.info(f"Processing completed successfully for capture {capture_id}")
        
    except Exception as e:
        logger.exception(f"Error processing integrated transcription and recognition: {str(e)}")
    finally:
        db.close()
