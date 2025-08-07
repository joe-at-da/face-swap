"""
Parliament TV Sequential Processing API Endpoint

This module provides an endpoint for processing Parliament TV videos sequentially
in 30-minute segments to avoid memory issues with long-running videos.
"""

import logging
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
                capture_metadata=capture_metadata,
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
                    segment_results = processing_result.get("segment_results", [])
                    
                    # Get segment results and set up video path for recognition
                    video_segment_paths = []
                    audio_segment_paths = []
                    
                    # Process each segment individually (like the debug endpoint does)
                    logger.info(f"Processing {len(segment_results)} segments individually...")
                    processed_segments = []
                    
                    for i, segment in enumerate(segment_results):
                        if segment.get("video_path") and segment.get("audio_path"):
                            video_segment_paths.append(segment["video_path"])
                            audio_segment_paths.append(segment["audio_path"])
                            
                            # Process this segment (this is the missing piece!)
                            try:
                                logger.info(f"Processing segment {i+1}/{len(segment_results)}: {segment.get('start_time')}-{segment.get('end_time')}s")
                                
                                segment_title = f"{title} (Segment {i+1})"
                                segment_description = f"Segment {i+1} from {segment.get('start_time', 0)} to {segment.get('end_time', 0)} seconds"
                                
                                # Call process_segment for each segment (matching debug endpoint logic)
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
                        if len(video_segment_paths) > 1:
                            logger.info(f"Processing completed with {len(segment_results)} segments. Starting concatenation...")
                            
                            # Concatenate video segments if there are multiple
                            try:
                                concat_video_path = sequential_processor.concatenate_segments(
                                    segment_paths=video_segment_paths,
                                    output_path=f"{media_dir}/{capture_id}_concatenated.mp4",
                                    media_type="video"
                                )
                                
                                # Update capture with concatenated video path
                                capture.file_path = concat_video_path
                                capture.video_path = concat_video_path  # For recognition pipeline
                                capture.capture_metadata["concatenated_video_path"] = concat_video_path
                                logger.info(f"Successfully concatenated {len(video_segment_paths)} video segments")
                            except Exception as e:
                                logger.error(f"Error concatenating video segments: {str(e)}")
                                capture.capture_metadata["video_concatenation_error"] = str(e)
                                # Fallback to first segment if concatenation fails
                                capture.video_path = video_segment_paths[0]
                                capture.file_path = video_segment_paths[0]
                                logger.info(f"Using first segment as fallback: {video_segment_paths[0]}")
                        else:
                            # Single segment - use it directly
                            capture.video_path = video_segment_paths[0]
                            capture.file_path = video_segment_paths[0]
                            logger.info(f"Single segment processing - using: {video_segment_paths[0]}")
                    else:
                        logger.error("No video segments found - recognition will not be possible")
                        
                        # Concatenate audio segments if there are multiple
                        if len(audio_segment_paths) > 1:
                            try:
                                concat_audio_path = sequential_processor.concatenate_segments(
                                    segment_paths=audio_segment_paths,
                                    output_path=f"{media_dir}/{capture_id}_concatenated.mp3",
                                    media_type="audio"
                                )
                                
                                # Update capture with concatenated audio path
                                capture.capture_metadata["concatenated_audio_path"] = concat_audio_path
                                logger.info(f"Successfully concatenated {len(audio_segment_paths)} audio segments")
                            except Exception as e:
                                logger.error(f"Error concatenating audio segments: {str(e)}")
                                capture.capture_metadata["audio_concatenation_error"] = str(e)
                    
                    # Mark capture as completed
                    capture.status = "completed"
                    logger.info(f"Completed sequential processing for session {capture_id}")
                    
                    # Automatically trigger recognition pipeline after successful segment creation
                    try:
                        logger.info(f"Starting automatic recognition pipeline for session {capture_id}")
                        
                        # Import the recognition function
                        from backend.api.v1.endpoints.recognition_processor import process_recognition_background
                        import asyncio
                        import threading
                        
                        def trigger_recognition_async():
                            """Trigger recognition pipeline in a separate thread"""
                            try:
                                logger.info(f"Recognition thread started for session {capture_id}")
                                
                                # Create new event loop for this thread
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Run the recognition pipeline
                                loop.run_until_complete(process_recognition_background(capture_id, None))
                                
                                # Clean up
                                loop.close()
                                logger.info(f"Recognition pipeline completed successfully for session {capture_id}")
                                
                            except Exception as e:
                                logger.error(f"Error in automatic recognition pipeline for session {capture_id}: {str(e)}")
                                import traceback
                                logger.error(f"Recognition error traceback: {traceback.format_exc()}")
                        
                        # Start recognition in background thread (non-blocking)
                        recognition_thread = threading.Thread(
                            target=trigger_recognition_async,
                            name=f"recognition-{capture_id}",
                            daemon=True
                        )
                        recognition_thread.start()
                        
                        # Update capture metadata to track recognition trigger
                        if not hasattr(capture, 'capture_metadata') or capture.capture_metadata is None:
                            capture.capture_metadata = {}
                        
                        capture.capture_metadata["auto_recognition_triggered"] = True
                        capture.capture_metadata["auto_recognition_started_at"] = datetime.now().isoformat()
                        capture.capture_metadata["recognition_thread_name"] = f"recognition-{capture_id}"
                        
                        logger.info(f"Recognition pipeline triggered successfully for session {capture_id}")
                        
                    except Exception as e:
                        logger.error(f"Error triggering automatic recognition pipeline for session {capture_id}: {str(e)}")
                        import traceback
                        logger.error(f"Recognition trigger error traceback: {traceback.format_exc()}")
                        
                        # Don't fail the whole process if recognition trigger fails
                        if not hasattr(capture, 'capture_metadata') or capture.capture_metadata is None:
                            capture.capture_metadata = {}
                        capture.capture_metadata["auto_recognition_trigger_error"] = str(e)
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
