"""
Audio-Video combiner utility.

This module provides functions to combine separate audio and video files
into a single audio-video file, which is useful for the Supabase integration
while maintaining separate streams internally for Parliament TV.
"""

import os
import logging
import subprocess
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

def combine_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Combine separate audio and video files into a single audio-video file.
    
    This function uses FFmpeg to combine separate audio and video files
    into a single audio-video file without re-encoding the video stream
    to maintain quality and minimize processing time.
    
    Args:
        video_path: Path to the video file
        audio_path: Path to the audio file
        output_path: Path to save the combined file
        overwrite: Whether to overwrite the output file if it exists
        
    Returns:
        Dict with success status and output file path
    """
    logger.info(f"Combining audio ({audio_path}) and video ({video_path}) into {output_path}")
    
    # Check if input files exist
    if not os.path.exists(video_path):
        error_msg = f"Video file not found: {video_path}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "output_path": None}
    
    if not os.path.exists(audio_path):
        error_msg = f"Audio file not found: {audio_path}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "output_path": None}
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-y" if overwrite else "-n",  # Overwrite output file if it exists
        "-i", video_path,  # Video input
        "-i", audio_path,  # Audio input
        "-c:v", "copy",  # Copy video stream without re-encoding
        "-c:a", "aac",  # Use AAC codec for audio
        "-b:a", "192k",  # Audio bitrate
        "-map", "0:v:0",  # Map first video stream from first input
        "-map", "1:a:0",  # Map first audio stream from second input
        "-shortest",  # End when the shortest input ends
        output_path
    ]
    
    # Execute FFmpeg command
    try:
        logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = f"FFmpeg failed with error: {stderr}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "output_path": None}
        
        logger.info(f"Successfully combined audio and video into {output_path}")
        return {"success": True, "output_path": output_path}
    
    except Exception as e:
        error_msg = f"Error running FFmpeg: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "output_path": None}
