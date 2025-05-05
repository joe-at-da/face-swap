from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import sys
import subprocess
from typing import Dict, Any

from backend.db.session import get_db
from backend.api import deps
from backend.db.models import Capture

router = APIRouter()

@router.post("/{capture_id}", response_model=Dict[str, Any])
def extract_audio_for_capture(
    capture_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Extract audio for a specific capture ID.
    This endpoint runs the extract_audio_for_capture.py script for a specific capture ID.
    """
    try:
        # Path to the extract_audio_for_capture.py script
        script_path = os.path.join("/app", "scripts", "extract_audio_for_capture.py")
        
        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail=f"Script not found at {script_path}")
        
        # Run the script in a non-blocking way
        cmd = [sys.executable, script_path, str(capture_id)]
        subprocess.Popen(cmd)
        
        return {
            "success": True,
            "message": f"Audio extraction started for capture ID: {capture_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting audio: {str(e)}")

@router.get("/{capture_id}/status", response_model=Dict[str, Any])
def check_audio_status(
    capture_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
):
    """
    Check if audio extraction is complete for a specific capture ID.
    """
    try:
        # Get the capture from the database
        capture = db.query(Capture).filter(Capture.id == capture_id).first()
        
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture with ID {capture_id} not found")
        
        # Check if the capture has an audio_file_path
        has_audio = False
        audio_path = None
        
        # Check in the standard attribute
        if hasattr(capture, 'audio_file_path') and capture.audio_file_path:
            has_audio = True
            audio_path = capture.audio_file_path
        # Check in metadata if it exists
        elif hasattr(capture, 'metadata') and capture.metadata and isinstance(capture.metadata, dict):
            if 'audio_file_path' in capture.metadata and capture.metadata['audio_file_path']:
                has_audio = True
                audio_path = capture.metadata['audio_file_path']
        
        # Check if the audio file actually exists
        audio_exists = False
        if has_audio and audio_path:
            audio_exists = os.path.exists(audio_path)
        
        # If no audio path is found, check common locations
        if not has_audio or not audio_exists:
            # Format should be: capture_XXXX.audio.mp3 where XXXX is the zero-padded capture ID
            padded_capture_id = str(capture_id).zfill(4)
            docker_audio_extracts_dir = "/app/data/temp/audio_extracts"
            
            alt_patterns = [
                # Primary pattern we want: capture_XXXX.audio.mp3
                os.path.join(docker_audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3"),
                # Alternative patterns that might exist
                os.path.join(docker_audio_extracts_dir, f"capture_{capture_id}.audio.mp3"),
                os.path.join(docker_audio_extracts_dir, f"capture_{capture_id}_audio.mp3")
            ]
            
            for pattern in alt_patterns:
                if os.path.exists(pattern):
                    has_audio = True
                    audio_exists = True
                    audio_path = pattern
                    break
        
        return {
            "success": True,
            "has_audio": has_audio,
            "audio_exists": audio_exists,
            "audio_path": audio_path,
            "capture_status": capture.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking audio status: {str(e)}")
