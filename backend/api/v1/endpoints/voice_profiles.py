"""
API endpoints for voice profile management.
"""

import os
import logging
import json
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

from backend.api.deps import get_db, get_current_user, get_current_user_with_roles
from backend.db.models.user import UserRole
from backend.db import models
from backend.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

class VoiceProfileCreate(BaseModel):
    name: str
    role: Optional[str] = None
    party: Optional[str] = None

class VoiceProfileResponse(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    party: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sample_count: int
    confidence_score: Optional[float] = None

class VoiceSampleResponse(BaseModel):
    id: str
    profile_id: str
    filename: str
    duration: Optional[float] = None
    created_at: datetime

# Voice profile directory
VOICE_PROFILES_DIR = Path("/app/data/voice_profiles")
VOICE_SAMPLES_DIR = VOICE_PROFILES_DIR / "samples"

# Ensure directories exist
VOICE_PROFILES_DIR.mkdir(exist_ok=True, parents=True)
VOICE_SAMPLES_DIR.mkdir(exist_ok=True, parents=True)

# Voice profiles database file
VOICE_PROFILES_DB = VOICE_PROFILES_DIR / "profiles.json"

def get_voice_profiles():
    """Get all voice profiles from the database file"""
    if not VOICE_PROFILES_DB.exists():
        # Create empty profiles database
        with open(VOICE_PROFILES_DB, 'w') as f:
            json.dump({"profiles": []}, f)
        return {"profiles": []}
    
    try:
        with open(VOICE_PROFILES_DB, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading voice profiles database: {e}")
        return {"profiles": []}

def save_voice_profiles(data):
    """Save voice profiles to the database file"""
    try:
        with open(VOICE_PROFILES_DB, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving voice profiles database: {e}")
        return False

@router.get("/", response_model=List[VoiceProfileResponse])
async def list_voice_profiles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all voice profiles.
    """
    try:
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        
        # Add sample count for each profile
        for profile in profiles:
            profile_dir = VOICE_SAMPLES_DIR / profile["id"]
            sample_count = len(list(profile_dir.glob("*.mp3"))) if profile_dir.exists() else 0
            profile["sample_count"] = sample_count
            
            # Set default confidence score if not present
            if "confidence_score" not in profile:
                profile["confidence_score"] = 0.0
        
        # Return the profiles array directly
        return profiles
    except Exception as e:
        logger.error(f"Error listing voice profiles: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing voice profiles: {str(e)}")

@router.post("/", response_model=VoiceProfileResponse)
async def create_voice_profile(
    profile: VoiceProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Create a new voice profile.
    """
    try:
        # Generate a unique ID
        import uuid
        profile_id = str(uuid.uuid4())
        
        # Get existing profiles
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        
        # Check if profile with same name already exists
        if any(p["name"] == profile.name for p in profiles):
            raise HTTPException(status_code=400, detail=f"Voice profile with name '{profile.name}' already exists")
        
        # Create new profile
        now = datetime.now()
        new_profile = {
            "id": profile_id,
            "name": profile.name,
            "role": profile.role,
            "party": profile.party,
            "created_at": now,
            "updated_at": now,
            "sample_count": 0,
            "confidence_score": 0.0
        }
        
        # Add to profiles list
        profiles.append(new_profile)
        data["profiles"] = profiles
        
        # Save to database file
        if not save_voice_profiles(data):
            raise HTTPException(status_code=500, detail="Failed to save voice profile")
        
        # Create directory for samples
        sample_dir = VOICE_SAMPLES_DIR / profile_id
        sample_dir.mkdir(exist_ok=True, parents=True)
        
        return new_profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating voice profile: {str(e)}")

@router.get("/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific voice profile.
    """
    try:
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        
        # Find profile by ID
        profile = next((p for p in profiles if p["id"] == profile_id), None)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile with ID {profile_id} not found")
        
        # Add sample count
        profile_dir = VOICE_SAMPLES_DIR / profile_id
        sample_count = len(list(profile_dir.glob("*.mp3"))) if profile_dir.exists() else 0
        profile["sample_count"] = sample_count
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting voice profile: {str(e)}")

@router.delete("/{profile_id}")
async def delete_voice_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Delete a voice profile.
    """
    try:
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        
        # Find profile by ID
        profile = next((p for p in profiles if p["id"] == profile_id), None)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile with ID {profile_id} not found")
        
        # Remove from profiles list
        data["profiles"] = [p for p in profiles if p["id"] != profile_id]
        
        # Save to database file
        if not save_voice_profiles(data):
            raise HTTPException(status_code=500, detail="Failed to delete voice profile")
        
        # Delete sample directory
        sample_dir = VOICE_SAMPLES_DIR / profile_id
        if sample_dir.exists():
            shutil.rmtree(sample_dir)
        
        return {"success": True, "message": f"Voice profile '{profile['name']}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting voice profile: {str(e)}")

@router.post("/{profile_id}/samples", response_model=VoiceSampleResponse)
async def upload_voice_sample(
    profile_id: str,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Upload a voice sample for a profile.
    """
    try:
        # Check if profile exists
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        profile = next((p for p in profiles if p["id"] == profile_id), None)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile with ID {profile_id} not found")
        
        # Validate file type
        if not audio_file.filename.lower().endswith(('.mp3', '.wav', '.m4a')):
            raise HTTPException(status_code=400, detail="Only MP3, WAV, and M4A files are supported")
        
        # Generate a unique filename
        import uuid
        sample_id = str(uuid.uuid4())
        file_extension = os.path.splitext(audio_file.filename)[1].lower()
        filename = f"{sample_id}{file_extension}"
        
        # Save file
        sample_dir = VOICE_SAMPLES_DIR / profile_id
        sample_dir.mkdir(exist_ok=True, parents=True)
        file_path = sample_dir / filename
        
        with open(file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Convert to MP3 if not already
        if not file_path.suffix.lower() == '.mp3':
            import subprocess
            mp3_path = file_path.with_suffix('.mp3')
            
            try:
                subprocess.run([
                    "ffmpeg",
                    "-i", str(file_path),
                    "-q:a", "0",
                    "-map", "a",
                    str(mp3_path)
                ], check=True)
                
                # Remove original file
                file_path.unlink()
                file_path = mp3_path
                filename = file_path.name
            except Exception as e:
                logger.error(f"Error converting audio file to MP3: {e}")
                # Keep original file if conversion fails
        
        # Get audio duration
        duration = None
        try:
            import subprocess
            import json
            result = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(file_path)
            ], capture_output=True, text=True, check=True)
            
            probe_data = json.loads(result.stdout)
            duration = float(probe_data["format"]["duration"])
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
        
        # Update profile's updated_at timestamp
        for p in profiles:
            if p["id"] == profile_id:
                p["updated_at"] = datetime.now()
                break
        
        # Save to database file
        save_voice_profiles(data)
        
        return {
            "id": sample_id,
            "profile_id": profile_id,
            "filename": filename,
            "duration": duration,
            "created_at": datetime.now()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading voice sample: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading voice sample: {str(e)}")

@router.get("/{profile_id}/samples", response_model=List[VoiceSampleResponse])
async def list_voice_samples(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all voice samples for a profile.
    """
    try:
        # Check if profile exists
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        profile = next((p for p in profiles if p["id"] == profile_id), None)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile with ID {profile_id} not found")
        
        # Get samples
        sample_dir = VOICE_SAMPLES_DIR / profile_id
        if not sample_dir.exists():
            return []
        
        samples = []
        for file_path in sample_dir.glob("*.mp3"):
            sample_id = file_path.stem
            filename = file_path.name
            
            # Get audio duration
            duration = None
            try:
                import subprocess
                import json
                result = subprocess.run([
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(file_path)
                ], capture_output=True, text=True, check=True)
                
                probe_data = json.loads(result.stdout)
                duration = float(probe_data["format"]["duration"])
            except Exception as e:
                logger.warning(f"Could not determine audio duration: {e}")
            
            # Get file creation time
            created_at = datetime.fromtimestamp(file_path.stat().st_ctime)
            
            samples.append({
                "id": sample_id,
                "profile_id": profile_id,
                "filename": filename,
                "duration": duration,
                "created_at": created_at
            })
        
        # Sort by creation time (newest first)
        samples.sort(key=lambda x: x["created_at"], reverse=True)
        
        return samples
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing voice samples: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing voice samples: {str(e)}")

@router.delete("/{profile_id}/samples/{sample_id}")
async def delete_voice_sample(
    profile_id: str,
    sample_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_with_roles([UserRole.ADMIN]))
):
    """
    Delete a voice sample.
    """
    try:
        # Check if profile exists
        data = get_voice_profiles()
        profiles = data.get("profiles", [])
        profile = next((p for p in profiles if p["id"] == profile_id), None)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile with ID {profile_id} not found")
        
        # Find sample file
        sample_dir = VOICE_SAMPLES_DIR / profile_id
        sample_file = None
        for file_path in sample_dir.glob(f"{sample_id}.*"):
            sample_file = file_path
            break
        
        if not sample_file:
            raise HTTPException(status_code=404, detail=f"Voice sample with ID {sample_id} not found")
        
        # Delete file
        sample_file.unlink()
        
        # Update profile's updated_at timestamp
        for p in profiles:
            if p["id"] == profile_id:
                p["updated_at"] = datetime.now()
                break
        
        # Save to database file
        save_voice_profiles(data)
        
        return {"success": True, "message": "Voice sample deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting voice sample: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting voice sample: {str(e)}")
