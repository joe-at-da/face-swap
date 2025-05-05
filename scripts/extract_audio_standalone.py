#!/usr/bin/env python3
"""
Standalone script to extract audio for Parliament TV captures.
This script can be run manually or scheduled to process captures that need audio extraction.
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db/parliament_clips")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extract_audio(url, output_file):
    """Extract audio from a URL and save it as an MP3 file."""
    logger.info(f"Extracting audio from {url} to {output_file}")
    
    # Determine if this is a direct stream URL or a Parliament TV URL
    if url.startswith("http") and ("parliamentlive.tv" in url or "parliament.tv" in url):
        # For Parliament TV URLs, we need to extract the stream URL first
        logger.info("This is a Parliament TV URL, extracting stream URL...")
        
        # Use extract-url.py to get the direct stream URL
        extract_url_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract-url.py")
        if not os.path.exists(extract_url_script):
            logger.error(f"extract-url.py script not found at {extract_url_script}")
            return False
        
        try:
            # Run the extract-url.py script to get the direct stream URL
            result = subprocess.run(
                [sys.executable, extract_url_script, url],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the output to get the direct stream URL
            output_lines = result.stdout.strip().split('\n')
            audio_url = None
            
            for line in output_lines:
                if line.startswith("Audio URL:"):
                    audio_url = line.replace("Audio URL:", "").strip()
                    break
            
            if not audio_url:
                # If no specific audio URL is found, try to use the video URL
                for line in output_lines:
                    if line.startswith("Video URL:"):
                        audio_url = line.replace("Video URL:", "").strip()
                        break
            
            if not audio_url:
                logger.error("Failed to extract audio URL from Parliament TV URL")
                return False
            
            logger.info(f"Extracted audio URL: {audio_url}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running extract-url.py: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error extracting stream URL: {e}")
            return False
    else:
        # For direct stream URLs, use the URL as is
        audio_url = url
    
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Use ffmpeg to extract audio
    try:
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
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        if os.path.exists(output_file):
            logger.info(f"Audio extraction successful: {output_file}")
            return True
        else:
            logger.error(f"Audio file not created: {output_file}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running ffmpeg: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error extracting audio: {e}")
        return False

def get_capture_info(db, capture_id):
    """Get capture information from the database."""
    try:
        # Use a direct SQL query to avoid model import issues
        from sqlalchemy import text
        
        query = text("""
            SELECT id, source_url, file_path, status, metadata, audio_file_path
            FROM capture_sessions
            WHERE id = :capture_id
        """)
        
        result = db.execute(query, {"capture_id": capture_id})
        capture = result.fetchone()
        
        if not capture:
            logger.error(f"Capture with ID {capture_id} not found")
            return None
        
        return capture
    except Exception as e:
        logger.error(f"Error getting capture info: {e}")
        return None

def update_capture_audio_path(db, capture_id, audio_path):
    """Update the audio file path for a capture."""
    try:
        # Use a direct SQL query to avoid model import issues
        from sqlalchemy import text
        
        # First check if the capture exists
        check_query = text("""
            SELECT id, metadata, audio_file_path
            FROM capture_sessions
            WHERE id = :capture_id
        """)
        
        result = db.execute(check_query, {"capture_id": capture_id})
        capture = result.fetchone()
        
        if not capture:
            logger.error(f"Capture with ID {capture_id} not found")
            return False
        
        # Update the audio_file_path directly
        update_query = text("""
            UPDATE capture_sessions
            SET audio_file_path = :audio_path
            WHERE id = :capture_id
        """)
        
        db.execute(update_query, {"capture_id": capture_id, "audio_path": audio_path})
        
        # Commit the changes
        db.commit()
        logger.info(f"Updated audio file path for capture {capture_id}: {audio_path}")
        return True
    except Exception as e:
        logger.error(f"Error updating capture audio path: {e}")
        db.rollback()
        return False

def process_capture(capture_id):
    """Process a capture to extract audio."""
    logger.info(f"Processing capture ID: {capture_id}")
    
    # Get a database session
    db = next(get_db())
    
    try:
        # Get capture information
        capture = get_capture_info(db, capture_id)
        
        if not capture:
            logger.error(f"Failed to get capture info for ID: {capture_id}")
            return False
        
        # Define the audio file path
        docker_audio_extracts_dir = "/app/data/temp/audio_extracts"
        os.makedirs(docker_audio_extracts_dir, exist_ok=True)
        
        # Format should be: capture_XXXX.audio.mp3 where XXXX is the zero-padded capture ID
        padded_capture_id = str(capture_id).zfill(4)
        audio_file_path = os.path.join(docker_audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
        
        # Extract audio - use source_url instead of url
        source_url = capture.source_url
        if not source_url:
            logger.error(f"No source URL found for capture {capture_id}")
            return False
            
        logger.info(f"Extracting audio from source URL: {source_url}")
        success = extract_audio(source_url, audio_file_path)
        
        if success:
            # Update the capture with the audio file path
            update_capture_audio_path(db, capture_id, audio_file_path)
            logger.info(f"Audio extraction completed for capture {capture_id}")
            return True
        else:
            logger.error(f"Audio extraction failed for capture {capture_id}")
            return False
    except Exception as e:
        logger.error(f"Error processing capture {capture_id}: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Extract audio for Parliament TV captures')
    parser.add_argument('capture_id', type=int, help='ID of the capture to process')
    args = parser.parse_args()
    
    success = process_capture(args.capture_id)
    
    if success:
        logger.info(f"Successfully processed capture {args.capture_id}")
        sys.exit(0)
    else:
        logger.error(f"Failed to process capture {args.capture_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
