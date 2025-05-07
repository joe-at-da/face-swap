#!/usr/bin/env python
"""
Migration script to add recognition columns to the CaptureSession table.

This script adds the following columns to the capture_sessions table:
- video_path: Path to the video file (replacing file_path)
- audio_path: Path to the audio file (replacing audio_file_path)
- facial_recognition_path: Path to video with facial recognition
- speaker_identification_path: Path to video with speaker identification
- speaker_identification_results: Path to speaker identification results file
- voice_identification_results: Path to voice identification results file
- combined_recognition_results: Path to combined recognition results file

Usage:
    python scripts/migrations/add_recognition_columns.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.config import settings
from backend.db.session import engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add recognition columns to the CaptureSession table."""
    logger.info("Starting migration to add recognition columns to the CaptureSession table")
    
    # SQL statements to add new columns
    sql_statements = [
        # Add new columns
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS video_path VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS audio_path VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS facial_recognition_path VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS speaker_identification_path VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS speaker_identification_results VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS voice_identification_results VARCHAR(255);",
        "ALTER TABLE capture_sessions ADD COLUMN IF NOT EXISTS combined_recognition_results VARCHAR(255);",
        
        # Copy data from old columns to new ones if they exist
        "UPDATE capture_sessions SET video_path = file_path WHERE file_path IS NOT NULL AND video_path IS NULL;",
        "UPDATE capture_sessions SET audio_path = audio_file_path WHERE audio_file_path IS NOT NULL AND audio_path IS NULL;"
    ]
    
    # Execute the SQL statements
    with engine.connect() as connection:
        for sql in sql_statements:
            try:
                logger.info(f"Executing: {sql}")
                connection.execute(text(sql))
                connection.commit()
            except Exception as e:
                logger.error(f"Error executing SQL: {sql}")
                logger.error(f"Error details: {str(e)}")
                connection.rollback()
                raise
    
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    run_migration()
