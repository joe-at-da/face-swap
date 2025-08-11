"""
Supabase Automation API Endpoints

This module provides endpoints for automating the Parliament TV capture, recognition,
and Supabase export workflow in a single unified process, including saving individual
member clips with detailed metadata to the Supabase database.
"""

import logging
import os
import json
import time
import uuid
import glob
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from backend.services.utils import make_json_serializable
from fastapi import APIRouter, Depends, HTTPException, Security, status, BackgroundTasks, Body
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.api.deps import get_db, get_api_key
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.integration.supabase_upload import SupabaseUploader
from backend.services.integration.supabase_client import SupabaseService  # Keep for backward compatibility
from backend.services.parliament_tv import ParliamentTVCapture
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.recognition.simplified_export import normalize_and_export_clips
from sqlalchemy import desc
from backend.db.models import CaptureSession, RecognitionProcess, ParliamentTranscription
from backend.services.utils import make_json_serializable
from backend.api.v1.endpoints.parliament_tv_sequential_endpoint import process_parliament_tv_sequentially

logger = logging.getLogger(__name__)

router = APIRouter()
parliament_tv_service = ParliamentTVCapture()


@router.post("/process-parliament-tv", response_model=Dict[str, Any], dependencies=[Security(get_api_key)])
async def process_parliament_tv_to_supabase(
    background_tasks: BackgroundTasks,
    url: str = Body(None, description="Parliament TV URL to process (optional)"),
    title: str = Body(None, description="Title for the capture session (optional)"),
    description: str = Body(None, description="Description for the capture session (optional)"),
    duration: int = Body(None, description="Duration to capture in seconds (optional)"),
    debug: bool = Body(False, description="Enable debug/test mode with shorter durations for testing"),
    segment_info: Dict[str, Any] = Body(None, description="Information about the segment being processed"),
    db: Session = Depends(get_db)
):
    """
    Unified endpoint to process a Parliament TV URL through the entire pipeline:
    1. Extract stream URLs from Parliament TV
    2. Capture video
    3. Run combined recognition
    4. Export recognition results to Supabase
    5. Upload full video to Supabase storage
    
    This endpoint is secured with API key authentication and designed to be called
    from a cron job or other automated process.
    
    Args:
        url: Parliament TV URL to process
        title: Title for the capture session
        description: Description for the capture session
        duration: Duration to capture in seconds (default: 2 hours)
        debug: Enable debug/test mode with shorter durations for testing (default: False)
        
    Returns:
        Status information about the initiated process
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase integration is not enabled"
        )
    
    # Set DEBUG_MODE environment variable based on debug parameter
    if debug:
        os.environ["DEBUG_MODE"] = "true"
        logger.info("Debug mode enabled: Using shorter durations for testing")
    else:
        os.environ["DEBUG_MODE"] = "false"
        
    # Keep TEST_MODE separate from debug parameter
    # TEST_MODE should only be set explicitly, not via the debug parameter
    os.environ["TEST_MODE"] = "false"
    
    # Import the sequential processor
    from backend.services.parliament_tv_sequential import ParliamentTVSequentialProcessor
    sequential_processor = ParliamentTVSequentialProcessor()
    
    # Check if we need to use the sequential processor
    if url is None:
        # No URL provided, use sequential processor to scrape and process
        logger.info("No URL provided, redirecting to sequential processor for auto-detection")
        return await process_parliament_tv_sequentially(
            background_tasks=background_tasks,
            url=None,
            title=title or "Auto-detected Parliament TV",
            description=description or "Automatically detected from Parliament TV Commons",
            duration=duration,
            debug=debug,
            db=db
        )
    elif duration is None:
        # URL provided but no duration, use sequential processor without scraping
        logger.info(f"URL provided but no duration, using sequential processor for URL: {url}")
        return await process_parliament_tv_sequentially(
            background_tasks=background_tasks,
            url=url,
            title=title or "Parliament TV Sequential Processing",
            description=description or "Processed sequentially in 30-minute segments",
            duration=None,
            debug=debug,
            db=db
        )
    
    # If we get here, both URL and duration are provided, use the original logic
    logger.info(f"Starting unified Parliament TV processing for URL: {url} with duration: {duration}")
    
    # Step 1: Extract stream URLs from Parliament TV
    try:
        stream_info = parliament_tv_service.extract_stream_url(url)
        if "error" in stream_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract stream URL: {stream_info['error']}"
            )
        
        video_url = stream_info.get("video_url")
        audio_url = stream_info.get("audio_url")
        
        if not video_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract video stream URL"
            )
            
        if not audio_url:
            logger.warning("No audio URL extracted. Audio and video streams should be handled separately.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No audio URL extracted. Audio and video streams must be handled separately."
            )
            
        logger.info(f"Successfully extracted stream URLs: video={video_url}, audio={audio_url}")
    except Exception as e:
        logger.error(f"Error extracting stream URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting stream URL: {str(e)}"
        )
    
    # Create a background task for the rest of the process
    def process_parliament_tv_task():
        import json  # Import json module to fix UnboundLocalError
        import traceback  # Import traceback module for error logging
        try:
            # Step 2: Create capture session
            capture_metadata = {
                "video_url": video_url,
                "audio_url": audio_url,
                "original_url": url,
                "time_marker": stream_info.get("time_marker", {"seconds": 0})
            }
            
            # Check if this is a segment processing call and store segment info in metadata
            if segment_info and segment_info.get("is_segment") and segment_info.get("parent_session_id"):
                # This is a segment - store segment information in metadata for tracking
                parent_session_id = segment_info.get("parent_session_id")
                start_time = segment_info.get("start_time", 0)
                end_time = segment_info.get("end_time", 0)
                segment_number = (start_time // 1800) + 1  # 30-minute segments
                
                logger.info(f"Processing segment {segment_number} for session {parent_session_id}, creating new session with segment metadata")
                
                # Add segment information to metadata
                capture_metadata.update({
                    "is_segment": True,
                    "parent_session_id": parent_session_id,
                    "segment_number": segment_number,
                    "segment_start_time": start_time,
                    "segment_end_time": end_time
                })
                
                # Create capture session with segment metadata (normal integer ID)
                capture = CaptureSession(
                    title=f"{title} (Segment {segment_number})",
                    description=f"{description} - Segment {start_time}-{end_time}s",
                    status="draft",
                    capture_metadata=capture_metadata,
                    duration=duration
                )
            else:
                # This is a complete session - create normally
                capture = CaptureSession(
                    title=title,
                    description=description,
                    status="draft",
                    capture_metadata=capture_metadata,
                    duration=duration
                )
            
            db.add(capture)
            db.commit()
            db.refresh(capture)
            
            capture_id = capture.id
            logger.info(f"Created capture session with ID: {capture_id}")
            
            # Step 3: Start capture
            try:
                # Start synchronized capture for both audio and video
                capture_result = parliament_tv_service.start_synchronized_capture(
                    url={"video_url": video_url, "audio_url": audio_url},
                    capture_id=capture_id,
                    duration=duration
                )
                
                if not capture_result.get("success", False):
                    logger.error(f"Failed to start capture: {capture_result.get('error', 'Unknown error')}")
                    capture.status = "failed"
                    capture.error_message = capture_result.get("error", "Failed to start capture")
                    db.commit()
                    return
                
                logger.info(f"Started capture for session {capture_id}")
                
                # Wait for capture to complete
                # This is a blocking operation, but we're in a background task
                import time
                
                # Check status periodically
                max_wait_time = duration + 300  # Duration plus 5 minutes buffer
                start_time = time.time()
                completed = False
                
                while time.time() - start_time < max_wait_time:
                    # Refresh capture from database
                    db.refresh(capture)
                    
                    if capture.status == "completed":
                        completed = True
                        break
                    elif capture.status == "failed":
                        logger.error(f"Capture failed: {capture.error_message}")
                        return
                    
                    # Wait before checking again
                    time.sleep(30)
                
                if not completed:
                    logger.error(f"Capture timed out after {max_wait_time} seconds")
                    capture.status = "failed"
                    capture.error_message = "Capture timed out"
                    db.commit()
                    return
                
                logger.info(f"Capture completed for session {capture_id}")
                
                # Step 4: Run combined recognition
                recognition_service = MultimodalRecognitionService()
                recognition_result = recognition_service.start_combined_recognition(capture_id)
                
                if not recognition_result.get("success", False):
                    logger.error(f"Failed to start recognition: {recognition_result.get('error', 'Unknown error')}")
                    return
                
                logger.info(f"Started recognition for session {capture_id}")
                
                # Wait for recognition to complete
                max_wait_time = 3600  # 1 hour max for recognition
                start_time = time.time()
                recognition_completed = False
                
                while time.time() - start_time < max_wait_time:
                    try:
                        # Check recognition status directly from the database
                        db.refresh(capture)
                        status_value = capture.recognition_status
                        
                        logger.info(f"Recognition status: {status_value}")
                        
                        if status_value == "completed":
                            recognition_completed = True
                            break
                        elif status_value == "failed":
                            error_message = capture.error_message if hasattr(capture, 'error_message') else "Unknown error"
                            logger.error(f"Recognition failed: {error_message}")
                            return
                        elif status_value is None:
                            # Check if the recognition process has started
                            if not capture.recognition_started_at:
                                # If recognition hasn't started yet, try to start it
                                if time.time() - start_time > 300:  # Wait 5 minutes before retrying
                                    logger.info("Recognition hasn't started yet, retrying...")
                                    recognition_result = recognition_service.start_combined_recognition(capture_id)
                                    if not recognition_result.get("success", False):
                                        logger.error(f"Failed to start recognition: {recognition_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"Error checking recognition status: {str(e)}")
                        # Continue the loop and try again after waiting
                    
                    # Wait before checking again
                    time.sleep(60)
                
                if not recognition_completed:
                    logger.error(f"Recognition timed out after {max_wait_time} seconds")
                    return
                
                logger.info(f"Recognition completed for session {capture_id}")
                
                # Step 5: Export to Supabase
                # Get recognition results
                logger.info(f"Retrieving recognition results for session {capture_id} for Supabase export")
                recognition_data = recognition_service.get_recognition_results(capture_id)
                
                # Log the recognition data structure (not the full content)
                if recognition_data:
                    logger.info(f"Recognition data retrieved for session {capture_id}. Keys: {list(recognition_data.keys())}")
                    logger.info(f"Recognition data type: {type(recognition_data)}")
                    
                    # Check for identified_speakers
                    if "identified_speakers" in recognition_data:
                        logger.info(f"Found {len(recognition_data['identified_speakers'])} identified_speakers in recognition_data")
                    else:
                        logger.warning("No identified_speakers found in recognition_data")
                    
                    # Check for parliament_clips
                    if "parliament_clips" in recognition_data:
                        logger.info(f"Found {len(recognition_data['parliament_clips'])} parliament_clips in recognition_data")
                    else:
                        logger.warning("No parliament_clips found in recognition_data")
                        
                    # Check for transcription data
                    if "transcription" in recognition_data:
                        logger.info("Found transcription data in recognition_data")
                        if "speakers" in recognition_data["transcription"]:
                            logger.info(f"Found {len(recognition_data['transcription']['speakers'])} speakers in transcription data")
                    else:
                        logger.warning("No transcription data found in recognition_data")
                else:
                    logger.error(f"No recognition data found for session {capture_id}")
                    # Don't return here, try to continue with empty data for diagnostic purposes
                    recognition_data = {}
                
                # Get video metadata
                db.refresh(capture)
                
                # Handle capture_metadata properly - it might be a string or a dict
                capture_metadata = {}
                if capture.capture_metadata:
                    if isinstance(capture.capture_metadata, dict):
                        capture_metadata = capture.capture_metadata
                    elif isinstance(capture.capture_metadata, str):
                        try:
                            capture_metadata = json.loads(capture.capture_metadata)
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing capture metadata JSON for capture {capture_id}")
                    else:
                        logger.error(f"Unexpected metadata type: {type(capture.capture_metadata)}")
                
                # Use default Docker container paths if file_path is None
                if capture.file_path is None:
                    video_file_path = f"/app/data/media/parliament_tv_{capture_id}.mp4"
                    audio_file_path = f"/app/data/temp/audio_extracts/audio_{capture_id}.mp3"
                else:
                    video_file_path = capture.file_path
                    audio_file_path = os.path.join(os.path.dirname(capture.file_path), f"audio_{capture_id}.mp3")
                
                video_metadata = {
                    "video_id": capture_id,
                    "title": capture.title,
                    "description": capture.description,
                    "duration": capture.duration,
                    "file_path": video_file_path,
                    "audio_path": audio_file_path,
                    "video_url": capture_metadata.get("video_url"),
                    "audio_url": capture_metadata.get("audio_url"),
                    "original_url": capture_metadata.get("original_url")
                }
                
                # Export to Supabase using service role for privileged operations
                logger.info(f"Initializing SupabaseIntegration for export of session {capture_id}")
                supabase = SupabaseIntegration()
                
                # Ensure all metadata is properly serializable using the utility function
                # This handles SQLAlchemy MetaData objects, datetime objects, and other non-serializable types
                logger.info(f"Serializing recognition data and video metadata for session {capture_id}")
                try:
                    serializable_recognition_data = make_json_serializable(recognition_data)
                    logger.info(f"Successfully serialized recognition data for session {capture_id}")
                except Exception as e:
                    logger.error(f"Error serializing recognition data: {str(e)}")
                    # traceback already imported at function start
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Create a minimal serializable version
                    serializable_recognition_data = {"error": "Serialization failed", "original_keys": list(recognition_data.keys()) if isinstance(recognition_data, dict) else "Not a dict"}
                
                try:
                    serializable_video_metadata = make_json_serializable(video_metadata)
                    logger.info(f"Successfully serialized video metadata for session {capture_id}")
                except Exception as e:
                    logger.error(f"Error serializing video metadata: {str(e)}")
                    # traceback already imported at function start
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Create a minimal serializable version
                    serializable_video_metadata = {"video_id": capture_id, "error": "Serialization failed"}
                
                # Get the combined AV path from process metadata if available
                process = db.query(RecognitionProcess).filter(RecognitionProcess.video_id == capture_id).first()
                if process and process.process_metadata:
                    try:
                        metadata = {}
                        if isinstance(process.process_metadata, str):
                            try:
                                metadata = json.loads(process.process_metadata)
                            except json.JSONDecodeError:
                                logger.error(f"Error parsing process metadata JSON for process {process.id}")
                        elif isinstance(process.process_metadata, dict):
                            metadata = process.process_metadata
                        else:
                            logger.error(f"Unexpected process metadata type: {type(process.process_metadata)}")
                        
                        # Check for combined_av_path in the parsed metadata
                        if metadata and "combined_av_path" in metadata:
                            video_file_path = metadata["combined_av_path"]
                            logger.info(f"Using combined AV path from metadata: {video_file_path}")
                    except Exception as e:
                        logger.error(f"Error processing metadata for combined AV path: {str(e)}")
                        # traceback already imported at function start
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
                logger.info(f"Exporting recognition results to Supabase for session {capture_id} with video path: {video_file_path}")
                try:
                    # Check if the video file exists before attempting to export
                    if os.path.exists(video_file_path):
                        logger.info(f"Video file exists at {video_file_path}, size: {os.path.getsize(video_file_path)} bytes")
                    else:
                        logger.warning(f"Video file does not exist at {video_file_path}, checking for alternatives")
                        # Try to find the file in the media directory
                        media_dir = "/app/data/media"
                        potential_files = [f for f in os.listdir(media_dir) if str(capture_id) in f and f.endswith('.mp4')]
                        if potential_files:
                            video_file_path = os.path.join(media_dir, potential_files[0])
                            logger.info(f"Found alternative video file: {video_file_path}")
                        else:
                            logger.error(f"No suitable video file found for session {capture_id}")
                    
                    # Export recognition results to Supabase
                    try:
                        logger.warning(f"🚀 CALLING export_and_upload_recognition for video_id={capture_id}")
                        export_result = supabase.export_and_upload_recognition(
                            video_path=video_file_path,
                            recognition_results=serializable_recognition_data,
                            video_metadata=serializable_video_metadata,
                            db_session=db,
                            video_id=capture_id,
                            upload_media=True
                        )
                        logger.info(f"Export result for session {capture_id}: {export_result}")
                    except Exception as e:
                        logger.error(f"Error in export_and_upload_recognition: {str(e)}")
                        # traceback already imported at function start
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        export_result = {"error": str(e), "success": False}
                    
                    # Get the full video URL from the export result
                    full_video_url = None
                    if export_result and "supabase_urls" in export_result:
                        if isinstance(export_result["supabase_urls"], dict):
                            full_video_url = export_result["supabase_urls"].get("combined_av_url")
                            logger.debug(f"Found full_video_url in export_result[supabase_urls][combined_av_url]: {full_video_url}")
                    
                    # If full_video_url is still None, check if it's available in the capture session metadata
                    if not full_video_url:
                        capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
                        if capture and capture.capture_metadata:
                            # Try to get URL from metadata if it exists
                            metadata = capture.capture_metadata
                            if isinstance(metadata, dict) and "supabase_url" in metadata:
                                full_video_url = metadata["supabase_url"]
                                logger.debug(f"Found full_video_url in capture_metadata: {full_video_url}")
                            # Check recognition_results for URL information
                            elif capture.recognition_results:
                                try:
                                    rec_results = json.loads(capture.recognition_results) if isinstance(capture.recognition_results, str) else capture.recognition_results
                                    if isinstance(rec_results, dict) and "supabase_urls" in rec_results:
                                        full_video_url = rec_results["supabase_urls"].get("combined_av_url")
                                        logger.debug(f"Found full_video_url in recognition_results: {full_video_url}")
                                except (json.JSONDecodeError, AttributeError) as e:
                                    logger.warning(f"Could not parse recognition_results: {str(e)}")
                        logger.info(f"No supabase_url found in CaptureSession for ID {capture_id}")
                    
                    # If still None, check if there's a combined AV file in the media directory
                    if not full_video_url:
                        from backend.core.config import settings
                        import glob  # Local import to ensure it's available in this scope
                        media_dir = settings.MEDIA_STORAGE_PATH
                        combined_files = glob.glob(os.path.join(media_dir, f"combined_av_{capture_id}_*.mp4"))
                        if combined_files:
                            # Use the most recent file if multiple exist
                            combined_files.sort(key=os.path.getmtime, reverse=True)
                            combined_url = combined_files[0]
                            logger.debug(f"Found combined AV file in media directory: {combined_url}")
                            
                            # Try to upload it to Supabase
                            try:
                                # Use the upload_media_to_supabase method which internally calls upload_full_video
                                upload_result = supabase.upload_media_to_supabase(video_path=combined_url)
                                if "combined_av_url" in upload_result:
                                    full_video_url = upload_result.get("combined_av_url")
                                    logger.warning(f"🔍 Successfully uploaded combined AV file to Supabase: {full_video_url}")
                            except Exception as e:
                                logger.error(f"Error uploading combined AV file to Supabase: {str(e)}")
                                # traceback already imported at function start
                                logger.error(f"Upload traceback: {traceback.format_exc()}")
                    
                    logger.info(f"Full video URL from export: {full_video_url}")
                    
                    # Initialize SupabaseService for saving member clips
                    logger.info(f"Initializing SupabaseService with service role for saving member clips for session {capture_id}")
                    # Use the improved SupabaseUploader with extended timeout (1 hour) for large video uploads
                    supabase_service = SupabaseUploader(use_service_role=True, timeout=3600)
                    
                    # First run the synchronization script to ensure member IDs are properly synchronized
                    logger.info(f"Running member ID synchronization script before saving clips for session {capture_id}")
                    try:
                        # Member ID conversion is now handled inline in supabase_client.py
                        logger.info("Using inline member ID conversion in supabase_client.py")
                    except Exception as sync_error:
                        logger.error(f"Error synchronizing member IDs: {str(sync_error)}")
                        # traceback already imported at function start
                        logger.error(f"Synchronization traceback: {traceback.format_exc()}")
                        # Continue with the export, but log the error
                    
                    # Note: Export to Supabase is already handled by export_and_upload_recognition above
                    # The export_and_upload_recognition method internally calls normalize_and_export_clips
                    # No additional export is needed here to prevent duplicate exports
                    logger.info(f"Export to Supabase completed via export_and_upload_recognition for video_id={capture_id}")
                    save_result = {"success": True, "note": "Export handled by export_and_upload_recognition"}
                except Exception as e:
                    logger.error(f"Error saving member clips to Supabase: {str(e)}")
                    # traceback already imported at function start
                    logger.error(f"Traceback: {traceback.format_exc()})")
                
                
                logger.info(f"Exported recognition results to Supabase for session {capture_id}")
                
                # Verify MP clips in Supabase export
                try:
                    from backend.services.integration.mp_clip_verification import verify_mp_clips_in_supabase
                    
                    # Ensure export_result has a consistent structure with all required paths
                    if "export_paths" not in export_result:
                        logger.warning("export_paths not found in export_result, creating it now")
                        export_result["export_paths"] = {
                            "clips_export_path": export_result.get("clips_export_path"),
                            "video_export_path": export_result.get("video_export_path"),
                            "recognition_export_path": export_result.get("recognition_export_path"),
                            "combined_av_path": export_result.get("combined_av_path")
                        }
                    
                    # Ensure all paths in export_paths are also available at the root level for backward compatibility
                    for key, value in export_result["export_paths"].items():
                        if value:  # Only set if value is not None/empty
                            export_result[key] = value
                    
                    # Log the export paths for debugging
                    logger.info(f"Export paths for verification: {export_result.get('export_paths')}")
                    
                    # Validate that all required export paths exist and are accessible
                    for path_key, path_value in export_result["export_paths"].items():
                        if path_value:
                            file_exists = os.path.exists(path_value)
                            file_size = os.path.getsize(path_value) if file_exists else 0
                            logger.info(f"Export path validation - {path_key}: exists={file_exists}, size={file_size}, path={path_value}")
                    
                    # Check if clips_export_path exists and is valid
                    clips_export_path = export_result.get("export_paths", {}).get("clips_export_path")
                    if not clips_export_path or not os.path.exists(clips_export_path):
                        logger.warning(f"Clips export path is missing or invalid: {clips_export_path}")
                        
                        # Try to find alternative paths that might contain clip data
                        for key, path in export_result.items():
                            if isinstance(path, str) and "clip" in key.lower() and os.path.exists(path) and path.endswith(".json"):
                                logger.info(f"Found alternative clips export path: {key} -> {path}")
                                export_result["export_paths"]["clips_export_path"] = path
                                export_result["clips_export_path"] = path  # Also update at root level
                                break
                                
                        # Look for clips JSON files in common export directories
                        if not clips_export_path or not os.path.exists(clips_export_path):
                            data_dir = "/app/data"
                            export_dirs = [
                                os.path.join(data_dir, "temp", "supabase_export"),
                                os.path.join(data_dir, "exports"),
                                os.path.join(data_dir, "temp")
                            ]
                            
                            for export_dir in export_dirs:
                                if os.path.exists(export_dir):
                                    import glob
                                    # Try to find clips export files with patterns
                                    patterns = [
                                        f"*clip*{capture_id}*.json",
                                        f"*{capture_id}*clip*.json",
                                        "*clips_export*.json"
                                    ]
                                    
                                    for pattern in patterns:
                                        matches = glob.glob(os.path.join(export_dir, pattern))
                                        if matches:
                                            # Sort by modification time (newest first)
                                            matches.sort(key=os.path.getmtime, reverse=True)
                                            clips_export_path = matches[0]
                                            logger.info(f"Found clips export file via pattern search: {clips_export_path}")
                                            export_result["export_paths"]["clips_export_path"] = clips_export_path
                                            export_result["clips_export_path"] = clips_export_path
                                            break
                                    
                                    if clips_export_path and os.path.exists(clips_export_path):
                                        break
                    
                    # Validate export_result before verification
                    if not export_result.get("export_paths", {}).get("clips_export_path") or not os.path.exists(export_result.get("export_paths", {}).get("clips_export_path")):
                        logger.warning("No valid clips export path found after all attempts. Creating empty export files.")

                        # Create empty export files to ensure the pipeline can continue
                        # json already imported at function start
                        from datetime import datetime
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        export_dir = os.path.join("/app/data/temp/supabase_export", str(capture_id))
                        os.makedirs(export_dir, exist_ok=True)
                        
                        # Create empty export files
                        clips_export_path = os.path.join(export_dir, f"clips_export_{capture_id}_{timestamp}.json")
                        recognition_export_path = os.path.join(export_dir, f"recognition_export_{capture_id}_{timestamp}.json")
                        
                        # Write empty files with minimal content
                        with open(clips_export_path, 'w') as f:
                            json.dump({"video_id": capture_id, "timestamp": timestamp, "clips": [], "note": "No clips found for export"}, f)
                        
                        with open(recognition_export_path, 'w') as f:
                            json.dump({"video_id": capture_id, "timestamp": timestamp, "events": [], "note": "No recognition events found for export"}, f)
                        
                        logger.info(f"Created empty export files at:\n - {clips_export_path}\n - {recognition_export_path}")

                        # Update the export paths in the result
                        if "export_paths" not in export_result:
                            export_result["export_paths"] = {}
                        export_result["export_paths"]["clips_export_path"] = clips_export_path
                        export_result["export_paths"]["recognition_export_path"] = recognition_export_path
                        export_result["clips_export_path"] = clips_export_path  # Also update at root level
                        export_result["recognition_export_path"] = recognition_export_path  # Also update at root level
                        
                        logger.info("Created empty export files to ensure pipeline can continue")
                    else:
                        verification_result = verify_mp_clips_in_supabase(capture_id, db, export_result)
                        
                        if verification_result.get("success", False):
                            logger.info(f"Successfully verified {verification_result.get('mp_clips_count', 0)} MP clips in Supabase export")
                            logger.info(f"MP IDs found: {verification_result.get('mp_ids_found', [])}")
                            logger.info(f"MP names found: {verification_result.get('mp_names_found', [])}")
                            
                            # Update capture session with verification results
                            try:
                                capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
                                if capture:
                                    # Store verification results in capture_metadata JSON field
                                    if not capture.capture_metadata:
                                        capture.capture_metadata = {}
                                    elif isinstance(capture.capture_metadata, str):
                                        try:
                                            # json already imported at function start
                                            capture.capture_metadata = json.loads(capture.capture_metadata)
                                        except json.JSONDecodeError:
                                            capture.capture_metadata = {}
                                    
                                    # Ensure capture_metadata is a dictionary
                                    if not isinstance(capture.capture_metadata, dict):
                                        capture.capture_metadata = {}
                                    
                                    # Store verification results
                                    from datetime import datetime as dt
                                    capture.capture_metadata["mp_verification"] = {
                                        "success": verification_result.get("success"),
                                        "mp_clips_count": verification_result.get("mp_clips_count"),
                                        "total_clips_count": verification_result.get("total_clips_count"),
                                        "mp_ids_found": verification_result.get("mp_ids_found"),
                                        "verified_at": dt.now().isoformat()
                                    }
                                    db.commit()
                                    logger.info(f"Updated capture session with verification results")
                            except Exception as e:
                                logger.error(f"Error updating capture session with verification results: {str(e)}")
                        else:
                            logger.warning(f"MP clip verification failed: {verification_result.get('error', 'Unknown error')}")
                            logger.warning(f"MP clips count: {verification_result.get('mp_clips_count', 0)}, Total clips: {verification_result.get('total_clips_count', 0)}")
                            logger.warning(f"Verification details: {verification_result}")
                except Exception as e:
                    logger.error(f"Error verifying MP clips: {str(e)}")
                    # traceback already imported at function start
                    logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Update capture status with external ID
                capture.external_id = f"parliament_tv_{capture_id}"
                capture.external_status = "processed"
                db.commit()
                
                # Log comprehensive workflow summary at the very end (after all processing is complete)
                try:
                    # Calculate total processing time
                    from datetime import datetime as dt, timezone
                    end_time = dt.now(timezone.utc)
                    if hasattr(capture, 'created_at') and capture.created_at:
                        # Ensure both datetimes are timezone-aware for comparison
                        if capture.created_at.tzinfo is None:
                            # If created_at is naive, assume UTC
                            start_time = capture.created_at.replace(tzinfo=timezone.utc)
                        else:
                            start_time = capture.created_at
                        total_duration = (end_time - start_time).total_seconds()
                    else:
                        total_duration = 0
                    
                    # Get recognition results for metrics
                    recognition_data = recognition_service.get_recognition_results(capture_id)
                    
                    # Extract metrics from recognition data if available
                    total_faces = 0
                    total_events = 0
                    identified_speakers = 0
                    total_segments = 0
                    
                    if recognition_data:
                        # Extract metrics with type safety - use correct field names from actual data structure
                        # From logs: Keys: ['success', 'video_id', 'segments_count', 'recognition_events', 'correlations', 'timeline', 'speaker_appearances']
                        
                        # Get segments count (this is the number of transcript segments processed)
                        total_segments = recognition_data.get("segments_count", 0)
                        if not isinstance(total_segments, int):
                            total_segments = 0
                        
                        # Get recognition events (these are the face/speaker detection events)
                        events = recognition_data.get("recognition_events", [])
                        if isinstance(events, list):
                            total_events = len(events)
                            # Count identified speakers (events with valid member_id and name != "Unknown")
                            identified_speakers = len([
                                event for event in events 
                                if isinstance(event, dict) 
                                and event.get("member_id") 
                                and event.get("name") 
                                and event.get("name") != "Unknown"
                            ])
                        else:
                            total_events = 0
                            identified_speakers = 0
                        
                        # Get timeline data to count unique faces detected
                        timeline = recognition_data.get("timeline", [])
                        if isinstance(timeline, list):
                            # Count unique face detections from timeline events
                            face_events = [
                                event for event in timeline 
                                if isinstance(event, dict) 
                                and event.get("type") == "face"
                            ]
                            total_faces = len(face_events)
                        else:
                            total_faces = 0
                        
                        # If timeline doesn't have face data, try speaker_appearances
                        if total_faces == 0:
                            speaker_appearances = recognition_data.get("speaker_appearances", [])
                            if isinstance(speaker_appearances, list):
                                total_faces = len(speaker_appearances)
                        
                        # Fallback: if we still don't have face count, use recognition events
                        if total_faces == 0 and total_events > 0:
                            total_faces = total_events
                    
                    # Extract original capture information for context
                    capture_url = url if url else "Unknown URL"
                    capture_title = "Unknown Title"
                    capture_description = "No description available"
                    capture_duration = "Unknown duration"
                    
                    # Try to get additional metadata from the capture record
                    if hasattr(capture, 'metadata') and capture.metadata:
                        try:
                            import json
                            metadata = json.loads(capture.metadata) if isinstance(capture.metadata, str) else capture.metadata
                            capture_duration = metadata.get('duration', capture_duration)
                        except:
                            pass
                    
                    # Log comprehensive workflow summary
                    logger.info("\n" + "="*80)
                    logger.info("🏛️  MULTIMODAL RECOGNITION WORKFLOW SUMMARY")
                    logger.info("="*80)
                    logger.info(f"📺 Original Capture:")
                    logger.info(f"   • URL: {capture_url}")
                    logger.info(f"   • Title: {capture_title}")
                    logger.info(f"   • Description: {capture_description}")
                    logger.info(f"   • Duration: {capture_duration}")
                    logger.info(f"📹 Video ID: {capture_id}")
                    logger.info(f"⏱️  Total Processing Time: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
                    logger.info(f"🎯 Recognition Results:")
                    logger.info(f"   • Total Faces Detected: {total_faces}")
                    logger.info(f"   • Total Recognition Events: {total_events}")
                    logger.info(f"   • Identified Speakers: {identified_speakers}")
                    logger.info(f"   • Total Segments Processed: {total_segments}")
                    if total_events > 0:
                        identification_rate = (identified_speakers / total_events) * 100
                        logger.info(f"   • Speaker Identification Rate: {identification_rate:.1f}%")
                    logger.info(f"✅ Status: COMPLETED SUCCESSFULLY")
                    logger.info("="*80)
                except Exception as summary_error:
                    logger.warning(f"Could not generate workflow summary: {summary_error}")
                
                logger.info(f"Completed full processing pipeline for Parliament TV URL: {url}")
                
            except Exception as e:
                logger.error(f"Error in capture process: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # First rollback any failed transaction
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {str(rollback_error)}")
                
                # Update capture status with a fresh transaction
                try:
                    capture.status = "failed"
                    capture.error_message = str(e)
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Error updating capture status: {str(commit_error)}")
                    db.rollback()
                
        except Exception as e:
            logger.error(f"Error in Parliament TV processing task: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Ensure any failed transaction is rolled back
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback in outer exception handler: {str(rollback_error)}")
    
    # Start the background task
    background_tasks.add_task(process_parliament_tv_task)
    
    return {
        "status": "processing",
        "message": "Started Parliament TV processing pipeline",
        "url": url,
        "title": title,
        "description": description,
        "duration": duration
    }


