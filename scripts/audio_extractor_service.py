#!/usr/bin/env python3
"""
Audio Extractor Service

This script runs as a background service and automatically extracts audio for new captures.
It polls the database for new captures and extracts audio for them.

Usage:
    python audio_extractor_service.py

The script will run indefinitely, checking for new captures every 10 seconds.
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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
        return db
    except Exception as e:
        logger.error(f"Error getting database session: {e}")
        db.close()
        return None

def get_recent_captures(db, minutes=60):
    """Get recent captures from the database."""
    try:
        # Query for recent captures that are completed but don't have audio
        query = text("""
            SELECT c.id, c.url, c.file_path, c.status, c.metadata
            FROM capture_sessions c
            WHERE c.status = 'completed'
            AND c.created_at > :since
            AND (
                c.audio_file_path IS NULL
                OR c.audio_file_path = ''
                OR (c.metadata IS NOT NULL AND c.metadata->>'audio_file_path' IS NULL)
            )
            ORDER BY c.created_at DESC
        """)
        
        since = datetime.now() - timedelta(minutes=minutes)
        result = db.execute(query, {"since": since})
        captures = result.fetchall()
        
        logger.info(f"Found {len(captures)} recent captures without audio")
        return captures
    except Exception as e:
        logger.error(f"Error getting recent captures: {e}")
        return []

def extract_audio_for_capture(capture_id):
    """Extract audio for a capture."""
    try:
        # Path to the extract_audio_standalone.py script
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_audio_standalone.py")
        
        if not os.path.exists(script_path):
            logger.error(f"Script not found at {script_path}")
            return False
        
        # Run the script
        logger.info(f"Extracting audio for capture {capture_id}")
        cmd = [sys.executable, script_path, str(capture_id)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Audio extraction successful for capture {capture_id}")
            return True
        else:
            logger.error(f"Audio extraction failed for capture {capture_id}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error extracting audio for capture {capture_id}: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting Audio Extractor Service")
    
    while True:
        try:
            # Get a database session
            db = get_db()
            if not db:
                logger.error("Failed to get database session, retrying in 10 seconds")
                time.sleep(10)
                continue
            
            # Get recent captures
            captures = get_recent_captures(db)
            
            # Process each capture
            for capture in captures:
                capture_id = capture.id
                logger.info(f"Processing capture {capture_id}")
                
                # Extract audio
                success = extract_audio_for_capture(capture_id)
                
                if success:
                    logger.info(f"Successfully processed capture {capture_id}")
                else:
                    logger.error(f"Failed to process capture {capture_id}")
            
            # Close the database session
            db.close()
            
            # Sleep for 10 seconds
            logger.info("Sleeping for 10 seconds")
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, exiting")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
