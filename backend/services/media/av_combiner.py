"""
Audio-Video Combiner Module

This module provides functionality to combine separate audio and video files
into a single unified media file for Supabase integration.
"""

import os
import logging
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def combine_audio_video(
    video_url: str,
    audio_url: str,
    output_path: str,
    video_base_path: str = None,
    audio_base_path: str = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Combine separate audio and video files into a single file using FFmpeg.
    
    Args:
        video_url: URL or path to the video file
        audio_url: URL or path to the audio file
        output_path: Path where the combined file will be saved
        video_base_path: Base path to prepend to video_url if it's a relative path
        audio_base_path: Base path to prepend to audio_url if it's a relative path
        metadata: Additional metadata to include in the output file
        
    Returns:
        Dictionary with status and output file path
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Handle relative paths
        if video_base_path and not video_url.startswith(('http://', 'https://', '/')):
            video_path = os.path.join(video_base_path, video_url)
        else:
            video_path = video_url
            
        if audio_base_path and not audio_url.startswith(('http://', 'https://', '/')):
            audio_path = os.path.join(audio_base_path, audio_url)
        else:
            audio_path = audio_url
            
        # Prepare FFmpeg command
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',      # Copy video codec
            '-c:a', 'aac',       # Use AAC for audio
            '-strict', 'experimental',
            '-map', '0:v:0',     # Map first video stream from first input
            '-map', '1:a:0',     # Map first audio stream from second input
            '-shortest',         # End when shortest input ends
        ]
        
        # Add metadata if provided
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, str):
                    ffmpeg_cmd.extend(['-metadata', f'{key}={value}'])
        
        # Add output file
        ffmpeg_cmd.append(output_path)
        
        logger.info(f"Running FFmpeg command to combine audio and video: {' '.join(ffmpeg_cmd)}")
        
        # Run FFmpeg
        process = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check if successful
        if process.returncode == 0:
            logger.info(f"Successfully combined audio and video to: {output_path}")
            return {
                "success": True,
                "output_path": output_path,
                "combined_url": f"/media/combined/{os.path.basename(output_path)}"
            }
        else:
            logger.error(f"FFmpeg error: {process.stderr}")
            return {
                "success": False,
                "error": f"FFmpeg failed with return code {process.returncode}",
                "details": process.stderr
            }
            
    except Exception as e:
        logger.error(f"Error combining audio and video: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
