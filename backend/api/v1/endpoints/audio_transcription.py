"""
API endpoints for audio transcription.
"""

import os
import logging
import json
import subprocess
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    capture_id: int = Body(..., description="ID of the capture to transcribe"),
    model_size: str = Body("medium", description="Whisper model size to use"),
    save_output: bool = Body(True, description="Whether to save output files"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process audio transcription for a capture.
    """
    try:
        logger.info(f"Processing audio transcription for capture ID: {capture_id}")
        
        # Get the capture record
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture with ID {capture_id} not found")
        
        # Check if we have an audio file
        audio_path = None
        
        # First try the audio path in the database
        if hasattr(capture, 'audio_path') and capture.audio_path and os.path.exists(capture.audio_path):
            audio_path = capture.audio_path
            logger.info(f"Using audio path from database: {audio_path}")
        
        # If not found, try the standard audio extracts location
        if not audio_path:
            audio_path = f"/app/data/temp/audio_extracts/capture_{capture_id:04d}.audio.mp3"
            if os.path.exists(audio_path):
                logger.info(f"Using audio path from standard location: {audio_path}")
            else:
                # Try alternative format
                audio_path = f"/app/data/temp/audio_extracts/capture_{capture_id}.audio.mp3"
                if os.path.exists(audio_path):
                    logger.info(f"Using audio path from alternative location: {audio_path}")
                else:
                    audio_path = None
        
        # If still not found, check if there's a raw audio file
        if not audio_path:
            for ext in ['.mp3', '.wav', '.m4a', '.aac']:
                test_path = f"/app/data/temp/capture_{capture_id:04d}{ext}"
                if os.path.exists(test_path):
                    audio_path = test_path
                    logger.info(f"Using raw audio file: {audio_path}")
                    break
                
                # Try alternative format
                test_path = f"/app/data/temp/capture_{capture_id}{ext}"
                if os.path.exists(test_path):
                    audio_path = test_path
                    logger.info(f"Using raw audio file (alternative format): {audio_path}")
                    break
        
        if not audio_path:
            # Update the capture record with an error
            capture.transcription_status = "error"
            capture.transcription_error = f"No audio file found for capture ID {capture_id}. The video may not contain an audio track."
            db.commit()
            
            return {
                "success": False,
                "error": "No audio file found",
                "message": "The video file doesn't contain an audio track that can be transcribed."
            }
        
        # Check if the audio file exists and has content
        try:
            if os.path.getsize(audio_path) == 0:
                capture.transcription_status = "error"
                capture.transcription_error = f"Audio file exists but is empty: {audio_path}"
                db.commit()
                
                return {
                    "success": False,
                    "error": "Empty audio file",
                    "message": "The audio file exists but contains no data."
                }
        except Exception as e:
            logger.error(f"Error checking audio file: {str(e)}")
            capture.transcription_status = "error"
            capture.transcription_error = f"Error checking audio file: {str(e)}"
            db.commit()
            
            return {
                "success": False,
                "error": "Error checking audio file",
                "message": f"Error checking audio file: {str(e)}"
            }
        
        # Update the capture record
        capture.transcription_status = "processing"
        db.commit()
        
        # Run the transcription in a background task
        background_tasks.add_task(
            run_audio_transcription,
            capture_id,
            audio_path,
            model_size,
            save_output
        )
        
        return {
            "success": True,
            "message": f"Audio transcription started for capture ID: {capture_id}",
            "status": "processing",
            "audio_path": audio_path
        }
        
    except Exception as e:
        logger.error(f"Error starting audio transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{capture_id}")
async def get_transcription_status(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the status of a transcription process for a specific capture.
    """
    logger.info(f"Getting transcription status for capture ID: {capture_id}")
    
    # Get the capture from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f"Capture not found for ID {capture_id}"}
        )
    
    # Get the transcription status
    try:
        status = {
            "capture_id": capture_id,
            "status": capture.transcription_status or "not_started",
            "completed_at": capture.transcription_completed_at.isoformat() if capture.transcription_completed_at else None,
            "has_results": bool(capture.transcription_results),
            "transcription_path": capture.transcription_path
        }
    except AttributeError as e:
        # Handle case where columns don't exist yet
        logger.warning(f"Transcription status columns not available: {str(e)}")
        status = {
            "capture_id": capture_id,
            "status": "not_started",
            "completed_at": None,
            "has_results": False,
            "transcription_path": None,
            "message": "Transcription tracking not fully set up in database"
        }
    
    return {"success": True, "status": status}

@router.get("/results/{capture_id}")
async def get_transcription_results(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the transcription results for a specific capture.
    """
    logger.info(f"Getting transcription results for capture ID: {capture_id}")
    
    # Get the capture from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f"Capture not found for ID {capture_id}"}
        )
    
    # Check if transcription is completed
    if not hasattr(capture, 'transcription_status') or capture.transcription_status != "completed":
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Transcription not completed yet"}
        )
    
    # Get the transcription results
    try:
        if capture.transcription_results:
            # Results are stored directly in the database
            results = json.loads(capture.transcription_results)
        elif capture.transcription_path and os.path.exists(capture.transcription_path):
            # Results are stored in a file
            with open(capture.transcription_path, 'r') as f:
                results = json.load(f)
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Transcription results not found"}
            )
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error getting transcription results: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

def run_audio_transcription(capture_id: int, audio_path: str, model_size: str = "medium", save_output: bool = True):
    """
    Run audio transcription as a background task.
    """
    db = next(get_db())
    try:
        # Get the capture record
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture with ID {capture_id} not found")
            return
        
        # Prepare the output path
        output_dir = Path("/app/data/transcriptions")
        output_dir.mkdir(exist_ok=True, parents=True)
        output_file = output_dir / f"capture_{capture_id:04d}_transcription.json"
        
        # Run the transcription script
        cmd = [
            "python",
            "/app/scripts/audio_transcription.py",
            audio_path,
            "--output", str(output_file),
            "--model", model_size
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Transcription failed: {stderr.decode()}")
            capture.transcription_status = "error"
            capture.transcription_error = stderr.decode()
            db.commit()
            return
        
        # Load the transcription results to store in the database
        try:
            with open(output_file, 'r') as f:
                transcription_data = json.load(f)
                
            # Store a summary in the database (full text and first few segments)
            summary = {
                "text": transcription_data.get("text", ""),
                "language": transcription_data.get("language", ""),
                "segments": transcription_data.get("segments", [])[:5],  # First 5 segments
                "total_segments": len(transcription_data.get("segments", [])),
                "audio_file": audio_path,
                "model": model_size
            }
            
            # Update the capture record
            capture.transcription_status = "completed"
            capture.transcription_path = str(output_file)
            capture.transcription_completed_at = datetime.now()
            capture.transcription_results = json.dumps(summary)
            db.commit()
            
            logger.info(f"Transcription completed for capture ID: {capture_id}")
        except Exception as e:
            logger.error(f"Error processing transcription results: {str(e)}")
            capture.transcription_status = "error"
            capture.transcription_error = str(e)
            db.commit()
        
    except Exception as e:
        logger.error(f"Error in audio transcription: {str(e)}")
        try:
            capture.transcription_status = "error"
            capture.transcription_error = str(e)
            db.commit()
        except:
            pass
    finally:
        db.close()
