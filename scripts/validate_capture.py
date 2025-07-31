#!/usr/bin/env python3
"""
Script to validate and fix capture database entries.
This ensures that video_path and other essential fields are properly set.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import centralized configuration
try:
    from backend.core.recognition_config import TimeoutConfig
except ImportError:
    # Fallback values if config module is not available
    class TimeoutConfig:
        MAX_RECOGNITION_PROCESSING_TIME = 60
        MAX_TRANSCRIPTION_PROCESSING_TIME = 60

import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the necessary models and settings
from backend.core.config import settings
from backend.db.models.capture import CaptureSession

def validate_and_fix_capture(capture_id=None, fix=True):
    """
    Validate and optionally fix database entries for a capture.
    
    Args:
        capture_id: ID of the capture to validate, or None for the latest
        fix: Whether to automatically fix issues (default: True)
    
    Returns:
        bool: True if validation passed or issues were fixed, False otherwise
    """
    # Create SQLAlchemy engine and session
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get the capture session
        if capture_id:
            capture = session.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
            if not capture:
                logger.error(f"Capture with ID {capture_id} not found")
                return False
        else:
            # Get the latest capture
            capture = session.query(CaptureSession).order_by(CaptureSession.id.desc()).first()
            if not capture:
                logger.error("No captures found in the database")
                return False
        
        logger.info(f"Validating capture with ID: {capture.id}")
        
        # Track if any changes were made
        changes_made = False
        
        # Check file paths
        file_path = capture.file_path
        video_path = capture.video_path
        
        # Check if file_path exists but video_path is missing
        if file_path and os.path.exists(file_path) and not video_path:
            logger.warning(f"video_path is missing but file_path exists: {file_path}")
            if fix:
                capture.video_path = file_path
                logger.info(f"Fixed: Set video_path to {file_path}")
                changes_made = True
        
        # Check if neither file_path nor video_path is set, but a file exists at the expected location
        if not file_path and not video_path:
            expected_path = f"/app/data/temp/capture_{capture.id:04d}.mp4"
            if os.path.exists(expected_path):
                logger.warning(f"Both file_path and video_path are missing, but file exists at: {expected_path}")
                if fix:
                    capture.file_path = expected_path
                    capture.video_path = expected_path
                    logger.info(f"Fixed: Set file_path and video_path to {expected_path}")
                    changes_made = True
        
        # Check if recognition is stuck in processing state
        if capture.recognition_status == "processing" and capture.recognition_started_at:
            # Check if it's been processing for more than 10 minutes
            now = datetime.datetime.now(capture.recognition_started_at.tzinfo)
            processing_time = now - capture.recognition_started_at
            if processing_time.total_seconds() > TimeoutConfig.MAX_RECOGNITION_PROCESSING_TIME:
                logger.warning(f"Recognition has been processing for {processing_time.total_seconds()/60:.1f} minutes")
                if fix:
                    capture.recognition_status = None
                    capture.recognition_progress = None
                    logger.info("Fixed: Reset recognition_status and recognition_progress")
                    changes_made = True
        
        # Check if transcription is stuck in processing state
        if capture.transcription_status == "processing" and capture.transcription_started_at:
            # Check if it's been processing for more than 10 minutes
            now = datetime.datetime.now(capture.transcription_started_at.tzinfo)
            processing_time = now - capture.transcription_started_at
            if processing_time.total_seconds() > TimeoutConfig.MAX_TRANSCRIPTION_PROCESSING_TIME:
                logger.warning(f"Transcription has been processing for {processing_time.total_seconds()/60:.1f} minutes")
                if fix:
                    capture.transcription_status = None
                    logger.info("Fixed: Reset transcription_status")
                    changes_made = True
        
        # Commit changes if any were made
        if changes_made and fix:
            session.commit()
            logger.info(f"Successfully fixed issues with capture ID: {capture.id}")
        elif not changes_made:
            logger.info(f"No issues found with capture ID: {capture.id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error validating capture: {str(e)}")
        return False
    
    finally:
        session.close()

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Validate and fix capture database entries')
    parser.add_argument('--id', type=int, help='ID of the capture to validate (default: latest)')
    parser.add_argument('--no-fix', action='store_true', help='Only validate, do not fix issues')
    args = parser.parse_args()
    
    # Run validation
    validate_and_fix_capture(args.id, not args.no_fix)
