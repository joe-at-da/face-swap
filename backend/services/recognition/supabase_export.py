"""
Supabase export functionality for recognition results.

This module provides functions to export recognition results to a format
that can be consumed by the Supabase integration, including creating combined
audio-video files while maintaining separate streams internally.
"""

import os
import json
import shutil
import logging
from datetime import datetime
import subprocess

from typing import Dict, Any, Optional
from backend.core.config import settings
from backend.services.av_combiner import combine_audio_video
from backend.services.recognition.timeline_combiner import combine_recognition_and_transcription
from backend.db.session import SessionLocal
from backend.db.models import RecognitionProcess, ParliamentTranscription
from sqlalchemy.orm import Session

# Set up logging
logger = logging.getLogger(__name__)

def create_recognition_process(video_id: int, recognition_results: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create or update a RecognitionProcess record for the given video and recognition results.
    
    Args:
        video_id: ID of the video (CaptureSession.id)
        recognition_results: Recognition results dictionary
        metadata: Additional metadata (optional)
        
    Returns:
        Dict with status and process ID
    """
    logger.info(f"Creating/updating RecognitionProcess for video ID {video_id}")
    
    db = SessionLocal()
    try:
        # Check if a RecognitionProcess already exists for this video
        process = db.query(RecognitionProcess).filter(
            RecognitionProcess.video_id == video_id
        ).first()
        
        # Get the current time
        now = datetime.now()
        
        # Extract process metadata
        process_metadata = {}
        if metadata:
            process_metadata = metadata.copy()
        
        # If a process already exists, update it
        if process:
            logger.info(f"Updating existing RecognitionProcess for video ID {video_id}")
            process.status = "completed"
            process.end_time = now
            process.results = json.dumps(recognition_results) if isinstance(recognition_results, dict) else recognition_results
            process.process_metadata = json.dumps(process_metadata)
            process.updated_at = now
        else:
            # Create a new RecognitionProcess
            logger.info(f"Creating new RecognitionProcess for video ID {video_id}")
            process = RecognitionProcess(
                video_id=video_id,
                status="completed",
                start_time=now,
                end_time=now,
                results=json.dumps(recognition_results) if isinstance(recognition_results, dict) else recognition_results,
                process_metadata=json.dumps(process_metadata)
            )
            db.add(process)
        
        # Commit the changes
        db.commit()
        
        return {
            "success": True,
            "process_id": process.id,
            "video_id": video_id,
            "status": process.status
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating/updating RecognitionProcess: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "video_id": video_id
        }
    finally:
        db.close()

def export_recognition_results(
    video_id: int,
    recognition_results: Dict[str, Any],
    video_path: str,
    audio_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_session: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Export recognition results for Supabase integration.
    
    This function:
    1. Creates a combined audio-video file for Supabase
    2. Exports recognition results to a JSON file
    3. Updates the metadata with export information
    
    Args:
        video_id: ID of the video
        recognition_results: Recognition results dictionary
        video_path: Path to the video file
        audio_path: Path to the audio file (optional)
        metadata: Additional metadata (optional)
        
    Returns:
        Dict with export status and paths
    """
    logger.info(f"Exporting recognition results for video ID {video_id} to Supabase format")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return {
            "success": False,
            "error": f"Video file not found: {video_path}",
            "export_path": None,
            "combined_av_path": None
        }
    
    # Create export directory if it doesn't exist
    export_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "exports", "supabase")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate export filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"recognition_export_{video_id}_{timestamp}.json"
    export_path = os.path.join(export_dir, export_filename)
    
    combined_av_filename = f"combined_av_{video_id}_{timestamp}.mp4"
    combined_av_path = os.path.join(export_dir, combined_av_filename)
    
    # Create combined audio-video file for Supabase
    # This maintains separate streams internally while providing a combined file for Supabase
    try:
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Creating combined audio-video file using separate audio: {audio_path}")
            combine_result = combine_audio_video(video_path, audio_path, combined_av_path)
        else:
            # Try to find the audio file using common patterns
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            data_dir = os.environ.get("DATA_DIR", "/app/data")
            audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
            
            # Try common naming patterns for audio files
            potential_audio_files = [
                os.path.join(audio_extracts_dir, f"{video_name}.audio.mp3"),
                os.path.join(audio_extracts_dir, f"{video_name}.mp3"),
                os.path.join(audio_extracts_dir, f"capture_{video_name}.audio.mp3"),
                os.path.join(audio_extracts_dir, f"capture_{video_name}.mp3"),
                os.path.join(audio_extracts_dir, f"{video_name}_audio.mp3"),
                os.path.join(audio_extracts_dir, f"{video_name}.audio.m4a"),
                os.path.join(audio_extracts_dir, f"{video_name}.m4a"),
                os.path.join(audio_extracts_dir, f"{video_name}_audio.m4a"),
                os.path.join(audio_extracts_dir, f"{video_name}.audio.aac"),
                os.path.join(audio_extracts_dir, f"{video_name}.aac"),
                os.path.join(audio_extracts_dir, f"{video_name}_audio.aac"),
            ]
            
            found_audio = None
            for audio_file in potential_audio_files:
                if os.path.exists(audio_file):
                    logger.info(f"Found audio file: {audio_file}")
                    found_audio = audio_file
                    break
            
            if found_audio:
                logger.info(f"Creating combined audio-video file using discovered audio: {found_audio}")
                combine_result = combine_audio_video(video_path, found_audio, combined_av_path)
            else:
                logger.warning(f"No audio file found for video: {video_path}, copying video only")
                # Copy video file as combined AV file if no audio is found
                shutil.copy(video_path, combined_av_path)
                combine_result = {
                    "success": True,
                    "combined_path": combined_av_path,
                    "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
                }
    except Exception as e:
        logger.error(f"Error creating combined audio-video file: {str(e)}")
        # Continue with export even if combining fails
        shutil.copy(video_path, combined_av_path)
        combine_result = {
            "success": True,
            "combined_path": combined_av_path,
            "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
        }
    
    # Prepare export data
    export_data = {
        "video_id": video_id,
        "export_timestamp": datetime.now().isoformat(),
        "recognition_results": recognition_results,
        "metadata": metadata or {}
    }
    
    # Add combined AV file path to metadata
    if os.path.exists(combined_av_path):
        export_data["metadata"]["combined_av_path"] = combined_av_path
        export_data["metadata"]["combined_av_url"] = f"/api/v1/media/file?path={os.path.basename(combined_av_path)}"
    
    # Create or update RecognitionProcess record
    process_result = create_recognition_process(
        video_id=video_id,
        recognition_results=recognition_results,
        metadata=export_data["metadata"]
    )
    
    if not process_result["success"]:
        logger.warning(f"Failed to create/update RecognitionProcess: {process_result.get('error')}")
        # Continue with export even if RecognitionProcess creation fails
    
    # Get transcription data if available and db_session is provided
    transcription_data = None
    if db_session:
        transcription = db_session.query(ParliamentTranscription).filter(
            ParliamentTranscription.capture_session_id == video_id,
            ParliamentTranscription.status == "completed"
        ).order_by(ParliamentTranscription.created_at.desc()).first()
        
        if transcription and transcription.output_file and os.path.exists(transcription.output_file):
            try:
                with open(transcription.output_file, 'r') as f:
                    transcription_data = json.load(f)
                logger.info(f"Loaded transcription data from {transcription.output_file}")
            except Exception as e:
                logger.error(f"Error loading transcription file: {str(e)}")
    
    # Add transcription data to recognition results if available
    if transcription_data:
        recognition_results["transcription"] = transcription_data
        
        # Create combined timeline and speaker-attributed transcripts
        try:
            combined_data = combine_recognition_and_transcription(
                recognition_results=recognition_results,
                transcription_data=transcription_data
            )
            
            # Add combined data to recognition results
            recognition_results["combined_timeline"] = combined_data["combined_timeline"]
            recognition_results["speaker_attributed_transcripts"] = combined_data["speaker_attributed_transcripts"]
            
            logger.info("Created combined timeline and speaker-attributed transcripts")
        except Exception as e:
            logger.error(f"Error creating combined timeline: {str(e)}")
            # Continue with export even if combining fails
    
    # Export recognition results to JSON
    try:
        with open(export_path, 'w') as f:
            json.dump(recognition_results, f, indent=2)
        logger.info(f"Exported recognition results to {export_path}")
    except Exception as e:
        logger.error(f"Error exporting recognition results: {str(e)}")
        return {
            "success": False,
            "error": f"Error exporting recognition results: {str(e)}",
            "export_path": None,
            "combined_av_path": combined_av_path if os.path.exists(combined_av_path) else None
        }
    
    return {
        "success": True,
        "export_path": export_path,
        "combined_av_path": combined_av_path if os.path.exists(combined_av_path) else None,
        "combined_av_url": f"/api/v1/media/file?path={os.path.basename(combined_av_path)}" if os.path.exists(combined_av_path) else None,
        "has_transcription": transcription_data is not None
    }
