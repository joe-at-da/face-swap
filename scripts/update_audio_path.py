#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - update-audio-path - %(levelname)s - %(message)s",
)
logger = logging.getLogger("update-audio-path")

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

def update_audio_path(capture_id: int) -> bool:
    """
    Update the audio file path for a specific capture ID.
    
    Args:
        capture_id: The ID of the capture to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Format the audio file path based on the ID
    audio_file_path = f"/app/data/temp/audio_extracts/capture_{str(capture_id).zfill(4)}.audio.mp3"
    
    # Check if the audio file exists
    if not os.path.exists(audio_file_path):
        logger.error(f"Audio file does not exist: {audio_file_path}")
        return False
    
    # Update the database
    db = SessionLocal()
    try:
        capture = db.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture with ID {capture_id} not found")
            return False
            
        # Update the audio file path
        capture.audio_file_path = audio_file_path
        capture.updated_at = datetime.datetime.now()
        db.commit()
        
        logger.info(f"Updated audio file path for capture {capture_id}: {audio_file_path}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating audio file path: {e}")
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Update audio file path for a capture")
    parser.add_argument("capture_id", type=int, help="ID of the capture to update")
    args = parser.parse_args()
    
    success = update_audio_path(args.capture_id)
    if success:
        logger.info(f"Successfully updated audio file path for capture {args.capture_id}")
    else:
        logger.error(f"Failed to update audio file path for capture {args.capture_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
