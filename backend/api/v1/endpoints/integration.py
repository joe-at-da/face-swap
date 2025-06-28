"""
Integration endpoints for external systems like Supabase.

These endpoints provide secure access to Parliament TV data for external systems.
"""

from fastapi import APIRouter, Depends, HTTPException, Security, Query, Path
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import os
import logging
import json
from datetime import datetime

from backend.db.session import get_db
from backend.db.models import CaptureSession, RecognitionProcess, ParliamentTranscription
from backend.core.security import get_api_key
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recognition/{video_id}", dependencies=[Security(get_api_key)])
def get_recognition_results(
    video_id: int = Path(..., description="ID of the video to get recognition results for"),
    db: Session = Depends(get_db)
):
    """
    Get recognition results for integration with external systems like Supabase.
    
    This endpoint provides access to the recognition results for a specific video,
    including speaker identification data and timestamps.
    
    Authentication is required via API key.
    """
    logger.info(f"Integration API: Getting recognition results for video ID {video_id}")
    
    # Find the recognition process for this video
    process = db.query(RecognitionProcess).filter(
        RecognitionProcess.video_id == video_id
    ).first()
    
    if not process:
        logger.warning(f"Integration API: Recognition process not found for video ID {video_id}")
        raise HTTPException(status_code=404, detail="Recognition process not found")
    
    # Get the capture session for additional metadata
    capture = db.query(CaptureSession).filter(
        CaptureSession.id == video_id
    ).first()
    
    if not capture:
        logger.warning(f"Integration API: Capture session not found for video ID {video_id}")
        raise HTTPException(status_code=404, detail="Capture session not found")
    
    # Get transcription data if available
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    # Load transcription data from file if available
    transcription_data = None
    
    # First try to load from the output_file if it exists
    if transcription and transcription.output_file and os.path.exists(transcription.output_file):
        try:
            with open(transcription.output_file, 'r') as f:
                transcription_data = json.load(f)
            logger.info(f"Loaded transcription data from {transcription.output_file}")
        except Exception as e:
            logger.error(f"Error loading transcription file: {str(e)}")
    
    # If we couldn't load from file, try to get it from the recognition_results
    if not transcription_data and capture.recognition_results:
        try:
            recognition_results = json.loads(capture.recognition_results)
            
            # Check for transcript in different possible locations in the recognition_results
            transcript_text = None
            
            # Option 1: Direct transcript_text field
            if "transcript_text" in recognition_results:
                transcript_text = recognition_results.get("transcript_text")
                logger.info("Found transcript_text in recognition_results")
                
            # Option 2: In the transcription field
            elif "transcription" in recognition_results and recognition_results["transcription"]:
                transcription_info = recognition_results["transcription"]
                if isinstance(transcription_info, dict) and "transcript" in transcription_info:
                    transcript_text = transcription_info.get("transcript")
                    logger.info("Found transcript in recognition_results.transcription")
                    
            # Option 3: In the results_summary field
            elif "results_summary" in recognition_results and recognition_results["results_summary"]:
                results_summary = recognition_results["results_summary"]
                if isinstance(results_summary, dict) and "transcript_text" in results_summary:
                    transcript_text = results_summary.get("transcript_text")
                    logger.info("Found transcript_text in recognition_results.results_summary")
            
            # Create transcription data if we found a transcript
            if transcript_text and transcript_text != "No transcript available." and \
               transcript_text != "No transcript available due to processing error.":
                # Create a simple transcription data structure
                transcription_data = {
                    "video_id": video_id,
                    "language": "en",
                    "transcript": transcript_text,
                    "segments": [
                        {
                            "start": 0,
                            "end": capture.duration if capture.duration else 60,
                            "text": transcript_text
                        }
                    ]
                }
                logger.info(f"Created transcription data from recognition_results with transcript length: {len(transcript_text)}")
        except Exception as e:
            logger.error(f"Error parsing recognition_results: {str(e)}")
            
    # If we still don't have transcription data but we have an audio file, try to create it
    if not transcription_data and capture.audio_path and os.path.exists(capture.audio_path):
        try:
            # Create a simple transcription data structure with a placeholder
            # This ensures the frontend knows transcription is available but needs to be processed
            transcription_data = {
                "video_id": video_id,
                "language": "en",
                "transcript": "Audio available for transcription. Please run the transcription process.",
                "segments": []
            }
            logger.info(f"Created placeholder transcription data because audio file exists")
        except Exception as e:
            logger.error(f"Error creating placeholder transcription data: {str(e)}")
    
    # Generate a combined timeline from recognition and transcription data
    timeline_data = []
    
    # Try to get recognition results from the process or capture session
    recognition_data = None
    if process.results and isinstance(process.results, dict):
        recognition_data = process.results
    elif capture.recognition_results:
        try:
            recognition_data = json.loads(capture.recognition_results)
        except Exception as e:
            logger.error(f"Error parsing recognition_results from capture session: {str(e)}")
    
    # Add speaker recognition events to timeline if available
    if recognition_data:
        # Check different possible structures for speaker data
        speakers_data = []
        
        # Option 1: Direct speakers list
        if "speakers" in recognition_data and isinstance(recognition_data["speakers"], list):
            speakers_data = recognition_data["speakers"]
            logger.info(f"Found {len(speakers_data)} speakers in recognition_data.speakers list")
        
        # Option 2: Nested in results
        elif "results" in recognition_data and isinstance(recognition_data["results"], dict) and "speakers" in recognition_data["results"]:
            speakers_data = recognition_data["results"]["speakers"]
            logger.info(f"Found {len(speakers_data)} speakers in recognition_data.results.speakers")
        
        # Option 3: Speaker identification results
        elif "speaker_identification" in recognition_data and isinstance(recognition_data["speaker_identification"], dict) and "results" in recognition_data["speaker_identification"]:
            speaker_results = recognition_data["speaker_identification"]["results"]
            if isinstance(speaker_results, dict) and "speakers" in speaker_results:
                speakers_data = speaker_results["speakers"]
                logger.info(f"Found {len(speakers_data)} speakers in speaker_identification.results.speakers")
        
        # Process speakers data
        for speaker in speakers_data:
            # Handle different speaker data structures
            appearances = []
            if isinstance(speaker, dict):
                if "appearances" in speaker and isinstance(speaker["appearances"], list):
                    appearances = speaker["appearances"]
                elif "segments" in speaker and isinstance(speaker["segments"], list):
                    appearances = speaker["segments"]
                
                speaker_name = speaker.get("name", "Unknown")
                speaker_id = speaker.get("id", None)
                
                for appearance in appearances:
                    if isinstance(appearance, dict) and "start_time" in appearance and "end_time" in appearance:
                        timeline_data.append({
                            "type": "speaker",
                            "start": appearance.get("start_time"),
                            "end": appearance.get("end_time"),
                            "speaker_name": speaker_name,
                            "speaker_id": speaker_id,
                            "confidence": appearance.get("confidence", 0)
                        })
    
    # Add transcription segments to timeline if available
    if transcription_data and isinstance(transcription_data, dict):
        segments = transcription_data.get("segments", [])
        
        # If we have a transcript but no segments, create a single segment with the full transcript
        if not segments and transcription_data.get("transcript"):
            segments = [{
                "start": 0,
                "end": capture.duration if capture.duration else 60,
                "text": transcription_data.get("transcript")
            }]
        
        for segment in segments:
            if isinstance(segment, dict) and "start" in segment and "end" in segment and "text" in segment:
                timeline_data.append({
                    "type": "transcription",
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "text": segment.get("text"),
                    "language": transcription_data.get("language", "en")
                })
    
    # Sort the timeline by start time
    if timeline_data:
        timeline_data.sort(key=lambda x: x.get("start", 0))
        logger.info(f"Generated combined timeline with {len(timeline_data)} events")
    else:
        # Create a minimal timeline with the placeholder transcription if we have it
        if transcription_data and transcription_data.get("transcript"):
            timeline_data = [{
                "type": "transcription",
                "start": 0,
                "end": capture.duration if capture.duration else 60,
                "text": transcription_data.get("transcript"),
                "language": transcription_data.get("language", "en")
            }]
            logger.info("Created minimal timeline with transcription data")
        else:
            logger.info("No timeline data available")
            timeline_data = None
    
    # Prepare the response with recognition results, transcription, and metadata
    response = {
        "success": True,
        "video_id": video_id,
        "title": capture.title,
        "description": capture.description,
        "capture_date": capture.start_time,
        "duration": capture.duration,
        "status": process.status,
        "results": process.results,
        "audio_url": capture.capture_metadata.get("audio_url", "") if capture.capture_metadata else "",
        "video_url": capture.capture_metadata.get("video_url", "") if capture.capture_metadata else "",
        "combined_av_url": json.loads(process.process_metadata).get("combined_av_url", "") if process.process_metadata and isinstance(process.process_metadata, str) else \
                           process.process_metadata.get("combined_av_url", "") if process.process_metadata else "",
        "transcription": {
            "available": transcription is not None,
            "status": transcription.status if transcription else "not_found",
            "language": transcription.language if transcription else "en",
            "data": transcription_data
        },
        "timeline": timeline_data
    }
    
    # Make the response JSON serializable (handle datetime objects)
    serializable_response = make_json_serializable(response)
    
    return serializable_response


