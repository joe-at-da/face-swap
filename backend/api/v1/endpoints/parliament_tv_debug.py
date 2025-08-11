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
    
    # Check if files exist, and if not, try to find them using naming convention
    video_path = capture.file_path or capture.video_path
    audio_path = capture.audio_path or capture.capture_metadata.get("audio_path")
    
    media_dir = settings.MEDIA_STORAGE_PATH
    
    # If video_path is not set, try to find it using naming convention
    if not video_path:
        # Look for video file with pattern parliament_tv_{session_id}_*.mp4
        # Exclude segment files (which contain "debug_" in their name)
        possible_video_files = [f for f in os.listdir(media_dir) 
                               if f.startswith(f"parliament_tv_{session_id}_") 
                               and f.endswith(".mp4") 
                               and "debug_" not in f]
        
        if possible_video_files:
            # Sort by file size (largest first) to prefer complete downloads
            video_files_with_size = [(f, os.path.getsize(os.path.join(media_dir, f))) for f in possible_video_files]
            video_files_with_size.sort(key=lambda x: x[1], reverse=True)
            
            selected_video_file = video_files_with_size[0][0]
            video_path = os.path.join(media_dir, selected_video_file)
            logger.info(f"Found video file using naming convention: {video_path} ({video_files_with_size[0][1]/1024/1024:.1f} MB)")
            
            if len(video_files_with_size) > 1:
                logger.info(f"Multiple video files found, selected largest: {selected_video_file}")
    
    # If audio_path is not set, try to find it using naming convention
    if not audio_path:
        # Look for audio file with pattern audio_{session_id}_*.mp3
        # Exclude segment files (which contain "debug_" in their name)
        possible_audio_files = [f for f in os.listdir(media_dir) 
                               if f.startswith(f"audio_{session_id}_") 
                               and f.endswith(".mp3") 
                               and "debug_" not in f]
        
        if possible_audio_files:
            # Sort by file size (largest first) to prefer complete downloads
            audio_files_with_size = [(f, os.path.getsize(os.path.join(media_dir, f))) for f in possible_audio_files]
            audio_files_with_size.sort(key=lambda x: x[1], reverse=True)
            
            selected_audio_file = audio_files_with_size[0][0]
            audio_path = os.path.join(media_dir, selected_audio_file)
            logger.info(f"Found audio file using naming convention: {audio_path} ({audio_files_with_size[0][1]/1024/1024:.1f} MB)")
            
            if len(audio_files_with_size) > 1:
                logger.info(f"Multiple audio files found, selected largest: {selected_audio_file}")
    
    # If files don't exist but we have stream URLs in metadata, download them
    files_missing = (not video_path or not os.path.exists(video_path)) or (not audio_path or not os.path.exists(audio_path))
    
    if files_missing:
        # Check if we have stream URLs in metadata to download
        video_url = capture.capture_metadata.get("video_url")
        audio_url = capture.capture_metadata.get("audio_url")
        
        if not video_url or not audio_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} has no existing files and no stream URLs in metadata for download"
            )
        
        logger.info(f"Files missing for session {session_id}, but stream URLs available. Downloading...")
        
        # Download the files using the sequential processor
        try:
            # Set up expected file paths
            media_dir = settings.MEDIA_STORAGE_PATH
            video_path = os.path.join(media_dir, f"parliament_tv_{session_id}.mp4")
            audio_path = os.path.join(media_dir, f"parliament_tv_{session_id}.mp3")
            wav_path = os.path.join(media_dir, f"parliament_tv_{session_id}.wav")
            
            # Download the files using the sequential processor
            download_result = sequential_processor.download_full_video(
                video_url, audio_url, media_dir, session_id
            )
            
            # The download_full_video method returns paths, update our variables
            if download_result and download_result.get("success"):
                video_path = download_result.get("video_path")
                audio_path = download_result.get("audio_path")
                wav_path = download_result.get("wav_path")
            
            # Update the database with the file paths
            capture.video_path = video_path
            capture.audio_path = audio_path
            capture.file_path = video_path  # Legacy field
            
            # Update metadata with local file paths
            if capture.capture_metadata:
                capture.capture_metadata["video_path"] = video_path
                capture.capture_metadata["audio_path"] = audio_path
                capture.capture_metadata["wav_path"] = wav_path
            
            db.commit()
            db.refresh(capture)
            
            logger.info(f"Successfully downloaded files for session {session_id}")
            logger.info(f"  Video: {video_path}")
            logger.info(f"  Audio: {audio_path}")
            
        except Exception as e:
            logger.error(f"Failed to download files for session {session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download files for session {session_id}: {str(e)}"
            )
    
    # Final check that files exist
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found for session {session_id}"
        )
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found for session {session_id}"
        )
    
    # Create a background task for segment processing
    def process_segment_task():
        try:
            # Get metadata from capture session
            original_url = capture.capture_metadata.get("original_url", "")
            video_url = capture.capture_metadata.get("video_url", "")
            audio_url = capture.capture_metadata.get("audio_url", "")
            
            # Determine which sequential segment contains this time range
            # Sequential segments are 30 minutes (1800 seconds) each
            segment_index = (start_time // 1800) + 1
            
            # Look for existing sequential segment files
            media_dir = settings.MEDIA_STORAGE_PATH
            segment_video_path = os.path.join(media_dir, f"{session_id}_{segment_index}.mp4")
            segment_audio_path = os.path.join(media_dir, f"{session_id}_{segment_index}.mp3")
            segment_wav_path = os.path.join(media_dir, f"{session_id}_{segment_index}.wav")
            
            logger.info(f"Using sequential segment {segment_index} for time range {start_time}-{end_time}s")
            logger.info(f"  Segment video: {segment_video_path}")
            logger.info(f"  Segment audio: {segment_audio_path}")
            
            # Check if segment files exist
            if not os.path.exists(segment_video_path):
                logger.error(f"Sequential segment video file not found: {segment_video_path}")
                # Fallback: extract from original full files
                logger.info("Falling back to extracting from original full files")
                
                temp_dir = os.path.join(media_dir, f"debug_segments_{session_id}")
                os.makedirs(temp_dir, exist_ok=True)
                
                segment_id = f"debug_{session_id}_{start_time}_{end_time}"
                if segment_label:
                    segment_id += f"_{segment_label.replace(' ', '_')}"
                
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
                        "error": "Segment extraction failed and no existing segment files found"
                    }
                
                segment_video_path = segment_result.get("video_path")
                segment_audio_path = segment_result.get("audio_path")
            else:
                logger.info(f"Found existing sequential segment files")
                logger.info(f"  Video: {segment_video_path} ({os.path.getsize(segment_video_path)/1024/1024:.1f} MB)")
                logger.info(f"  Audio: {segment_audio_path} ({os.path.getsize(segment_audio_path)/1024/1024:.1f} MB)")
            
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
                
                # Trigger recognition pipeline for this segment (using segment files, not full video)
                try:
                    logger.info(f"Starting recognition pipeline for debug segment {start_time}-{end_time}s")
                    logger.info(f"Using segment files: video={segment_video_path}, audio={segment_audio_path}")
                    
                    # Import the recognition function
                    from backend.api.v1.endpoints.recognition_processor import process_recognition_background
                    from backend.db.session import get_db
                    from backend.db.models.capture import CaptureSession
                    import asyncio
                    import threading
                    
                    def trigger_recognition_async():
                        """Trigger recognition pipeline for the debug segment using segment files"""
                        try:
                            logger.info(f"Recognition thread started for debug segment {start_time}-{end_time}s")
                            
                            # Temporarily update the capture session to use segment files for recognition
                            db = next(get_db())
                            capture = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
                            if capture:
                                # Store original paths
                                original_video_path = capture.video_path
                                original_file_path = capture.file_path
                                original_audio_path = capture.audio_path
                                
                                # Temporarily set to segment files
                                capture.video_path = segment_video_path
                                capture.file_path = segment_video_path
                                capture.audio_path = segment_audio_path  # Set audio path for multimodal service
                                db.commit()
                                
                                logger.info(f"Temporarily updated capture {session_id} to use segment files for recognition")
                                
                                try:
                                    # Create new event loop for this thread
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    # Run the recognition pipeline on the segment
                                    loop.run_until_complete(process_recognition_background(session_id, None))
                                    
                                    # Clean up
                                    loop.close()
                                    logger.info(f"Recognition pipeline completed successfully for debug segment")
                                    
                                finally:
                                    # Restore original paths
                                    capture.video_path = original_video_path
                                    capture.file_path = original_file_path
                                    capture.audio_path = original_audio_path
                                    db.commit()
                                    db.close()
                                    logger.info(f"Restored original paths for capture {session_id}")
                            else:
                                logger.error(f"Could not find capture session {session_id}")
                                
                        except Exception as e:
                            logger.error(f"Error in debug recognition pipeline: {str(e)}")
                            import traceback
                            logger.error(f"Debug recognition error traceback: {traceback.format_exc()}")
                    
                    # Start recognition in background thread (non-blocking)
                    recognition_thread = threading.Thread(
                        target=trigger_recognition_async,
                        name=f"debug-recognition-{session_id}-{start_time}",
                        daemon=True
                    )
                    recognition_thread.start()
                    
                    logger.info(f"Recognition pipeline triggered for debug segment {start_time}-{end_time}s using segment files")
                    
                except Exception as e:
                    logger.error(f"Error triggering recognition for debug segment: {str(e)}")
                    import traceback
                    logger.error(f"Debug recognition trigger error: {traceback.format_exc()}")
                
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
