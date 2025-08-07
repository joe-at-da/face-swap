"""
API endpoints for processing recognition data.

This module provides endpoints for processing face and voice recognition data,
storing it in the database, and generating timeline data.
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
from backend.services.recognition.timeline_service import TimelineService
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
timeline_service = TimelineService()
facial_recognition = FacialRecognitionService()
multimodal_service = MultimodalRecognitionService()


@router.post("/{capture_id}/process_recognition")
async def process_recognition(
    capture_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Process recognition data for a capture session.
    
    This endpoint will:
    1. Process face recognition for the video
    2. Process voice recognition (if transcription exists)
    3. Generate timeline data
    4. Find correlations between face and voice data
    
    The processing is done in the background to avoid blocking the API.
    """
    logger.info(f"Starting recognition processing for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Check if the video file exists
    if not capture.video_path or not os.path.exists(capture.video_path):
        raise HTTPException(status_code=400, detail="Video file not found")
    
    # Add the processing task to the background
    background_tasks.add_task(
        process_recognition_background,
        capture_id,
        current_user.id
    )
    
    return {
        "success": True,
        "message": f"Recognition processing started for capture {capture_id}",
        "status": "processing"
    }


@router.get("/{capture_id}/recognition_status")
async def get_recognition_status(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Get the status of recognition processing for a capture session."""
    logger.info(f"Getting recognition status for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Check if face detection results exist
    has_face_detection = capture.face_detection_results is not None
    
    # Check if timeline data exists
    has_timeline = capture.timeline_data is not None
    
    # Check if recognition results exist (legacy format)
    has_recognition = capture.recognition_results is not None
    
    # Check if transcription results exist
    has_transcription = capture.transcription_results is not None
    
    # Determine the status
    status = "not_started"
    if has_face_detection and has_timeline:
        status = "completed"
    elif has_face_detection or has_recognition:
        status = "partially_completed"
    
    # Get recognition events count
    events_count = db.query(models.RecognitionEvent).filter(
        models.RecognitionEvent.capture_session_id == capture_id
    ).count()
    
    return {
        "success": True,
        "capture_id": capture_id,
        "status": status,
        "has_face_detection": has_face_detection,
        "has_timeline": has_timeline,
        "has_recognition": has_recognition,
        "has_transcription": has_transcription,
        "events_count": events_count
    }


@router.post("/{capture_id}/store_face_detection")
async def store_face_detection(
    capture_id: int,
    detection_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Store face detection data for a capture session."""
    logger.info(f"Storing face detection for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Store the detection data
    result = timeline_service.store_face_detection(db, capture_id, detection_data)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to store face detection"))
    
    return result


@router.post("/{capture_id}/store_speaker_segment")
async def store_speaker_segment(
    capture_id: int,
    segment_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Store speaker segment data for a capture session."""
    logger.info(f"Storing speaker segment for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Store the segment data
    result = timeline_service.store_speaker_segment(db, capture_id, segment_data)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to store speaker segment"))
    
    return result


@router.post("/{capture_id}/update_timeline")
async def update_timeline(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Update the timeline data for a capture session."""
    logger.info(f"Updating timeline for capture {capture_id}")
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
    
    # Update the timeline data
    result = timeline_service.update_timeline_data(db, capture_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to update timeline"))
    
    return result


async def process_recognition_background(capture_id: int, user_id: int):
    """
    Process recognition data in the background.
    
    This function is called by the background task system and should not be called directly.
    """
    logger.info(f"Processing recognition in background for capture {capture_id}")
    
    # Create a new database session for the background task
    db = next(get_db())
    
    try:
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture not found: {capture_id}")
            return
        
        # Process face recognition
        logger.info(f"Processing face recognition for capture {capture_id}")
        face_result = facial_recognition.identify_speakers(capture.video_path)
        
        if face_result.get("success", False):
            # Store the face detection results
            capture.face_detection_results = json.dumps(make_json_serializable(face_result))
            db.commit()
            
            # Store face detections in the timeline
            if "faces" in face_result:
                for face in face_result["faces"]:
                    if "timestamp" in face and "name" in face:
                        detection = {
                            "timestamp": face["timestamp"],
                            "name": face["name"],
                            "confidence": face.get("confidence", 0.0),
                            "person_id": face.get("person_id"),
                            "box": face.get("box")
                        }
                        timeline_service.store_face_detection(db, capture_id, detection)
            
            # If we have transcription data, try to process with multimodal recognition
            if capture.transcription_results:
                logger.info(f"Processing multimodal recognition for capture {capture_id}")
                multimodal_result = multimodal_service.process_video_with_transcription(db, capture_id)
                
                if multimodal_result.get("success", False):
                    # Store speaker segments in the timeline
                    if "segments" in multimodal_result:
                        for segment in multimodal_result["segments"]:
                            if "start" in segment and "end" in segment and "speaker" in segment:
                                speaker_segment = {
                                    "start": segment["start"],
                                    "end": segment["end"],
                                    "speaker": segment["speaker"],
                                    "confidence": segment.get("confidence", 0.0),
                                    "speaker_id": segment.get("speaker_id"),
                                    "text": segment.get("text", "")
                                }
                                timeline_service.store_speaker_segment(db, capture_id, speaker_segment)
            
            # Update the timeline data
            logger.info(f"Updating timeline data for capture {capture_id}")
            timeline_service.update_timeline_data(db, capture_id)
            
            # CRITICAL: Add missing integration step - populate parliament_clips.db and export to Supabase
            try:
                logger.info(f"Starting parliament clips integration for capture {capture_id}")
                
                # Import the integration services
                from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
                from backend.services.recognition.simplified_export import normalize_and_export_clips
                
                # Initialize integration service
                integration_service = ParliamentClipsIntegrationService()
                
                # Check if face identification results JSON exists
                video_path = capture.video_path or capture.file_path
                if video_path:
                    # Determine results file path based on video path
                    video_name = os.path.splitext(os.path.basename(video_path))[0]
                    results_file = os.path.join(os.path.dirname(video_path), f"{video_name}_speaker_identification_results.json")
                    
                    if os.path.exists(results_file):
                        logger.info(f"Found face identification results: {results_file}")
                        
                        # Read the results JSON
                        with open(results_file, 'r') as f:
                            face_results = json.load(f)
                        
                        # Integrate results into parliament_clips.db
                        logger.info(f"Integrating face identification results into parliament_clips.db")
                        integration_result = integration_service.integrate_recognition_results(
                            db_session=db,
                            video_id=capture_id,
                            recognition_results=face_results,
                            video_path=video_path,
                            audio_path=capture.audio_path
                        )
                        
                        if integration_result.get("success", False):
                            logger.info(f"Successfully integrated recognition results for capture {capture_id}")
                            
                            # Export to Supabase using the standardized export function
                            logger.info(f"Exporting clips to Supabase for capture {capture_id}")
                            
                            # Get SQLite session for export
                            sqlite_db_path = integration_service.db_path
                            
                            # Use the standardized export function with SQLite database path
                            export_result = normalize_and_export_clips(
                                db=sqlite_db_path,
                                video_id=capture_id,
                                supabase_service=None
                            )
                            
                            if export_result.get("success", False):
                                logger.info(f"Successfully exported clips to Supabase for capture {capture_id}")
                                logger.info(f"Exported {export_result.get('exported_count', 0)} grouped clips")
                            else:
                                logger.error(f"Failed to export clips to Supabase: {export_result.get('error', 'Unknown error')}")
                        else:
                            logger.error(f"Failed to integrate recognition results: {integration_result.get('error', 'Unknown error')}")
                    else:
                        logger.warning(f"Face identification results file not found: {results_file}")
                        logger.info("This may be normal if face identification is still in progress")
                else:
                    logger.warning(f"No video path found for capture {capture_id}")
                    
            except Exception as e:
                logger.error(f"Error in parliament clips integration for capture {capture_id}: {str(e)}")
                import traceback
                logger.error(f"Integration error traceback: {traceback.format_exc()}")
            
            logger.info(f"Recognition processing completed for capture {capture_id}")
        else:
            logger.error(f"Face recognition failed for capture {capture_id}: {face_result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.exception(f"Error processing recognition: {str(e)}")
    finally:
        db.close()
