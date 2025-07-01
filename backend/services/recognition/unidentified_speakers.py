"""
Module for handling unidentified speakers in Parliament TV recognition
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

logger = logging.getLogger(__name__)

def save_unidentified_clips_to_supabase(
    db: Session,
    video_id: int,
    full_video_url: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    supabase_service: SupabaseService
) -> Dict[str, Any]:
    """
    Process recognition results and save clips for unidentified speakers.
    
    This function:
    1. Extracts segments from recognition results where the speaker is not identified
    2. Creates temporary clips for these segments
    3. Saves metadata about these unidentified clips for later matching
    
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
    logger.info(f"Processing unidentified speaker clips for video ID: {video_id}")
    
    # Get session information from metadata
    session_info = {
        "title": video_metadata.get("title", f"Parliament TV Session {video_id}"),
        "date": video_metadata.get("capture_date", datetime.now().date().isoformat()),
        "description": video_metadata.get("description", ""),
        "original_url": video_metadata.get("original_url", ""),
        "house": determine_house_from_metadata(video_metadata)
    }
    
    # Initialize variables for tracking results
    saved_clips = []
    failed_clips = []
    unidentified_segments = []
    
    # Extract unidentified speaker segments from recognition results
    if recognition_results and isinstance(recognition_results, dict):
        if "timeline" in recognition_results and recognition_results["timeline"]:
            timeline = recognition_results["timeline"]
            
            # Extract segments where speaker is not identified
            for segment in timeline:
                if "speaker_id" not in segment or not segment.get("speaker_id"):
                    # This is an unidentified speaker segment
                    unidentified_segments.append({
                        "start_time": segment.get("start_time", 0),
                        "end_time": segment.get("end_time", 0),
                        "transcript": segment.get("transcript", ""),
                        "confidence": segment.get("confidence", 0.5),
                        "face_data": segment.get("face_data", {}),
                        "voice_data": segment.get("voice_data", {})
                    })
    
    # If no unidentified segments found, create a single segment for the entire video
    if not unidentified_segments:
        logger.info("No specific unidentified segments found. Creating a single segment for the entire video.")
        duration = video_metadata.get("duration", 60)
        
        unidentified_segments = [{
            "start_time": 0,
            "end_time": duration,
            "transcript": "No transcript available",
            "confidence": 0.5,
            "face_data": {},
            "voice_data": {}
        }]
    
    # Format timestamps as HH:MM:SS
    def format_timestamp(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    
    # Save metadata about unidentified segments for later matching
    unidentified_metadata = {
        "video_id": video_id,
        "full_video_url": full_video_url,
        "session_info": session_info,
        "segments": []
    }
    
    # Process each unidentified segment
    for i, segment in enumerate(unidentified_segments):
        try:
            # Generate a unique clip ID
            clip_id = str(uuid.uuid4())
            
            # Calculate duration
            duration = segment["end_time"] - segment["start_time"]
            
            # Format timestamps
            start_timestamp = format_timestamp(segment["start_time"])
            end_timestamp = format_timestamp(segment["end_time"])
            
            # Add segment to metadata
            unidentified_metadata["segments"].append({
                "clip_id": clip_id,
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration": duration,
                "transcript": segment["transcript"],
                "face_data": segment["face_data"],
                "voice_data": segment["voice_data"]
            })
        except Exception as e:
            logger.error(f"Error processing unidentified segment {i}: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Save this information to a local file for later processing
        try:
            # Create directory if it doesn't exist
            unidentified_dir = "/app/data/temp/unidentified_speakers"
            os.makedirs(unidentified_dir, exist_ok=True)
            
            # Save metadata to file
            metadata_file = os.path.join(unidentified_dir, f"unidentified_{video_id}.json")
            with open(metadata_file, "w") as f:
                json.dump(unidentified_metadata, f, indent=2)
            
            logger.info(f"Saved unidentified speaker metadata to {metadata_file}")
        except Exception as e:
            logger.error(f"Error saving unidentified speaker metadata: {str(e)}")
    
    # Return results
    return {
        "success": True,
        "video_id": video_id,
        "unidentified_segment_count": len(unidentified_segments),
        "metadata_file": f"unidentified_{video_id}.json"
    }

def determine_house_from_metadata(metadata: Dict[str, Any]) -> str:
    """
    Determine which house (Commons or Lords) the video is from based on metadata.
    
    Args:
        metadata: Video metadata
        
    Returns:
        String indicating "commons", "lords", or "unknown"
    """
    # Check the title, description, and original URL for clues
    title = metadata.get("title", "").lower()
    description = metadata.get("description", "").lower()
    url = metadata.get("original_url", "").lower()
    
    if any(term in title for term in ["commons", "house of commons"]) or \
       any(term in description for term in ["commons", "house of commons"]) or \
       "commons" in url:
        return "commons"
    
    if any(term in title for term in ["lords", "house of lords"]) or \
       any(term in description for term in ["lords", "house of lords"]) or \
       "lords" in url:
        return "lords"
    
    # Default to unknown
    return "unknown"

def match_unidentified_speakers(
    db: Session,
    video_id: int,
    supabase_service: SupabaseService
) -> Dict[str, Any]:
    """
    Match previously saved unidentified speakers to actual parliament members.
    
    This function:
    1. Loads unidentified speaker metadata for a video
    2. For each segment, attempts to match the speaker to a parliament member
    3. Creates clips in the parliament_member_clips table for matched speakers
    
    Args:
        db: Database session
        video_id: ID of the video to process
        supabase_service: Initialized Supabase service
        
    Returns:
        Dictionary with results of the matching process
    """
    logger.info(f"Matching unidentified speakers for video ID: {video_id}")
    
    # Load unidentified speaker metadata
    metadata_file = f"/app/data/temp/unidentified_speakers/unidentified_{video_id}.json"
    
    if not os.path.exists(metadata_file):
        logger.error(f"Unidentified speaker metadata file not found: {metadata_file}")
        return {
            "success": False,
            "error": "Metadata file not found"
        }
    
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"Error loading unidentified speaker metadata: {str(e)}")
        return {
            "success": False,
            "error": f"Error loading metadata: {str(e)}"
        }
    
    # Get the house from session info
    house = metadata.get("session_info", {}).get("house", "unknown")
    
    # Initialize results
    matched_clips = []
    failed_matches = []
    
    # Process each segment
    for segment in metadata.get("segments", []):
        # TODO: Implement actual matching logic here
        # For now, we'll just log that we would match this segment
        logger.info(f"Would match segment {segment['clip_id']} from {segment['start_timestamp']} to {segment['end_timestamp']}")
        
        # In a real implementation, we would:
        # 1. Use the face_data and voice_data to find the best matching parliament member
        # 2. Filter by house (commons or lords) if known
        # 3. Create a clip in the parliament_member_clips table for the matched member
        
        # For now, just add to failed matches
        failed_matches.append({
            "clip_id": segment["clip_id"],
            "reason": "Matching not yet implemented"
        })
    
    # Return results
    return {
        "success": True,
        "video_id": video_id,
        "matched_count": len(matched_clips),
        "failed_count": len(failed_matches),
        "matched_clips": matched_clips,
        "failed_matches": failed_matches
    }

# Import traceback for better error reporting
import traceback

def integrate_with_member_clips(
    db: Session,
    video_id: int,
    full_video_url: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    supabase_service: SupabaseService
) -> Dict[str, Any]:
    """
    Integrated function to save both identified and unidentified speaker clips.
    
    This function:
    1. Processes recognition results to identify speaker segments
    2. Saves clips for identified speakers directly to parliament_member_clips
    3. Saves metadata for unidentified speakers for later matching
    
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
    logger.info(f"Processing all speaker clips for video ID: {video_id}")
    
    # Helper function to format timestamp
    def format_timestamp(seconds):
        try:
            seconds = float(seconds)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        except (ValueError, TypeError):
            logger.error(f"Invalid timestamp value: {seconds}")
            return "00:00:00"
    
    # Get session information from metadata
    session_info = {
        "title": video_metadata.get("title", f"Parliament TV Session {video_id}"),
        "date": video_metadata.get("capture_date", datetime.now().date().isoformat()),
        "description": video_metadata.get("description", ""),
        "original_url": video_metadata.get("original_url", "")
    }
    
    # Initialize variables for tracking results
    identified_clips = []
    unidentified_segments = []
    
    # Helper function to parse timeline entries which may be in different formats
    def parse_segment(segment):
        # Check if segment is a string (some implementations might have string entries)
        if isinstance(segment, str):
            try:
                # Try to parse as JSON
                segment_data = json.loads(segment)
                return segment_data
            except:
                # If not JSON, return basic segment with transcript only
                return {
                    "transcript": segment,
                    "speaker_id": None,
                    "start_time": 0,
                    "end_time": 0,
                    "confidence": 0.5
                }
        return segment

    # Check if recognition_results contains speaker segments
    if recognition_results and isinstance(recognition_results, dict):
        if "timeline" in recognition_results and recognition_results["timeline"]:
            timeline = recognition_results["timeline"]
            
            # Process each segment in the timeline
            for raw_segment in timeline:
                # Parse the segment to ensure it's in the right format
                segment = parse_segment(raw_segment)
                
                # Log the segment structure to help debug
                logger.info(f"Processing segment: {type(segment)}, keys: {segment.keys() if isinstance(segment, dict) else 'N/A'}")
                
                if isinstance(segment, dict) and "speaker_id" in segment and segment["speaker_id"]:
                    # This is an identified speaker
                    try:
                        # Format timestamps
                        start_time = segment.get("start_time", 0)
                        end_time = segment.get("end_time", 0)
                        start_timestamp = format_timestamp(start_time)
                        end_timestamp = format_timestamp(end_time)
                        duration = end_time - start_time
                        
                        # Create clip data for identified speaker
                        clip_id = str(uuid.uuid4())
                        clip_data = {
                            "id": clip_id,
                            "member_id": segment["speaker_id"],
                            "transcript": segment.get("transcript", "No transcript available"),
                            "full_video_path": full_video_url,
                            "session_date": session_info["date"],
                            "session_type": "parliament_tv",
                            "debate_topic": session_info["title"],
                            "status": "pending_review",
                            "confidence_score": float(segment.get("confidence", 0.5)),
                            "start_timestamp": start_timestamp,
                            "end_timestamp": end_timestamp,
                            "duration_seconds": float(duration),
                            "is_deleted": False
                        }
                        
                        # Insert clip into parliament_member_clips table
                        response = supabase_service.client.table('parliament_member_clips').insert(clip_data).execute()
                        
                        if response and hasattr(response, 'data') and response.data:
                            identified_clips.append(clip_id)
                            logger.info(f"Saved clip {clip_id} for member {segment['speaker_id']} to Supabase")
                    except Exception as e:
                        logger.error(f"Error saving clip for identified speaker: {str(e)}")
                        logger.error(traceback.format_exc())
                else:
                    # This is an unidentified speaker
                    # Extract face and voice data if available
                    face_data = {}
                    voice_data = {}
                    
                    if isinstance(segment, dict):
                        # Try to extract face data
                        if "face_data" in segment:
                            face_data = segment["face_data"]
                        elif "face" in segment:
                            face_data = segment["face"]
                        
                        # Try to extract voice data
                        if "voice_data" in segment:
                            voice_data = segment["voice_data"]
                        elif "voice" in segment:
                            voice_data = segment["voice"]
                        
                        # Create unidentified segment
                        unidentified_segments.append({
                            "start_time": segment.get("start_time", 0),
                            "end_time": segment.get("end_time", 0),
                            "transcript": segment.get("transcript", ""),
                            "confidence": segment.get("confidence", 0.5),
                            "face_data": face_data,
                            "voice_data": voice_data
                        })
                    else:
                        # If segment isn't a dict, create a basic unidentified segment
                        unidentified_segments.append({
                            "start_time": 0,
                            "end_time": 0,
                            "transcript": str(segment) if segment else "",
                            "confidence": 0.5,
                            "face_data": {},
                            "voice_data": {}
                        })
    
    # If we have unidentified segments, save them for later matching
    unidentified_result = None
    if unidentified_segments:
        # Create directory if it doesn't exist
        unidentified_dir = "/app/data/temp/unidentified_speakers"
        os.makedirs(unidentified_dir, exist_ok=True)
        
        # Save unidentified segments metadata
        unidentified_metadata = {
            "video_id": video_id,
            "full_video_url": full_video_url,
            "session_info": session_info,
            "segments": []
        }
        
        # Process each unidentified segment
        for i, segment in enumerate(unidentified_segments):
            # Generate a unique clip ID
            clip_id = str(uuid.uuid4())
            
            # Calculate duration
            duration = segment["end_time"] - segment["start_time"]
            
            # Format timestamps
            start_timestamp = format_timestamp(segment["start_time"])
            end_timestamp = format_timestamp(segment["end_time"])
            
            # Add segment to metadata
            unidentified_metadata["segments"].append({
                "clip_id": clip_id,
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration": duration,
                "transcript": segment["transcript"],
                "face_data": segment["face_data"],
                "voice_data": segment["voice_data"]
            })
        
        # Save metadata to file
        try:
            metadata_file = os.path.join(unidentified_dir, f"unidentified_{video_id}.json")
            with open(metadata_file, "w") as f:
                json.dump(unidentified_metadata, f, indent=2)
            
            logger.info(f"Saved {len(unidentified_segments)} unidentified speaker segments to {metadata_file}")
            
            unidentified_result = {
                "success": True,
                "segment_count": len(unidentified_segments),
                "metadata_file": metadata_file
            }
        except Exception as e:
            logger.error(f"Error saving unidentified speaker metadata: {str(e)}")
            unidentified_result = {
                "success": False,
                "error": str(e)
            }
    
    # Return results
    return {
        "success": len(identified_clips) > 0 or (unidentified_result and unidentified_result["success"]),
        "video_id": video_id,
        "identified_clip_count": len(identified_clips),
        "identified_clips": identified_clips,
        "unidentified_segment_count": len(unidentified_segments),
        "unidentified_result": unidentified_result
    }
