#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import json
import subprocess
import datetime
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - extract-audio-for-all-captures - %(levelname)s - %(message)s",
)
logger = logging.getLogger("extract-audio-for-all-captures")

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    # Try importing directly
    from backend.db.session import SessionLocal
    from backend.db.models.capture import CaptureSession
except ImportError:
    # Try Docker container paths
    sys.path.insert(0, "/app")
    try:
        from backend.db.session import SessionLocal
        from backend.db.models.capture import CaptureSession
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        sys.exit(1)

def extract_audio_for_capture(capture_id: int, force: bool = False) -> bool:
    """
    Extract audio for a specific capture ID using the Parliament TV URL stored in the database.
    
    Args:
        capture_id: The ID of the capture to extract audio for
        force: Whether to force extraction even if audio file already exists
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get the capture from the database
    db = SessionLocal()
    try:
        capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture {capture_id} not found")
            return False
            
        # Check if the capture has a source URL
        if not capture.source_url:
            logger.error(f"Capture {capture_id} has no source URL")
            return False
            
        # Format the audio file path based on the ID
        audio_file_path = f"/app/data/temp/audio_extracts/capture_{str(capture_id).zfill(4)}.audio.mp3"
        
        # Check if the audio file already exists
        if os.path.exists(audio_file_path) and not force:
            logger.info(f"Audio file already exists for capture {capture_id}: {audio_file_path}")
            
            # Update the database with the audio file path if it's not already set
            if not capture.audio_file_path:
                capture.audio_file_path = audio_file_path
                capture.updated_at = datetime.datetime.now()
                db.commit()
                logger.info(f"Updated audio file path for capture {capture_id}")
                
            return True
            
        # Create the audio_extracts directory if it doesn't exist
        os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)
        
        # Extract the audio using the extract_audio_only.py script
        extract_script = "/app/scripts/extract_audio_only.py"
        if not os.path.exists(extract_script):
            extract_script = os.path.join(os.path.dirname(__file__), "extract_audio_only.py")
            
        if not os.path.exists(extract_script):
            logger.error(f"Extract script not found: {extract_script}")
            return False
            
        # Run the extract_audio_only.py script
        cmd = [sys.executable, extract_script, capture.source_url, audio_file_path]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Failed to extract audio for capture {capture_id}: {stderr.decode()}")
            return False
            
        logger.info(f"Successfully extracted audio for capture {capture_id}")
        
        # Update the database with the audio file path
        capture.audio_file_path = audio_file_path
        capture.updated_at = datetime.datetime.now()
        db.commit()
        
        logger.info(f"Updated audio file path for capture {capture_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error extracting audio for capture {capture_id}: {e}")
        return False
    finally:
        db.close()

def extract_audio_for_all_captures(force: bool = False) -> bool:
    """
    Extract audio for all captures that have a source URL.
    
    Args:
        force: Whether to force extraction even if audio file already exists
        
    Returns:
        bool: True if all extractions were successful, False otherwise
    """
    # Get all captures from the database
    db = SessionLocal()
    try:
        captures = db.query(CaptureSession).filter(CaptureSession.source_url.isnot(None)).all()
        
        if not captures:
            logger.info("No captures found with source URLs")
            return True
            
        logger.info(f"Found {len(captures)} captures with source URLs")
        
        # Extract audio for each capture
        success_count = 0
        for capture in captures:
            logger.info(f"Processing capture {capture.id}: {capture.title}")
            
            if extract_audio_for_capture(capture.id, force):
                success_count += 1
                
            # Add a small delay to avoid overwhelming the system
            time.sleep(1)
            
        logger.info(f"Successfully extracted audio for {success_count} out of {len(captures)} captures")
        return success_count == len(captures)
    except Exception as e:
        logger.error(f"Error extracting audio for all captures: {e}")
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Extract audio for captures")
    parser.add_argument("--capture-id", type=int, help="ID of the capture to extract audio for")
    parser.add_argument("--force", action="store_true", help="Force extraction even if audio file already exists")
    args = parser.parse_args()
    
    if args.capture_id:
        # Extract audio for a specific capture
        success = extract_audio_for_capture(args.capture_id, args.force)
    else:
        # Extract audio for all captures
        success = extract_audio_for_all_captures(args.force)
        
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
