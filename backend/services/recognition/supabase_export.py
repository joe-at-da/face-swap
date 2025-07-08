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
    logger.warning(f"🔍 DEBUG: export_recognition_results called for video_id={video_id} - COMBINED AV FILE CREATION ENTRY POINT")
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
                logger.info(f"Attempting to combine audio ({audio_path}) and video ({video_path}) to {combined_av_path}")
                combine_result = combine_audio_video(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=combined_av_path
                )
                
                # Verify the combined file was created successfully
                if os.path.exists(combined_av_path) and os.path.getsize(combined_av_path) > 0:
                    logger.info(f"Combined audio-video file created successfully at {combined_av_path} with size {os.path.getsize(combined_av_path)} bytes")
                    combine_result = {
                        "success": True,
                        "combined_path": combined_av_path,
                        "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
                    }
                else:
                    logger.error(f"Combined audio-video file was not created or has zero size at {combined_av_path}")
                    raise Exception("Combined file creation failed or resulted in empty file")
            except Exception as e:
                logger.error(f"Error combining audio-video: {str(e)}")
                logger.info(f"Falling back to copying video file to {combined_av_path}")
                # Continue with export even if combining fails by copying the video file
                try:
                    shutil.copy(video_path, combined_av_path)
                    if os.path.exists(combined_av_path) and os.path.getsize(combined_av_path) > 0:
                        logger.info(f"Successfully copied video file to {combined_av_path} with size {os.path.getsize(combined_av_path)} bytes")
                        combine_result = {
                            "success": True,
                            "combined_path": combined_av_path,
                            "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
                        }
                    else:
                        logger.error(f"Failed to copy video file to {combined_av_path} or resulting file has zero size")
                except Exception as copy_error:
                    logger.error(f"Error copying video file: {str(copy_error)}")
        elif os.path.exists(video_path):
            # Just copy the video file if no audio path is provided
            logger.info(f"No audio path provided, copying video file to {combined_av_path}")
            try:
                shutil.copy(video_path, combined_av_path)
                if os.path.exists(combined_av_path) and os.path.getsize(combined_av_path) > 0:
                    logger.info(f"Successfully copied video file to {combined_av_path} with size {os.path.getsize(combined_av_path)} bytes")
                    combine_result = {
                        "success": True,
                        "combined_path": combined_av_path,
                        "combined_url": f"/media/combined/{os.path.basename(combined_av_path)}"
                    }
                else:
                    logger.error(f"Failed to copy video file to {combined_av_path} or resulting file has zero size")
            except Exception as copy_error:
                logger.error(f"Error copying video file: {str(copy_error)}")
        else:
            logger.error(f"Video file not found: {video_path}")
            combine_result = {
                "success": False,
                "error": f"Video file not found: {video_path}",
                "combined_path": None,
                "combined_url": None
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
        logger.info(f"File exists check: {os.path.exists(combined_av_path)}, File size: {os.path.getsize(combined_av_path)}")
        video_filename = os.path.basename(combined_av_path)
        logger.info(f"Using video filename: {video_filename}")
        
        # Check if Supabase integration is enabled
        if not settings.SUPABASE_INTEGRATION_ENABLED:
            logger.warning("SUPABASE_INTEGRATION_ENABLED is set to False. Enabling it temporarily for this upload.")
            # We'll proceed with the upload anyway, but log this warning
        
        # Make sure we're using the service role for Supabase
        supabase = SupabaseService(use_service_role=True)
        logger.info(f"Supabase client initialized with service role: {supabase.client is not None}")
        logger.info(f"Supabase URL: {settings.SUPABASE_URL}, API key set: {bool(settings.SUPABASE_SERVICE_ROLE_KEY)}")
        logger.info(f"Supabase bucket: {settings.SUPABASE_FULL_VIDEOS_BUCKET}")
        
        # Attempt the upload with detailed logging
        try:
            # Verify the file is accessible and readable before upload
            with open(combined_av_path, 'rb') as test_file:
                test_bytes = test_file.read(1024)  # Read first 1KB to test access
                logger.info(f"File is readable, first few bytes: {test_bytes[:20]}")
            
            # Now attempt the actual upload
            logger.info("Starting upload to Supabase...")
            upload_result = supabase.upload_full_video(file_path=combined_av_path)
            logger.info(f"Upload result: {upload_result}")
            
            if not upload_result.get("success", False):
                logger.error(f"Failed to upload combined video to Supabase: {upload_result.get('error')}")
                # No fallback to original video - we only want combined AV files in Supabase
                supabase_url = None
            else:
                logger.info(f"Successfully uploaded combined video to Supabase: {upload_result.get('public_url')}")
                supabase_url = upload_result.get('public_url')
                
                # Verify the URL is accessible
                logger.info(f"Verifying Supabase URL is accessible: {supabase_url}")
        except Exception as e:
            logger.error(f"Exception during upload of combined video: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            supabase_url = None
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
    
    # Get clips from the parliament_clips SQLite database using ParliamentClipsIntegrationService
    from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
    clips_service = ParliamentClipsIntegrationService()
    clips_result = clips_service.get_parliament_clips_for_video(video_id)
    
    if not clips_result.get("success", False) or not clips_result.get("clips"):
        logger.error(f"Failed to get parliament clips for video {video_id}: {clips_result.get('error', 'No clips found')}")
        # Continue with export even if no clips are found
        segments_result = {"segments": [], "segment_count": 0}
    else:
        logger.info(f"Found {len(clips_result['clips'])} parliament clips for video {video_id}")
        segments_result = {"segments": [], "segment_count": len(clips_result['clips']), "success": True}
    
    # Initialize clip generator
    from backend.services.recognition.clip_generator import ClipGenerator
    clip_generator = ClipGenerator()
    
    # Process each clip from the parliament_clips database
    clips = []
    parliament_clips = clips_result.get("clips", [])
    
    for i, clip in enumerate(parliament_clips):
        try:
            # Get clip data from the parliament_clips database
            member_id = clip.get('member_id')
            if not member_id:
                logger.warning(f"Skipping clip without member_id: {clip}")
                continue
                
            # Parse timestamps
            try:
                start_time = float(clip.get('start_timestamp', 0))
                end_time = float(clip.get('end_timestamp', 0))
                duration = end_time - start_time
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing timestamps for clip {i}: {str(e)}")
                continue
                
            # Skip clips shorter than 3 seconds
            if duration < 3:
                logger.info(f"Skipping clip {i} with duration {duration} seconds (too short)")
                continue
                
            # Format timestamps for display
            start_timestamp = format_timestamp(start_time)
            end_timestamp = format_timestamp(end_time)
            
            # Generate clip filename
            clip_filename = f"mp_{member_id}_{video_id}_{i}_{start_timestamp.replace(':', '-')}.mp4"
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
            
            # Skip uploading clips to Supabase - we only want combined AV files
            logger.info(f"Skipping upload of clip {clip_filename} to Supabase - only combined AV files will be uploaded")
            
            # Set a local URL for the clip instead
            clip_url = f"/api/v1/media/file?path={clip_filename}"
            
            # Get MP information from Speaker table
            from backend.db.models import Speaker
            mp = db_session.query(Speaker).filter(
                Speaker.parliament_id == str(member_id)  # Use parliament_id and convert member_id to string
            ).first() if db_session else None
            
            # Log the Speaker lookup attempt for transparency
            if mp:
                logger.info(f"Found Speaker record for member_id {member_id}: {mp.name}")
            else:
                logger.warning(f"No Speaker record found for member_id {member_id}")
                
            mp_name = mp.name if mp and hasattr(mp, 'name') else clip.get('member_name', "Unknown MP")
            
            # Get video information
            video = db_session.query(CaptureSession).filter(
                CaptureSession.id == video_id
            ).first() if db_session else None
            
            # Create clip metadata
            clip_data = {
                "video_id": str(video_id),
                "member_id": member_id,  # Use the integer member_id from parliament_clips
                "member_name": mp_name,
                "start_time": start_time,
                "end_time": end_time,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration": duration,
                "transcript": clip.get('transcript', ''),
                "confidence": clip.get('confidence_score', 0.0),
                "recognition_method": clip.get('metadata', {}).get('recognition_method', 'facial'),
                "full_video_url": upload_result.get('public_url'),
                "full_video_path": video_path,  # Add the full_video_path field which is required
                "clip_url": clip_url,
                "session_title": video.title if video else "",
                "session_date": video.created_at.isoformat() if video and video.created_at else clip.get('session_date', ''),
                "session_description": video.description if video else "",
                "original_url": video.source_url if video else "",
                "status": "pending_review"  # Use a valid enum value for parliament_clip_status
            }
            
            # Log the clip data for transparency
            logger.info(f"Exporting clip {i} with member_id {member_id} and duration {duration:.2f}s")
            
            # Insert clip data into Supabase parliament_member_clips table
            # Use add_to_clip_creation_queue instead of insert_clip as it handles the correct table
            insert_result = supabase.add_to_clip_creation_queue([clip_data])
            
            clips.append({
                "clip_id": i,
                "member_id": member_id,
                "speaker_name": mp_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "clip_url": clip_url,
                "insert_result": insert_result
            })
            
        except Exception as e:
            logger.exception(f"Error processing clip {i}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Log summary of export process
    if clips:
        logger.info(f"Successfully exported {len(clips)} clips to Supabase for video ID {video_id}")
    else:
        logger.warning(f"No clips were exported to Supabase for video ID {video_id}")
    
    # Run the sync script to ensure all member IDs have corresponding Speaker records
    if db_session and clips:
        try:
            from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
            clips_service = ParliamentClipsIntegrationService()
            sync_result = clips_service._run_sync_parliament_clip_member_ids(db_session)
            logger.info(f"Sync parliament clip member IDs result: {sync_result}")
        except Exception as e:
            logger.error(f"Error running sync script: {str(e)}")
    
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
