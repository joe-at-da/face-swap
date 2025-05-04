#!/usr/bin/env python3
"""
Extract Audio Only from Parliament TV URLs

This script extracts audio from Parliament TV URLs and saves it as MP3 files.
It uses the extract-url.py script to get the audio stream URL and then uses
ffmpeg to extract the audio.

Usage:
    python extract_audio_only.py <parliament_tv_url> <output_file>

Example:
    python extract_audio_only.py "https://parliamentlive.tv/event/index/c63e4bed-0da2-4d85-a742-e5d247a7aceb?in=12:23:30" "output.mp3"
"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract-audio-only')

def extract_audio(url, output_file):
    """Extract audio from a Parliament TV URL and save it as an MP3 file."""
    logger.info(f"Extracting audio from: {url}")
    
    # Find the extract-url.py script
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract-url.py")
    if not os.path.exists(script_path):
        logger.error(f"Could not find extract-url.py at {script_path}")
        return False
    
    # Run the extract-url.py script to get stream info
    extract_cmd = [sys.executable, script_path, url]
    logger.info(f"Running extract-url.py: {' '.join(extract_cmd)}")
    
    try:
        extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
        
        if extract_result.returncode != 0:
            logger.error(f"extract-url.py failed with return code {extract_result.returncode}")
            logger.error(f"extract-url.py error: {extract_result.stderr}")
            return False
        
        # Parse the JSON output
        stream_info = json.loads(extract_result.stdout)
        logger.info(f"Parsed stream info: {json.dumps(stream_info, indent=2)}")
        
        # Check if we have separate audio and video URLs
        audio_url = None
        if isinstance(stream_info.get('direct_stream'), dict) and 'audio_url' in stream_info['direct_stream']:
            audio_url = stream_info['direct_stream']['audio_url']
            logger.info(f"Found separate audio URL: {audio_url}")
        elif isinstance(stream_info.get('direct_stream'), str):
            # Try to derive an audio URL from the video URL
            video_url = stream_info['direct_stream']
            if 'video=' in video_url:
                audio_url = video_url.replace('video=', 'audio=')
                logger.info(f"Derived audio URL from video URL: {audio_url}")
            else:
                # Use the main URL but extract only audio
                audio_url = video_url
                logger.info(f"Using main URL for audio extraction: {audio_url}")
        
        if not audio_url:
            logger.error("No audio URL found in stream info")
            return False
        
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Extract audio using ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_url,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-ar", "44100",
            "-f", "mp3",
            output_file
        ]
        
        logger.info(f"Running ffmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Audio extraction successful: {output_file}")
            return True
        else:
            logger.error(f"ffmpeg failed with return code {result.returncode}")
            logger.error(f"ffmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <parliament_tv_url> <output_file>")
        return 1
    
    url = sys.argv[1]
    output_file = sys.argv[2]
    
    if extract_audio(url, output_file):
        print(f"Successfully extracted audio to: {output_file}")
        return 0
    else:
        print("Failed to extract audio")
        return 1

if __name__ == "__main__":
    sys.exit(main())
