"""
API endpoints for retrieving recognition status.
"""

import json
import logging
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.api.deps import get_current_user, get_db
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/recognition-status/{video_id}", response_model=Dict)
async def get_recognition_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the recognition status and progress for a specific video.
    """
    logger.info(f"Getting recognition status for video ID: {video_id}")
    
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found for video ID {video_id}"
        )
    
    # Check if recognition status exists
    recognition_status = getattr(video, 'recognition_status', None)
    recognition_progress = getattr(video, 'recognition_progress', None)
    
    # Parse progress if it exists
    progress_data = None
    if recognition_progress:
        try:
            progress_data = json.loads(recognition_progress)
        except Exception as e:
            logger.error(f"Error parsing recognition progress for video ID {video_id}: {str(e)}")
            progress_data = {"steps": []}
    
    # Check if we have results
    recognition_results = getattr(video, 'recognition_results', None)
    has_results = recognition_results is not None and recognition_results != ''
    
    # Format response to match frontend expectations
    status_data = {
        "status": recognition_status or "not_started",
        "progress": progress_data or {"steps": []},
        "video_id": video_id,
        "started_at": video.recognition_started_at.isoformat() if hasattr(video, 'recognition_started_at') and video.recognition_started_at else None,
        "completed_at": video.recognition_completed_at.isoformat() if hasattr(video, 'recognition_completed_at') and video.recognition_completed_at else None,
        "has_results": has_results
    }
    
    # Return the status in the format expected by the frontend
    return {
        "success": True,
        "status": status_data,
        "error": None
    }

@router.get("/detailed-status/{video_id}", response_model=Dict[str, Any])
@router.get("/recognition-status/detailed-status/{video_id}", response_model=Dict[str, Any])
async def get_detailed_recognition_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get detailed status information about the recognition process for a video.
    Includes logs, progress, file information, and estimated time remaining.
    """
    logger.info(f"Getting detailed recognition status for video ID: {video_id}")
    
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found for video ID {video_id}"
        )
    
    # Get the recognition status
    recognition_status = getattr(video, 'recognition_status', None) or "not_started"
    
    # Parse progress data
    progress_data = {}
    try:
        if hasattr(video, 'recognition_progress') and video.recognition_progress:
            progress_data = json.loads(video.recognition_progress)
    except Exception as e:
        logger.error(f"Error parsing recognition progress: {str(e)}")
    
    # Parse results data
    results_data = {}
    try:
        if hasattr(video, 'recognition_results') and video.recognition_results:
            results_data = json.loads(video.recognition_results)
    except Exception as e:
        logger.error(f"Error parsing recognition results: {str(e)}")
    
    # Check if files exist and add file status information
    file_status = {
        "video_path": {
            "path": video.video_path if hasattr(video, 'video_path') else None,
            "exists": os.path.exists(video.video_path) if hasattr(video, 'video_path') and video.video_path else False,
            "size": os.path.getsize(video.video_path) if hasattr(video, 'video_path') and video.video_path and os.path.exists(video.video_path) else 0
        },
        "audio_path": {
            "path": video.audio_path if hasattr(video, 'audio_path') else None,
            "exists": os.path.exists(video.audio_path) if hasattr(video, 'audio_path') and video.audio_path else False,
            "size": os.path.getsize(video.audio_path) if hasattr(video, 'audio_path') and video.audio_path and os.path.exists(video.audio_path) else 0
        }
    }
    
    # Calculate completion percentage if not present
    completion_percentage = 0
    if progress_data and "completion_percentage" in progress_data:
        completion_percentage = progress_data["completion_percentage"]
    elif recognition_status == "completed":
        completion_percentage = 100
    elif recognition_status == "processing":
        # Estimate based on steps
        steps = progress_data.get("steps", [])
        if steps:
            step_names = [step.get("name") for step in steps]
            if "completion" in step_names:
                completion_percentage = 100
            elif "speaker_identification" in step_names:
                completion_percentage = 75
            elif "transcription" in step_names:
                completion_percentage = 50
            elif "facial_recognition" in step_names:
                completion_percentage = 25
            else:
                completion_percentage = 10
    
    # Generate a user-friendly status message
    status_message = get_status_message(recognition_status, progress_data, completion_percentage)
    
    # Estimate time remaining
    time_remaining = estimate_time_remaining(recognition_status, progress_data, video)
    
    # Add more detailed information about the recognition process
    detailed_status = {
        "success": True,
        "video_id": video_id,
        "status": recognition_status,
        "progress": progress_data,
        "completion_percentage": completion_percentage,
        "file_status": file_status,
        "recognition_started_at": video.recognition_started_at.isoformat() if hasattr(video, 'recognition_started_at') and video.recognition_started_at else None,
        "recognition_completed_at": video.recognition_completed_at.isoformat() if hasattr(video, 'recognition_completed_at') and video.recognition_completed_at else None,
        "has_results": bool(results_data),
        "results_summary": get_results_summary(results_data),
        "current_time": datetime.now().isoformat(),
        "message": status_message,
        "estimated_time_remaining": time_remaining,
        "is_running": recognition_status == "processing",
        "last_activity": get_last_activity_time(progress_data)
    }
    
    return detailed_status

