#!/usr/bin/env python
"""
Script to create and manage the parliament_clips table in the local SQLite database
"""
import os
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_db_directory():
    """Ensure the database directory exists"""
    db_dir = "/app/data/db"
    os.makedirs(db_dir, exist_ok=True)
    return db_dir

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_dir = ensure_db_directory()
    db_path = os.path.join(db_dir, "parliament.db")
    return sqlite3.connect(db_path)

def create_parliament_clips_table():
    """Create the parliament_clips table if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create the parliament_clips table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS parliament_clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Required fields
            member_id INTEGER NOT NULL,
            transcript TEXT NOT NULL,
            full_video_path TEXT NOT NULL,
            session_date TEXT NULL,  -- SQLite uses TEXT for dates
            session_type TEXT NULL,
            start_timestamp TEXT NOT NULL,
            end_timestamp TEXT NOT NULL,
            
            -- Optional fields
            transcript_embedding TEXT NULL,  -- JSON string for vector storage
            clip_url TEXT NULL,
            debate_topic TEXT NULL,
            status TEXT NULL DEFAULT 'pending_review',
            processing_notes TEXT NULL,
            confidence_score REAL NULL,
            audio_quality_score REAL NULL,
            duration_seconds REAL NULL,
            
            -- Metadata fields
            is_deleted INTEGER NOT NULL DEFAULT 0,  -- SQLite uses INTEGER for boolean
            deleted_at TEXT NULL,  -- SQLite uses TEXT for timestamps
            last_synced_at TEXT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parliament_clips_member_id ON parliament_clips(member_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parliament_clips_session_date ON parliament_clips(session_date)')
        
        conn.commit()
        logger.info("Parliament clips table created or already exists")
        return True
    except Exception as e:
        logger.error(f"Error creating parliament_clips table: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def insert_parliament_clip(clip_data: Dict[str, Any]):
    """
    Insert a new parliament clip into the database
    
    Args:
        clip_data: Dictionary containing clip data with at least the required fields:
                  member_id, transcript, full_video_path, start_timestamp, end_timestamp
    
    Returns:
        ID of the inserted clip or None if failed
    """
    # Validate required fields
    required_fields = ['member_id', 'transcript', 'full_video_path', 'start_timestamp', 'end_timestamp']
    for field in required_fields:
        if field not in clip_data:
            logger.error(f"Missing required field: {field}")
            return None
    
    # Calculate duration if not provided
    if 'duration_seconds' not in clip_data and 'start_timestamp' in clip_data and 'end_timestamp' in clip_data:
        try:
            # Parse timestamps in format HH:MM:SS
            start_parts = clip_data['start_timestamp'].split(':')
            end_parts = clip_data['end_timestamp'].split(':')
            
            start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
            end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
            
            clip_data['duration_seconds'] = end_seconds - start_seconds
        except Exception as e:
            logger.warning(f"Could not calculate duration: {str(e)}")
    
    # Handle transcript embedding (convert to JSON string if it's a list or dict)
    if 'transcript_embedding' in clip_data and clip_data['transcript_embedding'] is not None:
        if isinstance(clip_data['transcript_embedding'], (list, dict)):
            clip_data['transcript_embedding'] = json.dumps(clip_data['transcript_embedding'])
    
    # Set timestamps
    now = datetime.now().isoformat()
    if 'created_at' not in clip_data:
        clip_data['created_at'] = now
    if 'updated_at' not in clip_data:
        clip_data['updated_at'] = now
    if 'last_synced_at' not in clip_data:
        clip_data['last_synced_at'] = now
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Prepare fields and values for the SQL query
        fields = list(clip_data.keys())
        placeholders = ', '.join(['?' for _ in fields])
        values = [clip_data[field] for field in fields]
        
        # Insert the clip
        cursor.execute(
            f"INSERT INTO parliament_clips ({', '.join(fields)}) VALUES ({placeholders})",
            values
        )
        
        # Get the ID of the inserted clip
        clip_id = cursor.lastrowid
        
        conn.commit()
        logger.info(f"Inserted parliament clip with ID {clip_id}")
        return clip_id
    except Exception as e:
        logger.error(f"Error inserting parliament clip: {str(e)}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_parliament_clip(clip_id: int):
    """
    Get a parliament clip by ID
    
    Args:
        clip_id: ID of the clip to retrieve
    
    Returns:
        Dictionary with clip data or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM parliament_clips WHERE id = ?", (clip_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Convert row to dictionary
        columns = [column[0] for column in cursor.description]
        clip_data = {columns[i]: row[i] for i in range(len(columns))}
        
        # Parse transcript embedding if it's a JSON string
        if 'transcript_embedding' in clip_data and clip_data['transcript_embedding']:
            try:
                clip_data['transcript_embedding'] = json.loads(clip_data['transcript_embedding'])
            except:
                pass  # Keep as string if not valid JSON
        
        return clip_data
    except Exception as e:
        logger.error(f"Error retrieving parliament clip {clip_id}: {str(e)}")
        return None
    finally:
        conn.close()

def main():
    """Main function to create the parliament_clips table"""
    logger.info("Creating parliament_clips table...")
    success = create_parliament_clips_table()
    
    if success:
        logger.info("Parliament clips table created successfully")
        
        # Example: Insert a test clip
        test_clip = {
            'member_id': 1234,
            'transcript': 'This is a test transcript',
            'full_video_path': '/app/data/videos/test_video.mp4',
            'session_date': datetime.now().strftime('%Y-%m-%d'),
            'session_type': 'commons',
            'start_timestamp': '00:10:53',
            'end_timestamp': '00:11:43',
            'debate_topic': 'Test Debate',
            'status': 'pending_review'
        }
        
        clip_id = insert_parliament_clip(test_clip)
        if clip_id:
            logger.info(f"Test clip inserted with ID {clip_id}")
            
            # Retrieve the test clip
            retrieved_clip = get_parliament_clip(clip_id)
            if retrieved_clip:
                logger.info(f"Retrieved test clip: {retrieved_clip}")
            else:
                logger.warning("Could not retrieve test clip")
        else:
            logger.warning("Could not insert test clip")
    else:
        logger.error("Failed to create parliament_clips table")

if __name__ == "__main__":
    main()
