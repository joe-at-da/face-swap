"""
Parliament TV Debug Endpoint

This module provides a debug endpoint for processing specific segments of Parliament TV videos
without requiring re-downloading of the full audio/video files.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, BackgroundTasks, Body, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.db.session import get_db
from backend.api.deps import get_api_key
from backend.services.parliament_tv_sequential import ParliamentTVSequentialProcessor
from backend.db.models.capture import CaptureSession
from backend.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/process-segment", dependencies=[Depends(get_api_key)])
async def process_specific_segment(
    background_tasks: BackgroundTasks,
    session_id: int = Body(..., description="ID of the existing capture session with downloaded files"),
    start_time: int = Body(..., description="Start time of the segment in seconds"),
    end_time: int = Body(..., description="End time of the segment in seconds"),
    segment_label: str = Body(None, description="Optional label for the segment (e.g., 'MP John Smith speech')"),
    db: Session = Depends(get_db)
):
    """
    Process a specific segment from already-downloaded Parliament TV files.
    
    This endpoint allows debugging and reprocessing of specific segments without
    re-downloading the entire audio/video files. Useful for testing recognition
    of specific speakers or content.
    
    Args:
        session_id: ID of the existing capture session with downloaded files
        start_time: Start time of the segment in seconds
        end_time: End time of the segment in seconds
        segment_label: Optional label for the segment (e.g., 'MP John Smith speech')
        
    Returns:
        Status information about the initiated process
    """
    # Initialize the sequential processor
    sequential_processor = ParliamentTVSequentialProcessor()
    
    # Validate input
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be greater than start time"
        )
    
    # Get the capture session
    capture = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {session_id} not found"
        )
    
    # Check if files exist
    video_path = capture.file_path
    audio_path = capture.capture_metadata.get("audio_path")
    
    # If audio_path is not in metadata, try to find it using naming convention
    if not audio_path:
        # Look for audio file with pattern audio_{session_id}_*.mp3
        media_dir = settings.MEDIA_STORAGE_PATH
        possible_audio_files = [f for f in os.listdir(media_dir) if f.startswith(f"audio_{session_id}_") and f.endswith(".mp3")]
        
        if possible_audio_files:
            audio_path = os.path.join(media_dir, possible_audio_files[0])
            logger.info(f"Found audio file using naming convention: {audio_path}")
    
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found for session {session_id}"
        )
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found for session {session_id}. Checked metadata and naming convention."
        )
    
    # Create a background task for segment processing
    def process_segment_task():
        try:
            # Get metadata from capture session
            original_url = capture.capture_metadata.get("original_url", "")
            video_url = capture.capture_metadata.get("video_url", "")
            audio_url = capture.capture_metadata.get("audio_url", "")
            
            # Generate segment ID
            segment_id = f"debug_{session_id}_{start_time}_{end_time}"
            if segment_label:
                segment_id += f"_{segment_label.replace(' ', '_')}"
            
            # Get media directory from settings
            media_dir = settings.MEDIA_STORAGE_PATH
            temp_dir = os.path.join(media_dir, f"debug_segments_{session_id}")
            os.makedirs(temp_dir, exist_ok=True)
            
            logger.info(f"Extracting segment {start_time}-{end_time}s from session {session_id}")
            
            # Extract the segment from the local files
            segment_result = sequential_processor.extract_segment(
                video_path=video_path,
                audio_path=audio_path,
                start_time=start_time,
                end_time=end_time,
                output_dir=temp_dir,
                segment_id=segment_id
            )
            
            if not segment_result.get("video_success") or not segment_result.get("audio_success"):
                logger.error(f"Failed to extract segment {start_time}-{end_time}s")
                return {
                    "success": False,
                    "error": "Segment extraction failed"
                }
            
            # Get the segment file paths
            segment_video_path = segment_result.get("segment_video_path")
            segment_audio_path = segment_result.get("segment_audio_path")
            
            # Create a title for the segment
            segment_title = segment_label if segment_label else f"{capture.title} (Segment {start_time}-{end_time}s)"
            segment_description = f"Debug segment from {start_time} to {end_time} seconds of session {session_id}"
            
            # Process the segment
            logger.info(f"Processing segment {start_time}-{end_time}s")
            process_result = sequential_processor.process_segment(
                original_url=original_url,
                video_url=video_url,
                audio_url=audio_url,
                start_time=start_time,
                end_time=end_time,
                title=segment_title,
                description=segment_description,
                session_id=str(session_id),
                video_path=segment_video_path,
                audio_path=segment_audio_path
            )
            
            # Log the result
            if process_result.get("success", False):
                logger.info(f"Successfully processed segment {start_time}-{end_time}s")
            else:
                logger.error(f"Failed to process segment {start_time}-{end_time}s: {process_result.get('error')}")
            
            return process_result
            
        except Exception as e:
            logger.error(f"Error processing segment: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Error processing segment: {str(e)}"
            }
    
    # Start the background task
    background_tasks.add_task(process_segment_task)
    
    # Return immediate response
    return {
        "success": True,
        "message": f"Started processing segment {start_time}-{end_time}s from session {session_id}",
        "session_id": session_id,
        "segment_info": {
            "start_time": start_time,
            "end_time": end_time,
            "label": segment_label
        }
    }
