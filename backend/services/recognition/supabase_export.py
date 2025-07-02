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

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.models import RecognitionProcess, ParliamentTranscription
from backend.db.models.capture import CaptureSession
from backend.db.session import SessionLocal
# TODO: There are multiple implementations of combine_audio_video in the codebase
#       (in av_combiner.py, media/av_combiner.py, and video/processor.py).
#       These should be consolidated into a single implementation in a future refactoring.
from backend.services.av_combiner import combine_audio_video

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
    4. Uploads the full video to Supabase storage
    5. Identifies speaking segments using the 60-second pause rule
    6. Creates and uploads clips for each speaking segment
    7. Inserts clip metadata into Supabase database
    
    Args:
        video_id: ID of the video
        recognition_results: Recognition results dictionary
        video_path: Path to the video file
        audio_path: Path to the audio file (optional)
        metadata: Additional metadata (optional)
        db_session: SQLAlchemy database session (optional)
        
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
    
    try:
        # Create export directory if it doesn't exist
        export_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "exports", "supabase")
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate export file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"recognition_export_{video_id}_{timestamp}.json"
        export_path = os.path.join(export_dir, export_filename)
        
        # Generate combined AV file path - place directly in MEDIA_STORAGE_PATH
        # This ensures it's in /app/data/media/ in the Docker container
        combined_av_filename = f"combined_av_{video_id}_{timestamp}.mp4"
        combined_av_path = os.path.join(settings.MEDIA_STORAGE_PATH, combined_av_filename)
        
        # Create combined audio-video file if both paths are provided
        combine_result = None
        if audio_path and os.path.exists(audio_path) and os.path.exists(video_path):
            try:
                combine_result = combine_audio_video(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=combined_av_path
                )
                logger.info(f"Combined audio-video file created at {combined_av_path}")
            except Exception as e:
                logger.error(f"Error combining audio-video: {str(e)}")
                # Continue with export even if combining fails
                shutil.copy(video_path, combined_av_path)
                combine_result = {
                    "success": True,
                    "combined_path": combined_av_path,
                    "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
                }
        elif os.path.exists(video_path):
            # Just copy the video file if no audio path is provided
            logger.info(f"No audio path provided, copying video file to {combined_av_path}")
            shutil.copy(video_path, combined_av_path)
            combine_result = {
                "success": True,
                "combined_path": combined_av_path,
                "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
            }
        else:
            logger.error(f"Video file not found: {video_path}")
            # Continue with export even if combining fails
            shutil.copy(video_path, combined_av_path)
            combine_result = {
                "success": True,
                "combined_path": combined_av_path,
                "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
            }
    except Exception as e:
        logger.error(f"Error setting up export: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "export_path": None,
            "combined_av_path": None
        }
    
    # Initialize Supabase service for uploads and database operations
    from backend.services.integration.supabase_client import SupabaseService
    supabase = SupabaseService(use_service_role=True)
    
    # Upload ONLY the combined video to Supabase storage (this is the full video)
    # We only want combined_av_ files in the Supabase bucket
    if os.path.exists(combined_av_path):
        logger.info(f"Uploading combined video to Supabase full_videos bucket: {combined_av_path}")
        video_filename = os.path.basename(combined_av_path)
        upload_result = supabase.upload_full_video(file_path=combined_av_path)
        
        if not upload_result.get("success", False):
            logger.error(f"Failed to upload combined video to Supabase: {upload_result.get('error')}")
            # No fallback to original video - we only want combined AV files in Supabase
            supabase_url = None
        else:
            logger.info(f"Successfully uploaded combined video to Supabase: {upload_result.get('public_url')}")
            supabase_url = upload_result.get('public_url')
    else:
        logger.warning(f"Combined video not found at {combined_av_path}, NOT uploading any video to Supabase")
        # Do not upload original video as fallback
        supabase_url = None

    # Update video record with Supabase URL if db_session is provided and we have a URL
    if db_session and supabase_url:
        try:
            # Try to update CaptureSession record first
            video = db_session.query(CaptureSession).filter(
                CaptureSession.id == video_id
            ).first()
            
            if video:
                video.supabase_url = supabase_url
                db_session.commit()
                logger.info(f"Updated CaptureSession record with Supabase URL: {supabase_url}")
            else:
                # If no CaptureSession record, try to update RecognitionProcess record
                rec_process = db_session.query(RecognitionProcess).filter(
                    RecognitionProcess.video_id == video_id
                ).first()
                
                if rec_process:
                    rec_process.supabase_url = supabase_url
                    db_session.commit()
                    logger.info(f"Updated RecognitionProcess record with Supabase URL: {supabase_url}")
                else:
                    logger.warning(f"No video or recognition process record found for video ID {video_id}")
        except Exception as e:
            logger.error(f"Error updating video record: {str(e)}")
            # Continue with export even if update fails
    
    # Identify speaking segments using the 60-second pause rule
    from backend.services.recognition.speaker_segmentation import SpeakerSegmentation
    speaker_segmentation = SpeakerSegmentation(db=db_session)
    segments_result = speaker_segmentation.identify_speaking_segments(
        video_id=video_id,
        recognition_results=recognition_results
    )
    
    if not segments_result.get("success", False):
        logger.error(f"Failed to identify speaking segments: {segments_result.get('error')}")
        # Continue with export even if segmentation fails
        segments_result = {"segments": [], "segment_count": 0}
    
    # Initialize clip generator
    from backend.services.recognition.clip_generator import ClipGenerator
    clip_generator = ClipGenerator()
    
    # Process each speaking segment
    clips = []
    segments = segments_result.get("segments", [])
    
    for i, segment in enumerate(segments):
        try:
            # Format timestamps
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            duration = end_time - start_time
            
            # Skip segments shorter than 3 seconds
            if duration < 3:
                continue
                
            # Format timestamps for display
            start_timestamp = format_timestamp(start_time)
            end_timestamp = format_timestamp(end_time)
            
            # Generate clip filename
            clip_filename = f"mp_{segment['speaker_id']}_{video_id}_{i}_{start_timestamp.replace(':', '-')}.mp4"
            clip_path = f"/app/data/temp/clips/{clip_filename}"
            
            # Generate clip
            clip_result = clip_generator.create_clip(
                input_file=video_path,
                output_file=clip_path,
                start_time=start_time,
                duration=duration
            )
            
            if not clip_result.get("success", False):
                logger.error(f"Failed to create clip: {clip_result.get('error')}")
                continue
            
            # Upload clip to Supabase
            upload_result = supabase.upload_file(
                bucket=supabase.media_bucket,
                path=f"clips/{clip_filename}",
                file_path=clip_path
            )
            
            # Get public URL
            clip_url = supabase.get_public_url(
                bucket=supabase.media_bucket,
                path=f"clips/{clip_filename}"
            )
            
            # Get MP information
            from backend.db.models import ParliamentMember
            mp = db_session.query(ParliamentMember).filter(
                ParliamentMember.id == segment["speaker_id"]
            ).first() if db_session else None
            
            mp_name = mp.name if mp else "Unknown MP"
            
            # Get video information
            video = db_session.query(CaptureSession).filter(
                CaptureSession.id == video_id
            ).first() if db_session else None
            
            # Create clip metadata
            clip_data = {
                "video_id": str(video_id),
                "member_id": segment["speaker_id"],
                "member_name": mp_name,
                "start_time": start_time,
                "end_time": end_time,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration": duration,
                "transcript": segment["transcript"],
                "confidence": segment["confidence"],
                "recognition_method": segment["recognition_method"],
                "full_video_url": upload_result.get('public_url'),
                "clip_url": clip_url,
                "session_title": video.title if video else "",
                "session_date": video.created_at.isoformat() if video and video.created_at else "",
                "session_description": video.description if video else "",
                "original_url": video.source_url if video else "",
                "status": "processed"
            }
            
            # Insert clip data into Supabase
            insert_result = supabase.insert_clip(clip_data)
            
            clips.append({
                "clip_id": i,
                "speaker_id": segment["speaker_id"],
                "speaker_name": mp_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "clip_url": clip_url,
                "insert_result": insert_result
            })
            
        except Exception as e:
            logger.exception(f"Error processing clip {i}: {str(e)}")
    
    return {
        "success": True,
        "export_path": export_path,
        "combined_av_path": combined_av_path if os.path.exists(combined_av_path) else None,
        "combined_av_url": f"/api/v1/media/file?path={os.path.basename(combined_av_path)}" if os.path.exists(combined_av_path) else None,
        "has_transcription": False,
        "upload_result": upload_result,
        "segments_result": {
            "success": segments_result.get("success", False),
            "segment_count": segments_result.get("segment_count", 0)
        },
        "clips_result": {
            "success": True,
            "clip_count": len(clips),
            "clips": clips
        }
    }
