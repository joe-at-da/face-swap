"""
Transcript Directory Finder Module.

This module provides a simple, reliable way to find transcript directories
without complex fallback logic or reliance on chunked results.
"""

import os
import logging
import glob
from typing import Optional, List

logger = logging.getLogger(__name__)

# Standard locations where transcript files might be found
STANDARD_TRANSCRIPT_LOCATIONS = [
    "/app/data/temp/audio_extracts",
    "/app/data/temp/transcripts",
    "/app/data/media/transcripts",
]

def find_transcript_directory(video_path: Optional[str] = None) -> str:
    """
    Find the transcript directory for a given video or from standard locations.
    
    This function uses a simple, direct approach to find transcript directories:
    1. If video_path is provided, check for transcripts in the same directory
    2. Check standard locations where transcripts are typically stored
    3. Look for any directory containing transcript files
    
    Args:
        video_path: Optional path to the video file
        
    Returns:
        Path to the transcript directory, or empty string if not found
    """
    # Initialize with empty string
    transcript_dir = ""
    
    # List of potential directories to check
    potential_dirs = []
    
    # 1. If video path is provided, check related directories
    if video_path:
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Add video-specific directories
        potential_dirs.extend([
            os.path.join(video_dir, "transcripts"),
            os.path.join(video_dir, "audio_extracts"),
            os.path.join("/app/data/temp", f"transcripts_{video_name}"),
            os.path.join("/app/data/temp", f"audio_extracts_{video_name}"),
        ])
    
    # 2. Add standard locations
    potential_dirs.extend(STANDARD_TRANSCRIPT_LOCATIONS)
    
    # 3. Check each potential directory
    for dir_path in potential_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            # Check if directory contains transcript files
            transcript_files = glob.glob(os.path.join(dir_path, "transcript*.txt"))
            if transcript_files:
                transcript_dir = dir_path
                logger.info(f"Found transcript directory: {transcript_dir} with {len(transcript_files)} transcript files")
                break
    
    # If no directory with transcript files was found, just return the first existing directory
    if not transcript_dir:
        for dir_path in potential_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                transcript_dir = dir_path
                logger.info(f"No transcript files found, using directory: {transcript_dir}")
                break
    
    # Log the result
    if transcript_dir:
        logger.info(f"Using transcript directory: {transcript_dir}")
    else:
        logger.warning("No valid transcript directory found")
    
    return transcript_dir
