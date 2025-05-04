#!/usr/bin/env python3
"""
Extract Audio for a Specific Capture

This script extracts audio for a specific capture ID using the Parliament TV URL
stored in the database.

Usage:
    python extract_audio_for_capture.py <capture_id>

Example:
    python extract_audio_for_capture.py 82
"""

import os
import sys
import json
import subprocess
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract-audio-for-capture')

def get_capture_info(capture_id):
    """Get the capture information from the database."""
    try:
        # Use the API to get capture info
        cmd = ["curl", "-s", f"http://localhost:8000/api/v1/capture/{capture_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to get capture info: {result.stderr}")
            return None
        
        try:
            capture_info = json.loads(result.stdout)
            return capture_info
        except json.JSONDecodeError:
            logger.error(f"Failed to parse capture info: {result.stdout}")
            return None
    except Exception as e:
        logger.error(f"Error getting capture info: {str(e)}")
        return None

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

def update_capture_audio_path(capture_id, audio_file_path):
    """Update the audio_file_path for a capture in the database."""
    try:
        # Use curl to update the capture
        cmd = [
            "curl", "-X", "PUT",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"audio_file_path": audio_file_path}),
            f"http://localhost:8000/api/v1/capture/{capture_id}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to update capture: {result.stderr}")
            return False
        
        logger.info(f"Updated audio_file_path for capture {capture_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating capture: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Extract Audio for a Specific Capture')
    parser.add_argument('capture_id', type=int, help='Capture ID')
    args = parser.parse_args()
    
    capture_id = args.capture_id
    
    # Get the capture info
    capture_info = get_capture_info(capture_id)
    if not capture_info:
        logger.error(f"Failed to get capture info for capture {capture_id}")
        return 1
    
    # Check if the capture has a source URL
    source_url = capture_info.get('source_url')
    if not source_url:
        logger.error(f"Capture {capture_id} has no source URL")
        return 1
    
    logger.info(f"Capture {capture_id} has source URL: {source_url}")
    
    # Generate the output file path
    audio_dir = "/app/data/temp/audio_extracts"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)
    
    output_file = f"{audio_dir}/capture_{capture_id:04d}.audio.mp3"
    
    # Extract the audio
    if extract_audio(source_url, output_file):
        logger.info(f"Successfully extracted audio to: {output_file}")
        
        # Update the capture in the database
        if update_capture_audio_path(capture_id, output_file):
            logger.info(f"Successfully updated capture {capture_id} with audio file path")
            return 0
        else:
            logger.error(f"Failed to update capture {capture_id} with audio file path")
            return 1
    else:
        logger.error(f"Failed to extract audio for capture {capture_id}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