@router.get("/videos", dependencies=[Security(get_api_key)])
def list_videos(
    limit: int = Query(10, description="Maximum number of videos to return"),
    offset: int = Query(0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Filter by recognition status"),
    db: Session = Depends(get_db)
):
    """
    List videos with recognition data for integration with external systems.
    
    This endpoint provides a paginated list of videos with recognition data,
    including metadata and status information.
    
    Authentication is required via API key.
    """
    logger.info(f"Integration API: Listing videos with limit {limit}, offset {offset}")
    
    # Build the query for recognition processes
    query = db.query(RecognitionProcess)
    
    # Apply status filter if provided
    if status:
        query = query.filter(RecognitionProcess.status == status)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    processes = query.offset(offset).limit(limit).all()
    
    # Prepare the response with video list
    videos = []
    for process in processes:
        # Get the capture session for additional metadata
        capture = db.query(CaptureSession).filter(
            CaptureSession.id == process.video_id
        ).first()
        
        if capture:
            video_data = {
                "video_id": process.video_id,
                "title": capture.title,
                "description": capture.description,
                "capture_date": capture.start_time,
                "duration": capture.duration,
                "status": process.status,
                "has_results": process.results is not None,
                "audio_url": capture.capture_metadata.get("audio_url", "") if capture.capture_metadata else "",
                "video_url": capture.capture_metadata.get("video_url", "") if capture.capture_metadata else "",
                "combined_av_url": json.loads(process.process_metadata).get("combined_av_url", "") if process.process_metadata and isinstance(process.process_metadata, str) else \
                                  process.process_metadata.get("combined_av_url", "") if process.process_metadata else ""
            }
            videos.append(video_data)
    
    # Make the response JSON serializable (handle datetime objects)
    serializable_videos = make_json_serializable(videos)
    
    return {
        "success": True,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "videos": serializable_videos
    }
