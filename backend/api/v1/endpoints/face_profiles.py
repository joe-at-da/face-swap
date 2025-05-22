"""
API endpoints for managing face profiles.
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
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
face_profile_service = FaceProfileService()

# Schema models
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FaceProfileCreate(BaseModel):
    name: str
    role: Optional[str] = None
    party: Optional[str] = None
    voice_profile_id: Optional[int] = None

class FaceProfileResponse(BaseModel):
    id: int
    name: str
    role: Optional[str] = None
    party: Optional[str] = None
    voice_profile_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    sample_count: int = 0
    confidence_score: Optional[float] = None
    is_verified: bool = False

class FaceSampleResponse(BaseModel):
    id: int
    face_profile_id: int
    image_path: str
    confidence_score: Optional[float] = None
    timestamp: Optional[float] = None
    created_at: datetime

@router.post("/", response_model=FaceProfileResponse)
async def create_face_profile(
    profile: FaceProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Create a new face profile.
    """
    try:
        logger.info(f"Creating face profile: {profile.name}")
        
        # Create the face profile
        face_profile = face_profile_service.create_face_profile(
            db=db,
            name=profile.name,
            role=profile.role,
            party=profile.party,
            voice_profile_id=profile.voice_profile_id
        )
        
        # Prepare response
        return {
            "id": face_profile.id,
            "name": face_profile.name,
            "role": face_profile.role,
            "party": face_profile.party,
            "voice_profile_id": face_profile.voice_profile_id,
            "created_at": face_profile.created_at,
            "updated_at": face_profile.updated_at,
            "sample_count": face_profile.profile_metadata.get("sample_count", 0) if face_profile.profile_metadata else 0,
            "confidence_score": face_profile.confidence_score,
            "is_verified": face_profile.is_verified
        }
    except Exception as e:
        logger.exception(f"Error creating face profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating face profile: {str(e)}")

