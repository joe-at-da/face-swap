"""
API endpoints for multimodal recognition (combining voice and face recognition).
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
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
multimodal_service = MultimodalRecognitionService()

@router.post("/process-video/{video_id}", response_model=Dict[str, Any])
async def process_video_with_multimodal_recognition(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process a video with multimodal recognition (voice + face).
    
    This endpoint will:
    1. Extract faces from speaker segments in the video
    2. Create or update face profiles for each speaker
    3. Link face profiles with existing voice profiles
    4. Update the video metadata with recognition results
    """
    try:
        logger.info(f"Processing video with multimodal recognition: {video_id}")
        
        # Process the video
        results = multimodal_service.process_video_with_transcription(db=db, video_id=video_id)
        
        if not results["success"]:
            raise HTTPException(status_code=400, detail=results.get("error", "Unknown error"))
        
        # Return results
        return make_json_serializable(results)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

@router.post("/identify-speaker-in-frame", response_model=Dict[str, Any])
async def identify_speaker_in_frame(
    file: UploadFile = File(...),
    threshold: float = Form(0.6),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Identify a speaker in a video frame using facial recognition.
    
    This endpoint will:
    1. Extract faces from the uploaded frame
    2. Match the faces with existing face profiles
    3. Return the identified speaker information
    """
    try:
        logger.info("Identifying speaker in uploaded frame")
        
        # Create a temporary directory for the uploaded frame
        temp_dir = Path("/app/data/temp/frames")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the uploaded file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        frame_filename = f"frame_{timestamp_str}{file_extension}"
        frame_path = str(temp_dir / frame_filename)
        
        # Write the file
        with open(frame_path, "wb") as f:
            f.write(await file.read())
        
        # Identify the speaker
        results = multimodal_service.identify_speaker_in_frame(
            db=db,
            frame_path=frame_path,
            threshold=threshold
        )
        
        if not results["success"]:
            raise HTTPException(status_code=400, detail=results.get("error", "Unknown error"))
        
        # Return results
        return make_json_serializable(results)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error identifying speaker: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error identifying speaker: {str(e)}")

@router.post("/combine-recognition-results", response_model=Dict[str, Any])
async def combine_recognition_results(
    voice_results: Dict[str, Any] = Body(...),
    face_results: Dict[str, Any] = Body(...),
    current_user: models.User = Depends(get_current_user)
):
    """
    Combine voice and face recognition results for improved speaker identification.
    
    This endpoint will:
    1. Take results from both voice and face recognition
    2. Combine them using a weighted approach
    3. Return the combined recognition results
    """
    try:
        logger.info("Combining voice and face recognition results")
        
        # Combine the results
        results = multimodal_service.combine_recognition_results(
            voice_results=voice_results,
            face_results=face_results
        )
        
        if not results["success"]:
            raise HTTPException(status_code=400, detail=results.get("error", "Unknown error"))
        
        # Return results
        return make_json_serializable(results)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error combining recognition results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error combining recognition results: {str(e)}")

@router.post("/calculate-speaker-confidence", response_model=Dict[str, Any])
async def calculate_speaker_confidence(
    face_data: Dict[str, Any] = Body(...),
    voice_data: Dict[str, Any] = Body(...),
    current_user: models.User = Depends(get_current_user)
):
    """
    Calculate confidence score for speaker identification based on both face and voice recognition.
    
    This endpoint will:
    1. Take data from both face and voice recognition
    2. Calculate a detailed confidence score with boosters and penalties
    3. Return the confidence assessment with detailed factors
    
    The confidence calculation includes:
    - Name similarity between profiles
    - Explicit links between face and voice profiles
    - Individual confidence scores from each modality
    - Confidence boosters for matching data
    - Confidence penalties for mismatches
    """
    try:
        logger.info("Calculating speaker confidence score")
        
        # Calculate confidence score
        results = multimodal_service.calculate_speaker_confidence(
            face_data=face_data,
            voice_data=voice_data
        )
        
        if not results["success"]:
            raise HTTPException(status_code=400, detail=results.get("error", "Unknown error"))
        
        # Return results
        return make_json_serializable(results)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error calculating speaker confidence: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating speaker confidence: {str(e)}")
