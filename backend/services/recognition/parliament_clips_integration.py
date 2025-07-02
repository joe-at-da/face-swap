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
        
        # Check if we're running in Docker or locally
        self.docker_db_path = "/app/data/db/parliament.db"
        self.local_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data/db/parliament.db")
        
        # Use the path that exists
        if os.path.exists(self.docker_db_path):
            self.db_path = self.docker_db_path
            logger.info(f"Using Docker database path: {self.db_path}")
        elif os.path.exists(self.local_db_path):
            self.db_path = self.local_db_path
            logger.info(f"Using local database path: {self.db_path}")
        else:
            logger.warning("Neither Docker nor local database path exists. Creating local path.")
            os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
            self.db_path = self.local_db_path
            logger.info(f"Created and using local database path: {self.db_path}")
    
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
        try:
            logger.info(f"Saving {len(recognition_events)} recognition events to parliament_clips for video {video_id}")
            
            clips_saved = 0
            clips_failed = 0
            clip_ids = []
            
            # Process each recognition event
            for event in recognition_events:
                # Only process speaker events with text
                if event.get("type") == "speaker" and event.get("text"):
                    try:
                        # Create clip data for parliament_clips table
                        clip_data = {
                            'member_id': event.get("member_id", 0),
                            'transcript': event.get("text", ""),
                            'full_video_path': video_path,
                            'start_timestamp': str(event.get("start_time", 0)),
                            'end_timestamp': str(event.get("end_time", 0)),
                            'confidence': event.get("confidence", 0),
                            'recognition_method': event.get("recognition_method", "multimodal"),
                            'session_date': datetime.now().strftime("%Y-%m-%d"),
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'metadata': json.dumps({
                                'video_id': video_id,
                                'face_image_url': event.get("face_image_url", ""),
                                'matched_by': event.get("matched_by", "unknown")
                            })
                        }
                        
                        # Insert the clip into the parliament_clips table using direct SQLite connection
                        try:
                            conn = sqlite3.connect(self.db_path)
                            cursor = conn.cursor()
                            
                            # Prepare the SQL statement
                            fields = list(clip_data.keys())
                            placeholders = ', '.join(['?'] * len(fields))
                            values = [clip_data[field] for field in fields]
                            
                            # Execute the insert
                            cursor.execute(
                                f"INSERT INTO parliament_clips ({', '.join(fields)}) VALUES ({placeholders})",
                                values
                            )
                            
                            # Get the ID of the inserted clip
                            clip_id = cursor.lastrowid
                            conn.commit()
                            
                            if clip_id:
                                clips_saved += 1
                                clip_ids.append(clip_id)
                                logger.info(f"Saved parliament clip with ID {clip_id} for member {event.get('name', 'Unknown')}")
                            else:
                                clips_failed += 1
                                logger.warning(f"Failed to save parliament clip for member {event.get('name', 'Unknown')}")
                        except Exception as db_error:
                            clips_failed += 1
                            logger.error(f"Database error saving parliament clip: {str(db_error)}")
                        finally:
                            if conn:
                                conn.close()
                    
                    except Exception as e:
                        clips_failed += 1
                        logger.error(f"Error saving parliament clip: {str(e)}")
            
            return {
                "success": True,
                "clips_saved": clips_saved,
                "clips_failed": clips_failed,
                "clip_ids": clip_ids
            }
            
        except Exception as e:
            logger.exception(f"Error saving recognition events to parliament_clips: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "clips_saved": 0,
                "clips_failed": 0,
                "clip_ids": []
            }
    
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
