"""
API endpoints for MP profile management.
"""

import os
import logging
import json
import shutil
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.services.recognition import FacialRecognitionService
from backend.services.utils import make_json_serializable
from backend.core.security import has_permission

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
facial_recognition_service = FacialRecognitionService()

# Constants
MP_PHOTOS_DIR = Path("/app/data/mp_photos")
MP_ENCODINGS_FILE = Path("/app/data/mp_encodings.json")

# Ensure directories exist
MP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/mp-profiles", response_model=Dict)
async def get_mp_profiles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all MP profiles.
    """
    try:
        # Get all speakers from the database
        speakers = db.query(models.Speaker).all()
        
        # Check if each speaker has face encoding
        profiles = []
        for speaker in speakers:
            has_face_encoding = speaker.face_encoding is not None
            
            profiles.append({
                "id": speaker.id,
                "name": speaker.name,
                "parliament_id": speaker.parliament_id,
                "party": speaker.party,
                "constituency": speaker.constituency,
                "photo_url": speaker.photo_url,
                "has_face_encoding": has_face_encoding,
                "is_active": speaker.is_active,
                "created_at": speaker.created_at
            })
        
        return {
            "success": True,
            "profiles": make_json_serializable(profiles)
        }
    except Exception as e:
        logger.exception(f"Error getting MP profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting MP profiles: {str(e)}")

@router.get("/mp-profiles/{profile_id}", response_model=Dict)
async def get_mp_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific MP profile.
    """
    try:
        # Get the speaker from the database
        speaker = db.query(models.Speaker).filter(models.Speaker.id == profile_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail=f"MP profile with ID {profile_id} not found")
        
        has_face_encoding = speaker.face_encoding is not None
        
        profile = {
            "id": speaker.id,
            "name": speaker.name,
            "parliament_id": speaker.parliament_id,
            "party": speaker.party,
            "constituency": speaker.constituency,
            "photo_url": speaker.photo_url,
            "has_face_encoding": has_face_encoding,
            "is_active": speaker.is_active,
            "created_at": speaker.created_at
        }
        
        return {
            "success": True,
            "profile": make_json_serializable(profile)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting MP profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting MP profile: {str(e)}")

@router.post("/mp-profiles", response_model=Dict)
async def create_mp_profile(
    name: str = Body(..., description="MP name"),
    parliament_id: Optional[str] = Body(None, description="Parliament ID"),
    party: Optional[str] = Body(None, description="Political party"),
    constituency: Optional[str] = Body(None, description="Constituency"),
    photo_url: Optional[str] = Body(None, description="Photo URL"),
    is_active: bool = Body(True, description="Whether the MP is active"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new MP profile.
    """
    try:
        # Create a new speaker
        speaker = models.Speaker(
            name=name,
            parliament_id=parliament_id,
            party=party,
            constituency=constituency,
            photo_url=photo_url,
            is_active=is_active,
            created_at=datetime.now()
        )
        
        db.add(speaker)
        db.commit()
        db.refresh(speaker)
        
        # If photo URL is provided, try to generate face encoding
        if photo_url:
            try:
                # Download the photo and generate face encoding
                result = facial_recognition_service._generate_face_encoding_from_url(photo_url)
                
                if result.get("success"):
                    # Update the speaker with face encoding
                    speaker.face_encoding = result.get("encoding")
                    db.commit()
                    
                    # Update the MP encodings file
                    facial_recognition_service.update_mp_database()
                    
                    logger.info(f"Generated face encoding for MP {speaker.name}")
                else:
                    logger.warning(f"Failed to generate face encoding for MP {speaker.name}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error generating face encoding: {str(e)}")
        
        return {
            "success": True,
            "message": f"MP profile for {name} created successfully",
            "profile_id": speaker.id
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Error creating MP profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating MP profile: {str(e)}")

@router.put("/mp-profiles/{profile_id}", response_model=Dict)
async def update_mp_profile(
    profile_id: int,
    name: str = Body(..., description="MP name"),
    parliament_id: Optional[str] = Body(None, description="Parliament ID"),
    party: Optional[str] = Body(None, description="Political party"),
    constituency: Optional[str] = Body(None, description="Constituency"),
    photo_url: Optional[str] = Body(None, description="Photo URL"),
    is_active: bool = Body(True, description="Whether the MP is active"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update an existing MP profile.
    """
    try:
        # Get the speaker from the database
        speaker = db.query(models.Speaker).filter(models.Speaker.id == profile_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail=f"MP profile with ID {profile_id} not found")
        
        # Update the speaker
        speaker.name = name
        speaker.parliament_id = parliament_id
        speaker.party = party
        speaker.constituency = constituency
        speaker.is_active = is_active
        speaker.updated_at = datetime.now()
        
        # Check if photo URL has changed
        photo_url_changed = photo_url != speaker.photo_url
        if photo_url_changed and photo_url:
            speaker.photo_url = photo_url
            
            # Try to generate face encoding for the new photo
            try:
                # Download the photo and generate face encoding
                result = facial_recognition_service._generate_face_encoding_from_url(photo_url)
                
                if result.get("success"):
                    # Update the speaker with face encoding
                    speaker.face_encoding = result.get("encoding")
                    
                    # Update the MP encodings file
                    facial_recognition_service.update_mp_database()
                    
                    logger.info(f"Generated face encoding for MP {speaker.name}")
                else:
                    logger.warning(f"Failed to generate face encoding for MP {speaker.name}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error generating face encoding: {str(e)}")
        elif photo_url_changed and not photo_url:
            speaker.photo_url = None
        
        db.commit()
        
        return {
            "success": True,
            "message": f"MP profile for {name} updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Error updating MP profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating MP profile: {str(e)}")

@router.delete("/mp-profiles/{profile_id}", response_model=Dict)
async def delete_mp_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete an MP profile.
    """
    try:
        # Get the speaker from the database
        speaker = db.query(models.Speaker).filter(models.Speaker.id == profile_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail=f"MP profile with ID {profile_id} not found")
        
        # Delete the speaker
        db.delete(speaker)
        db.commit()
        
        # Update the MP encodings file
        facial_recognition_service.update_mp_database()
        
        return {
            "success": True,
            "message": f"MP profile deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Error deleting MP profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting MP profile: {str(e)}")

@router.post("/upload-mp-photo", response_model=Dict)
async def upload_mp_photo(
    photo: UploadFile = File(...),
    mp_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Upload a photo for an MP and generate face encoding.
    """
    try:
        # Create the MP photos directory if it doesn't exist
        MP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(photo.filename)[1]
        filename = f"mp_photo_{timestamp}{file_extension}"
        file_path = MP_PHOTOS_DIR / filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        # Generate a URL for the photo
        photo_url = f"/app/data/mp_photos/{filename}"
        
        # If mp_id is provided, update the speaker's photo URL
        if mp_id:
            speaker_id = int(mp_id)
            speaker = db.query(models.Speaker).filter(models.Speaker.id == speaker_id).first()
            
            if speaker:
                speaker.photo_url = photo_url
                db.commit()
        
        # Generate face encoding
        try:
            # Generate face encoding
            result = facial_recognition_service._generate_face_encoding(file_path)
            
            if result.get("success") and mp_id:
                # Update the speaker with face encoding
                speaker = db.query(models.Speaker).filter(models.Speaker.id == int(mp_id)).first()
                if speaker:
                    speaker.face_encoding = result.get("encoding")
                    db.commit()
                
                # Update the MP encodings file
                facial_recognition_service.update_mp_database()
                
                logger.info(f"Generated face encoding for MP photo {filename}")
            elif not result.get("success"):
                logger.warning(f"Failed to generate face encoding for MP photo {filename}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error generating face encoding: {str(e)}")
        
        return {
            "success": True,
            "message": "Photo uploaded successfully",
            "photo_url": photo_url,
            "filename": filename
        }
    except Exception as e:
        logger.exception(f"Error uploading MP photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading MP photo: {str(e)}")

@router.post("/mp-profiles/{profile_id}/regenerate-encoding", response_model=Dict)
async def regenerate_face_encoding(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Regenerate face encoding for an MP profile.
    """
    try:
        # Get the speaker from the database
        speaker = db.query(models.Speaker).filter(models.Speaker.id == profile_id).first()
        
        if not speaker:
            raise HTTPException(status_code=404, detail=f"MP profile with ID {profile_id} not found")
        
        if not speaker.photo_url:
            raise HTTPException(status_code=400, detail="MP profile does not have a photo URL")
        
        # Generate face encoding
        try:
            # Download the photo and generate face encoding
            result = facial_recognition_service._generate_face_encoding_from_url(speaker.photo_url)
            
            if result.get("success"):
                # Update the speaker with face encoding
                speaker.face_encoding = result.get("encoding")
                db.commit()
                
                # Update the MP encodings file
                facial_recognition_service.update_mp_database()
                
                logger.info(f"Regenerated face encoding for MP {speaker.name}")
                
                return {
                    "success": True,
                    "message": f"Face encoding regenerated successfully for {speaker.name}"
                }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Failed to regenerate face encoding for MP {speaker.name}: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Failed to regenerate face encoding: {error_msg}")
        except Exception as e:
            logger.error(f"Error regenerating face encoding: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error regenerating face encoding: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error regenerating face encoding: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error regenerating face encoding: {str(e)}")

@router.post("/update-mp-database", response_model=Dict)
async def update_mp_database(
    current_user: models.User = Depends(get_current_user)
):
    """
    Update the MP database with the latest face encodings.
    """
    try:
        # Update the MP database
        result = facial_recognition_service.update_mp_database()
        
        if result.get("success"):
            return {
                "success": True,
                "message": "MP database updated successfully"
            }
        else:
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(status_code=500, detail=f"Failed to update MP database: {error_msg}")
    except Exception as e:
        logger.exception(f"Error updating MP database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating MP database: {str(e)}")
