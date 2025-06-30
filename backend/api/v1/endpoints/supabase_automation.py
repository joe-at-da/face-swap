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
from datetime import datetime
from typing import Dict, Any, Optional, List
from services.utils import make_json_serializable
from fastapi import APIRouter, Depends, HTTPException, Security, status, BackgroundTasks, Body
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.api.deps import get_db, get_api_key
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.integration.supabase_client import SupabaseService
from backend.services.parliament_tv import ParliamentTVCapture
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from sqlalchemy import desc
from backend.db.models import CaptureSession, RecognitionProcess, ParliamentTranscription
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
                
                video_metadata = {
                    "video_id": capture_id,
                    "title": capture.title,
                    "description": capture.description,
                    "duration": capture.duration,
                    "file_path": capture.file_path,
                    "audio_path": os.path.join(os.path.dirname(capture.file_path), f"audio_{capture_id}.mp3"),
                    "video_url": capture_metadata.get("video_url"),
                    "audio_url": capture_metadata.get("audio_url"),
                    "original_url": capture_metadata.get("original_url")
                }
                
                # Export to Supabase
                supabase = SupabaseIntegration()
                
                # Ensure all metadata is properly serializable using the utility function
                # This handles SQLAlchemy MetaData objects, datetime objects, and other non-serializable types
                serializable_recognition_data = make_json_serializable(recognition_data)
                serializable_video_metadata = make_json_serializable(video_metadata)
                
                logger.info(f"Exporting recognition results to Supabase for session {capture_id}")
                export_result = supabase.export_and_upload_recognition(
                    video_path=capture.file_path,
                    recognition_results=serializable_recognition_data,
                    video_metadata=serializable_video_metadata,
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
                    # Handle process_metadata properly - it might be a string, dict, or other type
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
                            video_path = metadata["combined_av_path"]
                            logger.info(f"Using combined AV path from metadata: {video_path}")
                    except Exception as e:
                        logger.error(f"Error processing metadata for combined AV path: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
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
                    
                    # Step 7: Process and save individual member clips to parliament_member_clips table
                    try:
                        # Get the public URL for the full video
                        full_video_url = upload_result.get("public_url")
                        
                        # Process and save member clips
                        save_result = save_member_clips_to_supabase(
                            db=db,
                            video_id=capture_id,
                            full_video_url=full_video_url,
                            recognition_results=recognition_data,
                            video_metadata=video_metadata,
                            supabase_service=supabase_service
                        )
                        
                        logger.info(f"Saved {save_result.get('clip_count', 0)} member clips to Supabase for session {capture_id}")
                    except Exception as e:
                        logger.error(f"Error saving member clips to Supabase: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
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


def save_member_clips_to_supabase(
    db: Session,
    video_id: int,
    full_video_url: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    supabase_service: SupabaseService
) -> Dict[str, Any]:
    """
    Process recognition results and save individual member clips to the Supabase parliament_member_clips table.
    
    This function:
    1. Processes recognition results to identify speaker segments
    2. Merges segments by the same speaker if they are close together (less than 60 seconds apart)
    3. Creates detailed clip metadata including timestamps, transcript segments, and confidence scores
    4. Saves clips to the Supabase parliament_member_clips table
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        full_video_url: URL to the full video in Supabase storage
        recognition_results: Recognition results from facial and voice recognition
        video_metadata: Metadata about the video
        supabase_service: Initialized Supabase service with appropriate permissions
        
    Returns:
        Dictionary with results of the clip saving process
    """
    logger.info(f"Processing member clips for video ID: {video_id}")
    
    # Get session information from metadata
    session_info = {
        "title": video_metadata.get("title", f"Parliament TV Session {video_id}"),
        "date": video_metadata.get("capture_date", datetime.now().isoformat()),
        "description": video_metadata.get("description", ""),
        "original_url": video_metadata.get("original_url", "")
    }
    
    # Get transcription data if available
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    transcript_data = None
    if transcription and transcription.output_file and os.path.exists(transcription.output_file):
        try:
            with open(transcription.output_file, 'r') as f:
                transcript_data = json.load(f)
            logger.info(f"Loaded transcription data from {transcription.output_file}")
        except Exception as e:
            logger.error(f"Error loading transcription file: {str(e)}")
    
    # Extract speaker segments from recognition results
    speaker_segments = []
    
    # Process identified speakers from facial recognition
    if "identified_speakers" in recognition_results:
        for speaker in recognition_results["identified_speakers"]:
            speaker_id = speaker.get("mp_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id or not speaker_name:
                continue
                
            for segment in speaker.get("segments", []):
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "facial",
                    "transcript": ""
                })
    
    # Process speaker segments from voice recognition if available
    if transcript_data and "speakers" in transcript_data:
        for speaker in transcript_data["speakers"]:
            speaker_id = speaker.get("profile_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id:
                continue
                
            for segment in speaker.get("segments", []):
                # Find corresponding transcript text
                transcript_text = ""
                if "segments" in transcript_data:
                    for transcript_segment in transcript_data["segments"]:
                        if (transcript_segment["start"] >= segment["start_time"] and 
                            transcript_segment["end"] <= segment["end_time"]):
                            transcript_text += " " + transcript_segment["text"]
                
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name or "Unknown Speaker",
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "voice",
                    "transcript": transcript_text.strip()
                })
    
    # Sort segments by start time
    speaker_segments.sort(key=lambda x: x["start_time"])
    
    # Merge segments by the same speaker if they are close together (less than 60 seconds apart)
    MAX_GAP_SECONDS = 60
    merged_segments = []
    
    current_segment = None
    for segment in speaker_segments:
        if current_segment is None:
            current_segment = segment.copy()
            continue
            
        # If same speaker and gap is small enough, merge segments
        if (segment["speaker_id"] == current_segment["speaker_id"] and 
            segment["start_time"] - current_segment["end_time"] <= MAX_GAP_SECONDS):
            
            # Merge transcripts if available
            if segment["transcript"] and current_segment["transcript"]:
                current_segment["transcript"] += " " + segment["transcript"]
            elif segment["transcript"]:
                current_segment["transcript"] = segment["transcript"]
                
            # Update end time and confidence (use max confidence)
            current_segment["end_time"] = segment["end_time"]
            current_segment["confidence"] = max(current_segment["confidence"], segment["confidence"])
        else:
            # Different speaker or gap too large, add current segment and start a new one
            merged_segments.append(current_segment)
            current_segment = segment.copy()
    
    # Add the last segment if there is one
    if current_segment is not None:
        merged_segments.append(current_segment)
    
    # Create clips for Supabase parliament_member_clips table
    member_clips = []
    for segment in merged_segments:
        # Generate a unique clip ID
        clip_id = str(uuid.uuid4())
        
        # Calculate duration
        duration = segment["end_time"] - segment["start_time"]
        
        # Format timestamps as HH:MM:SS
        def format_timestamp(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
        start_timestamp = format_timestamp(segment["start_time"])
        end_timestamp = format_timestamp(segment["end_time"])
        
        # Create clip metadata
        clip_data = {
            "id": clip_id,
            "video_id": str(video_id),
            "member_id": segment["speaker_id"],
            "member_name": segment["speaker_name"],
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "duration": duration,
            "transcript": segment["transcript"],
            "confidence": segment["confidence"],
            "recognition_method": segment["recognition_method"],
            "full_video_url": full_video_url,
            "session_title": session_info["title"],
            "session_date": session_info["date"],
            "session_description": session_info["description"],
            "original_url": session_info["original_url"],
            "created_at": datetime.now().isoformat(),
            "status": "processed"
        }
        
        member_clips.append(clip_data)
    
    # Save clips to Supabase parliament_member_clips table
    saved_clips = []
    failed_clips = []
    
    for clip in member_clips:
        try:
            # Ensure clip data is serializable before inserting
            # Use the make_json_serializable utility function to handle all non-serializable types
            serializable_clip = make_json_serializable(clip)
                    
            # Insert clip into parliament_member_clips table
            response = supabase_service.client.table('parliament_member_clips').insert(serializable_clip).execute()
            
            if response.data:
                saved_clips.append(clip["id"])
                logger.info(f"Saved clip {clip['id']} for member {clip['member_name']} to Supabase")
            else:
                failed_clips.append({
                    "clip_id": clip["id"],
                    "error": "No data returned from Supabase"
                })
                logger.warning(f"No data returned when saving clip {clip['id']} to Supabase")
        except Exception as e:
            failed_clips.append({
                "clip_id": clip["id"],
                "error": str(e)
            })
            logger.error(f"Error saving clip {clip['id']} to Supabase: {str(e)}")
    
    return {
        "success": True,
        "video_id": video_id,
        "clip_count": len(saved_clips),
        "saved_clips": saved_clips,
        "failed_clips": failed_clips
    }
