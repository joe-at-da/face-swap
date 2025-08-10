"""
Parliament TV Sequential Processing API Endpoint

This module provides an endpoint for processing Parliament TV videos sequentially
in 30-minute segments to avoid memory issues with long-running videos.
"""

import logging
import asyncio
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.session import get_db
from backend.db.models.capture import CaptureSession
from backend.services.parliament_tv_sequential import ParliamentTVSequentialProcessor
from backend.core.security import get_api_key

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/process-parliament-tv", dependencies=[Depends(get_api_key)])
async def process_parliament_tv_sequentially(
    background_tasks: BackgroundTasks,
    url: str = Body(None, description="Parliament TV URL to process (optional)"),
    title: str = Body(None, description="Title for the capture session (optional)"),
    description: str = Body(None, description="Description for the capture session (optional)"),
    duration: int = Body(None, description="Duration to capture in seconds (optional)"),
    debug: bool = Body(False, description="Enable debug/test mode with shorter durations for testing"),
    db: Session = Depends(get_db)
):
    """
    Process a Parliament TV video sequentially in 30-minute segments.
    
    If URL, title, and duration are provided, use the existing processing logic.
    If not provided, automatically detect the latest live or archived video from Parliament TV Commons.
    
    Args:
        url: Parliament TV URL to process (optional)
        title: Title for the capture session (optional)
        description: Description for the capture session (optional)
        duration: Duration to capture in seconds (optional)
        debug: Enable debug/test mode with shorter durations for testing
        
    Returns:
        Status information about the initiated process
    """
    # Initialize the sequential processor
    sequential_processor = ParliamentTVSequentialProcessor()
    
    # If URL is not provided, get the latest video from Parliament TV Commons
    if not url:
        logger.info("No URL provided, getting latest video from Parliament TV Commons")
        video_info = sequential_processor.get_latest_video_info()
        
        if not video_info or not video_info.get("url"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No live or recent videos found on Parliament TV Commons"
            )
        
        url = video_info["url"]
        is_live = video_info.get("is_live", False)
        
        # Use the video title if no title provided
        if not title:
            title = video_info.get("title", "Parliament TV Video")
        
        # Use a default description if none provided
        if not description:
            description = f"{'Live' if is_live else 'Archived'} Parliament TV video from Commons"
        
        logger.info(f"Found {'live' if is_live else 'archived'} video: {title} ({url})")
    else:
        # If URL is provided but no title, use a default title
        if not title:
            title = "Parliament TV Video"
        
        # If URL is provided but no description, use a default description
        if not description:
            description = "Parliament TV video processing"
        
        # Determine if the video is live (this is a placeholder, we'll need to check properly)
        is_live = False
    
    # Create a background task for the sequential processing
    def process_parliament_tv_sequential_task():
        # Import CaptureSession within the function scope to avoid UnboundLocalError
        from backend.db.models.capture import CaptureSession
        
        try:
            # Step 1: Extract stream URLs
            logger.info(f"Extracting stream URLs from {url}")
            try:
                stream_info = sequential_processor.extract_stream_urls(url)
                
                if not stream_info:
                    logger.error("Failed to extract stream URLs")
                    return
                
                video_url = stream_info.get("video_url")
                audio_url = stream_info.get("audio_url")
                time_marker = stream_info.get("time_marker", {}).get("seconds", 0)
                
                if not video_url or not audio_url:
                    logger.error(f"Missing video or audio URL: video_url={video_url}, audio_url={audio_url}")
                    return
                
                logger.info(f"Successfully extracted stream URLs: video={video_url}, audio={audio_url}")
                logger.info(f"Time marker: {time_marker} seconds")
                
            except Exception as e:
                logger.error(f"Error extracting stream URLs: {str(e)}")
                return
            
            # Step 2: Create capture session
            capture_metadata = {
                "video_url": video_url,
                "audio_url": audio_url,
                "original_url": url,
                "time_marker": {"seconds": time_marker},
                "is_sequential": True,
                "is_live": is_live
            }
            
            # Create capture session in database
            capture = CaptureSession(
                title=title,
                description=description,
                status="draft",
                capture_metadata=capture_metadata,  # This maps to 'metadata' column in DB
                duration=duration if duration else (7200 if not is_live else 86400)  # Default to 2 hours for archived, 24 hours for live
            )
            db.add(capture)
            db.commit()
            db.refresh(capture)
            
            capture_id = capture.id
            logger.info(f"Created capture session with ID: {capture_id}")
            
            # Step 3: Start sequential processing
            try:
                logger.info(f"Starting sequential processing for session {capture_id}")
                
                # Start sequential processing (includes download)
                processing_result = sequential_processor.process_video_sequentially(
                    original_url=url,
                    video_url=video_url,
                    audio_url=audio_url,
                    title=title,
                    description=description,
                    total_duration=duration,
                    is_live=is_live,
                    session_id=str(capture_id)
                )
                
                # Update capture session with processing results
                capture.capture_metadata["sequential_processing"] = processing_result
                
                # Check if processing was successful
                if processing_result.get("success", False):
                    # Get segment results for concatenation
                    segment_results = processing_result.get("segments", [])
                    
                    # Get segment results and set up video path for recognition
                    video_segment_paths = []
                    audio_segment_paths = []
                    
                    # Process each segment individually and run recognition on each segment (efficient approach)
                    logger.info(f"Processing {len(segment_results)} segments individually with recognition...")
                    processed_segments = []
                    
                    for i, segment in enumerate(segment_results):
                        if segment.get("video_path") and segment.get("audio_path"):
                            video_segment_paths.append(segment["video_path"])
                            audio_segment_paths.append(segment["audio_path"])
                            
                            # Process this segment (metadata storage)
                            try:
                                logger.info(f"Processing segment {i+1}/{len(segment_results)}: {segment.get('start_time')}-{segment.get('end_time')}s")
                                
                                segment_title = f"{title} (Segment {i+1})"
                                segment_description = f"Segment {i+1} from {segment.get('start_time', 0)} to {segment.get('end_time', 0)} seconds"
                                
                                # Call process_segment for each segment (metadata storage)
                                process_result = sequential_processor.process_segment(
                                    original_url=url,
                                    video_url=video_url,
                                    audio_url=audio_url,
                                    start_time=segment.get('start_time', 0),
                                    end_time=segment.get('end_time', 0),
                                    title=segment_title,
                                    description=segment_description,
                                    session_id=str(capture_id),
                                    video_path=segment["video_path"],
                                    audio_path=segment["audio_path"]
                                )
                                
                                if process_result.get("success", False):
                                    processed_segments.append(process_result)
                                    logger.info(f"Successfully processed segment {i+1}")
                                    
                                    # Note: Recognition will be triggered once after all segments are processed
                                    # This matches the non-sequential pipeline approach for consistency
                                    logger.info(f"Segment {i+1} processed - recognition will be triggered after all segments complete")
                                        
                                else:
                                    logger.error(f"Failed to process segment {i+1}: {process_result.get('error')}")
                                    
                            except Exception as e:
                                logger.error(f"Error processing segment {i+1}: {str(e)}")
                                import traceback
                                logger.error(f"Segment processing error traceback: {traceback.format_exc()}")
                    
                    logger.info(f"Completed processing {len(processed_segments)}/{len(segment_results)} segments")
                    capture.capture_metadata["processed_segments"] = len(processed_segments)
                    
                    # Set video_path for recognition pipeline
                    if video_segment_paths:
                        # Define media directory path
                        media_dir = "/app/data/media"
                        
                        if len(video_segment_paths) > 1:
                            logger.info(f"Processing completed with {len(segment_results)} segments. Starting concatenation...")
                            
                            # Concatenate video segments if there are multiple
                            try:
                                concat_video_path = sequential_processor.concatenate_segments(
                                    segment_paths=video_segment_paths,
                                    output_path=f"{media_dir}/{capture_id}_concatenated.mp4",
                                    is_audio=False
                                )
                                
                                # Update capture with concatenated video path
                                capture.video_path = concat_video_path  # Model field (primary)
                                capture.capture_metadata["video_url"] = stream_info.get("video_url", "")  # Stream URL (original)
                                capture.capture_metadata["concatenated_video_path"] = concat_video_path
                                
                                # Also concatenate audio segments for recognition
                                if audio_segment_paths:
                                    try:
                                        concat_audio_path = sequential_processor.concatenate_segments(
                                            segment_paths=audio_segment_paths,
                                            output_path=f"{media_dir}/{capture_id}_concatenated.mp3",
                                            is_audio=True
                                        )
                                        # Store audio and video paths exactly like non-sequential pipeline
                                        capture.audio_path = concat_audio_path  # Model field (primary)
                                        capture.capture_metadata["audio_file_path"] = concat_audio_path  # Metadata field (secondary)
                                        capture.capture_metadata["audio_url"] = stream_info.get("audio_url", "")  # Stream URL (original)
                                        logger.info(f"Successfully concatenated {len(audio_segment_paths)} audio segments")
                                    except Exception as audio_e:
                                        logger.warning(f"Audio concatenation failed: {str(audio_e)}, using first audio segment")
                                        # Fallback: use first audio segment, matching non-sequential pattern
                                        first_audio = audio_segment_paths[0] if audio_segment_paths else None
                                        if first_audio:
                                            capture.audio_path = first_audio  # Model field (primary)
                                            capture.capture_metadata["audio_file_path"] = first_audio  # Metadata field (secondary)
                                else:
                                    # No audio segments available
                                    capture.audio_path = None  # Model field (primary)
                                    capture.capture_metadata["audio_file_path"] = None  # Metadata field (secondary)
                                
                                logger.info(f"Successfully concatenated {len(video_segment_paths)} video segments")
                            except Exception as e:
                                logger.error(f"Error concatenating video segments: {str(e)}")
                                capture.capture_metadata["video_concatenation_error"] = str(e)
                                # Fallback to first segment if concatenation fails
                                capture.video_path = video_segment_paths[0]
                                capture.file_path = video_segment_paths[0]
                                capture.capture_metadata["audio_path"] = audio_segment_paths[0] if audio_segment_paths else None  # For recognition service
                                capture.capture_metadata["audio_url"] = audio_segment_paths[0] if audio_segment_paths else None  # For metadata compatibility
                                capture.audio_path = audio_segment_paths[0] if audio_segment_paths else None  # Set model field directly
                                logger.info(f"Using first segment as fallback: {video_segment_paths[0]}")
                        else:
                            # Single segment - use it directly
                            capture.video_path = video_segment_paths[0]
                            capture.file_path = video_segment_paths[0]
                            capture.capture_metadata["audio_path"] = audio_segment_paths[0] if audio_segment_paths else None  # For recognition service
                            capture.capture_metadata["audio_url"] = audio_segment_paths[0] if audio_segment_paths else None  # For metadata compatibility
                            capture.audio_path = audio_segment_paths[0] if audio_segment_paths else None  # Set model field directly
                            logger.info(f"Single segment processing - using: {video_segment_paths[0]}")
                        
                        # Now trigger unified recognition on the complete/concatenated video
                        # This matches the non-sequential pipeline approach
                        logger.info(f"Starting unified recognition for session {capture_id}")
                        try:
                            from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
                            
                            # Mark capture as completed before recognition
                            capture.status = "completed"
                            
                            # DEBUG: Log the exact metadata being stored
                            logger.info(f"DEBUG: About to commit capture {capture_id} with metadata:")
                            logger.info(f"DEBUG: capture.capture_metadata = {capture.capture_metadata}")
                            logger.info(f"DEBUG: capture.audio_path = {capture.audio_path}")
                            logger.info(f"DEBUG: capture.video_path = {capture.video_path}")
                            
                            db.commit()
                            
                            # DEBUG: Verify what was actually stored by re-reading from DB
                            db.refresh(capture)
                            logger.info(f"DEBUG: After commit and refresh:")
                            logger.info(f"DEBUG: capture.capture_metadata = {capture.capture_metadata}")
                            logger.info(f"DEBUG: capture.audio_path = {capture.audio_path}")
                            logger.info(f"DEBUG: capture.video_path = {capture.video_path}")
                            
                            # Start recognition using the same approach as non-sequential pipeline
                            recognition_service = MultimodalRecognitionService()
                            recognition_result = recognition_service.start_combined_recognition(capture_id)
                            
                            if recognition_result.get("success", False):
                                logger.info(f"Recognition started successfully for session {capture_id}")
                                capture.capture_metadata["recognition_triggered"] = True
                                capture.capture_metadata["recognition_started_at"] = datetime.now().isoformat()
                                
                                # Wait for recognition to complete and then export to Supabase
                                # This matches the non-sequential pipeline approach
                                logger.info(f"Waiting for recognition to complete for session {capture_id}")
                                
                                # Wait for recognition completion (similar to non-sequential pipeline)
                                import time
                                max_wait_time = 3600  # 1 hour max for recognition
                                start_time = time.time()
                                recognition_completed = False
                                
                                while time.time() - start_time < max_wait_time:
                                    try:
                                        # Refresh capture from database
                                        db.refresh(capture)
                                        status_value = capture.recognition_status
                                        
                                        logger.info(f"Recognition status: {status_value}")
                                        
                                        if status_value == "completed":
                                            recognition_completed = True
                                            break
                                        elif status_value == "failed":
                                            error_message = capture.error_message if hasattr(capture, 'error_message') else "Unknown error"
                                            logger.error(f"Recognition failed: {error_message}")
                                            break
                                    except Exception as e:
                                        logger.error(f"Error checking recognition status: {str(e)}")
                                    
                                    # Wait before checking again
                                    time.sleep(60)
                                
                                if recognition_completed:
                                    logger.info(f"Recognition completed for session {capture_id}. Starting export to Supabase...")
                                    
                                    # Export to Supabase using the same approach as non-sequential pipeline
                                    try:
                                        # Get recognition results
                                        recognition_data = recognition_service.get_recognition_results(capture_id)
                                        
                                        if recognition_data:
                                            logger.info(f"Recognition data retrieved for session {capture_id}. Starting Supabase export...")
                                            
                                            # Use the same export approach as non-sequential pipeline
                                            # Process recognition results directly instead of reading from SQLite
                                            from backend.services.integration.supabase_integration import SupabaseIntegration
                                            from backend.services.utils import make_json_serializable
                                            import json
                                            
                                            # Get video metadata
                                            db.refresh(capture)
                                            
                                            # Handle capture_metadata properly
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
                                            
                                            # Use the concatenated video path
                                            video_file_path = capture.video_path or capture.file_path
                                            if not video_file_path:
                                                video_file_path = f"/app/data/media/parliament_tv_{capture_id}.mp4"
                                            
                                            audio_file_path = os.path.join(os.path.dirname(video_file_path), f"audio_{capture_id}.mp3")
                                            
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
                                            
                                            # Export to Supabase using the same approach as non-sequential pipeline
                                            logger.info(f"Initializing SupabaseIntegration for export of session {capture_id}")
                                            supabase = SupabaseIntegration()
                                            
                                            # Serialize data
                                            try:
                                                serializable_recognition_data = make_json_serializable(recognition_data)
                                                serializable_video_metadata = make_json_serializable(video_metadata)
                                                logger.info(f"Successfully serialized data for session {capture_id}")
                                            except Exception as e:
                                                logger.error(f"Error serializing data: {str(e)}")
                                                serializable_recognition_data = {"error": "Serialization failed"}
                                                serializable_video_metadata = {"video_id": capture_id, "error": "Serialization failed"}
                                            
                                            # Export recognition results to Supabase
                                            try:
                                                logger.info(f"Calling export_and_upload_recognition for session {capture_id}")
                                                export_result = supabase.export_and_upload_recognition(
                                                    video_path=video_file_path,
                                                    recognition_results=serializable_recognition_data,
                                                    video_metadata=serializable_video_metadata,
                                                    db_session=db,
                                                    video_id=capture_id,
                                                    upload_media=True
                                                )
                                                logger.info(f"Export result for session {capture_id}: {export_result}")
                                                
                                                if export_result.get("success", False):
                                                    logger.info(f"Successfully exported recognition results to Supabase for session {capture_id}")
                                                    capture.capture_metadata["supabase_export_completed"] = True
                                                    capture.capture_metadata["supabase_export_completed_at"] = datetime.now().isoformat()
                                                else:
                                                    logger.error(f"Failed to export to Supabase: {export_result.get('error', 'Unknown error')}")
                                                    capture.capture_metadata["supabase_export_error"] = export_result.get('error', 'Unknown error')
                                                    
                                            except Exception as e:
                                                logger.error(f"Error in export_and_upload_recognition: {str(e)}")
                                                import traceback
                                                logger.error(f"Export traceback: {traceback.format_exc()}")
                                                capture.capture_metadata["supabase_export_error"] = str(e)
                                                
                                        else:
                                            logger.error(f"No recognition data found for session {capture_id}")
                                            capture.capture_metadata["export_error"] = "No recognition data found"
                                            
                                    except Exception as export_error:
                                        logger.error(f"Error in Supabase export for session {capture_id}: {str(export_error)}")
                                        import traceback
                                        logger.error(f"Export traceback: {traceback.format_exc()}")
                                        capture.capture_metadata["supabase_export_error"] = str(export_error)
                                        
                                else:
                                    logger.error(f"Recognition timed out or failed for session {capture_id}")
                                    capture.capture_metadata["recognition_timeout"] = True
                                    
                            else:
                                logger.error(f"Failed to start recognition: {recognition_result.get('error', 'Unknown error')}")
                                capture.capture_metadata["recognition_error"] = recognition_result.get('error', 'Unknown error')
                                
                        except Exception as e:
                            logger.error(f"Error starting unified recognition: {str(e)}")
                            import traceback
                            logger.error(f"Recognition error traceback: {traceback.format_exc()}")
                            capture.capture_metadata["recognition_error"] = str(e)
                    else:
                        logger.error("No video segments found - recognition will not be possible")
                        capture.status = "failed"
                        capture.error_message = "No video segments found for recognition"
                        
                        # Concatenate audio segments if there are multiple (for completeness)
                        if len(audio_segment_paths) > 1:
                            try:
                                concat_audio_path = sequential_processor.concatenate_segments(
                                    segment_paths=audio_segment_paths,
                                    output_path=f"{media_dir}/{capture_id}_concatenated.mp3",
                                    is_audio=True
                                )
                                
                                # Update capture with concatenated audio path
                                capture.capture_metadata["concatenated_audio_path"] = concat_audio_path
                                logger.info(f"Successfully concatenated {len(audio_segment_paths)} audio segments")
                            except Exception as e:
                                logger.error(f"Error concatenating audio segments: {str(e)}")
                                capture.capture_metadata["audio_concatenation_error"] = str(e)
                    
                    logger.info(f"Completed sequential processing for session {capture_id}")
                    logger.info(f"Unified recognition has been triggered on the complete video (matching non-sequential approach)")
                else:
                    # Mark capture as failed
                    capture.status = "failed"
                    capture.error_message = processing_result.get("error", "Unknown error in sequential processing")
                    logger.error(f"Sequential processing failed for session {capture_id}: {capture.error_message}")
                
                # Commit changes to database
                db.commit()
                
            except Exception as e:
                logger.error(f"Error in sequential processing: {str(e)}")
                capture.status = "failed"
                capture.error_message = str(e)
                db.commit()
                return
                
        except Exception as e:
            logger.error(f"Error in Parliament TV sequential processing task: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Ensure any failed transaction is rolled back
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback in outer exception handler: {str(rollback_error)}")
    
    # Start the background task
    background_tasks.add_task(process_parliament_tv_sequential_task)
    
    return {
        "status": "processing",
        "message": "Started Parliament TV sequential processing pipeline",
        "url": url,
        "title": title,
        "description": description,
        "duration": duration,
        "is_live": is_live
    }
