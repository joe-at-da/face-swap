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
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "capture_date": capture_date,
        "duration": duration,
        "video_url": video_url,
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
        "status": status,
        "metadata": metadata or {
            "source": "parliament_tv"
        }
    }


def format_clips_for_supabase(
    video_id: str,
    recognition_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Format recognition results for Supabase clip_creation queue
    
    Args:
        video_id: Reference to the parent video
        recognition_results: Recognition results from facial recognition
        
    Returns:
        List of clips formatted for Supabase clip_creation queue
    """
    clips = []
    
    # Process identified speakers
    for speaker in recognition_results.get("identified_speakers", []):
        for segment in speaker.get("segments", []):
            clips.append({
                "video_id": video_id,
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "speaker_id": speaker["mp_id"],
                "speaker_name": speaker["name"],
                "confidence": segment.get("confidence", 0.0),
                "transcript": segment.get("transcript", ""),
                "face_image_url": segment.get("face_image_url", ""),
                "metadata": {
                    "recognition_method": "facial",
                }
            })
    
    # Process unidentified faces
    for face in recognition_results.get("unidentified_faces", []):
        for appearance in face.get("appearances", []):
            # Convert frame-based appearances to time-based segments if needed
            start_time = appearance.get("timestamp", 0)
            # Assume each appearance is 5 seconds if end_time not provided
            end_time = appearance.get("end_time", start_time + 5)
            
            clips.append({
                "video_id": video_id,
                "start_time": start_time,
                "end_time": end_time,
                "speaker_id": None,
                "speaker_name": "Unknown",
                "confidence": 0.0,
                "transcript": "",
                "face_image_url": face.get("filename", ""),
                "metadata": {
                    "recognition_method": "facial",
                    "unidentified_face_id": face.get("id", "")
                }
            })
    
    return clips


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
    create_combined_av: bool = True
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
    video_id = os.path.basename(video_path).split('.')[0]
    data_dir = os.environ.get("DATA_DIR", "/app/data")
    media_dir = os.path.join(data_dir, "media")
    combined_dir = os.path.join(media_dir, "combined")
    os.makedirs(combined_dir, exist_ok=True)
    
    # Get paths for video and audio
    video_url = f"/media/videos/{os.path.basename(video_path)}"
    audio_url = video_metadata.get("audio_url", "")
    combined_url = ""
    
    # If audio_url is not provided, try to find the audio file using common patterns
    if not audio_url:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
        
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
        ]
        
        for audio_file in potential_audio_files:
            if os.path.exists(audio_file):
                logger.info(f"Found audio file: {audio_file}")
                # Convert to URL format for the combine_audio_video function
                audio_url = f"/temp/audio_extracts/{os.path.basename(audio_file)}"
                break
        
        if not audio_url:
            logger.warning(f"No audio file found for video: {video_path}")
    
    logger.info(f"Using audio URL: {audio_url}")
    
    # Create combined audio-video file if requested and both audio and video are available
    if create_combined_av and audio_url:
        try:
            logger.info(f"Creating combined audio-video file for Supabase integration")
            combined_filename = f"{video_id}_combined.mp4"
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
    
    # Format data for Supabase queues - use combined URL if available, otherwise keep separate URLs
    video_data = format_video_for_supabase(
        video_id=video_id,
        title=video_metadata.get("title", f"Parliament TV Video {video_id}"),
        description=video_metadata.get("description", ""),
        capture_date=video_metadata.get("capture_date", datetime.now().isoformat()),
        duration=video_metadata.get("duration", 0),
        video_url=combined_url if combined_url else video_url,  # Use combined URL if available
        audio_url=audio_url if not combined_url else "",  # Only include audio URL if not using combined
        status="processed",
        metadata={
            "source": "parliament_tv",
            "parliament_tv_url": video_metadata.get("source_url", ""),
            "has_combined_av": bool(combined_url),
            "original_video_url": video_url,
            "original_audio_url": audio_url
        }
    )
    
    clips_data = format_clips_for_supabase(video_id, recognition_results)
    
    # Create export directory if it doesn't exist
    os.makedirs(export_dir, exist_ok=True)
    
    # Export to JSON files for Supabase integration
    video_export_path = os.path.join(export_dir, f"{video_id}_video.json")
    clips_export_path = os.path.join(export_dir, f"{video_id}_clips.json")
    
    export_to_json(video_data, video_export_path)
    export_to_json({"clips": clips_data}, clips_export_path)
    
    return {
        "video_data": video_export_path,
        "clips_data": clips_export_path,
        "combined_av": combined_url if combined_url else None
    }
