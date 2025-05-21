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
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

class TranscriptionProgressInfo(BaseModel):
    stage: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    estimated_completion: Optional[str] = None

class TranscriptionResponse(BaseModel):
    id: int
    status: str
    error: Optional[str] = None
    results_available: bool = False
    results_path: Optional[str] = None
    progress: Optional[TranscriptionProgressInfo] = None

def get_audio_path(capture_id: int, db: Session = None) -> Path:
    """Get the audio file path for a capture"""
    if db is None:
        db = next(get_db())
        
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
                # Try raw audio files
                for ext in ['.mp3', '.wav', '.m4a', '.aac']:
                    test_path = f"/app/data/temp/capture_{capture_id:04d}{ext}"
                    if os.path.exists(test_path):
                        audio_path = test_path
                        logger.info(f"Using raw audio file: {audio_path}")
                        break
    
    if not audio_path:
        raise HTTPException(status_code=404, detail=f"No audio file found for capture ID {capture_id}")
    
    return Path(audio_path)


def get_capture_status(capture_id: int, db: Session = Depends(get_db)):
    """Get the status of an audio transcription for a capture"""
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture with ID {capture_id} not found")
    
    # Check if transcription results are available
    results_available = False
    results_path = None
    
    if capture.transcription_status == "completed":
        # Check if the transcription file exists
        try:
            audio_path = get_audio_path(capture_id)
            transcript_path = audio_path.with_suffix('.audio_transcript.txt')
            
            if transcript_path.exists():
                results_available = True
                results_path = str(transcript_path)  # Convert Path to string
        except Exception as e:
            logger.error(f"Error checking transcript path: {e}")
    
    # Check for progress information
    progress_info = None
    if capture.transcription_status == "processing":
        try:
            audio_path = get_audio_path(capture_id)
            progress_file_path = audio_path.with_suffix('.audio_transcript.meta.json.progress.json')
            
            if progress_file_path.exists():
                try:
                    with open(str(progress_file_path), 'r') as f:  # Convert Path to string
                        progress_data = json.load(f)
                        
                    # Calculate estimated completion time
                    estimated_completion = None
                    if 'timestamp' in progress_data and 'progress' in progress_data and progress_data['progress'] > 0:
                        timestamp = datetime.fromisoformat(progress_data['timestamp'])
                        progress_percent = progress_data['progress']
                        
                        if progress_percent > 0:
                            # Estimate time remaining based on progress
                            elapsed_time = datetime.now() - timestamp
                            total_estimated_time = elapsed_time * (100 / progress_percent)
                            remaining_time = total_estimated_time - elapsed_time
                            
                            # Only provide estimate if it's reasonable (less than 30 minutes)
                            if remaining_time < timedelta(minutes=30):
                                completion_time = datetime.now() + remaining_time
                                estimated_completion = completion_time.isoformat()
                    
                    progress_info = TranscriptionProgressInfo(
                        stage=progress_data.get('stage'),
                        progress=progress_data.get('progress'),
                        message=progress_data.get('message'),
                        estimated_completion=estimated_completion
                    )
                except Exception as e:
                    logger.error(f"Error reading progress file: {e}")
        except Exception as e:
            logger.error(f"Error accessing progress file: {e}")
    
    # Use make_json_serializable to ensure all values are JSON serializable
    response_data = {
        "id": capture_id,
        "status": capture.transcription_status or "not_started",
        "error": capture.transcription_error,
        "results_available": results_available,
        "results_path": results_path,
        "progress": progress_info.dict() if progress_info else None
    }
    
    # Make all values JSON serializable
    response_data = make_json_serializable(response_data)
    
    return TranscriptionResponse(**response_data)

