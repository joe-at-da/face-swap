"""
Parliament Clips Integration Service.

This service integrates the multimodal recognition service with the local SQLite parliament_clips database,
ensuring that recognized clips are properly saved for local development and testing.
It also integrates with Supabase to ensure clips are available in the production environment.
"""

import os
import sys
import json
import logging
import sqlite3
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to sys.path to allow importing from scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from scripts.create_parliament_clips_model import get_parliament_clip
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.integration.supabase_export import format_clips_for_supabase

# Set up logging
logger = logging.getLogger(__name__)

class ParliamentClipsIntegrationService:
    """Service for integrating recognition events with the local SQLite parliament_clips database."""
    
    def __init__(self):
        """Initialize the parliament clips integration service."""
        logger.info("Initializing ParliamentClipsIntegrationService")
        
        # Initialize Supabase integration
        self.supabase_integration = SupabaseIntegration()
        
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
                    member_id TEXT NOT NULL,
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
        member_id_counts = {}
        confidence_distribution = {
            "0.0-0.1": 0,
            "0.1-0.15": 0,
            "0.15-0.2": 0,
            "0.2-0.3": 0,
            "0.3+": 0
        }
        
        for event in recognition_events:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Count member IDs
            if event_type == "speaker":
                member_id = event.get("member_id", "none")
                member_id_counts[member_id] = member_id_counts.get(member_id, 0) + 1
                
                # Track confidence distribution
                confidence = event.get("confidence", 0.0)
                if confidence < 0.1:
                    confidence_distribution["0.0-0.1"] += 1
                elif confidence < 0.15:
                    confidence_distribution["0.1-0.15"] += 1
                elif confidence < 0.2:
                    confidence_distribution["0.15-0.2"] += 1
                elif confidence < 0.3:
                    confidence_distribution["0.2-0.3"] += 1
                else:
                    confidence_distribution["0.3+"] += 1
        
        logger.info(f"Event types breakdown: {event_types}")
        logger.info(f"Member ID distribution: {member_id_counts}")
        logger.info(f"Confidence score distribution: {confidence_distribution}")
        
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
            
            # Ensure member_id is stored as a string to handle UUIDs properly
            if member_id:
                member_id = str(member_id)
            
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
            
            # Now export clips to Supabase
            try:
                logger.info(f"Exporting {clips_saved} clips to Supabase")
                self._export_clips_to_supabase(video_id, recognition_events, video_path)
            except Exception as e:
                logger.error(f"Error exporting clips to Supabase: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                result["supabase_export_error"] = str(e)
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query clips for the given video ID
            cursor.execute("""
                SELECT * FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = ?
            """, (str(video_id),))
            
            clips = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                clip = {
                    'id': row[0],
                    'member_id': row[1],
                    'transcript': row[2],
                    'full_video_path': row[3],
                    'start_timestamp': row[4],
                    'end_timestamp': row[5],
                    'confidence_score': row[6],
                    'duration_seconds': row[7],
                    'session_date': row[8],
                    'created_at': row[9],
                    'updated_at': row[10],
                    'metadata': json.loads(row[11]) if row[11] else {}
                }
                clips.append(clip)
            
            conn.close()
            
            logger.info(f"Found {len(clips)} clips for video {video_id}")
            return {
                "success": True,
                "clips": clips
            }
        except Exception as e:
            logger.error(f"Error getting parliament clips for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "clips": []
            }
    
    def _export_clips_to_supabase(self, video_id: int, recognition_events: List[Dict[str, Any]], video_path: str) -> Dict[str, Any]:
        """
        Export clips to Supabase after saving them locally.
        
        Args:
            video_id: ID of the video
            recognition_events: List of recognition events
            video_path: Path to the video file
            
        Returns:
            Dict with export status and results
        """
        import uuid  # Ensure uuid is imported in this method's scope
        
        # Initialize cache for temporary Speaker objects
        temp_members_cache = {}
        logger.info(f"===== EXPORTING CLIPS TO SUPABASE =====")
        logger.info(f"Video ID: {video_id}, Video Path: {video_path}")
        
        try:
            # Get video metadata from the database
            from backend.db.session import get_db
            from backend.db.models import CaptureSession
            
            db_generator = get_db()
            db = next(db_generator)
            
            video = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
            if not video:
                logger.error(f"Video not found: {video_id}")
                return {"success": False, "error": f"Video not found: {video_id}"}
            
            # Extract metadata
            metadata = {}
            if video.metadata:
                try:
                    if isinstance(video.metadata, str):
                        metadata = json.loads(video.metadata)
                    elif isinstance(video.metadata, dict):
                        metadata = video.metadata
                except Exception as e:
                    logger.error(f"Error parsing video metadata: {str(e)}")
            
            # Retrieve clips from the local SQLite database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query clips for the given video ID
            cursor.execute("""
                SELECT * FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = ?
            """, (str(video_id),))
            
            clips = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                clip = {
                    'id': row[0],
                    'member_id': row[1],
                    'transcript': row[2],
                    'full_video_path': row[3],
                    'start_timestamp': row[4],
                    'end_timestamp': row[5],
                    'confidence_score': row[6],
                    'duration_seconds': row[7],
                    'session_date': row[8],
                    'created_at': row[9],
                    'updated_at': row[10],
                    'metadata': json.loads(row[11]) if row[11] else {}
                }
                clips.append(clip)
            
            conn.close()
            
            logger.info(f"Found {len(clips)} clips in local database for video {video_id}")
            
            # If no clips found in the database, check if we can create them from recognition events
            if not clips and recognition_events:
                logger.info(f"No clips found in database, creating from {len(recognition_events)} recognition events")
                
                # Count how many events are filtered out for different reasons
                filtered_stats = {
                    "not_speaker_event": 0,
                    "no_member_id": 0,
                    "default_unknown": 0,
                    "low_confidence": 0,
                    "valid_clips": 0
                }
                
                # Create clips from recognition events
                for event in recognition_events:
                    if event.get("type") != "speaker":
                        filtered_stats["not_speaker_event"] += 1
                        continue
                        
                    if not event.get("member_id"):
                        filtered_stats["no_member_id"] += 1
                        logger.debug(f"Skipping event with no member_id: {event}")
                        continue
                        
                    if event.get("member_id") == "default_unknown":
                        filtered_stats["default_unknown"] += 1
                        logger.debug(f"Skipping event with default_unknown member_id")
                        continue
                        
                    confidence = event.get("confidence", 0.0)
                    if confidence < 0.15:
                        filtered_stats["low_confidence"] += 1
                        logger.debug(f"Skipping low confidence event: {confidence} < 0.15")
                        continue
                        
                    # This event passes all filters
                    filtered_stats["valid_clips"] += 1
                    
                    clip = {
                        'id': str(uuid.uuid4()),
                        'member_id': event.get("member_id"),
                        'transcript': event.get("text", ""),
                        'full_video_path': video_path,
                        'start_timestamp': event.get("start_time", 0),
                        'end_timestamp': event.get("end_time", 0),
                        'confidence_score': confidence,
                        'duration_seconds': event.get("end_time", 0) - event.get("start_time", 0),
                        'session_date': datetime.now().strftime("%Y-%m-%d"),
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'metadata': {
                            'video_id': str(video_id),
                            'matched_by': event.get("matched_by", "unknown"),
                            'face_image_url': event.get("face_image_url", "")
                        }
                    }
                    clips.append(clip)
                    
                logger.info(f"Recognition events filtering stats: {filtered_stats}")
                logger.info(f"Created {len(clips)} clips from recognition events")
            
            # Create a structured recognition results dict with speaker appearances
            recognition_results = {
                "recognition_events": recognition_events,
                "speaker_appearances": []
            }
            
            # Add speaker appearances from clips
            filtered_clips_stats = {
                "default_unknown": 0,
                "low_confidence": 0,
                "valid_clips": 0
            }
            
            for clip in clips:
                # Skip unknown members
                if clip['member_id'] == "default_unknown":
                    filtered_clips_stats["default_unknown"] += 1
                    logger.info(f"Skipping clip with default_unknown member_id")
                    continue
                
                # Log the member ID for debugging
                logger.info(f"Processing clip with member_id: {clip['member_id']} (type: {type(clip['member_id']).__name__})")
                
                # Set a minimum confidence threshold for including clips
                if clip['confidence_score'] < 0.15:  # Lowered threshold to include existing clips
                    filtered_clips_stats["low_confidence"] += 1
                    logger.info(f"Skipping low confidence clip: {clip['confidence_score']} < 0.15")
                    continue
                    
                # This clip passes all filters
                filtered_clips_stats["valid_clips"] += 1
                    
                appearance = {
                    "member_id": clip['member_id'],
                    "member_name": "Unknown",  # We'll try to get the name from the database
                    "start_time": clip['start_timestamp'],
                    "end_time": clip['end_timestamp'],
                    "confidence": clip['confidence_score'],
                    "transcript": clip['transcript'],
                    "face_image_url": clip['metadata'].get('face_image_url', ""),
                    "matched_by": clip['metadata'].get('matched_by', "unknown")
                }
                
                # Try to get member name from the database
                try:
                    from backend.db.models import Speaker
                    
                    # Check if member_id is a UUID string (from facial recognition)
                    import uuid
                    member_id_str = str(clip['member_id'])
                    is_uuid = False
                    try:
                        uuid_obj = uuid.UUID(member_id_str)
                        is_uuid = True
                        logger.info(f"Member ID {member_id_str} is a UUID")
                    except ValueError:
                        is_uuid = False
                    
                    # Try multiple approaches to find the speaker
                    member = None
                    
                    # Skip direct ID match since Speaker.id is an integer and clip['member_id'] is a UUID string
                    # Instead, first try parliament_id match
                    try:
                        member = db.query(Speaker).filter(Speaker.parliament_id == member_id_str).first()
                        if member:
                            logger.info(f"Found member by parliament_id: {member_id_str}")
                    except Exception as e:
                        logger.warning(f"Error finding member by parliament_id: {str(e)}")
                    
                    # Second try: if it's a UUID, try to find by string representation in any field
                    if not member and is_uuid:
                        try:
                            # Try a more flexible search if it's a UUID
                            member = db.query(Speaker).filter(
                                (Speaker.parliament_id.like(f"%{member_id_str}%")) |
                                (Speaker.name.like(f"%{member_id_str}%"))
                            ).first()
                            if member:
                                logger.info(f"Found member by flexible search: {member_id_str}")
                        except Exception as e:
                            logger.warning(f"Error finding member by flexible search: {str(e)}")
                    
                    # Third try: look up by name if the member_id might be a name
                    if not member and not is_uuid:
                        try:
                            # Try to find by name if the member_id is not a UUID
                            member = db.query(Speaker).filter(Speaker.name.ilike(f"%{member_id_str}%")).first()
                            if member:
                                logger.info(f"Found member by name search: {member_id_str}")
                        except Exception as e:
                            logger.warning(f"Error finding member by name: {str(e)}")
                    
                    # Fallback: If no member found, create a temporary one for export purposes
                    if not member:
                        logger.warning(f"No matching Speaker found for member_id: {member_id_str}, creating temporary record for export")
                        try:
                            # Check if we already created a temporary Speaker for this member_id in this session
                            temp_member_key = f"temp_member_{member_id_str}"
                            if temp_member_key in temp_members_cache:
                                member = temp_members_cache[temp_member_key]
                                logger.info(f"Using cached temporary Speaker for {member_id_str}")
                            else:
                                # Create a temporary Speaker object (not persisted to database)
                                from sqlalchemy import inspect
                                member = Speaker()
                                member.id = -1  # Temporary ID
                                member.name = f"Unknown Speaker ({member_id_str[:8]})"
                                member.parliament_id = member_id_str
                                member.image_url = ""
                                
                                # Cache this temporary member for future use in this export session
                                temp_members_cache[temp_member_key] = member
                                logger.info(f"Created temporary Speaker for {member_id_str}")
                        except Exception as e:
                            logger.error(f"Error creating temporary Speaker: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    # Log the result
                    if member:
                        logger.info(f"Successfully found member: {member.name} (ID: {member.id})")
                    else:
                        logger.warning(f"Could not find member for ID: {member_id_str}")
                    
                    if member:
                        appearance["member_name"] = member.name
                        logger.info(f"Found member name: {member.name}")
                    else:
                        logger.warning(f"Member not found for ID: {clip['member_id']}")
                except Exception as e:
                    logger.warning(f"Could not get member name from database: {str(e)}")
                    import traceback
                    logger.warning(traceback.format_exc())
                
                recognition_results["speaker_appearances"].append(appearance)
            
            logger.info(f"Added {len(recognition_results['speaker_appearances'])} speaker appearances to recognition results")
            logger.info(f"Clip filtering stats: {filtered_clips_stats}")
            
            # Check if we have any valid appearances to export
            if len(recognition_results['speaker_appearances']) == 0:
                logger.warning(f"No valid speaker appearances to export to Supabase for video ID {video_id}")
                return {"success": False, "error": "No valid speaker appearances to export"}
            
            # Export and upload to Supabase
            logger.info(f"Preparing to export {len(recognition_results['speaker_appearances'])} appearances to Supabase")
            
            # Log the full recognition results for debugging
            logger.debug(f"Recognition results: {json.dumps(recognition_results, indent=2)}")
            
            try:
                result = self.supabase_integration.export_and_upload_recognition(
                    video_path=video_path,
                    recognition_results=recognition_results,
                    video_metadata=metadata,
                    db_session=db,
                    video_id=video_id
                )
                
                logger.info(f"Supabase export result: {result}")
                return {"success": True, "supabase_result": result}
            except Exception as e:
                logger.error(f"Error in Supabase export: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return {"success": False, "error": f"Supabase export error: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Error exporting clips to Supabase: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
