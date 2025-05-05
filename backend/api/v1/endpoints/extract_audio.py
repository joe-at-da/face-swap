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