@router.post("/transcribe")
async def transcribe_audio(
    capture_id: int = Body(..., description="ID of the capture to transcribe"),
    model_size: str = Body("medium", description="Whisper model size to use"),
    save_output: bool = Body(True, description="Whether to save output files"),
    with_speaker_diarization: bool = Body(False, description="Whether to perform speaker diarization"),
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
        
        # Run the transcription in the background
        if background_tasks:
            logger.info(f"Adding transcription task to background tasks")
            background_tasks.add_task(run_audio_transcription, capture_id, model_size, with_speaker_diarization, db)
        else:
            # Run in the current process (not recommended for production)
            logger.info(f"Running transcription synchronously")
            run_audio_transcription(capture_id, model_size, with_speaker_diarization, db)
        
        return get_capture_status(capture_id, db)
        
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
    return get_capture_status(capture_id, db)

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
        elif capture.transcription_path and os.path.exists(str(capture.transcription_path)):
            # Results are stored in a file
            with open(str(capture.transcription_path), 'r') as f:
                results = json.load(f)
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Transcription results not found"}
            )
        
        # Ensure all values are JSON serializable
        results = make_json_serializable(results)
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Error getting transcription results: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

def run_audio_transcription(capture_id: int, model_size: str, with_speaker_diarization: bool, db: Session):
    """Run the audio transcription process for a capture"""
    try:
        # Get the capture
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture with ID {capture_id} not found")
            return
        
        # Update status to processing
        capture.transcription_status = "processing"
        capture.transcription_error = None
        db.commit()
        
        # Get paths
        audio_path = get_audio_path(capture_id)
        output_path = audio_path.with_suffix('.audio_transcript.meta.json')
        
        # Check if audio file exists
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            capture.transcription_status = "error"
            capture.transcription_error = f"Audio file not found: {audio_path}"
            db.commit()
            return
        
        # Get video path if available
        video_path = None
        if capture.video_path:
            video_path = Path(capture.video_path)
            if not video_path.exists():
                logger.warning(f"Video file not found: {video_path}")
                video_path = None
        
        # Run the transcription script
        cmd = [
            "python", "/app/scripts/audio_transcription.py",
            str(audio_path),
            "--output", str(output_path),
            "--model", model_size
        ]
        
        # Add speaker diarization if requested
        if with_speaker_diarization:
            cmd.append("--diarize")
            
            # Add video path if available for facial recognition integration
            if video_path:
                cmd.extend(["--video-path", str(video_path)])
            
            # Add a reasonable timeout based on audio duration
            # Get audio duration if available
            timeout = 1800  # Default 30 minutes
            try:
                if hasattr(capture, 'duration') and capture.duration:
                    # Set timeout to 10x the audio duration, with a minimum of 5 minutes
                    # and maximum of 2 hours
                    audio_duration = float(capture.duration)
                    timeout = max(300, min(7200, int(audio_duration * 10)))
                    logger.info(f"Setting timeout to {timeout}s based on audio duration of {audio_duration}s")
            except Exception as e:
                logger.warning(f"Error calculating timeout from duration: {e}")
                
            cmd.extend(["--timeout", str(timeout)])
        
        # Run the command
        logger.info(f"Running transcription command: {' '.join(cmd)}")
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
            with open(str(output_path), 'r') as f:  # Convert Path to string
                transcription_data = json.load(f)
                
            # Store a summary in the database (full text and first few segments)
            summary = {
                "text": transcription_data.get("text", ""),
                "language": transcription_data.get("language", ""),
                "segments": transcription_data.get("segments", [])[:5],  # First 5 segments
                "total_segments": len(transcription_data.get("segments", [])),
                "audio_file": str(audio_path),  # Ensure Path is converted to string
                "model": model_size,
                "with_speaker_diarization": with_speaker_diarization
            }
            
            # If speaker diarization was performed, store the status
            if with_speaker_diarization:
                capture.speaker_diarization_status = "completed"
                capture.speaker_diarization_completed_at = datetime.now()
                
                # Store speaker information if available
                if "speakers" in transcription_data:
                    summary["speakers"] = transcription_data.get("speakers", [])
                    
                # Store combined results if available
                if "combined_results" in transcription_data:
                    summary["combined_results"] = transcription_data.get("combined_results", {})
            
            # Update the capture record
            capture.transcription_status = "completed"
            capture.transcription_path = str(output_path)
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
