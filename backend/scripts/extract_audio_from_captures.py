#!/usr/bin/env python3
"""
Extract Audio from Captured Video Files

This script extracts audio from existing video capture files and saves them
as MP3 files in the audio_extracts directory.

Usage:
    python extract_audio_from_captures.py [--video-dir VIDEO_DIR] [--audio-dir AUDIO_DIR]

Example:
    python extract_audio_from_captures.py --video-dir /app/data/temp --audio-dir /app/data/temp/audio_extracts
"""

import os
import sys
import argparse
import subprocess
import logging
import glob
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract-audio-from-captures')

def check_command_exists(command):
    """Check if a command exists on the system."""
    try:
        subprocess.run(['which', command], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def extract_audio_from_video(video_file, audio_dir):
    """Extract audio from a video file and save it as an MP3 file."""
    logger.info(f"Extracting audio from: {video_file}")
    
    # Generate output filename based on the video filename
    video_basename = os.path.basename(video_file)
    audio_filename = f"{os.path.splitext(video_basename)[0]}.audio.mp3"
    output_file = os.path.join(audio_dir, audio_filename)
    
    # Check if the output file already exists
    if os.path.exists(output_file):
        logger.info(f"Audio file already exists: {output_file}")
        return output_file
    
    # Make sure the output directory exists
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)
    
    try:
        # Use ffmpeg to extract audio from the video
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-ar", "44100",
            "-f", "mp3",
            output_file
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            logger.info(f"Audio extraction successful: {output_file}")
            return output_file
        else:
            logger.error(f"ffmpeg failed with return code {result.returncode}")
            logger.error(f"ffmpeg output: {result.stdout}")
            logger.error(f"ffmpeg error: {result.stderr}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running ffmpeg: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def process_video_directory(video_dir, audio_dir):
    """Process all video files in a directory and extract audio from them."""
    logger.info(f"Processing video directory: {video_dir}")
    
    # Check if ffmpeg is installed
    if not check_command_exists("ffmpeg"):
        logger.error("ffmpeg not found. Please install it.")
        return False
    
    # Find all video files in the directory
    video_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    
    if not video_files:
        logger.warning(f"No video files found in {video_dir}")
        return False
    
    logger.info(f"Found {len(video_files)} video files")
    
    # Extract audio from each video file
    success_count = 0
    for video_file in video_files:
        output_file = extract_audio_from_video(video_file, audio_dir)
        if output_file:
            success_count += 1
    
    logger.info(f"Successfully extracted audio from {success_count} of {len(video_files)} video files")
    return success_count > 0

def main():
    parser = argparse.ArgumentParser(description='Extract Audio from Captured Video Files')
    parser.add_argument('--video-dir', default='/app/data/temp', help='Directory containing video files')
    parser.add_argument('--audio-dir', default='/app/data/temp/audio_extracts', help='Directory to save audio files')
    args = parser.parse_args()
    
    # Process the video directory
    success = process_video_directory(args.video_dir, args.audio_dir)
    
    if not success:
        logger.error("Failed to extract audio from any video files")
        return 1
    
    logger.info("Audio extraction completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
