"""
Parliament Clips Integration Service.

This service integrates the multimodal recognition service with the local SQLite parliament_clips database,
ensuring that recognized clips are properly saved for local development and testing.
"""

import os
import sys
import json
import logging
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to sys.path to allow importing from scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from scripts.create_parliament_clips_model import get_parliament_clip

# Set up logging
logger = logging.getLogger(__name__)

class ParliamentClipsIntegrationService:
    """Service for integrating recognition events with the local SQLite parliament_clips database."""
    
    def __init__(self):
        """Initialize the parliament clips integration service."""
        logger.info("Initializing ParliamentClipsIntegrationService")
        
        # Define database paths with correct location
        self.docker_db_path = "/app/backend/parliament_clips.db"  # Path in Docker container
        self.local_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "backend/parliament_clips.db")  # Local path
        
        # Use the path that exists
        if os.path.exists(self.docker_db_path):
            self.db_path = self.docker_db_path
            logger.info(f"Using Docker database path: {self.db_path}")
        elif os.path.exists(self.local_db_path):
            self.db_path = self.local_db_path
            logger.info(f"Using local database path: {self.db_path}")
        else:
            logger.warning("Parliament clips database doesn't exist. Creating it at the local path.")
            # Ensure the directory exists
            parent_dir = os.path.dirname(self.local_db_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            # Create an empty database file
            self.db_path = self.local_db_path
            # Create the database and necessary table
            self._create_parliament_clips_table()
            logger.info(f"Created and using local database path: {self.db_path}")
            
    def _create_parliament_clips_table(self):
        """Create the parliament_clips table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create the parliament_clips table with the correct schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parliament_clips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    transcript TEXT,
                    full_video_path TEXT,
                    start_timestamp TEXT,
                    end_timestamp TEXT,
                    confidence_score REAL,
                    duration_seconds REAL,
                    session_date TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            logger.info("Successfully created parliament_clips table")
        except Exception as e:
            logger.error(f"Error creating parliament_clips table: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def save_recognition_events_to_parliament_clips(self, 
                                                   video_id: int, 
                                                   recognition_events: List[Dict[str, Any]],
                                                   video_path: str) -> Dict[str, Any]:
        """
        Save recognition events to the local SQLite parliament_clips database.
        
        Args:
            video_id: ID of the video
            recognition_events: List of recognition events
            video_path: Path to the full video
            
        Returns:
            Dict with results of the operation
        """
        logger.info(f"===== SAVING RECOGNITION EVENTS TO PARLIAMENT_CLIPS =====")
        logger.info(f"Video ID: {video_id}, Video Path: {video_path}")
        logger.info(f"Total recognition events: {len(recognition_events)}")
        
        # Log some stats about the recognition events
        event_types = {}
        for event in recognition_events:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        logger.info(f"Event types breakdown: {event_types}")
        
        # Create the database and table if they don't exist
        self._create_parliament_clips_table()
        
        clips_saved = 0
        errors = []
        
        # Filter for speaker events with text
        speaker_events = [event for event in recognition_events if event.get("type") == "speaker" and event.get("text")]
        logger.info(f"Found {len(speaker_events)} speaker events with text")
        
        # Log a sample of the speaker events for debugging
        if speaker_events:
            sample_event = speaker_events[0]
            logger.info(f"Sample speaker event: {json.dumps(sample_event, indent=2)}")
        
        member_id_counts = {}
        for event in speaker_events:
            # Extract data from the event
            start_time = event.get("start_time", 0)
            end_time = event.get("end_time", 0)
            text = event.get("text", "")
            member_id = event.get("member_id", "")
            confidence = event.get("confidence", 0.0)
            
            # Count member IDs for debugging
            member_id_counts[member_id] = member_id_counts.get(member_id, 0) + 1
            
            # Skip events without a member_id
            if not member_id:
                logger.warning(f"Skipping event without member_id at {start_time}-{end_time}")
                logger.debug(f"Full event data: {json.dumps(event, indent=2)}")
                errors.append(f"Event at {start_time}-{end_time} has no member_id")
                continue
                
            logger.info(f"Processing event for member_id: {member_id} at {start_time}-{end_time}")
            
            # Calculate duration in seconds
            duration_seconds = end_time - start_time
            
            # Verify video_path exists
            if not os.path.exists(video_path):
                logger.error(f"❌ Video path does not exist: {video_path}")
                errors.append(f"Video path does not exist: {video_path}")
                continue
                
            # Create clip data for parliament_clips table
            clip_data = {
                'member_id': member_id,
                'transcript': text,
                'full_video_path': video_path,
                'start_timestamp': str(start_time),
                'end_timestamp': str(end_time),
                'confidence_score': confidence,
                'duration_seconds': duration_seconds,
                'session_date': datetime.now().strftime("%Y-%m-%d"),
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'metadata': json.dumps({
                    'video_id': video_id,
                    'face_image_url': event.get("face_image_url", ""),
                    'matched_by': event.get("matched_by", "unknown"),
                    'recognition_method': event.get("recognition_method", "multimodal")
                })
            }
            
            logger.info(f"Prepared data for clip: member_id={member_id}, duration={duration_seconds:.2f}s")
            
            # Insert into database
            conn = None
            try:
                # Check if clip already exists
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Prepare the SQL statement
                fields = list(clip_data.keys())
                placeholders = ', '.join(['?'] * len(fields))
                values = [clip_data[field] for field in fields]
                
                # Log the SQL statement for debugging
                sql_statement = f"INSERT INTO parliament_clips ({', '.join(fields)}) VALUES ({placeholders})"
                logger.debug(f"Executing SQL: {sql_statement}")
                
                # Execute the insert
                cursor.execute(sql_statement, values)
                
                # Get the ID of the inserted clip
                clip_id = cursor.lastrowid
                conn.commit()
                conn.close()
                conn = None
                
                if clip_id:
                    clips_saved += 1
                    logger.info(f"✅ Successfully saved clip with ID {clip_id} for member {member_id}")
                else:
                    logger.warning(f"⚠️ No clip ID returned when saving clip for member {member_id}")
                    errors.append(f"No clip ID returned for member {member_id}")
                
            except Exception as e:
                logger.error(f"❌ Error saving clip to parliament_clips database: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                errors.append(f"Error saving clip: {str(e)}")
                if conn:
                    conn.close()
        
        # Log summary of member IDs
        logger.info(f"Member ID counts: {member_id_counts}")
        
        # Check database size and contents after saving
        try:
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            logger.info(f"Parliament clips database size: {db_size} bytes")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM parliament_clips")
            total_clips = cursor.fetchone()[0]
            logger.info(f"Total clips in database: {total_clips}")
            
            # Get a sample of clips if any exist
            if total_clips > 0:
                cursor.execute("SELECT id, member_id, start_timestamp, end_timestamp FROM parliament_clips LIMIT 5")
                sample_clips = cursor.fetchall()
                logger.info(f"Sample clips: {sample_clips}")
            
            conn.close()
        except Exception as e:
            logger.error(f"Error checking database after saving: {str(e)}")
        
        # Return results
        success = clips_saved > 0
        result = {
            "success": success,
            "clips_saved": clips_saved,
            "errors": errors
        }
        
        if success:
            logger.info(f"✅ Successfully saved {clips_saved} clips to parliament_clips database")
        else:
            logger.warning(f"❌ Failed to save any clips to parliament_clips database. Errors: {errors}")
            
        return result
    
    def get_parliament_clips_for_video(self, video_id: int) -> Dict[str, Any]:
        """
        Get all parliament clips associated with a video ID.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Dict with clips data
        """
        try:
            # This would require a custom query to the SQLite database
            # For now, we'll return a placeholder
            return {
                "success": True,
                "message": f"Feature not implemented: Get parliament clips for video {video_id}",
                "clips": []
            }
        except Exception as e:
            logger.error(f"Error getting parliament clips for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "clips": []
            }
