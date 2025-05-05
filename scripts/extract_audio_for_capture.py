#!/usr/bin/env python3
"""
Extract Audio for a Specific Capture

This script extracts audio for a specific capture ID using the Parliament TV URL
stored in the database.

Usage:
    python extract_audio_for_capture.py <capture_id>

Example:
    python extract_audio_for_capture.py 96
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import traceback
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('extract-audio-for-capture')

# Get the data directory from environment variable or use default
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@db/app')

# Create the audio directory if it doesn't exist
audio_dir = os.path.join(DATA_DIR, 'audio')
os.makedirs(audio_dir, exist_ok=True)

# Create a temporary directory for audio extracts
temp_audio_dir = os.path.join(DATA_DIR, 'temp', 'audio_extracts')
os.makedirs(temp_audio_dir, exist_ok=True)

# Setup database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define a minimal version of the CaptureSession model
class CaptureSession(Base):
    __tablename__ = "capture_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String)
    status = Column(String)
    audio_file_path = Column(String, nullable=True)

def get_capture_info(capture_id):
    """Get the capture information directly from the database."""
    try:
        # Create a new session
        db = SessionLocal()
        try:
            # Query the database for the capture
            capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
            
            if not capture:
                logger.error(f"Capture {capture_id} not found in database")
                return None
            
            # Convert the SQLAlchemy model to a dictionary
            capture_info = {
                "id": capture.id,
                "source_url": capture.source_url,
                "status": capture.status,
                "audio_file_path": capture.audio_file_path
            }
            
            return capture_info
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting capture info from database: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def extract_audio(url, output_file):
    """Extract audio from a Parliament TV URL or direct stream URL and save it as an MP3 file."""
    logger.info(f"Extracting audio from: {url}")
    
    # Determine if this is a direct stream URL or a Parliament TV URL
    is_direct_stream = False
    if url.endswith(".m3u8") or "cdn.redbee.live" in url:
        is_direct_stream = True
        logger.info(f"Detected direct stream URL: {url}")
    
    audio_url = None
    
    if is_direct_stream:
        # This is already a direct stream URL, try to derive the audio URL
        if "video=" in url:
            # Standard format: video=3000000.m3u8 -> audio_eng=64000.m3u8
            audio_url = url.replace("video=", "audio_eng=")
            # Make sure we have the right audio bitrate
            audio_url = audio_url.replace("3000000", "64000")
            logger.info(f"Derived audio URL from video URL: {audio_url}")
        elif "vod-idx-video=" in url:
            # Parliament TV format: vod-idx-video=3000000.m3u8 -> vod-idx-audio_eng=64000.m3u8
            audio_url = url.replace("vod-idx-video=", "vod-idx-audio_eng=")
            # Make sure we have the right audio bitrate
            audio_url = audio_url.replace("3000000", "64000")
            logger.info(f"Derived audio URL from Parliament TV URL: {audio_url}")
        else:
            # Use the main URL but extract only audio
            audio_url = url
            logger.info(f"Using main URL for audio extraction: {audio_url}")
    else:
        # This is a Parliament TV URL, use extract-url.py to get the stream info
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract-url.py")
        if not os.path.exists(script_path):
            logger.error(f"Could not find extract-url.py at {script_path}")
            return False
        
        try:
            # Run the extract-url.py script to get stream info
            extract_cmd = [sys.executable, script_path, url]
            logger.info(f"Running extract-url.py: {' '.join(extract_cmd)}")
            
            extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            if extract_result.returncode != 0:
                logger.error(f"extract-url.py failed with return code {extract_result.returncode}")
                logger.error(f"extract-url.py error: {extract_result.stderr}")
                return False
            
            # Parse the JSON output
            stream_info = json.loads(extract_result.stdout)
            logger.info(f"Parsed stream info: {json.dumps(stream_info, indent=2)}")
            
            # Check if we have separate audio and video URLs
            if isinstance(stream_info.get('direct_stream'), dict) and 'audio_url' in stream_info['direct_stream']:
                audio_url = stream_info['direct_stream']['audio_url']
                logger.info(f"Found separate audio URL: {audio_url}")
            elif isinstance(stream_info.get('direct_stream'), str):
                # Try to derive an audio URL from the video URL
                video_url = stream_info['direct_stream']
                if 'video=' in video_url:
                    # Standard format: video=3000000.m3u8 -> audio_eng=64000.m3u8
                    audio_url = video_url.replace('video=', 'audio_eng=')
                    # Make sure we have the right audio bitrate
                    audio_url = audio_url.replace('3000000', '64000')
                    logger.info(f"Derived audio URL from video URL: {audio_url}")
                elif 'vod-idx-video=' in video_url:
                    # Parliament TV format: vod-idx-video=3000000.m3u8 -> vod-idx-audio_eng=64000.m3u8
                    audio_url = video_url.replace('vod-idx-video=', 'vod-idx-audio_eng=')
                    # Make sure we have the right audio bitrate
                    audio_url = audio_url.replace('3000000', '64000')
                    logger.info(f"Derived audio URL from Parliament TV URL: {audio_url}")
                else:
                    # Use the main URL but extract only audio
                    audio_url = video_url
                    logger.info(f"Using main URL for audio extraction: {audio_url}")
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    if not audio_url:
        logger.error("No audio URL found")
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
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Audio extraction successful: {output_file}")
            return True
        else:
            logger.error(f"ffmpeg failed with return code {result.returncode}")
            logger.error(f"ffmpeg error: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running ffmpeg: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def update_capture_audio_path(capture_id, audio_file_path):
    """Update the audio_file_path for a capture directly in the database."""
    try:
        # Create a new session
        db = SessionLocal()
        try:
            # Query the database for the capture
            capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
            
            if not capture:
                logger.error(f"Capture {capture_id} not found in database")
                return False
            
            # Update the audio_file_path
            capture.audio_file_path = audio_file_path
            db.commit()
            
            logger.info(f"Updated audio_file_path for capture {capture_id} in database")
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating capture in database: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    
    # Generate the output file path - use temp/audio_extracts as expected by the frontend
    audio_file = f"/app/data/temp/audio_extracts/capture_{capture_id:04d}.audio.mp3"
    
    # Extract the audio
    if extract_audio(source_url, audio_file):
        logger.info(f"Successfully extracted audio to: {audio_file}")
        
        # Update the capture in the database
        if update_capture_audio_path(capture_id, audio_file):
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
