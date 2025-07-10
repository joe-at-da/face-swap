"""
Supabase Export Module

This module provides functionality to export Parliament TV recognition data
in a format compatible with Supabase queues.
"""

import json
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from backend.services.media.av_combiner import combine_audio_video
from backend.db.models import ParliamentTranscription
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def format_video_for_supabase(
    video_id: str,
    title: str,
    description: str,
    capture_date: str,
    duration: float,
    video_url: str,
    audio_url: str,
    thumbnail_url: Optional[str] = None,
    combined_av_url: Optional[str] = None,
    status: str = "processed",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format video data for Supabase video_processing queue
    
    Args:
        video_id: Unique identifier for the video
        title: Title of the video
        description: Description of the video
        capture_date: ISO-8601 formatted date when the video was captured
        duration: Duration in seconds
        video_url: URL to the video file
        audio_url: URL to the audio file (separate from video)
        thumbnail_url: URL to the video thumbnail (optional)
        status: Processing status
        metadata: Additional metadata
        
    Returns:
        Dictionary formatted for Supabase video_processing queue
    """
    # Prepare metadata with combined_av_url if available
    meta = metadata or {"source": "parliament_tv"}
    if combined_av_url:
        meta["combined_av_url"] = combined_av_url
    
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "capture_date": capture_date,
        "duration": duration,
        "video_url": video_url,
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
        "combined_av_url": combined_av_url,  # Add as a top-level field
        "status": status,
        "metadata": meta
    }


def format_clips_for_supabase(
    video_id: str,
    recognition_results: Dict[str, Any],
    combined_av_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Format recognition results for Supabase clip_creation queue
    
    Args:
        video_id: Reference to the parent video
        recognition_results: Recognition results from facial recognition
        combined_av_url: URL to the combined audio-video file
        
    Returns:
        List of clips formatted for Supabase clip_creation queue
    """
    # Function to validate and convert member_id to integer
    def validate_member_id(member_id):
        if not member_id:
            return None
            
        # Handle default_unknown or already -1 - use a special ID for unknown members
        if member_id == "default_unknown" or member_id == -1:
            if member_id == "default_unknown":
                logger.warning("Using special ID -1 for default_unknown member_id")
            return -1  # Use -1 as a special ID for unknown members
            
        # If already an integer, return as is
        if isinstance(member_id, int):
            return member_id
            
        # Try to convert string to integer
        try:
            # Standard conversion to integer
            return int(member_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid member_id format: {member_id}, using special ID -1")
            return -1  # Use special ID for invalid formats
    # Log the structure of the recognition_results for debugging
    logger.info(f"Recognition results keys: {list(recognition_results.keys())}")
    if 'speaker_appearances' in recognition_results:
        logger.info(f"Found {len(recognition_results.get('speaker_appearances', []))} speaker appearances")
        # Log a sample speaker appearance if available
        if recognition_results.get('speaker_appearances'):
            sample = recognition_results['speaker_appearances'][0]
            logger.info(f"Sample speaker appearance keys: {list(sample.keys())}")
    
    clips = []
    
    # Process identified speakers from the traditional format
    for speaker in recognition_results.get("identified_speakers", []):
        for segment in speaker.get("segments", []):
            # Ensure required fields are present
            mp_id = speaker.get("mp_id")
            start_time = segment.get("start_time")
            end_time = segment.get("end_time")
            
            # Skip this segment if any required field is missing
            if mp_id is None or start_time is None or end_time is None:
                logger.warning(f"Skipping identified speaker segment with missing required fields: mp_id={mp_id}, start_time={start_time}, end_time={end_time}")
                continue
                
            # Validate and convert member_id
            valid_mp_id = validate_member_id(mp_id)
            if valid_mp_id is None:
                logger.warning(f"Skipping identified speaker segment with invalid member_id: {mp_id}")
                continue
                
            clips.append({
                "video_id": video_id,
                "start_timestamp": start_time,
                "end_timestamp": end_time,
                "member_id": valid_mp_id,  # Use validated member_id
                "speaker_name": speaker.get("name", "Unknown"),
                "confidence": segment.get("confidence", 0.0),
                "transcript": segment.get("transcript", ""),
                "face_image_url": segment.get("face_image_url", ""),
                "full_video_path": combined_av_url or "unknown_path",  # Ensure full_video_path is present
                "metadata": {
                    "recognition_method": "facial",
                    "matched_by": "traditional",
                    "combined_av_url": combined_av_url
                }
            })
    
    # Process speaker appearances from our improved local database format
    for appearance in recognition_results.get("speaker_appearances", []):
        # Ensure required fields are present
        member_id = appearance.get("member_id")
        start_time = appearance.get("start_time")
        end_time = appearance.get("end_time")
        
        # Skip this appearance if any required field is missing
        if member_id is None or start_time is None or end_time is None:
            logger.warning(f"Skipping appearance with missing required fields: member_id={member_id}, start_time={start_time}, end_time={end_time}")
            continue
            
        # Validate and convert member_id
        valid_member_id = validate_member_id(member_id)
        if valid_member_id is None:
            logger.warning(f"Skipping appearance with invalid member_id: {member_id}")
            continue
            
        clips.append({
            "video_id": video_id,
            "start_timestamp": start_time,
            "end_timestamp": end_time,
            "member_id": valid_member_id,  # Use validated member_id
            "speaker_name": appearance.get("member_name", "Unknown"),
            "confidence": appearance.get("confidence", 0.0),
            "transcript": appearance.get("transcript", ""),  # Ensure transcript is present
            "face_image_url": appearance.get("face_image_url", ""),
            "full_video_path": combined_av_url or "unknown_path",  # Ensure full_video_path is present
            "metadata": {
                "recognition_method": "facial",
                "matched_by": appearance.get("matched_by", "parliament_member_matcher"),
                "appearance_id": appearance.get("id"),
                "identification_id": appearance.get("identification_id"),
                "combined_av_url": combined_av_url
            }
        })
    
    # Process timeline data which may contain both identified and unidentified speakers
    if "timeline" in recognition_results:
        for event in recognition_results.get("timeline", []):
            if event.get("type") == "speaker":
                # Skip if we don't have timing information
                if "start_time" not in event or "end_time" not in event:
                    continue
                    
                # Ensure required fields are present
                member_id = event.get("member_id")
                start_time = event.get("start_time")
                end_time = event.get("end_time")
                
                # Skip this event if any required field is missing
                if member_id is None or start_time is None or end_time is None:
                    logger.warning(f"Skipping timeline event with missing required fields: member_id={member_id}, start_time={start_time}, end_time={end_time}")
                    continue
                    
                # Validate and convert member_id
                valid_member_id = validate_member_id(member_id)
                if valid_member_id is None:
                    logger.warning(f"Skipping timeline event with invalid member_id: {member_id}")
                    continue
                    
                # Create clip for this timeline event
                clips.append({
                    "video_id": video_id,
                    "start_timestamp": start_time,
                    "end_timestamp": end_time,
                    "member_id": valid_member_id,  # Use validated member_id
                    "speaker_name": event.get("name", "Unknown"),
                    "confidence": event.get("confidence", 0.0),
                    "transcript": event.get("text", "") or "No transcript available",  # Ensure transcript is not empty
                    "face_image_url": event.get("face_image_url", ""),
                    "full_video_path": combined_av_url or "unknown_path",  # Ensure full_video_path is present
                    "metadata": {
                        "recognition_method": event.get("recognition_method", "multimodal"),
                        "matched_by": event.get("matched_by", "timeline"),
                        "timeline_event_id": event.get("id"),
                        "combined_av_url": combined_av_url
                    }
                })
    
    # Process unidentified faces
    for face in recognition_results.get("unidentified_faces", []):
        for appearance in face.get("appearances", []):
            # Convert frame-based appearances to time-based segments if needed
            start_time = appearance.get("timestamp", 0)
            # Assume each appearance is 5 seconds if end_time not provided
            end_time = appearance.get("end_time", start_time + 5)
            
            # For unidentified faces, we need to use a default member_id since it's required
            # Use a consistent default ID for unidentified speakers
            # We'll log this clearly so it's transparent that these are unidentified speakers
            default_member_id = "default_unknown"
            logger.info(f"Using default_unknown member_id for unidentified face at time {start_time}")
            
            clips.append({
                "video_id": video_id,
                "start_timestamp": start_time,
                "end_timestamp": end_time,
                "member_id": default_member_id,  # Use default member_id for unidentified faces
                "speaker_name": "Unknown",
                "confidence": 0.0,
                "transcript": "Unidentified speaker",  # Provide a default transcript
                "face_image_url": face.get("filename", ""),
                "full_video_path": combined_av_url or "unknown_path",  # Ensure full_video_path is present
                "metadata": {
                    "recognition_method": "facial",
                    "matched_by": "unidentified",
                    "unidentified_face_id": face.get("id", ""),
                    "combined_av_url": combined_av_url
                }
            })
    
    # Remove duplicate clips based on time ranges and member_id
    # This prevents multiple entries for the same speaker in the same time segment
    unique_clips = {}
    for clip in clips:
        # Ensure all required fields are present before deduplication
        if 'member_id' not in clip or 'start_timestamp' not in clip or 'end_timestamp' not in clip:
            logger.warning(f"Skipping clip with missing fields during deduplication: {clip.keys()}")
            continue
            
        # Create a key based on time range and member_id
        start_time = clip['start_timestamp']
        end_time = clip['end_timestamp']
        member_id = clip['member_id']
        key = f"{start_time:.2f}_{end_time:.2f}_{member_id}"
        
        # Prioritize clips with real MP associations (member_id < 9000)
        # This ensures our default unidentified member_id (9999) gets lower priority
        has_real_mp = isinstance(member_id, int) and member_id < 9000
        existing_has_real_mp = key in unique_clips and isinstance(unique_clips[key].get('member_id'), int) and unique_clips[key]['member_id'] < 9000
        
        # Logic for deciding which clip to keep:
        # 1. If this is a new unique clip, keep it
        # 2. If this clip has a real MP association and existing doesn't, replace it
        # 3. If both have real MP associations or both don't, use the one with higher confidence
        if (key not in unique_clips or 
            (has_real_mp and not existing_has_real_mp) or
            (has_real_mp == existing_has_real_mp and clip['confidence'] > unique_clips[key]['confidence'])):
            unique_clips[key] = clip
    
    # Log the number of clips with MP associations
    mp_clips = [clip for clip in unique_clips.values() if clip.get('member_id') is not None and clip.get('member_id') != 9999]
    logger.info(f"Formatted {len(unique_clips)} unique clips for Supabase, {len(mp_clips)} with MP associations")
    
    # Add detailed debug logging to help diagnose issues
    if len(unique_clips) == 0:
        logger.warning("No clips were formatted for Supabase export")
        # Log the keys in recognition_results to help diagnose
        logger.warning(f"Recognition results keys: {list(recognition_results.keys())}")
        # Log counts of various data sources
        logger.warning(f"Identified speakers: {len(recognition_results.get('identified_speakers', []))}")
        logger.warning(f"Speaker appearances: {len(recognition_results.get('speaker_appearances', []))}")
        logger.warning(f"Timeline events: {len(recognition_results.get('timeline', []))}")
        logger.warning(f"Unidentified faces: {len(recognition_results.get('unidentified_faces', []))}")
    elif len(mp_clips) == 0:
        logger.warning("No clips with real MP associations were found")
    
    # Verify all clips have the required fields before returning
    valid_clips = []
    for clip in unique_clips.values():
        missing_fields = []
        for field in ['member_id', 'start_timestamp', 'end_timestamp', 'transcript', 'full_video_path']:
            if field not in clip or clip[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Clip still missing required fields after formatting: {missing_fields}")
        else:
            valid_clips.append(clip)
    
    logger.info(f"Returning {len(valid_clips)} valid clips after final validation")
    return valid_clips


def export_to_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Export data to JSON file
    
    Args:
        data: Data to export
        output_path: Path to output file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)


def export_recognition_results(
    video_path: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    export_dir: str,
    create_combined_av: bool = True,
    db_session: Optional[Session] = None,
    video_id: Optional[int] = None
) -> Dict[str, str]:
    """
    Export recognition results for Supabase integration
    
    Args:
        video_path: Path to the video file
        recognition_results: Recognition results from facial recognition
        video_metadata: Metadata about the video
        export_dir: Directory to export files to
        create_combined_av: Whether to create a combined audio-video file for Supabase
        
    Returns:
        Dictionary with paths to exported files
    """
    video_file_id = os.path.basename(video_path).split('.')[0]
    data_dir = os.environ.get("DATA_DIR", "/app/data")
    media_dir = os.path.join(data_dir, "media")
    # Store combined files directly in the media directory
    combined_dir = media_dir
    os.makedirs(combined_dir, exist_ok=True)
    
    # Check if the video file exists with the provided path
    if not os.path.exists(video_path):
        # Try alternative naming pattern
        # If the path is like /app/data/media/parliament_tv_467.mp4, try /app/data/media/467.mp4
        if 'parliament_tv_' in video_path:
            capture_id = video_path.split('parliament_tv_')[-1].split('.')[0]
            alternative_path = os.path.join(os.path.dirname(video_path), f"{capture_id}.mp4")
            if os.path.exists(alternative_path):
                logger.info(f"Using alternative video file path: {alternative_path}")
                video_path = alternative_path
    
    # Get paths for video and audio using Docker container paths
    video_url = video_path  # Use the full path directly
    audio_url = video_metadata.get("audio_url", "")
    combined_url = ""
    
    # If audio_url is not provided, try to find the audio file using common patterns
    if not audio_url:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        logger.info(f"Looking for audio file for video: {video_name}")
        audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
        logger.info(f"Searching in audio extracts directory: {audio_extracts_dir}")
        
        # Check if audio extracts directory exists
        if os.path.exists(audio_extracts_dir):
            logger.info(f"Audio extracts directory exists, contains: {os.listdir(audio_extracts_dir)}")
        else:
            logger.warning(f"Audio extracts directory does not exist: {audio_extracts_dir}")
            # Try to create the directory
            try:
                os.makedirs(audio_extracts_dir, exist_ok=True)
                logger.info(f"Created audio extracts directory: {audio_extracts_dir}")
            except Exception as e:
                logger.error(f"Failed to create audio extracts directory: {str(e)}")
        
        # Try common naming patterns for audio files
        potential_audio_files = [
            os.path.join(audio_extracts_dir, f"{video_name}.audio.mp3"),
            os.path.join(audio_extracts_dir, f"{video_name}.mp3"),
            os.path.join(audio_extracts_dir, f"capture_{video_name}.audio.mp3"),
            os.path.join(audio_extracts_dir, f"capture_{video_name}.mp3"),
            os.path.join(audio_extracts_dir, f"{video_name}_audio.mp3"),
            os.path.join(audio_extracts_dir, f"{video_name}.audio.m4a"),
            os.path.join(audio_extracts_dir, f"{video_name}.m4a"),
            os.path.join(audio_extracts_dir, f"{video_name}_audio.m4a"),
            os.path.join(audio_extracts_dir, f"{video_name}.audio.aac"),
            os.path.join(audio_extracts_dir, f"{video_name}.aac"),
            os.path.join(audio_extracts_dir, f"{video_name}_audio.aac"),
            # Try in the media directory as well
            os.path.join(media_dir, f"{video_name}.audio.mp3"),
            os.path.join(media_dir, f"{video_name}.mp3"),
            os.path.join(media_dir, f"{video_name}_audio.mp3"),
        ]
        
        for audio_file in potential_audio_files:
            if os.path.exists(audio_file):
                logger.info(f"Found audio file: {audio_file}")
                # Use the full path directly instead of a URL format
                audio_url = audio_file
                break
        
        if not audio_url:
            logger.warning(f"No audio file found for video: {video_path}")
    
    logger.info(f"Using audio URL: {audio_url}")
    
    # Create combined audio-video file if requested and both audio and video are available
    if create_combined_av and audio_url:
        try:
            logger.info(f"Creating combined audio-video file for Supabase integration")
            # Use timestamp format for the combined file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_filename = f"combined_av_{video_id}_{timestamp}.mp4"
            combined_path = os.path.join(combined_dir, combined_filename)
            
            # Combine audio and video
            result = combine_audio_video(
                video_url=video_url,
                audio_url=audio_url,
                output_path=combined_path,
                video_base_path=data_dir,
                audio_base_path=data_dir,
                metadata={
                    "title": video_metadata.get("title", f"Parliament TV Video {video_id}"),
                    "source": "parliament_tv",
                    "combined_by": "Parliament TV Supabase Integration"
                }
            )
            
            if result["success"]:
                combined_url = result["combined_url"]
                logger.info(f"Successfully created combined audio-video file: {combined_url}")
            else:
                logger.error(f"Failed to create combined audio-video file: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error creating combined audio-video file: {str(e)}")
    
    # Get transcription data if available and db_session is provided
    transcription_data = None
    if db_session and video_id:
        transcription = db_session.query(ParliamentTranscription).filter(
            ParliamentTranscription.capture_session_id == video_id,
            ParliamentTranscription.status == "completed"
        ).order_by(ParliamentTranscription.created_at.desc()).first()
        
        if transcription and transcription.output_file and os.path.exists(transcription.output_file):
            try:
                with open(transcription.output_file, 'r') as f:
                    transcription_data = json.load(f)
                logger.info(f"Loaded transcription data from {transcription.output_file}")
            except Exception as e:
                logger.error(f"Error loading transcription file: {str(e)}")
    
    # Format video data for Supabase
    formatted_video = format_video_for_supabase(
        video_id=video_file_id,
        title=video_metadata.get("title", f"Parliament TV Capture {video_file_id}"),
        description=video_metadata.get("description", "Parliament TV video capture"),
        capture_date=video_metadata.get("capture_date", datetime.now().isoformat()),
        duration=video_metadata.get("duration", 0.0),
        video_url=video_url,
        audio_url=audio_url,
        thumbnail_url=video_metadata.get("thumbnail_url", ""),
        combined_av_url=combined_url,  # Pass combined URL directly
        status="processed",
        metadata={
            "source": "parliament_tv",
            "has_transcription": transcription_data is not None
        }
    )
    
    formatted_clips = format_clips_for_supabase(video_file_id, recognition_results, combined_url)
    
    # Add transcription data to recognition results if available
    if transcription_data:
        recognition_results["transcription"] = transcription_data
        
        # Add transcript text to clips for better searchability
        if "segments" in transcription_data:
            for clip in formatted_clips:
                # Find transcript segments that overlap with this clip
                clip_start = clip.get("start_time", 0)
                clip_end = clip.get("end_time", 0)
                
                matching_segments = []
                for segment in transcription_data["segments"]:
                    seg_start = segment.get("start", 0)
                    seg_end = segment.get("end", 0)
                    
                    # Check for overlap
                    if (seg_start <= clip_end and seg_end >= clip_start):
                        matching_segments.append(segment["text"])
                
                if matching_segments:
                    clip["transcript"] = " ".join(matching_segments)
    
    # Export to JSON files
    video_export_path = os.path.join(export_dir, f"{video_file_id}_video.json")
    clips_export_path = os.path.join(export_dir, f"{video_file_id}_clips.json")
    recognition_export_path = os.path.join(export_dir, f"{video_file_id}_recognition.json")
    
    export_to_json(formatted_video, video_export_path)
    export_to_json(formatted_clips, clips_export_path)
    export_to_json(recognition_results, recognition_export_path)
    
    logger.info(f"Exported recognition results for video {video_file_id} to {export_dir}")
    
    # Ensure all export paths are properly set in the return value
    result = {
        "video_export_path": video_export_path,
        "clips_export_path": clips_export_path,
        "recognition_export_path": recognition_export_path,
        "combined_av_url": combined_url,
        "combined_av_path": combined_av_path,  # Use the actual file path, not the URL
        "has_transcription": transcription_data is not None
    }
    
    # Add export_paths dictionary for compatibility with mp_clip_verification
    result["export_paths"] = {
        "video_export_path": video_export_path,
        "clips_export_path": clips_export_path,
        "recognition_export_path": recognition_export_path,
        "combined_av_path": combined_av_path
    }
    
    logger.info(f"Returning export result with combined AV path: {combined_url}")
    if combined_url and os.path.exists(combined_url):
        logger.info(f"Combined AV file exists, size: {os.path.getsize(combined_url)} bytes")
    else:
        logger.warning(f"Combined AV file does not exist or path is empty: {combined_url}")
        
    return result