@router.get("/", response_model=List[FaceProfileResponse])
async def get_face_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all face profiles.
    """
    try:
        logger.info(f"Getting face profiles (skip={skip}, limit={limit})")
        
        # Get all face profiles
        face_profiles = face_profile_service.get_face_profiles(db, skip=skip, limit=limit)
        
        # Prepare response
        return [
            {
                "id": profile.id,
                "name": profile.name,
                "role": profile.role,
                "party": profile.party,
                "voice_profile_id": profile.voice_profile_id,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
                "sample_count": profile.metadata.get("sample_count", 0) if profile.metadata else 0,
                "confidence_score": profile.confidence_score,
                "is_verified": profile.is_verified
            }
            for profile in face_profiles
        ]
    except Exception as e:
        logger.exception(f"Error getting face profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting face profiles: {str(e)}")

@router.get("/{profile_id}", response_model=FaceProfileResponse)
async def get_face_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a face profile by ID.
    """
    try:
        logger.info(f"Getting face profile: {profile_id}")
        
        # Get the face profile
        face_profile = face_profile_service.get_face_profile(db, profile_id)
        if not face_profile:
            raise HTTPException(status_code=404, detail=f"Face profile not found: {profile_id}")
        
        # Prepare response
        return {
            "id": face_profile.id,
            "name": face_profile.name,
            "role": face_profile.role,
            "party": face_profile.party,
            "voice_profile_id": face_profile.voice_profile_id,
            "created_at": face_profile.created_at,
            "updated_at": face_profile.updated_at,
            "sample_count": face_profile.profile_metadata.get("sample_count", 0) if face_profile.profile_metadata else 0,
            "confidence_score": face_profile.confidence_score,
            "is_verified": face_profile.is_verified
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting face profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting face profile: {str(e)}")

@router.post("/{profile_id}/samples", response_model=FaceSampleResponse)
async def upload_face_sample(
    profile_id: int,
    file: UploadFile = File(...),
    confidence_score: Optional[float] = Form(None),
    source_video_id: Optional[int] = Form(None),
    timestamp: Optional[float] = Form(None),
    frame_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Upload a face sample for a profile.
    """
    try:
        logger.info(f"Uploading face sample for profile: {profile_id}")
        
        # Check if the profile exists
        face_profile = face_profile_service.get_face_profile(db, profile_id)
        if not face_profile:
            raise HTTPException(status_code=404, detail=f"Face profile not found: {profile_id}")
        
        # Create the samples directory if it doesn't exist
        samples_dir = Path("/app/data/face_profiles/samples") / str(profile_id)
        samples_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the uploaded file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        image_filename = f"face_sample_{profile_id}_{timestamp_str}{file_extension}"
        image_path = str(samples_dir / image_filename)
        
        # Write the file
        with open(image_path, "wb") as f:
            f.write(await file.read())
        
        # Extract face encoding
        try:
            import face_recognition
            import numpy as np
            
            # Load the image and extract face encoding
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                raise HTTPException(status_code=400, detail="No face detected in the uploaded image")
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                raise HTTPException(status_code=400, detail="Failed to extract face encoding")
            
            # Use the first face encoding
            encoding = face_encodings[0].tolist()
        except Exception as e:
            logger.error(f"Error extracting face encoding: {str(e)}")
            encoding = None
        
        # Add the face sample
        face_sample = face_profile_service.add_face_sample(
            db=db,
            face_profile_id=profile_id,
            image_path=image_path,
            encoding=encoding,
            confidence_score=confidence_score,
            source_video_id=source_video_id,
            timestamp=timestamp,
            frame_number=frame_number
        )
        
        # Prepare response
        return {
            "id": face_sample.id,
            "face_profile_id": face_sample.face_profile_id,
            "image_path": face_sample.image_path,
            "confidence_score": face_sample.confidence_score,
            "timestamp": face_sample.timestamp,
            "created_at": face_sample.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error uploading face sample: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading face sample: {str(e)}")

@router.get("/{profile_id}/samples", response_model=List[FaceSampleResponse])
async def get_face_samples(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all face samples for a profile.
    """
    try:
        logger.info(f"Getting face samples for profile: {profile_id}")
        
        # Check if the profile exists
        face_profile = face_profile_service.get_face_profile(db, profile_id)
        if not face_profile:
            raise HTTPException(status_code=404, detail=f"Face profile not found: {profile_id}")
        
        # Get all face samples
        face_samples = face_profile_service.get_face_samples(db, profile_id)
        
        # Prepare response
        return [
            {
                "id": sample.id,
                "face_profile_id": sample.face_profile_id,
                "image_path": sample.image_path,
                "confidence_score": sample.confidence_score,
                "timestamp": sample.timestamp,
                "created_at": sample.created_at
            }
            for sample in face_samples
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting face samples: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting face samples: {str(e)}")

@router.post("/{profile_id}/link-voice", response_model=Dict[str, Any])
async def link_face_to_voice_profile(
    profile_id: int,
    voice_profile_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Link a face profile to a voice profile.
    """
    try:
        logger.info(f"Linking face profile {profile_id} to voice profile {voice_profile_id}")
        
        # Link the profiles
        success = face_profile_service.link_face_to_voice_profile(db, profile_id, voice_profile_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to link profiles")
        
        return {
            "success": True,
            "message": f"Face profile {profile_id} linked to voice profile {voice_profile_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error linking profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error linking profiles: {str(e)}")

@router.post("/extract-from-video", response_model=Dict[str, Any])
async def extract_faces_from_video(
    video_id: int = Body(...),
    interval: float = Body(1.0),
    min_confidence: float = Body(0.6),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Extract faces from a video file.
    """
    try:
        logger.info(f"Extracting faces from video: {video_id}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
        
        # Check if the video file exists
        video_path = video.video_path
        if not video_path or not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
        
        # Create output directory
        output_dir = f"/app/data/face_profiles/extracted/{video_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract faces
        results = face_profile_service.extract_faces_from_video(
            video_path=video_path,
            output_dir=output_dir,
            interval=interval,
            min_confidence=min_confidence
        )
        
        if not results["success"]:
            raise HTTPException(status_code=500, detail=results.get("error", "Unknown error"))
        
        # Return results
        return {
            "success": True,
            "video_id": video_id,
            "faces_found": results["faces_found"],
            "frames_processed": results["frames_processed"],
            "output_dir": results["output_dir"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error extracting faces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting faces: {str(e)}")

@router.post("/extract-from-speaker-segments", response_model=Dict[str, Any])
async def extract_faces_from_speaker_segments(
    video_id: int = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Extract faces from video segments where specific speakers are talking.
    """
    try:
        logger.info(f"Extracting faces from speaker segments in video: {video_id}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
        
        # Check if the video file exists
        video_path = video.video_path
        if not video_path or not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
        
        # Check if transcription with speaker diarization exists
        if not video.transcription_results:
            raise HTTPException(status_code=404, detail="Transcription results not found")
        
        # Parse transcription results
        try:
            transcription = json.loads(video.transcription_results)
            segments = transcription.get("segments", [])
            
            # Check if segments have speaker information
            has_speakers = False
            for segment in segments:
                if segment.get("speaker") or segment.get("speaker_id") or segment.get("speaker_name"):
                    has_speakers = True
                    break
            
            if not has_speakers:
                raise HTTPException(status_code=400, detail="No speaker information found in transcription")
            
        except Exception as e:
            logger.error(f"Error parsing transcription: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error parsing transcription: {str(e)}")
        
        # Create output directory
        output_dir = f"/app/data/face_profiles/speaker_faces/{video_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract faces from speaker segments
        results = face_profile_service.extract_faces_from_speaker_segments(
            db=db,
            video_path=video_path,
            speaker_segments=segments,
            output_dir=output_dir
        )
        
        if not results["success"]:
            raise HTTPException(status_code=500, detail=results.get("error", "Unknown error"))
        
        # Return results
        return {
            "success": True,
            "video_id": video_id,
            "total_faces": results["total_faces"],
            "segments_processed": results["segments_processed"],
            "output_dir": results["output_dir"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error extracting speaker faces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting speaker faces: {str(e)}")
