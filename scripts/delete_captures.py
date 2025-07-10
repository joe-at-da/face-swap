#!/usr/bin/env python3
"""
Delete all capture sessions and associated data from the database.

This script provides a clean slate by removing all capture-related data,
including associated files and database records.
"""

import os
import sys
import shutil
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models.capture import CaptureSession as Capture

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('delete-captures')

def check_table_exists(db, table_name):
    """Check if a table exists in the database."""
    try:
        result = db.execute(text(f"SELECT to_regclass('public.{table_name}');"))
        exists = result.scalar() is not None
        return exists
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def clean_database():
    """Clean all capture-related data from the database."""
    logger.info("Starting database cleanup for all capture-related data")
    
    # Get a database session
    db = next(get_db())
    
    try:
        # List of all tables that might have capture-related data
        tables_to_clean = [
            "capture_sessions",
            "capture_logs",
            "parliament_transcriptions",
            "speaker_identifications",
            "transcription_segments",
            "transcription_speakers"
        ]
        
        # First, check which tables actually exist
        existing_tables = []
        for table in tables_to_clean:
            if check_table_exists(db, table):
                existing_tables.append(table)
                logger.info(f"Table {table} exists and will be cleaned")
            else:
                logger.info(f"Table {table} does not exist, skipping")
        
        if not existing_tables:
            logger.info("No tables to clean found in the database")
            return
        
        # For each table that exists, delete its contents
        for table in existing_tables:
            try:
                # First try with a simple DELETE
                result = db.execute(text(f"DELETE FROM {table};"))
                db.commit()  # Commit after each table to avoid transaction issues
                logger.info(f"Cleaned table: {table}")
            except Exception as e:
                logger.warning(f"Error cleaning table {table}: {str(e)}")
                db.rollback()  # Rollback on error
                
                # Try with a more direct approach if available
                try:
                    # Disable triggers temporarily for this table
                    db.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER ALL;"))
                    result = db.execute(text(f"DELETE FROM {table};"))
                    db.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER ALL;"))
                    db.commit()
                    logger.info(f"Cleaned table {table} with triggers disabled")
                except Exception as e2:
                    logger.error(f"Failed to clean table {table}: {str(e2)}")
                    db.rollback()
        
        logger.info("Successfully cleaned all capture-related data from the database")
        
        # Clean SQLite database (parliament_clips.db)
        try:
            import sqlite3
            import os
            from pathlib import Path
            
            # Try multiple possible paths for the SQLite database
            possible_paths = [
                "/app/backend/parliament_clips.db",  # Docker container path
                str(Path(__file__).resolve().parent.parent / "backend" / "parliament_clips.db"),  # Local development path
                str(Path.home() / "Veedoo" / "Development" / "the-mp" / "backend" / "parliament_clips.db")  # User-specific path
            ]
            
            sqlite_db_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    sqlite_db_path = path
                    break
            
            if sqlite_db_path:
                logger.info(f"Cleaning SQLite database at {sqlite_db_path}")
                conn = sqlite3.connect(sqlite_db_path)
                cursor = conn.cursor()
                
                # First check if parliament_clips table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parliament_clips'")
                if cursor.fetchone():
                    # Count clips before deletion
                    cursor.execute("SELECT COUNT(*) FROM parliament_clips")
                    count = cursor.fetchone()[0]
                    logger.info(f"Found {count} clips in parliament_clips table")
                    
                    # Delete all clips
                    cursor.execute("DELETE FROM parliament_clips")
                    logger.info(f"Deleted {cursor.rowcount} clips from parliament_clips table")
                else:
                    logger.info("parliament_clips table not found in SQLite database")
                
                # Also check and clean other tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                sqlite_tables = cursor.fetchall()
                
                for table in sqlite_tables:
                    table_name = table[0]
                    if table_name != 'sqlite_sequence' and table_name != 'parliament_clips':  # Skip already processed tables
                        try:
                            cursor.execute(f"DELETE FROM {table_name}")
                            logger.info(f"Cleaned SQLite table: {table_name}")
                        except Exception as e:
                            logger.error(f"Error cleaning SQLite table {table_name}: {str(e)}")
                
                # Reset the autoincrement counters
                cursor.execute("DELETE FROM sqlite_sequence")
                
                conn.commit()
                conn.close()
                logger.info("Successfully cleaned SQLite database")
            else:
                logger.warning("SQLite parliament_clips database not found in any of the expected locations")
                for path in possible_paths:
                    logger.info(f"Tried path: {path}")
                
        except Exception as e:
            logger.error(f"Error cleaning SQLite database: {str(e)}")
            import traceback
            logger.error(f"SQLite cleanup traceback: {traceback.format_exc()}")
        
    except Exception as e:
        logger.error(f"Error cleaning database: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Roll back any changes
        db.rollback()
    finally:
        # Close the database session
        db.close()
        logger.info("Closed database session")

def clean_files():
    """Clean all capture-related files from the filesystem."""
    logger.info("Starting cleanup of capture-related files")
    
    # Paths to clean
    paths_to_clean = [
        "/app/data/temp",
        "/app/data/media",
        "/app/data/temp/audio_extracts"
    ]
    
    for path in paths_to_clean:
        try:
            if os.path.exists(path):
                # Remove all files in the directory but keep the directory itself
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    try:
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                            logger.info(f"Removed file: {item_path}")
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            logger.info(f"Removed directory: {item_path}")
                    except Exception as e:
                        logger.error(f"Error removing {item_path}: {str(e)}")
                logger.info(f"Cleaned directory: {path}")
            else:
                # Create the directory if it doesn't exist
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created directory: {path}")
        except Exception as e:
            logger.error(f"Error cleaning path {path}: {str(e)}")

def clean_all():
    """Clean all capture-related data from the database and filesystem."""
    logger.info("Starting complete cleanup of all capture-related data")
    
    # Clean the database
    clean_database()
    
    # Clean the filesystem
    clean_files()
    
    logger.info("Completed cleanup of all capture-related data")

if __name__ == "__main__":
    clean_all()
