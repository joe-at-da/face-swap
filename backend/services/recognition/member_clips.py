"""
Enhanced member clips processing for Parliament TV
This module provides functions to create member clips from recognition results,
including support for unidentified speakers.
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import ParliamentTranscription
from backend.services.integration.supabase_client import SupabaseService
from backend.services.utils import make_json_serializable

logger = logging.getLogger(__name__)

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
    5. Handles unidentified speakers by assigning temporary IDs
    
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
    
    # Process recognition events if no identified speakers were found
    if len(speaker_segments) == 0 and "recognition_events" in recognition_results:
        logger.info("No identified speakers found. Processing recognition events to create unidentified speaker segments.")
        
        # Group recognition events by time to create segments
        events = recognition_results["recognition_events"]
        if isinstance(events, list):
            # Sort events by time
            events.sort(key=lambda x: x.get("time", 0))
            
            # Create segments from recognition events
            current_segment = None
            unidentified_count = 0
            
            for event in events:
                event_time = event.get("time", 0)
                event_text = event.get("segment_text", "")
                
                if not current_segment:
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,  # Default 5 second segment
                        "confidence": 0.5,  # Medium confidence for unidentified speakers
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
                elif event_time - current_segment["end_time"] <= 60:  # If within 60 seconds
                    # Extend the current segment
                    current_segment["end_time"] = event_time + 5
                    current_segment["transcript"] += " " + event_text
                    current_segment["events"].append(event)
                else:
                    # Finalize the current segment and start a new one
                    speaker_segments.append({
                        "speaker_id": current_segment["speaker_id"],
                        "speaker_name": current_segment["speaker_name"],
                        "start_time": current_segment["start_time"],
                        "end_time": current_segment["end_time"],
                        "confidence": current_segment["confidence"],
                        "recognition_method": current_segment["recognition_method"],
                        "transcript": current_segment["transcript"].strip()
                    })
                    
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,
                        "confidence": 0.5,
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
            
            # Add the last segment if there is one
            if current_segment:
                speaker_segments.append({
                    "speaker_id": current_segment["speaker_id"],
                    "speaker_name": current_segment["speaker_name"],
                    "start_time": current_segment["start_time"],
                    "end_time": current_segment["end_time"],
                    "confidence": current_segment["confidence"],
                    "recognition_method": current_segment["recognition_method"],
                    "transcript": current_segment["transcript"].strip()
                })
    
    # If still no segments, create a single segment for the entire video
    if len(speaker_segments) == 0:
        logger.info("No speaker segments found. Creating a single segment for the entire video.")
        
        # Get video duration from metadata or default to 60 seconds
        duration = video_metadata.get("duration", 60)
        
        speaker_segments.append({
            "speaker_id": f"unidentified_{video_id}_full",
            "speaker_name": "Unidentified Speaker",
            "start_time": 0,
            "end_time": duration,
            "confidence": 0.3,  # Low confidence
            "recognition_method": "default",
            "transcript": "No transcript available"
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
        
        # Create clip metadata - simplified to match the actual Supabase schema
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
            "full_video_url": full_video_url,
            "session_title": session_info["title"],
            "created_at": datetime.now().isoformat(),
            "is_unidentified": segment["recognition_method"] in ["unidentified", "default"]
        }
        
        member_clips.append(clip_data)
    
    # Save clips to Supabase parliament_member_clips table
    saved_clips = []
    failed_clips = []
    
    for clip in member_clips:
        try:
            # Ensure clip data is serializable and matches the Supabase schema
            try:
                # Create a clean serializable version of the clip
                serializable_clip = {
                    "id": clip.get("id"),
                    "video_id": clip.get("video_id"),
                    "member_id": clip.get("member_id"),
                    "member_name": clip.get("member_name"),
                    "start_time": float(clip.get("start_time", 0)),
                    "end_time": float(clip.get("end_time", 0)),
                    "start_timestamp": clip.get("start_timestamp", ""),
                    "end_timestamp": clip.get("end_timestamp", ""),
                    "duration": float(clip.get("duration", 0)),
                    "transcript": (clip.get("transcript", "") or "")[:1000],  # Truncate long transcripts
                    "full_video_url": clip.get("full_video_url", ""),
                    "session_title": clip.get("session_title", ""),
                    "created_at": datetime.now().isoformat(),
                    "is_unidentified": bool(clip.get("is_unidentified", False))
                }
                
                # Log the clip data we're about to insert
                logger.info(f"Inserting clip for {serializable_clip['member_name']} with ID {serializable_clip['id']}")
                
                # Insert clip into parliament_member_clips table
                response = supabase_service.client.table('parliament_member_clips').insert(serializable_clip).execute()
                
                if response and hasattr(response, 'data') and response.data:
                    saved_clips.append(clip["id"])
                    logger.info(f"Saved clip {clip['id']} for member {clip['member_name']} to Supabase")
                else:
                    failed_clips.append({
                        "clip_id": clip["id"],
                        "error": "No data returned from Supabase"
                    })
                    logger.warning(f"No data returned when saving clip {clip['id']} to Supabase")
            except Exception as e:
                logger.error(f"Error inserting clip {clip.get('id', 'unknown')}: {str(e)}")
                failed_clips.append({
                    "clip_id": clip["id"],
                    "error": str(e)
                })
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
