#!/usr/bin/env python
"""
Clip generator module for Parliament TV recognition.

This module handles the creation of clips from full videos based on speaker segments.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClipGenerator:
    """Clip generator service for Parliament TV recognition."""
    
    def __init__(self):
        """Initialize the clip generator service."""
        # Create clips directory if it doesn't exist
        self.clips_dir = Path("/app/data/temp/clips")
        self.clips_dir.mkdir(parents=True, exist_ok=True)
    
    def create_clip(self, input_file: str, output_file: str, start_time: float, duration: float) -> Dict[str, Any]:
        """
        Create a clip from a video file.
        
        Args:
            input_file: Path to the input video file
            output_file: Path to the output clip file
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Dict with clip creation result
        """
        try:
            # Ensure input file exists
            if not os.path.exists(input_file):
                return {"success": False, "error": f"Input file not found: {input_file}"}
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            os.makedirs(output_dir, exist_ok=True)
            
            # Format start time as HH:MM:SS
            start_time_str = self._format_timestamp(start_time)
            
            # Use ffmpeg to create the clip
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-ss", start_time_str,  # Start time
                "-i", input_file,  # Input file
                "-t", str(duration),  # Duration
                "-c", "copy",  # Copy all streams (much faster)
                "-movflags", "+faststart",  # Optimize for web streaming
                output_file  # Output file
            ]
            
            logger.info(f"Creating clip: {' '.join(cmd)}")
            
            # Run ffmpeg command
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Check if clip was created successfully
            if process.returncode != 0:
                logger.error(f"Error creating clip: {process.stderr}")
                return {"success": False, "error": process.stderr}
            
            # Check if output file exists
            if not os.path.exists(output_file):
                return {"success": False, "error": "Output file not created"}
            
            return {
                "success": True,
                "input_file": input_file,
                "output_file": output_file,
                "start_time": start_time,
                "duration": duration
            }
            
        except Exception as e:
            logger.exception(f"Error creating clip: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds as HH:MM:SS.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
