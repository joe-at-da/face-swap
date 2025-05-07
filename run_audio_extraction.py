#!/usr/bin/env python3
"""
Run audio extraction for a specific capture ID.
This script directly uses the extract_audio function from the parliament_tv module.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('run-audio-extraction')

# Add the current directory to the path so we can import from backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the extract_audio function from the parliament_tv module
from backend.services.parliament_tv import extract_audio
from backend.db.session import get_db

def run_audio_extraction(capture_id):
    """Run audio extraction for a specific capture ID."""
    print(f"Running audio extraction for capture ID: {capture_id}")
    
    try:
        # Get a database session
        db = next(get_db())
        
        try:
            # Call the extract_audio function directly
            logger.info(f"Calling extract_audio function for capture ID: {capture_id}")
            result = extract_audio(db, capture_id)
            
            if result.get('success'):
                print(f"Audio extraction successful for capture ID: {capture_id}")
                print(f"Audio file: {result.get('audio_file')}")
                print(f"File size: {result.get('file_size', 'unknown')} bytes")
                return True
            else:
                print(f"Audio extraction failed for capture ID: {capture_id}")
                print(f"Error: {result.get('error')}")
                return False
        finally:
            # Always close the database session
            db.close()
            logger.info("Closed database session")
    except Exception as e:
        print(f"Error running audio extraction: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_audio_extraction.py <capture_id>")
        sys.exit(1)
    
    capture_id = sys.argv[1]
    success = run_audio_extraction(capture_id)
    
    if success:
        print("Audio extraction completed successfully")
        sys.exit(0)
    else:
        print("Audio extraction failed")
        sys.exit(1)
