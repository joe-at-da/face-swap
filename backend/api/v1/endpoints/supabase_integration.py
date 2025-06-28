"""
Supabase integration API endpoints for exporting data to Supabase.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Security, HTTPException, Body, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_api_key
from backend.db.models import CaptureSession, ParliamentTranscription, RecognitionProcess
from backend.services.recognition.supabase_export import export_recognition_results
import json
import os
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/status/{video_id}", dependencies=[Security(get_api_key)])
async def get_supabase_status(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Check the status of Supabase integration for a specific video.
    
    This endpoint:
    1. Checks if the video exists in the database
    2. Checks if recognition results exist for the video
    3. Checks if transcription data exists for the video
    4. Checks if the combined export exists
    
    Args:
        video_id: ID of the video to check
        
    Returns:
        Dict with integration status
    """
    logger.info(f"Checking Supabase integration status for video ID: {video_id}")
    
    # Check if video exists
    video = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found"
        )
    
    # Check recognition results
    recognition_process = db.query(RecognitionProcess).filter(
        RecognitionProcess.video_id == video_id
    ).order_by(RecognitionProcess.updated_at.desc()).first()
    
    has_recognition = recognition_process is not None and recognition_process.results is not None
    
    # Check transcription data
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    has_transcription = transcription is not None and transcription.output_file is not None
    
    # Check for exported files
    export_dir = Path(settings.MEDIA_STORAGE_PATH) / "exports" / "supabase"
    export_files = list(export_dir.glob(f"recognition_export_{video_id}_*.json"))
    combined_av_files = list(export_dir.glob(f"combined_av_{video_id}_*.mp4"))
    
    has_export = len(export_files) > 0
    has_combined_av = len(combined_av_files) > 0
    
    # Get latest export file if available
    latest_export = None
    latest_export_path = None
    if export_files:
        latest_export_path = str(sorted(export_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
        try:
            with open(latest_export_path, 'r') as f:
                latest_export = json.load(f)
        except Exception as e:
            logger.error(f"Error loading export file: {str(e)}")
    
    # Check if combined timeline and speaker-attributed transcripts exist
    has_combined_timeline = False
    has_speaker_attributed_transcripts = False
    if latest_export:
        has_combined_timeline = "combined_timeline" in latest_export
        has_speaker_attributed_transcripts = "speaker_attributed_transcripts" in latest_export
    
    return {
        "video_id": video_id,
        "video_title": video.title if video else None,
        "has_recognition": has_recognition,
        "has_transcription": has_transcription,
        "has_export": has_export,
        "has_combined_av": has_combined_av,
        "has_combined_timeline": has_combined_timeline,
        "has_speaker_attributed_transcripts": has_speaker_attributed_transcripts,
        "latest_export_path": latest_export_path,
        "latest_export_time": datetime.fromtimestamp(Path(latest_export_path).stat().st_mtime).isoformat() if latest_export_path else None,
        "integration_complete": has_recognition and has_transcription and has_export and has_combined_av and has_combined_timeline and has_speaker_attributed_transcripts
    }

@router.post("/export-to-supabase/{video_id}", dependencies=[Security(get_api_key)])
async def export_to_supabase(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Export recognition and transcription data to Supabase format for a specific video.
    
    This endpoint:
    1. Retrieves recognition results from the database
    2. Retrieves transcription data from the database
    3. Combines them into a unified format
    4. Exports the combined data to Supabase
    
    Args:
        video_id: ID of the video to export
        
    Returns:
        Dict with export status and paths
    """
    logger.info(f"Exporting data to Supabase for video ID: {video_id}")
    
    # Check if video exists
    video = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found"
        )
    
    # Get recognition results
    recognition_process = db.query(RecognitionProcess).filter(
        RecognitionProcess.video_id == video_id
    ).order_by(RecognitionProcess.updated_at.desc()).first()
    
    if not recognition_process or not recognition_process.results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recognition results for video ID {video_id} not found"
        )
    
    # Parse recognition results
    try:
        if isinstance(recognition_process.results, str):
            recognition_results = json.loads(recognition_process.results)
        else:
            recognition_results = recognition_process.results
    except Exception as e:
        logger.error(f"Error parsing recognition results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing recognition results: {str(e)}"
        )
    
    # Get transcription data
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    # Get video path
    video_path = video.output_file if video.output_file else None
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file for ID {video_id} not found"
        )
    
    # Get metadata
    metadata = {}
    if video.metadata:
        if isinstance(video.metadata, dict):
            metadata = video.metadata
        elif isinstance(video.metadata, str):
            try:
                metadata = json.loads(video.metadata)
            except:
                pass
    
    # Export to Supabase format
    try:
        export_result = export_recognition_results(
            video_id=video_id,
            recognition_results=recognition_results,
            video_path=video_path,
            metadata=metadata,
            db_session=db  # Pass the database session for transcription lookup
        )
        
        return {
            "success": True,
            "message": "Data exported to Supabase successfully",
            "export_details": export_result,
            "has_transcription": transcription is not None
        }
    except Exception as e:
        logger.error(f"Error exporting data to Supabase: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting data to Supabase: {str(e)}"
        )