def get_status_message(status: str, progress_data: Dict, completion_percentage: int) -> str:
    """
    Generate a user-friendly status message based on the current status and progress.
    """
    if status == "completed":
        return "Recognition process has completed successfully."
    elif status == "failed":
        return "Recognition process failed. Check logs for more details."
    elif status == "processing":
        current_step = progress_data.get("current_step", "unknown")
        
        if current_step == "facial_recognition":
            return f"Processing facial recognition ({completion_percentage}% complete)."
        elif current_step == "transcription":
            return f"Processing audio transcription ({completion_percentage}% complete)."
        elif current_step == "speaker_identification":
            return f"Processing speaker identification ({completion_percentage}% complete)."
        else:
            return f"Recognition in progress ({completion_percentage}% complete)."
    else:
        return "Recognition has not started yet."

def get_results_summary(results_data: Dict) -> Dict:
    """
    Generate a summary of the recognition results.
    """
    summary = {
        "has_speaker_identification": False,
        "has_transcription": False,
        "total_speakers": 0,
        "transcript_length": 0
    }
    
    # Check if we have speaker identification results
    speaker_data = results_data.get("speaker_identification", {})
    if speaker_data and speaker_data.get("success", False):
        summary["has_speaker_identification"] = True
        speakers_results = speaker_data.get("results", {})
        summary["total_speakers"] = speakers_results.get("total_speakers", 0)
    
    # Check if we have transcription results
    transcription_data = results_data.get("transcription", {})
    if transcription_data and transcription_data.get("success", False):
        summary["has_transcription"] = True
        transcript = transcription_data.get("transcript", "")
        summary["transcript_length"] = len(transcript)
    
    return summary

def estimate_time_remaining(status: str, progress_data: Dict, video) -> Optional[int]:
    """
    Estimate the time remaining for the recognition process in seconds.
    Returns None if the process is not running or if we can't estimate.
    """
    if status != "processing":
        return None
    
    completion_percentage = progress_data.get("completion_percentage", 0)
    if completion_percentage <= 0:
        return None
    
    # Get the start time if available
    start_time = None
    if hasattr(video, 'recognition_started_at') and video.recognition_started_at:
        start_time = video.recognition_started_at
    else:
        # Try to get from steps
        steps = progress_data.get("steps", [])
        for step in steps:
            if step.get("status") == "started":
                try:
                    start_time = datetime.fromisoformat(step.get("timestamp"))
                    break
                except (ValueError, TypeError):
                    pass
    
    if not start_time:
        return None
    
    # Calculate elapsed time
    current_time = datetime.now()
    
    # Ensure both datetimes are timezone-naive or timezone-aware
    if isinstance(start_time, str):
        try:
            start_time = datetime.fromisoformat(start_time)
        except (ValueError, TypeError):
            return None
    
    # Check if one datetime is timezone-aware and the other is not
    if start_time.tzinfo is not None and current_time.tzinfo is None:
        # Convert current_time to timezone-aware with the same timezone
        current_time = current_time.replace(tzinfo=start_time.tzinfo)
    elif start_time.tzinfo is None and current_time.tzinfo is not None:
        # Convert start_time to timezone-aware with the same timezone
        start_time = start_time.replace(tzinfo=current_time.tzinfo)
    
    try:
        elapsed_seconds = (current_time - start_time).total_seconds()
    except TypeError:
        # If we still have timezone issues, make both naive
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        elapsed_seconds = (current_time - start_time).total_seconds()
    
    # Estimate total time based on elapsed time and completion percentage
    if completion_percentage > 0:
        total_estimated_seconds = (elapsed_seconds / completion_percentage) * 100
        remaining_seconds = total_estimated_seconds - elapsed_seconds
        return max(0, int(remaining_seconds))
    
    return None

def get_last_activity_time(progress_data: Dict) -> Optional[str]:
    """
    Get the timestamp of the last activity in the progress data.
    """
    steps = progress_data.get("steps", [])
    if not steps:
        return None
    
    # Sort steps by timestamp if available
    steps_with_time = []
    for step in steps:
        if "timestamp" in step:
            try:
                timestamp = datetime.fromisoformat(step["timestamp"])
                steps_with_time.append((timestamp, step))
            except (ValueError, TypeError):
                pass
    
    if not steps_with_time:
        return None
    
    # Sort by timestamp (newest first)
    steps_with_time.sort(reverse=True)
    
    # Return the timestamp of the most recent step
    return steps_with_time[0][0].isoformat()
