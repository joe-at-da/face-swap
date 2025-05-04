#!/usr/bin/env python3
"""
Extract Audio for Existing Captures

This script extracts audio directly from Parliament TV URLs for existing captures
and saves them as MP3 files in the audio_extracts directory.

Usage:
    python extract_audio_for_captures.py
"""

import os
import sys
import subprocess
import logging
import tempfile
from datetime import datetime
import json
import glob

# Add the parent directory to the path so we can import from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database models
try:
    # Try direct imports first (for running inside Docker)
    from db.session import SessionLocal
    from models import CaptureSession
    from core.config import settings
except ImportError:
    # Fall back to backend prefixed imports (for running outside Docker)
    from backend.db.session import SessionLocal
    from backend.models import CaptureSession
    from backend.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract-audio-for-captures')

def extract_audio_using_extract_url_script(url, output_file):
    """Extract audio from a Parliament TV URL using the extract-url.py script."""
    logger.info(f"Extracting audio from: {url}")
    
    try:
        # Find the extract-url.py script
        script_paths = [
            "/app/scripts/extract-url.py",
            "/app/backend/scripts/extract-url.py",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "extract-url.py")
        ]
        
        script_path = None
        for path in script_paths:
            if os.path.exists(path):
                script_path = path
                logger.info(f"Found extract-url.py script at: {script_path}")
                break
        
        if not script_path:
            logger.error("Could not find extract-url.py script")
            return None
        
        # Run the extract-url.py script to get stream info
        extract_cmd = [sys.executable, script_path, url]
        logger.info(f"Running extract-url.py: {' '.join(extract_cmd)}")
        extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
        
        if extract_result.returncode != 0:
            logger.error(f"extract-url.py failed with return code {extract_result.returncode}")
            logger.error(f"extract-url.py error: {extract_result.stderr}")
            return None
        
        # Parse the JSON output
        try:
            stream_info = json.loads(extract_result.stdout)
            logger.info(f"Parsed stream info: {stream_info}")
            
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
                return None
            
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
                return output_file
            else:
                logger.error(f"ffmpeg failed with return code {result.returncode}")
                logger.error(f"ffmpeg error: {result.stderr}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON output from extract-url.py: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def process_captures():
    """Process all captures and extract audio for them."""
    logger.info("Processing captures")
    
    # Create audio directory if it doesn't exist
    audio_dir = os.path.join(settings.DATA_DIR, "temp", "audio_extracts")
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Get all captures
        captures = db.query(CaptureSession).all()
        
        if not captures:
            logger.warning("No captures found in the database")
            return False
        
        logger.info(f"Found {len(captures)} captures")
        
        # Create sample audio files for testing
        sample1_file = os.path.join(audio_dir, "sample1.mp3")
        if not os.path.exists(sample1_file):
            logger.info(f"Creating sample audio file: {sample1_file}")
            extract_audio_using_extract_url_script("https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e", sample1_file)
        
        sample2_file = os.path.join(audio_dir, "sample2.mp3")
        if not os.path.exists(sample2_file):
            logger.info(f"Creating sample audio file: {sample2_file}")
            extract_audio_using_extract_url_script("https://parliamentlive.tv/event/index/4f25e3f3-7c8e-4a81-8eaa-6c6f91299a7b", sample2_file)
        
        # Extract audio for each capture
        success_count = 0
        for capture in captures:
            # Skip captures without a source URL
            if not capture.source_url:
                logger.warning(f"Capture {capture.id} has no source URL, skipping")
                continue
            
            # Generate output filename
            output_filename = f"capture_{capture.id:04d}.audio.mp3"
            output_file = os.path.join(audio_dir, output_filename)
            
            # Skip if the audio file already exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Audio file already exists for capture {capture.id}: {output_file}")
                
                # Update the capture record if needed
                if not capture.audio_file_path:
                    capture.audio_file_path = output_file
                    db.commit()
                    logger.info(f"Updated audio_file_path for capture {capture.id}")
                
                success_count += 1
                continue
            
            # Try to extract audio from the source URL
            logger.info(f"Extracting audio for capture {capture.id} from {capture.source_url}")
            
            # Use our extract-url.py script to get the audio URL
            success = extract_audio_using_extract_url_script(capture.source_url, output_file)
            
            # Update the capture record if successful
            if success:
                logger.info(f"Successfully extracted audio for capture {capture.id}")
                capture.audio_file_path = output_file
                db.commit()
                logger.info(f"Updated audio_file_path for capture {capture.id}")
                success_count += 1
            else:
                logger.error(f"Failed to extract audio for capture {capture.id}")
        
        logger.info(f"Successfully processed {success_count} of {len(captures)} captures")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error processing captures: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        db.close()

def main():
    try:
        # Process all captures
        success = process_captures()
        
        if not success:
            logger.error("Failed to extract audio for any captures")
            return 1
        
        logger.info("Audio extraction completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
