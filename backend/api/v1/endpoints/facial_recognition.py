"""
API endpoints for facial recognition processing of Parliament TV videos.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from backend.api.deps import get_db, get_current_user, get_current_user_with_roles
from backend.db import models
from backend.core.security import UserRole
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
facial_recognition_service = FacialRecognitionService()
face_profile_service = FaceProfileService()
multimodal_service = MultimodalRecognitionService()

@router.post("/process-video/{capture_id}", response_model=Dict[str, Any])
async def process_video_with_facial_recognition(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process a Parliament TV video with facial recognition.
    
    This endpoint will:
    1. Check if the video exists and has been transcribed
    2. Extract faces from the video
    3. Create face profiles for detected speakers
    4. Link face profiles with existing voice profiles if available
    """
    try:
        logger.info(f"Processing video with facial recognition: {capture_id}")
        
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture session not found: {capture_id}")
        
        # Check if the video file exists
        if not capture.file_path or not os.path.exists(capture.file_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Check if facial recognition is already in progress or completed
        metadata = capture.metadata or {}
        if metadata.get("facial_recognition_status") == "processing":
            return {
                "success": True,
                "message": "Facial recognition is already in progress",
                "capture_id": capture_id,
                "status": "processing"
            }
        elif metadata.get("facial_recognition_status") == "completed":
            return {
                "success": True,
                "message": "Facial recognition has already been completed",
                "capture_id": capture_id,
                "status": "completed",
                "results": metadata.get("facial_recognition_results", {})
            }
        
        # Update metadata to indicate processing has started
        metadata["facial_recognition_status"] = "processing"
        metadata["facial_recognition_started_at"] = datetime.now().isoformat()
        capture.metadata = metadata
        db.commit()
        
        # Start facial recognition processing in background
        try:
            # Use Celery to run the task asynchronously
            from backend.services.tasks.recognition_tasks import process_video_with_facial_recognition
            process_video_with_facial_recognition.delay(
                capture_id=capture_id
            )
            
            return {
                "success": True,
                "message": "Facial recognition processing started",
                "capture_id": capture_id,
                "status": "processing"
            }
        except Exception as e:
            # Update metadata with error
            metadata["facial_recognition_status"] = "failed"
            metadata["facial_recognition_error"] = str(e)
            capture.metadata = metadata
            db.commit()
            
            raise HTTPException(
                status_code=500,
                detail=f"Error starting facial recognition processing: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing video with facial recognition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{capture_id}", response_model=Dict[str, Any])
async def get_facial_recognition_status(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the status of facial recognition processing for a video.
    """
    try:
        logger.info(f"Getting facial recognition status for capture: {capture_id}")
        
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture session not found: {capture_id}")
        
        # Get facial recognition status from metadata
        metadata = capture.metadata or {}
        status = metadata.get("facial_recognition_status", "not_started")
        
        response = {
            "success": True,
            "capture_id": capture_id,
            "status": status
        }
        
        # Add additional information based on status
        if status == "completed":
            response["results"] = metadata.get("facial_recognition_results", {})
            response["completed_at"] = metadata.get("facial_recognition_completed_at")
        elif status == "failed":
            response["error"] = metadata.get("facial_recognition_error")
        elif status == "processing":
            response["started_at"] = metadata.get("facial_recognition_started_at")
        
        return make_json_serializable(response)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting facial recognition status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/identify-speaker", response_model=Dict[str, Any])
async def identify_speaker_in_image(
    file: UploadFile = File(...),
    threshold: float = Form(0.6),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Identify a speaker in an uploaded image using facial recognition.
    """
    try:
        logger.info("Identifying speaker in uploaded image")
        
        # Create a temporary directory for the uploaded image
        temp_dir = Path("/app/data/temp/face_recognition")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the uploaded file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        image_filename = f"speaker_identification_{timestamp_str}{file_extension}"
        image_path = str(temp_dir / image_filename)
        
        # Write the file
        with open(image_path, "wb") as f:
            f.write(await file.read())
        
        # Detect faces in the image
        try:
            import face_recognition
            
            # Load the image and detect faces
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return {
                    "success": False,
                    "message": "No faces detected in the image"
                }
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                return {
                    "success": False,
                    "message": "Failed to extract face encodings"
                }
            
            # Match the first face with existing profiles
            face_profile, confidence_score = face_profile_service.match_face_with_profiles(
                db=db,
                face_encoding=face_encodings[0].tolist(),
                threshold=threshold
            )
            
            if not face_profile:
                return {
                    "success": True,
                    "identified": False,
                    "message": "No matching face profile found"
                }
            
            # Get the voice profile if linked
            voice_profile = None
            if face_profile.voice_profile_id:
                voice_profile = db.query(models.VoiceProfile).filter(
                    models.VoiceProfile.id == face_profile.voice_profile_id
                ).first()
            
            # Prepare response
            response = {
                "success": True,
                "identified": True,
                "face_profile": {
                    "id": face_profile.id,
                    "name": face_profile.name,
                    "role": face_profile.role,
                    "party": face_profile.party,
                    "confidence_score": confidence_score
                }
            }
            
            if voice_profile:
                response["voice_profile"] = {
                    "id": voice_profile.id,
                    "name": voice_profile.name,
                    "role": voice_profile.role,
                    "party": voice_profile.party
                }
            
            return make_json_serializable(response)
        except Exception as e:
            logger.exception(f"Error identifying speaker: {str(e)}")
            return {
                "success": False,
                "message": f"Error identifying speaker: {str(e)}"
            }
    except Exception as e:
        logger.exception(f"Error processing uploaded image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
