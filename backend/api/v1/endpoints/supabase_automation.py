"""
Supabase Automation API Endpoints

This module provides endpoints for automating the Parliament TV capture, recognition,
and Supabase export workflow in a single unified process.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Security, status, BackgroundTasks, Body
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.api.deps import get_db, get_api_key
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.integration.supabase_client import SupabaseService
from backend.services.parliament_tv import ParliamentTVCapture
from backend.services.recognition.recognition_service import RecognitionService
from backend.db.models import CaptureSession, RecognitionProcess
from backend.services.utils import make_json_serializable

logger = logging.getLogger(__name__)

router = APIRouter()
parliament_tv_service = ParliamentTVCapture()


@router.post("/process-parliament-tv", response_model=Dict[str, Any], dependencies=[Security(get_api_key)])
async def process_parliament_tv_to_supabase(
    background_tasks: BackgroundTasks,
    url: str = Body(..., description="Parliament TV URL to process"),
    title: str = Body(..., description="Title for the capture session"),
    description: str = Body(None, description="Description for the capture session"),
    duration: int = Body(7200, description="Duration to capture in seconds (default: 2 hours)"),
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
        
    Returns:
        Status information about the initiated process
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase integration is not enabled"
        )
    
    logger.info(f"Starting unified Parliament TV processing for URL: {url}")
    
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
        try:
            # Step 2: Create capture session
            capture_metadata = {
                "video_url": video_url,
                "audio_url": audio_url,
                "original_url": url,
                "time_marker": stream_info.get("time_marker", {"seconds": 0})
            }
            
            # Create capture session in database
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
                recognition_service = RecognitionService(db)
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
                    # Check recognition status
                    status = recognition_service.get_recognition_status(capture_id)
                    
                    if status.get("status") == "completed":
                        recognition_completed = True
                        break
                    elif status.get("status") == "failed":
                        logger.error(f"Recognition failed: {status.get('error_message', 'Unknown error')}")
                        return
                    
                    # Wait before checking again
                    time.sleep(60)
                
                if not recognition_completed:
                    logger.error(f"Recognition timed out after {max_wait_time} seconds")
                    return
                
                logger.info(f"Recognition completed for session {capture_id}")
                
                # Step 5: Export to Supabase
                # Get recognition results
                recognition_data = recognition_service.get_recognition_results(capture_id)
                
                if not recognition_data:
                    logger.error(f"No recognition data found for session {capture_id}")
                    return
                
                # Get video metadata
                db.refresh(capture)
                video_metadata = {
                    "video_id": capture_id,
                    "title": capture.title,
                    "description": capture.description,
                    "duration": capture.duration,
                    "file_path": capture.file_path,
                    "audio_path": os.path.join(os.path.dirname(capture.file_path), f"audio_{capture_id}.mp3"),
                    "video_url": capture.capture_metadata.get("video_url"),
                    "audio_url": capture.capture_metadata.get("audio_url"),
                    "original_url": capture.capture_metadata.get("original_url")
                }
                
                # Export to Supabase
                supabase = SupabaseIntegration()
                export_result = supabase.export_and_upload_recognition(
                    video_path=capture.file_path,
                    recognition_results=recognition_data,
                    video_metadata=video_metadata,
                    db_session=db,
                    video_id=capture_id,
                    upload_media=True
                )
                
                logger.info(f"Exported recognition results to Supabase for session {capture_id}")
                
                # Step 6: Upload full video to Supabase using service role key
                supabase_service = SupabaseService(use_service_role=True)
                
                # Use the combined AV file if available, otherwise use the original video file
                video_path = capture.file_path
                process = db.query(RecognitionProcess).filter(RecognitionProcess.video_id == capture_id).first()
                
                if process and process.process_metadata:
                    import json
                    if isinstance(process.process_metadata, str):
                        try:
                            metadata = json.loads(process.process_metadata)
                            if "combined_av_path" in metadata:
                                video_path = metadata["combined_av_path"]
                        except:
                            pass
                    elif isinstance(process.process_metadata, dict) and "combined_av_path" in process.process_metadata:
                        video_path = process.process_metadata["combined_av_path"]
                
                # Upload the full video
                destination_path = f"full_videos/parliament_tv_{capture_id}.mp4"
                upload_result = supabase_service.upload_full_video(video_path, destination_path)
                
                if upload_result.get("success", False):
                    logger.info(f"Uploaded full video to Supabase: {upload_result.get('public_url')}")
                    
                    # Update capture with Supabase URL
                    capture.external_url = upload_result.get("public_url")
                    capture.external_id = f"parliament_tv_{capture_id}"
                    capture.external_status = "uploaded"
                    db.commit()
                else:
                    logger.error(f"Failed to upload full video: {upload_result.get('error', 'Unknown error')}")
                
                logger.info(f"Completed full processing pipeline for Parliament TV URL: {url}")
                
            except Exception as e:
                logger.error(f"Error in capture process: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Update capture status
                capture.status = "failed"
                capture.error_message = str(e)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error in Parliament TV processing task: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
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
