"""
Parliament Clips Integration Service.

This service integrates the multimodal recognition service with the local SQLite parliament_clips database,
ensuring that recognized clips are properly saved for local development and testing.
It also integrates with Supabase to ensure clips are available in the production environment.
"""

import os
import sys
import json
import sqlite3
import logging
import subprocess
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

# Add the parent directory to sys.path to allow importing from scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from scripts.create_parliament_clips_model import get_parliament_clip
from backend.services.integration.supabase_client import SupabaseService
from backend.services.integration.supabase_export import format_clips_for_supabase

# Set up logging
logger = logging.getLogger(__name__)

class ParliamentClipsIntegrationService:
    """Service for integrating recognition events with the local SQLite parliament_clips database."""
    
    def __init__(self):
        """Initialize the parliament clips integration service."""
        logger.info("Initializing ParliamentClipsIntegrationService")
        
        # Initialize Supabase service
        self.supabase_service = SupabaseService(use_service_role=True)
        
        # Define paths for data storage
        self.docker_temp_dir = "/app/data/temp"  # Path in Docker container
        self.local_temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data/temp")  # Local path
        
        # Use the temp directory that exists
        if os.path.exists(self.docker_temp_dir):
            self.temp_dir = self.docker_temp_dir
            logger.info(f"Using Docker temp directory: {self.temp_dir}")
        else:
            self.temp_dir = self.local_temp_dir
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.info(f"Using local temp directory: {self.temp_dir}")
        
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
                    speech_group_id TEXT,
                    session_date TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            
            # Check if the table already exists but doesn't have the speech_group_id column
            cursor.execute("PRAGMA table_info(parliament_clips)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'speech_group_id' not in columns:
                # Add the speech_group_id column if it doesn't exist
                logger.info("Adding speech_group_id column to existing parliament_clips table")
                cursor.execute("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
                logger.info("Successfully added speech_group_id column")
            
            conn.commit()
            logger.info("Successfully created/updated parliament_clips table")
        except Exception as e:
            logger.error(f"Error creating/updating parliament_clips table: {str(e)}")
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
        
        # Check if events have diarization data
        has_diarization = any(event.get("recognition_method") == "diarization" for event in speaker_events)
        logger.info(f"Events contain diarization data: {has_diarization}")
        
        # For diarization-based events, we'll use the speaker's turn index as part of the speech group ID
        # This preserves the original diarization-driven segmentation
        # Later, we'll run the update_speech_groups.py script to properly group by temporal proximity
        
        # Sort events by start time for consistent processing
        sorted_events = sorted(speaker_events, key=lambda x: x.get("start_time", 0))
        
        # Create a mapping of speaker to turn index to preserve diarization segmentation
        speaker_turn_indices = {}
        
        logger.info(f"Will save {len(sorted_events)} events as individual clips with original timestamps")
        logger.info(f"Speech groups will be updated using diarization data after saving clips")
        
        for event in sorted_events:
            # Extract data from the event
            start_time = event.get("start_time", 0)
            end_time = event.get("end_time", 0)
            text = event.get("text", "")
            member_id = event.get("member_id", "")
            confidence = event.get("confidence", 0.0)
            
            # Ensure member_id is stored as an integer as per the SQLite schema
            if member_id:
                try:
                    # Convert to integer if it's not already
                    if not isinstance(member_id, int):
                        member_id = int(member_id)
                except (ValueError, TypeError):
                    logger.error(f"Invalid member_id format: {member_id} - must be convertible to integer")
                    errors.append(f"Event at {start_time}-{end_time} has invalid member_id format")
                    continue
            
            # Skip events without a member_id
            if not member_id:
                logger.warning(f"Skipping event without member_id at {start_time}-{end_time}")
                logger.debug(f"Full event data: {json.dumps(event, indent=2)}")
                errors.append(f"Event at {start_time}-{end_time} has no member_id")
                continue
            
            logger.info(f"Processing event for member_id: {member_id} at {start_time}-{end_time}")
            
            # Calculate duration in seconds
            duration = end_time - start_time
            
            # Verify video_path exists
            if not os.path.exists(video_path):
                logger.error(f"❌ Video path does not exist: {video_path}")
                errors.append(f"Video path does not exist: {video_path}")
                continue
            
            # Generate a speech group ID based on speaker and turn index
            speaker_id = str(member_id)
            if speaker_id not in speaker_turn_indices:
                speaker_turn_indices[speaker_id] = 0
            else:
                speaker_turn_indices[speaker_id] += 1
                
            # Use speech_group_id from the event if available, otherwise use diarization-based or temporary ID
            if "speech_group_id" in event and event.get("speech_group_id"):
                # Use the speech_group_id directly from the event
                speech_group_id = f"diarization_group_{video_id}_{event.get('speech_group_id')}"
            elif event.get("recognition_method") == "diarization" and "speech_group_id" in event:
                # Use the speech_group_id from diarization data
                speech_group_id = f"diarization_group_{video_id}_{event.get('speech_group_id')}"
            else:
                # Create a speech group ID based on video ID and speaker turn index
                speech_group_id = f"speech_group_{video_id}_{speaker_id}_{speaker_turn_indices[speaker_id]}"
            
            logger.info(f"Using speech group ID: {speech_group_id} for event at {start_time}-{end_time}")
            
            # Create clip data for parliament_clips table
            clip_data = {
                'member_id': member_id,
                'transcript': text,
                'full_video_path': video_path,
                'start_timestamp': str(start_time),
                'end_timestamp': str(end_time),
                'confidence_score': confidence,
                'duration_seconds': duration,
                'speech_group_id': speech_group_id,
                'session_date': datetime.now().strftime("%Y-%m-%d"),
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'metadata': json.dumps({
                    'video_id': video_id,
                    'face_image_url': event.get("face_image_url", ""),
                    'matched_by': event.get("matched_by", "unknown"),
                    'recognition_method': event.get("recognition_method", "multimodal"),
                    'original_start_time': start_time,
                    'original_end_time': end_time
                })
            }
            
            logger.info(f"Prepared data for clip: member_id={member_id}, duration={duration:.2f}s")
            
            # Insert into database
            conn = None
            try:
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
        
        # Now run the update_speech_groups.py script to properly group clips by speaker using diarization data
        logger.info(f"Running update_speech_groups.py to properly group clips by speaker using diarization data")
        try:
            # Try multiple possible paths for the script
            possible_paths = [
                "/app/scripts/update_speech_groups.py",  # Docker container path
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts/update_speech_groups.py"),  # Local dev path
                "./scripts/update_speech_groups.py"  # Relative path
            ]
            
            script_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    script_path = path
                    logger.info(f"Found update_speech_groups.py at {script_path}")
                    break
            
            if not script_path:
                # List all files in the scripts directory to debug
                scripts_dir = "/app/scripts"
                if os.path.exists(scripts_dir):
                    logger.info(f"Contents of {scripts_dir}: {os.listdir(scripts_dir)}")
                else:
                    logger.warning(f"Scripts directory {scripts_dir} does not exist")
                    
                scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts")
                if os.path.exists(scripts_dir):
                    logger.info(f"Contents of {scripts_dir}: {os.listdir(scripts_dir)}")
                
                raise FileNotFoundError(f"Could not find update_speech_groups.py in any of the expected locations: {possible_paths}")
            
            # Run the script directly using python with the force flag to ensure it updates even if speech groups exist
            import subprocess
            cmd = [sys.executable, script_path, "--video-id", str(video_id), "--force", "--debug"]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Set environment variables for the subprocess
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # Run with full output capture
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            logger.info(f"Command exit code: {result.returncode}")
            logger.info(f"Command stdout: {result.stdout[:1000]}" + ("..." if len(result.stdout) > 1000 else ""))
            logger.info(f"Command stderr: {result.stderr[:1000]}" + ("..." if len(result.stderr) > 1000 else ""))
            
            if result.returncode == 0:
                logger.info(f"Successfully updated speech groups using diarization data")
                
                # Verify the speech groups were updated by checking the database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Use more flexible queries to find clips for this video
                # First try with video_id in the path
                cursor.execute(
                    "SELECT COUNT(DISTINCT speech_group_id) FROM parliament_clips WHERE full_video_path LIKE ?", 
                    (f"%{video_id}%",)
                )
                group_count = cursor.fetchone()[0]
                
                cursor.execute(
                    "SELECT COUNT(*) FROM parliament_clips WHERE full_video_path LIKE ?", 
                    (f"%{video_id}%",)
                )
                clip_count = cursor.fetchone()[0]
                
                # If no clips found, try checking metadata JSON for video_id
                if clip_count == 0:
                    cursor.execute(
                        "SELECT COUNT(DISTINCT speech_group_id) FROM parliament_clips WHERE metadata LIKE ?", 
                        (f"%{video_id}%",)
                    )
                    group_count = cursor.fetchone()[0]
                    
                    cursor.execute(
                        "SELECT COUNT(*) FROM parliament_clips WHERE metadata LIKE ?", 
                        (f"%{video_id}%",)
                    )
                    clip_count = cursor.fetchone()[0]
                
                # Check for temporary speech group IDs
                temp_speech_group = f"temp_speech_group_{video_id}"
                cursor.execute(
                    "SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id = ? AND full_video_path LIKE ?", 
                    (temp_speech_group, f"%{video_id}%")
                )
                temp_group_count = cursor.fetchone()[0]
                
                conn.close()
                
                logger.info(f"After update: {clip_count} clips in {group_count} speech groups for video {video_id}")
                
                if temp_group_count > 0:
                    logger.warning(f"⚠️ {temp_group_count} clips still have temporary speech group ID '{temp_speech_group}'")
                    logger.warning("This may indicate that diarization data was not found or could not be used")
                    
                if group_count == 1 and clip_count > 1:
                    logger.warning(f"⚠️ All clips still in one speech group after update. Diarization grouping may have failed.")
                    logger.warning("Check if diarization data exists and is correctly formatted")
            else:
                logger.warning(f"Failed to update speech groups: {result.stderr}")
                errors.append(f"Failed to update speech groups: {result.stderr}")
        except Exception as e:
            error_msg = f"Error running update_speech_groups: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            errors.append(error_msg)
        
        # Return results
        success = clips_saved > 0
        result = {
            "success": success,
            "clips_saved": clips_saved,
            "errors": errors
        }
        
        if success:
            logger.info(f"✅ Successfully saved {clips_saved} clips to parliament_clips database")
            # Note: We no longer export clips to Supabase here to prevent duplicate exports
            # The export will happen later in the process after member_id normalization
        else:
            logger.warning(f"❌ Failed to save any clips to parliament_clips database. Errors: {errors}")
            
        return result
    
    def get_clip_count_for_video(self, video_id: int) -> int:
        """
        Get the count of parliament clips associated with a video ID.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Count of clips
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if the video_id column exists
            cursor.execute("PRAGMA table_info(parliament_clips)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'video_id' in columns:
                # Use direct column query
                cursor.execute(
                    "SELECT COUNT(*) FROM parliament_clips WHERE video_id = ?", 
                    (video_id,)
                )
                count = cursor.fetchone()[0]
                logger.info(f"Found {count} clips with video_id {video_id} in video_id column")
                
                # If no clips found with video_id, count all clips
                if count == 0:
                    cursor.execute("SELECT COUNT(*) FROM parliament_clips")
                    count = cursor.fetchone()[0]
                    logger.info(f"No clips found with video_id {video_id}, counting all {count} clips")
            elif 'metadata' in columns:
                # Fall back to JSON extraction if video_id column doesn't exist
                try:
                    cursor.execute(
                        "SELECT COUNT(*) FROM parliament_clips WHERE json_extract(metadata, '$.video_id') = ?", 
                        (str(video_id),)
                    )
                    count = cursor.fetchone()[0]
                    logger.info(f"Found {count} clips with video_id {video_id} in metadata")
                    
                    # If no clips found with video_id in metadata, count all clips
                    if count == 0:
                        cursor.execute("SELECT COUNT(*) FROM parliament_clips")
                        count = cursor.fetchone()[0]
                        logger.info(f"No clips found with video_id in metadata, counting all {count} clips")
                except sqlite3.OperationalError:
                    # If JSON extraction fails, count all clips
                    logger.warning(f"Could not query JSON metadata for video_id {video_id}, counting all clips")
                    cursor.execute("SELECT COUNT(*) FROM parliament_clips")
                    count = cursor.fetchone()[0]
                    logger.info(f"Counting all {count} clips in database")
            else:
                # If neither column exists, count all clips
                cursor.execute("SELECT COUNT(*) FROM parliament_clips")
                count = cursor.fetchone()[0]
                logger.info(f"No video_id or metadata column found. Counting all {count} clips in database")
            
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting parliament clip count for video {video_id}: {str(e)}")
            return 0
        finally:
            if conn:
                conn.close()
                
    def get_parliament_clips_for_video(self, video_id: int) -> Dict[str, Any]:
        """
        Get all parliament clips associated with a video ID.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Dict with clips data
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            # First check if the table exists and has any data
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parliament_clips'")
            if not cursor.fetchone():
                logger.error(f"parliament_clips table does not exist in database {self.db_path}")
                return {"success": False, "error": "parliament_clips table does not exist", "clips": []}
            
            # Check if there are any clips at all
            cursor.execute("SELECT COUNT(*) FROM parliament_clips")
            total_clips = cursor.fetchone()[0]
            logger.info(f"Total clips in database: {total_clips}")
            
            if total_clips == 0:
                logger.warning(f"No clips found in database at all. The parliament_clips table is empty.")
                return {"success": False, "error": "No clips in database", "clips": []}
            
            # Check if the video_id column exists
            cursor.execute("PRAGMA table_info(parliament_clips)")
            columns = [col[1] for col in cursor.fetchall()]
            
            clips = []
            
            # Try multiple approaches to find clips for this video
            if 'video_id' in columns:
                # Try direct column query first
                cursor.execute(
                    "SELECT * FROM parliament_clips WHERE video_id = ?", 
                    (video_id,)
                )
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                for row in rows:
                    clip_dict = {}
                    for key in row.keys():
                        clip_dict[key] = row[key]
                    clips.append(clip_dict)
                
                logger.info(f"Found {len(clips)} clips with video_id {video_id} in video_id column")
            
            # If no clips found and metadata column exists, try that next
            if len(clips) == 0 and 'metadata' in columns:
                # Try multiple formats of the video_id in the metadata JSON
                for vid_format in [str(video_id), video_id, f'"{video_id}"']:
                    try:
                        logger.info(f"Trying to find clips with video_id {vid_format} in metadata JSON")
                        cursor.execute(
                            "SELECT * FROM parliament_clips WHERE json_extract(metadata, '$.video_id') = ?", 
                            (vid_format,)
                        )
                        rows = cursor.fetchall()
                        
                        # Convert rows to dictionaries
                        for row in rows:
                            clip_dict = {}
                            for key in row.keys():
                                clip_dict[key] = row[key]
                            clips.append(clip_dict)
                        
                        if len(clips) > 0:
                            logger.info(f"Found {len(clips)} clips with video_id {vid_format} in metadata")
                            break
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Error querying JSON metadata with format {vid_format}: {str(e)}")
            
            # If still no clips found, try a more flexible JSON search
            if len(clips) == 0 and 'metadata' in columns:
                try:
                    logger.info(f"Trying flexible JSON search for video_id {video_id}")
                    # This searches for the video_id anywhere in the metadata JSON
                    cursor.execute(
                        "SELECT * FROM parliament_clips WHERE metadata LIKE ?", 
                        (f'%"video_id":{video_id}%',)
                    )
                    rows = cursor.fetchall()
                    
                    # Convert rows to dictionaries
                    for row in rows:
                        clip_dict = {}
                        for key in row.keys():
                            clip_dict[key] = row[key]
                        clips.append(clip_dict)
                    
                    logger.info(f"Found {len(clips)} clips with flexible search for video_id {video_id} in metadata")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Error in flexible JSON search: {str(e)}")
            
            # If we still have no clips, log the issue but don't automatically get all clips
            if len(clips) == 0:
                logger.warning(f"No clips found for video_id {video_id} after trying all search methods")
                
                # Get a sample of clips to help with debugging
                cursor.execute("SELECT id, member_id, metadata FROM parliament_clips LIMIT 5")
                sample_rows = cursor.fetchall()
                if sample_rows:
                    logger.info(f"Sample clips in database:")
                    for row in sample_rows:
                        logger.info(f"  ID: {row[0]}, Member ID: {row[1]}, Metadata: {row[2]}")
                
                return {"success": False, "error": f"No clips found for video ID {video_id}", "clips": [], "count": 0, "total_count": total_clips}
            
            # Return the clips we found
            logger.info(f"Found {len(clips)} clips for video {video_id}")
            return {
                "success": True,
                "clips": clips,
                "count": len(clips),
                "total_count": total_clips,
                "clip_count": len(clips)
            }
            
        except Exception as e:
            logger.exception(f"Error getting parliament clips for video {video_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "clips": [],
                "count": 0,
                "total_count": 0
            }
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # End of get_parliament_clips_for_video method
    
    def _run_sync_parliament_clip_member_ids(self, db_session):
        """
        Run the sync_parliament_clip_member_ids.py script to ensure all member IDs in SQLite
        have corresponding Speaker records in PostgreSQL.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            Dict with sync results
        """
        try:
            logger.info("Running sync_parliament_clip_member_ids.py script to ensure all member IDs have Speaker records")
            import subprocess
            import sys
            import os
            
            # Get the path to the script
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      "backend/scripts/sync_parliament_clip_member_ids.py")
            
            # Check if we're running in Docker or locally
            if os.path.exists("/app/backend/scripts/sync_parliament_clip_member_ids.py"):
                script_path = "/app/backend/scripts/sync_parliament_clip_member_ids.py"
                
            logger.info(f"Sync script path: {script_path}")
            
            # Run the script using the Python interpreter
            result = subprocess.run([sys.executable, script_path], 
                                   capture_output=True, 
                                   text=True)
            
            if result.returncode == 0:
                logger.info("Successfully ran sync_parliament_clip_member_ids.py script")
                logger.info(f"Script output: {result.stdout}")
                return {"success": True, "output": result.stdout}
            else:
                logger.error(f"Error running sync_parliament_clip_member_ids.py script: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"Error running sync_parliament_clip_member_ids.py script: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def _get_sqlite_db_path(self):
        """
        Get the path to the SQLite database file.
        
        Returns:
            str: Path to the SQLite database file
        """
        import os
        
        # Check if we're running in Docker or locally
        if os.path.exists("/app/backend/parliament_clips.db"):
            return "/app/backend/parliament_clips.db"
        else:
            # Assume we're running locally
            return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "parliament_clips.db")
    
    def _normalize_speech_group_member_ids_in_sqlite(self, video_id=None):
        """
        Normalize member IDs within speech groups in the SQLite database.
        
        Speech groups are created based on speaker diarization data when available,
        or temporal proximity as a fallback.
        
        For each speech group, this function finds the clip with the highest confidence
        and uses its member_id ONLY for clips in that speech group that don't already have a valid member_id.
        This preserves member IDs from facial recognition while ensuring consistent speaker attribution
        for clips without a valid member_id.
        
        Args:
            video_id: Optional ID of the video to update. If None, update all videos.
            
        Returns:
            Dict with normalization results
        """
        logger.info(f"Normalizing member IDs within speech groups for video ID {video_id}")
        results = {
            "success": False,
            "groups_updated": 0,
            "clips_updated": 0,
            "errors": []
        }
        
        # Initialize conn to None so it's defined for the finally block
        conn = None
        
        try:
            # Connect to the SQLite database
            db_path = self._get_sqlite_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all speech groups for the specified video
            if video_id:
                # Find speech groups for this video_id using pattern matching
                # speech_group_id format is speech_group_{video_id}_{block_idx}_{timestamp}
                cursor.execute(
                    "SELECT DISTINCT speech_group_id FROM parliament_clips "
                    "WHERE speech_group_id LIKE ? AND speech_group_id IS NOT NULL",
                    (f"speech_group_{video_id}_%",)
                )
                
                speech_groups = [row[0] for row in cursor.fetchall()]
                
                # If no results, try with the video ID as a number without leading zeros
                if not speech_groups:
                    try:
                        # Convert to int to remove leading zeros, then back to string
                        numeric_video_id = str(int(video_id))
                        cursor.execute(
                            "SELECT DISTINCT speech_group_id FROM parliament_clips "
                            "WHERE speech_group_id LIKE ? AND speech_group_id IS NOT NULL",
                            (f"speech_group_{numeric_video_id}_%",)
                        )
                        speech_groups = [row[0] for row in cursor.fetchall()]
                    except ValueError:
                        # Not a numeric ID, continue with other methods
                        pass
                
                if not speech_groups:
                    # If we can't find by direct pattern matching, try metadata
                    cursor.execute(
                        "SELECT metadata FROM parliament_clips WHERE metadata LIKE ? LIMIT 1",
                        (f"%{video_id}%",)
                    )
                    result = cursor.fetchone()
                    if result:
                        try:
                            import json
                            metadata = json.loads(result[0])
                            if metadata.get('video_id') == str(video_id):
                                # Get all clips with this video_id in metadata
                                cursor.execute(
                                    "SELECT DISTINCT speech_group_id FROM parliament_clips "
                                    "WHERE metadata LIKE ? AND speech_group_id IS NOT NULL",
                                    (f"%{video_id}%",)
                                )
                                speech_groups = [row[0] for row in cursor.fetchall()]
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Could not parse metadata for video {video_id}")
                            speech_groups = []
                    
                    if not speech_groups:
                        logger.warning(f"Could not find speech groups for video {video_id}")
            else:
                # Get all speech groups if no video_id specified
                cursor.execute("SELECT DISTINCT speech_group_id FROM parliament_clips WHERE speech_group_id IS NOT NULL")
                speech_groups = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Found {len(speech_groups)} speech groups to normalize")
            
            for speech_group_id in speech_groups:
                try:
                    # Get all clips in this speech group
                    cursor.execute(
                        "SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id = ?",
                        (speech_group_id,)
                    )
                    clip_count = cursor.fetchone()[0]
                    
                    if clip_count == 0:
                        logger.warning(f"No clips found for speech group {speech_group_id}")
                        continue
                        
                    # Find the clip with the highest confidence in this speech group
                    cursor.execute(
                        "SELECT id, member_id, confidence_score FROM parliament_clips "
                        "WHERE speech_group_id = ? AND member_id IS NOT NULL AND member_id != '' "
                        "ORDER BY confidence_score DESC LIMIT 1",
                        (speech_group_id,)
                    )
                    best_clip = cursor.fetchone()
                    
                    if not best_clip:
                        logger.warning(f"No clips with valid member_id found for speech group {speech_group_id}")
                        continue
                    
                    best_clip_id, best_member_id, best_confidence = best_clip
                    
                    # Check if all clips in this group already have the same member_id
                    cursor.execute(
                        "SELECT COUNT(DISTINCT member_id) FROM parliament_clips WHERE speech_group_id = ? AND member_id IS NOT NULL AND member_id != ''",
                        (speech_group_id,)
                    )
                    distinct_member_count = cursor.fetchone()[0]
                    
                    # Get all clips in this speech group for detailed logging
                    if logger.level <= logging.DEBUG:
                        cursor.execute(
                            "SELECT id, member_id, confidence_score, start_timestamp, end_timestamp FROM parliament_clips "
                            "WHERE speech_group_id = ? ORDER BY CAST(start_timestamp AS REAL)",
                            (speech_group_id,)
                        )
                        clips_in_group = cursor.fetchall()
                        logger.debug(f"Speech group {speech_group_id} contains {len(clips_in_group)} clips:")
                        for clip in clips_in_group:
                            clip_id, member_id, confidence, start_time, end_time = clip
                            logger.debug(f"  Clip {clip_id} ({start_time}-{end_time}): Member ID {member_id}, Confidence {confidence}")
                        logger.debug(f"  Selected best clip {best_clip_id} with member_id {best_member_id} (confidence: {best_confidence})")
                    
                    if distinct_member_count <= 1 and clip_count == 1:
                        logger.debug(f"Speech group {speech_group_id} already has consistent member IDs or only contains one clip")
                        continue
                    
                    # Only update clips that don't have a valid member_id
                    # This preserves member IDs from facial recognition
                    cursor.execute(
                        "UPDATE parliament_clips SET member_id = ? "
                        "WHERE speech_group_id = ? AND (member_id IS NULL OR member_id = '')",
                        (best_member_id, speech_group_id)
                    )
                    
                    logger.info(f"Preserving existing member IDs in speech group {speech_group_id} - only updating clips without a valid member_id")
                    
                    updated_clips = cursor.rowcount
                    if updated_clips > 0:
                        logger.info(f"Updated {updated_clips} clips in speech group {speech_group_id} to use member_id {best_member_id}")
                        results["groups_updated"] += 1
                        results["clips_updated"] += updated_clips
                except Exception as e:
                    error_msg = f"Error normalizing speech group {speech_group_id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Commit the changes
            conn.commit()
            
            # Set overall success status
            results["success"] = len(results["errors"]) == 0
            
            if results["success"]:
                if results["groups_updated"] > 0:
                    logger.info(f"✅ Successfully normalized {results['groups_updated']} speech groups with {results['clips_updated']} clips updated")
                else:
                    logger.info("✅ All speech groups already had consistent member IDs")
            else:
                logger.warning(f"⚠️ Normalization completed with {len(results['errors'])} errors")
                
        except Exception as e:
            error_msg = f"Error normalizing speech group member IDs: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
            results["success"] = False
        finally:
            # Close the database connection
            if conn:
                try:
                    conn.close()
                except:
                    pass
                    
        return results
    
    def _clear_all_local_clips(self) -> Dict[str, Any]:
        """
        Clear all clips from the local SQLite database without affecting Supabase data.
        This is a safety method to clean up all local clips when needed.
        
        Returns:
            Dict with cleanup status and results
        """
        logger.info(f"===== CLEARING ALL LOCAL CLIPS =====")
        
        results = {
            "sqlite_clips_removed": 0,
            "errors": []
        }
        
        # Clean up all clips from SQLite parliament_clips database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First count how many clips we'll be removing
            cursor.execute("SELECT COUNT(*) FROM parliament_clips")
            
            count = cursor.fetchone()[0]
            logger.info(f"Found {count} clips to remove from SQLite database")
            
            # Delete all clips
            cursor.execute("DELETE FROM parliament_clips")
            
            # Get number of rows affected
            results["sqlite_clips_removed"] = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Removed {results['sqlite_clips_removed']} clips from SQLite database")
        except Exception as e:
            error_msg = f"Error cleaning up SQLite clips: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
        
        # Set overall success status
        results["success"] = len(results["errors"]) == 0
        
        if results["success"]:
            logger.info(f"✅ Successfully cleared {results['sqlite_clips_removed']} SQLite clips")
        else:
            logger.warning(f"⚠️ Cleanup completed with {len(results['errors'])} errors")
        
        return results
        
    def _cleanup_exported_clips(self, video_id: int, db_session: Session = None) -> Dict[str, Any]:
        """
        Clean up clips that have been successfully exported to Supabase.
        This removes clips from both the SQLite parliament_clips database and
        the PostgreSQL database to prevent duplicate uploads in future exports.
        
        Args:
            video_id: ID of the video whose clips should be cleaned up
            db_session: SQLAlchemy database session for PostgreSQL operations
            
        Returns:
            Dict with cleanup status and results
        """
        logger.info(f"===== CLEANING UP EXPORTED CLIPS =====")
        logger.info(f"Cleaning up clips for video ID: {video_id}")
        
        results = {
            "sqlite_clips_removed": 0,
            "postgres_events_removed": 0,
            "errors": []
        }
        
        # 1. Clean up clips from SQLite parliament_clips database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First check if the metadata column exists
            cursor.execute("PRAGMA table_info(parliament_clips)")
            columns = [col[1] for col in cursor.fetchall()]
            logger.info(f"SQLite parliament_clips table columns: {columns}")
            
            # Get a sample clip to examine metadata format
            cursor.execute("SELECT id, metadata FROM parliament_clips LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                logger.info(f"Sample clip metadata format: {sample[1][:100]}...")
            
            # Try multiple approaches to find and delete clips for this video_id
            total_deleted = 0
            
            # Approach 1: Try with JSON extraction if metadata is properly formatted
            if 'metadata' in columns:
                logger.info("Attempting cleanup using JSON extraction...")
                cursor.execute("""
                    SELECT COUNT(*) FROM parliament_clips 
                    WHERE json_extract(metadata, '$.video_id') = ?
                """, (str(video_id),))
                
                count = cursor.fetchone()[0]
                logger.info(f"Found {count} clips to remove from SQLite database using JSON extraction")
                
                if count > 0:
                    # Delete clips for this video_id using JSON extraction
                    cursor.execute("""
                        DELETE FROM parliament_clips 
                        WHERE json_extract(metadata, '$.video_id') = ?
                    """, (str(video_id),))
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} clips using JSON extraction")
                    total_deleted += deleted
            
            # Approach 2: Try string matching in the metadata field
            if 'metadata' in columns:
                logger.info("Attempting cleanup using string matching...")
                cursor.execute("""
                    SELECT COUNT(*) FROM parliament_clips 
                    WHERE metadata LIKE ?
                """, (f'%"video_id": {video_id}%',))
                
                count = cursor.fetchone()[0]
                logger.info(f"Found {count} clips to remove using string search")
                
                if count > 0:
                    cursor.execute("""
                        DELETE FROM parliament_clips 
                        WHERE metadata LIKE ?
                    """, (f'%"video_id": {video_id}%',))
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} clips using string matching")
                    total_deleted += deleted
            
            # Approach 3: Try another string pattern (different JSON format)
            if 'metadata' in columns:
                logger.info("Attempting cleanup using alternative string pattern...")
                cursor.execute("""
                    SELECT COUNT(*) FROM parliament_clips 
                    WHERE metadata LIKE ?
                """, (f'%"video_id":{video_id}%',))  # No space after colon
                
                count = cursor.fetchone()[0]
                logger.info(f"Found {count} clips to remove using alternative string pattern")
                
                if count > 0:
                    cursor.execute("""
                        DELETE FROM parliament_clips 
                        WHERE metadata LIKE ?
                    """, (f'%"video_id":{video_id}%',))
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} clips using alternative string pattern")
                    total_deleted += deleted
            
            # Get final count of clips for this video to verify cleanup
            cursor.execute("SELECT COUNT(*) FROM parliament_clips")
            remaining_total = cursor.fetchone()[0]
            logger.info(f"Total remaining clips in SQLite database: {remaining_total}")
            
            # Set the total deleted count
            results["sqlite_clips_removed"] = total_deleted
            conn.commit()
            conn.close()
            
            logger.info(f"Total removed from SQLite database: {total_deleted} clips")
            
            # If no clips were deleted, log a warning
            if total_deleted == 0:
                warning_msg = f"⚠️ No clips were deleted from SQLite for video ID {video_id}. Check if clips exist with this video ID."
                logger.warning(warning_msg)
                results["warnings"] = results.get("warnings", []) + [warning_msg]
        except Exception as e:
            error_msg = f"Error cleaning up SQLite clips: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
        
        # 2. Clean up recognition events from PostgreSQL database
        try:
            # Skip PostgreSQL cleanup if no database session provided
            if db_session is None:
                logger.info("No database session provided, skipping PostgreSQL cleanup")
                results["postgres_events_removed"] = 0
            else:
                from backend.db.models import RecognitionEvent, ParliamentMemberClip
                
                # First check if there are any ParliamentMemberClip records for this video
                # These are the records in Supabase that we've just exported to
                try:
                    parliament_clip_count = db_session.query(ParliamentMemberClip).filter(
                        ParliamentMemberClip.video_id == video_id
                    ).count()
                    logger.info(f"Found {parliament_clip_count} ParliamentMemberClip records in PostgreSQL for video ID {video_id}")
                except Exception as e:
                    logger.warning(f"Could not check ParliamentMemberClip records: {str(e)}")
                    parliament_clip_count = "unknown"
                
                # First check if the transaction is still valid
                try:
                    # Execute a simple query to test if transaction is valid
                    db_session.execute("SELECT 1").scalar()
                except Exception as tx_error:
                    logger.warning(f"Transaction appears to be in a failed state, rolling back: {str(tx_error)}")
                    try:
                        db_session.rollback()
                        logger.info("Successfully rolled back transaction after detecting failed state")
                    except Exception as rollback_error:
                        logger.error(f"Error during transaction rollback: {str(rollback_error)}")
                    
                    # Get a fresh session if possible
                    try:
                        from backend.db.session import get_db
                        db_generator = get_db()
                        db_session = next(db_generator)
                        logger.info("Created fresh database session after transaction failure")
                    except Exception as session_error:
                        logger.error(f"Could not create fresh database session: {str(session_error)}")
                        results["errors"].append(f"Could not create fresh database session: {str(session_error)}")
                        return results
                
                # Count how many recognition events we'll be removing
                try:
                    event_count = db_session.query(RecognitionEvent).filter(
                        RecognitionEvent.capture_session_id == video_id,
                        RecognitionEvent.event_type == "speaker"
                    ).count()
                    
                    logger.info(f"Found {event_count} recognition events to remove from PostgreSQL database")
                    
                    # Get a sample of the recognition events for debugging
                    sample_events = db_session.query(RecognitionEvent).filter(
                        RecognitionEvent.capture_session_id == video_id,
                        RecognitionEvent.event_type == "speaker"
                    ).limit(2).all()
                    
                    if sample_events:
                        logger.info(f"Sample recognition event: ID={sample_events[0].id}, Type={sample_events[0].event_type}, Start={sample_events[0].start_time}")
                    
                    # Delete recognition events for this video_id
                    deleted_count = db_session.query(RecognitionEvent).filter(
                        RecognitionEvent.capture_session_id == video_id,
                        RecognitionEvent.event_type == "speaker"
                    ).delete(synchronize_session=False)
                    
                    try:
                        db_session.commit()
                        logger.info(f"Successfully committed PostgreSQL deletion of {deleted_count} events")
                    except Exception as commit_error:
                        error_msg = f"Error committing PostgreSQL deletion: {str(commit_error)}"
                        logger.error(error_msg)
                        try:
                            db_session.rollback()
                            logger.info("Rolled back PostgreSQL transaction after commit error")
                        except Exception as rollback_error:
                            logger.error(f"Error rolling back PostgreSQL transaction: {str(rollback_error)}")
                        results["errors"].append(error_msg)
                except Exception as query_error:
                    error_msg = f"Error querying or deleting recognition events: {str(query_error)}"
                    logger.error(error_msg)
                    try:
                        db_session.rollback()
                        logger.info("Rolled back PostgreSQL transaction after query error")
                    except Exception as rollback_error:
                        logger.error(f"Error rolling back PostgreSQL transaction: {str(rollback_error)}")
                    results["errors"].append(error_msg)
                
                # Verify deletion was successful
                verification_count = db_session.query(RecognitionEvent).filter(
                    RecognitionEvent.capture_session_id == video_id,
                    RecognitionEvent.event_type == "speaker"
                ).count()
                
                if verification_count > 0:
                    warning_msg = f"⚠️ After deletion, {verification_count} recognition events still remain for video ID {video_id}"
                    logger.warning(warning_msg)
                    results["warnings"] = results.get("warnings", []) + [warning_msg]
                else:
                    logger.info(f"✅ Verified all recognition events were deleted for video ID {video_id}")
                
                results["postgres_events_removed"] = deleted_count
                logger.info(f"Removed {deleted_count} recognition events from PostgreSQL database")
                results["postgres_clips_count"] = parliament_clip_count
        except Exception as e:
            error_msg = f"Error cleaning up PostgreSQL recognition events: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
            try:
                db_session.rollback()
                logger.info("Rolled back PostgreSQL transaction after error")
            except Exception as rollback_error:
                logger.error(f"Error rolling back PostgreSQL transaction: {str(rollback_error)}")
        
        # Set overall success status
        results["success"] = len(results["errors"]) == 0
        
        # Add warnings count to results
        if "warnings" in results:
            results["warnings_count"] = len(results["warnings"])
        
        if results["success"]:
            if results["sqlite_clips_removed"] > 0 or results["postgres_events_removed"] > 0:
                logger.info(f"✅ Successfully cleaned up {results['sqlite_clips_removed']} SQLite clips and {results['postgres_events_removed']} PostgreSQL events")
            else:
                logger.warning(f"⚠️ No clips or events were removed during cleanup for video ID {video_id}. Check if they exist.")
                if "warnings" not in results:
                    results["warnings"] = []
                results["warnings"].append(f"No clips or events were removed during cleanup for video ID {video_id}")
        else:
            logger.warning(f"⚠️ Cleanup completed with {len(results['errors'])} errors")
        
        # Log a summary of the cleanup operation
        logger.info(f"===== CLEANUP SUMMARY =====")
        logger.info(f"Video ID: {video_id}")
        logger.info(f"SQLite clips removed: {results['sqlite_clips_removed']}")
        logger.info(f"PostgreSQL events removed: {results['postgres_events_removed']}")
        if "postgres_clips_count" in results:
            logger.info(f"PostgreSQL parliament clips count: {results['postgres_clips_count']}")
        if "warnings" in results and results["warnings"]:
            logger.warning(f"Warnings: {len(results['warnings'])}")
            for warning in results["warnings"]:
                logger.warning(f"  - {warning}")
        if results["errors"]:
            logger.error(f"Errors: {len(results['errors'])}")
            for error in results["errors"]:
                logger.error(f"  - {error}")
        
        return results
        
    def _run_sync_parliament_clip_member_ids(self, db: Session) -> Dict[str, Any]:
        """
        Run the sync_parliament_clip_member_ids.py script to ensure all member IDs in SQLite
        have corresponding Speaker records in PostgreSQL.
        
        Args:
            db_session: SQLAlchemy database session
            
        Returns:
            Dict with sync results
        """
        try:
            # First, check for existing member IDs in SQLite and PostgreSQL
            logger.info("Checking for member ID synchronization issues between SQLite and PostgreSQL...")
            
            # Check SQLite member IDs
            sqlite_member_ids = set()
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT member_id FROM parliament_clips")
                for row in cursor.fetchall():
                    member_id = row[0]
                    sqlite_member_ids.add(member_id)
                    logger.info(f"SQLite member_id: {member_id} (type: {type(member_id).__name__})")
                conn.close()
                logger.info(f"Found {len(sqlite_member_ids)} unique member IDs in SQLite")
            except Exception as e:
                logger.error(f"Error checking SQLite member IDs: {str(e)}")
            
            # Check PostgreSQL Speaker records
            from backend.db.models import Speaker
            postgres_member_ids = set()
            try:
                speakers = db.query(Speaker).all()
                for speaker in speakers:
                    if speaker.parliament_id:
                        postgres_member_ids.add(speaker.parliament_id)
                        logger.info(f"PostgreSQL Speaker parliament_id: {speaker.parliament_id} (name: {speaker.name})")
                logger.info(f"Found {len(postgres_member_ids)} unique parliament_ids in PostgreSQL Speakers")
            except Exception as e:
                logger.error(f"Error checking PostgreSQL Speaker records: {str(e)}")
            
            # Check for missing member IDs
            missing_ids = set()
            for sqlite_id in sqlite_member_ids:
                # Convert to string for comparison with PostgreSQL
                sqlite_id_str = str(sqlite_id)
                if sqlite_id_str not in postgres_member_ids:
                    missing_ids.add(sqlite_id)
                    logger.warning(f"Member ID {sqlite_id} exists in SQLite but not in PostgreSQL Speakers")
            
            logger.info(f"Found {len(missing_ids)} member IDs in SQLite that don't exist in PostgreSQL")
            
            # Run the synchronization script
            logger.info("Running sync_parliament_clip_member_ids.py script to ensure all member IDs have Speaker records")
            import subprocess
            import sys
            import os
            
            # Get the path to the script
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      "backend/scripts/sync_parliament_clip_member_ids.py")
            
            # Check if we're running in Docker or locally
            if os.path.exists("/app/backend/scripts/sync_parliament_clip_member_ids.py"):
                script_path = "/app/backend/scripts/sync_parliament_clip_member_ids.py"
                
            logger.info(f"Sync script path: {script_path}")
            
            # Run the script using the Python interpreter
            result = subprocess.run([sys.executable, script_path], 
                                   capture_output=True, 
                                   text=True)
            
            if result.returncode == 0:
                logger.info("Successfully ran sync_parliament_clip_member_ids.py script")
                logger.info(f"Script output: {result.stdout}")
                
                # Verify synchronization after running the script
                try:
                    # Check PostgreSQL Speaker records again
                    speakers = db.query(Speaker).all()
                    postgres_member_ids_after = set()
                    for speaker in speakers:
                        if speaker.parliament_id:
                            postgres_member_ids_after.add(speaker.parliament_id)
                    
                    # Check for any remaining missing IDs
                    still_missing = set()
                    for sqlite_id in sqlite_member_ids:
                        sqlite_id_str = str(sqlite_id)
                        if sqlite_id_str not in postgres_member_ids_after:
                            still_missing.add(sqlite_id)
                    
                    if still_missing:
                        logger.warning(f"After synchronization, {len(still_missing)} member IDs are still missing in PostgreSQL")
                        for missing_id in still_missing:
                            logger.warning(f"Still missing member ID: {missing_id}")
                    else:
                        logger.info("All SQLite member IDs now have corresponding Speaker records in PostgreSQL")
                except Exception as e:
                    logger.error(f"Error verifying synchronization: {str(e)}")
                
                return {"success": True, "output": result.stdout, "missing_before": len(missing_ids), "missing_after": len(still_missing) if 'still_missing' in locals() else 0}
            else:
                logger.error(f"Error running sync_parliament_clip_member_ids.py script: {result.stderr}")
                return {"success": False, "error": result.stderr, "missing_ids": list(missing_ids)}
        except Exception as e:
            logger.error(f"Error running sync_parliament_clip_member_ids.py script: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
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
        # CRITICAL: First, normalize member IDs within speech groups to ensure consistent speaker attribution
        # This ensures that all clips in a speech group have the correct member_id before export
        logger.info("Running member_id normalization before export")
        normalization_result = self._normalize_speech_group_member_ids_in_sqlite(video_id)
        
        if normalization_result and not normalization_result.get("success", False):
            logger.warning(f"Member ID normalization had issues: {normalization_result.get('errors', [])}")
            logger.warning("Continuing with export anyway, but some member IDs may not be properly normalized")
        else:
            logger.info(f"Member ID normalization completed successfully: {normalization_result.get('clips_updated', 0)} clips updated")
        
        # Initialize cache for temporary Speaker objects
        temp_members_cache = {}
        logger.info(f"===== EXPORTING CLIPS TO SUPABASE =====")
        logger.info(f"Video ID: {video_id}, Video Path: {video_path}")
        
        # Convert local file path to Supabase bucket URL or just the filename
        supabase_video_path = video_path
        if video_path:
            # Extract just the filename from the path
            filename = os.path.basename(video_path)
            
            # If it's a combined AV file (which it should be), use the Supabase bucket URL format
            if filename.startswith('combined_av_'):
                # Format: http://127.0.0.1:54321/storage/v1/object/public/full_videos//filename
                # For production, this would be the actual Supabase URL
                supabase_video_path = f"http://127.0.0.1:54321/storage/v1/object/public/full_videos/{filename}"
                logger.info(f"Converted local path to Supabase URL: {supabase_video_path}")
            else:
                # Just use the filename if it's not a combined AV file
                supabase_video_path = filename
                logger.info(f"Using filename for video path: {supabase_video_path}")
        
        # Import necessary modules
        import os
        import json
        from datetime import datetime
        
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
            # Try both numeric and string formats of video_id to handle different storage formats
            cursor.execute("""
                SELECT * FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = ? OR json_extract(metadata, '$.video_id') = ?
            """, (video_id, str(video_id)))
            
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
                    "unknown_speaker": 0,  # Using numeric ID -1 instead of string "default_unknown"
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
                        
                    if event.get("member_id") == "default_unknown" or event.get("member_id") == -1:
                        filtered_stats["unknown_speaker"] += 1
                        logger.debug(f"Skipping event with unknown speaker member_id: {event.get('member_id')}")
                        continue
                        
                    confidence = event.get("confidence", 0.0)
                    if confidence < 0.05:  # Lowered from 0.15 to 0.05 (5%)
                        filtered_stats["low_confidence"] += 1
                        logger.debug(f"Skipping low confidence event: {confidence} < 0.05")
                        continue
                        
                    # This event passes all filters
                    filtered_stats["valid_clips"] += 1
                    
                    # Ensure timestamps are numeric for calculation
                    start_time = event.get("start_time", 0)
                    end_time = event.get("end_time", 0)
                    
                    # Convert timestamps to float if they're strings
                    if isinstance(start_time, str):
                        try:
                            start_time = float(start_time)
                        except ValueError:
                            start_time = 0
                    
                    if isinstance(end_time, str):
                        try:
                            end_time = float(end_time)
                        except ValueError:
                            end_time = 0
                    
                    # Calculate duration
                    duration_seconds = end_time - start_time
                    
                    # Ensure member_id is an integer
                    member_id = event.get("member_id")
                    if isinstance(member_id, str) and member_id.isdigit():
                        member_id = int(member_id)
                    elif not isinstance(member_id, int):
                        logger.warning(f"Non-integer member_id found: {member_id}, skipping clip")
                        continue
                        
                    clip = {
                        'id': str(int(time.time() * 1000)),  # Use timestamp instead of UUID
                        'member_id': member_id,  # Use integer member_id
                        'transcript': event.get("text", ""),
                        'full_video_path': video_path,
                        'start_timestamp': start_time,
                        'end_timestamp': end_time,
                        'confidence_score': confidence,
                        'duration_seconds': duration_seconds,
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
                "unknown_speaker": 0,  # Using numeric ID -1 instead of string "default_unknown"
                "low_confidence": 0,
                "valid_clips": 0
            }
            
            for clip in clips:
                # Skip unknown members
                if clip['member_id'] == "default_unknown" or clip['member_id'] == -1:
                    filtered_clips_stats["unknown_speaker"] += 1
                    logger.info(f"Skipping clip with unknown speaker member_id: {clip['member_id']}")
                    continue
                
                # Enhanced logging for member ID debugging
                logger.info(f"Processing clip with member_id: {clip['member_id']} (type: {type(clip['member_id']).__name__})")
                
                # Log additional clip details for better diagnostics
                clip_details = {
                    "clip_id": clip['id'],
                    "member_id": clip['member_id'],
                    "member_id_type": type(clip['member_id']).__name__,
                    "start_time": clip['start_timestamp'],
                    "end_time": clip['end_timestamp'],
                    "confidence": clip['confidence_score'],
                    "matched_by": clip['metadata'].get('matched_by', 'unknown'),
                    "speech_group_id": clip.get('speech_group_id', None)  # Include speech_group_id in logging
                }
                logger.info(f"Clip details: {json.dumps(clip_details)}")
                
                # Log any potential issues with the member ID
                if not isinstance(clip['member_id'], int):
                    logger.warning(f"Non-integer member_id: {clip['member_id']} will be converted to int if possible")
                if clip['member_id'] == -1 or clip['member_id'] == "-1":
                    logger.warning(f"Default unknown member ID (-1) detected, this may cause export issues")
                
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
                    
                    # Get member_id as integer
                    member_id_int = clip['member_id']
                    if not isinstance(member_id_int, int):
                        try:
                            member_id_int = int(member_id_int)
                        except (ValueError, TypeError):
                            logger.warning(f"Cannot convert member_id to integer: {clip['member_id']}")
                            member_id_int = -1
                    
                    # Try to find the speaker by member_id
                    member = None
                    
                    try:
                        # Direct lookup by member_id (integer)
                        member = db.query(Speaker).filter(Speaker.parliament_id == str(member_id_int)).first()
                        if member:
                            logger.info(f"Found member by member_id: {member_id_int}")
                    except Exception as e:
                        logger.warning(f"Error finding member by member_id: {str(e)}")
                    
                    # If not found by member_id, try by ID
                    if not member:
                        try:
                            member = db.query(Speaker).filter(Speaker.id == member_id_int).first()
                            if member:
                                logger.info(f"Found member by id: {member_id_int}")
                        except Exception as e:
                            logger.warning(f"Error finding member by id: {str(e)}")
                    
                    # If still not found, try by parliament_id as a fallback
                    if not member:
                        try:
                            member_id_str = str(member_id_int)
                            member = db.query(Speaker).filter(Speaker.parliament_id == member_id_str).first()
                            if member:
                                logger.info(f"Found member by parliament_id: {member_id_str}")
                        except Exception as e:
                            logger.warning(f"Error finding member by parliament_id: {str(e)}")
                    
                    # Fallback: If no member found, create a temporary one for export purposes
                    if not member:
                        logger.warning(f"No matching Speaker found for member_id: {member_id_int}, creating temporary record for export")
                        try:
                            # Check if we already created a temporary Speaker for this member_id in this session
                            temp_member_key = f"temp_member_{member_id_int}"
                            if temp_member_key in temp_members_cache:
                                member = temp_members_cache[temp_member_key]
                                logger.info(f"Using cached temporary Speaker for {member_id_int}")
                            else:
                                # Create a temporary Speaker object (not persisted to database)
                                from sqlalchemy import inspect
                                member = Speaker()
                                member.id = -1  # Temporary ID
                                member.member_id = member_id_int  # Use the integer member_id
                                member.name = f"Unknown Speaker (ID: {member_id_int})"
                                member.parliament_id = str(member_id_int)
                                member.photo_url = ""
                                
                                # Cache this temporary member for future use in this export session
                                temp_members_cache[temp_member_key] = member
                                logger.info(f"Created temporary Speaker for {member_id_int}")
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
            
            # CRITICAL ADDITION: First, ensure we have the correct member_id mapping
            # by running the sync script to ensure all member IDs have corresponding Speaker records
            from backend.db.session import get_db
            db_generator = get_db()
            db = next(db_generator)
            
            sync_result = self._run_sync_parliament_clip_member_ids(db)
            if not sync_result.get("success"):
                logger.warning(f"Member ID sync failed: {sync_result.get('error')}")
                logger.warning("Continuing with export anyway, but some member IDs may not be properly mapped")
            else:
                logger.info("Successfully synchronized member IDs between SQLite and PostgreSQL")
            
            logger.info(f"Preparing to export {len(recognition_results['speaker_appearances'])} appearances to Supabase")
            
            # Log the full recognition results for debugging
            logger.debug(f"Recognition results: {json.dumps(recognition_results, indent=2)}")
            
            # Prepare clips with proper member_id format for Supabase
            clips_to_export = []
            skipped_clips_count = 0
            member_id_types = {}
            for clip in recognition_results['speaker_appearances']:
                # Get the member_id from the clip
                member_id = clip.get('member_id')
                if not member_id:
                    logger.warning(f"Skipping clip without member_id: {clip}")
                    skipped_clips_count += 1
                    continue
                
                # Log the original member_id for debugging
                logger.info(f"Original member_id: {member_id} (type: {type(member_id).__name__})")
                
                # SIMPLIFIED APPROACH: For Supabase, we need to use the integer member_id
                # After running the sync script, we should be able to find the corresponding integer member_id
                # in the parliament_members table
                
                # Try to convert member_id to integer directly if possible
                try:
                    if isinstance(member_id, str) and (len(member_id) > 30 or '-' in member_id):
                        # This looks like a UUID, query the parliament_members table to get the integer member_id
                        try:
                            # Query the Speaker table to find the corresponding integer member_id
                            from backend.db.models import Speaker
                            speaker = db.query(Speaker).filter(Speaker.id == member_id).first()
                            
                            if speaker and speaker.member_id:
                                member_id = speaker.member_id
                                logger.info(f"Found integer member_id {member_id} for UUID {clip.get('member_id')}")
                            else:
                                # Try to find by parliament_id
                                speaker = db.query(Speaker).filter(Speaker.parliament_id == str(member_id)).first()
                                if speaker and speaker.member_id:
                                    member_id = speaker.member_id
                                    logger.info(f"Found integer member_id {member_id} using parliament_id match")
                                else:
                                    # If we can't find a match, try direct conversion
                                    try:
                                        member_id = int(member_id)
                                        logger.info(f"Converted member_id directly to integer: {member_id}")
                                    except (ValueError, TypeError):
                                        logger.warning(f"Could not find or convert member_id {member_id} to integer, skipping clip")
                                        skipped_clips_count += 1
                                        continue
                        except Exception as e:
                            logger.error(f"Error looking up Speaker for member_id {member_id}: {str(e)}")
                            skipped_clips_count += 1
                            continue
                    else:
                        # Try direct conversion for non-UUID strings
                        member_id = int(member_id)
                        logger.info(f"Converted member_id directly to integer: {member_id}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to convert member_id to integer: {member_id} - {str(e)}")
                    skipped_clips_count += 1
                    continue
                
                # Final validation - ensure we have an integer
                if not isinstance(member_id, int):
                    logger.error(f"After all conversion attempts, member_id is still not an integer: {member_id} (type: {type(member_id).__name__})")
                    skipped_clips_count += 1
                    continue
                
                # Log the final member_id for debugging
                logger.info(f"Final member_id for export: {member_id} (type: {type(member_id).__name__})")
                
                # Ensure timestamps are properly formatted as strings
                start_timestamp = clip.get('start_time') or clip.get('start_timestamp')
                end_timestamp = clip.get('end_time') or clip.get('end_timestamp')
                
                logger.info(f"Raw timestamps: start={start_timestamp} (type: {type(start_timestamp).__name__ if start_timestamp is not None else 'None'}), end={end_timestamp} (type: {type(end_timestamp).__name__ if end_timestamp is not None else 'None'})")
                
                # Convert timestamps to string if they're numeric
                if start_timestamp is not None:
                    if isinstance(start_timestamp, (int, float)):
                        start_timestamp = str(start_timestamp)
                else:
                    logger.warning(f"Missing start_timestamp for clip, using default value")
                    start_timestamp = "0"  # Default to 0 if missing
                    
                if end_timestamp is not None:
                    if isinstance(end_timestamp, (int, float)):
                        end_timestamp = str(end_timestamp)
                else:
                    logger.warning(f"Missing end_timestamp for clip, using default value")
                    end_timestamp = "0"  # Default to 0 if missing
                
                # Log the timestamps for debugging
                logger.info(f"Final clip timestamps: start={start_timestamp} (type: {type(start_timestamp).__name__}), end={end_timestamp} (type: {type(end_timestamp).__name__})")
                
                # Get speech_group_id from the clip if available
                speech_group_id = None
                if hasattr(clip, 'speech_group_id'):
                    speech_group_id = clip.speech_group_id
                elif isinstance(clip, dict):
                    speech_group_id = clip.get('speech_group_id')
                
                export_clip = {
                    "video_id": str(video_id),
                    "start_timestamp": start_timestamp,
                    "end_timestamp": end_timestamp,
                    "member_id": member_id,  # Should now be an integer if conversion was successful
                    "speaker_name": clip.get('member_name', 'Unknown'),
                    "confidence": clip.get('confidence_score', 0.0),
                    "transcript": clip.get('transcript', ''),
                    "face_image_url": '',
                    "full_video_path": video_path,  # Combined audio+video file
                    "video_export_path": video_path,  # IMPORTANT: Always use full_video_path (combined AV) for video_export_path
                    "metadata": {
                        "recognition_method": "facial",
                        "matched_by": "parliament_clips",
                        "clip_id": clip.get('id'),
                        "combined_av_url": video_path,  # Combined audio+video file
                        "video_export_path": video_path,  # IMPORTANT: Always use full_video_path (combined AV) for all paths
                        "original_id": str(clip.get('member_id')),  # Store the original ID for reference
                        "speech_group_id": speech_group_id  # Include speech_group_id in metadata for grouping
                    }
                }
                
                logger.info(f"Prepared clip for export: {export_clip}")
                clips_to_export.append(export_clip)
            
            logger.info(f"Prepared {len(clips_to_export)} clips for export to Supabase, skipped {skipped_clips_count} clips")
            logger.info(f"Member ID types encountered: {member_id_types}")
            
            # Create export directory and files even if no clips are found
            # This ensures that the export paths are properly set and files exist
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(self.temp_dir, "supabase_export", str(video_id))
            os.makedirs(export_dir, exist_ok=True)
            
            # Create the export file paths
            video_export_path = os.path.join(export_dir, f"recognition_export_{video_id}_{timestamp}.json")
            clips_export_path = os.path.join(export_dir, f"clips_export_{video_id}_{timestamp}.json")
            
            # Write empty files or files with content depending on whether we have clips
            with open(video_export_path, 'w') as f:
                json.dump({"video_id": video_id, "timestamp": timestamp, "events": recognition_events}, f)
            
            with open(clips_export_path, 'w') as f:
                json.dump({"video_id": video_id, "timestamp": timestamp, "clips": clips_to_export}, f)
            
            logger.info(f"Created export files at:\n - {video_export_path}\n - {clips_export_path}")
            
            # Check if we have any clips to export
            if len(clips_to_export) == 0:
                logger.warning("No valid clips after cleaning. All clips were filtered out.")
                return {"success": False, "error": "No valid clips after cleaning", 
                        "video_export_path": video_export_path, 
                        "clips_export_path": clips_export_path}
            
            # Format clips for Supabase, grouping by speech_group_id
            from backend.services.integration.supabase_export import format_clips_for_supabase
            
            # Create a recognition results structure with speaker appearances
            formatted_recognition_results = {
                "speaker_appearances": clips_to_export
            }
            
            # Format clips for Supabase, enabling grouping by speech_group_id
            grouped_clips = format_clips_for_supabase(
                video_id=str(video_id),
                recognition_results=formatted_recognition_results,
                combined_av_url=supabase_video_path,  # Use the Supabase bucket URL or filename
                group_by_speech_group=True  # Enable grouping by speech_group_id
            )
            
            logger.info(f"Formatted {len(clips_to_export)} clips into {len(grouped_clips)} grouped clips for Supabase")
            
            # Use the SupabaseService's add_to_clip_creation_queue method to insert the grouped clips
            logger.info(f"Calling Supabase to insert {len(grouped_clips)} grouped clips")
            result = self.supabase_service.add_to_clip_creation_queue(grouped_clips)
            
            # Log detailed information about the result for debugging
            logger.info(f"Supabase export result: {result}")
            
            # Improved success condition check
            export_success = False
            
            # Check various success conditions
            if isinstance(result, dict):
                export_success = result.get("success", False)
                logger.info(f"Result is dict, success field: {export_success}")
            elif hasattr(result, "data") and result.data:
                export_success = True
                logger.info(f"Result has data attribute: {result.data}")
                if isinstance(result.data, dict):
                    logger.info(f"Data keys: {list(result.data.keys())}")
                elif isinstance(result.data, list):
                    logger.info(f"Data length: {len(result.data)}")
            elif result is not None:
                # Consider any non-None, non-empty result as success
                # This is a fallback for when the Supabase client returns unexpected formats
                if isinstance(result, (list, dict)) and len(result) > 0:
                    export_success = True
                    logger.info(f"Result is non-empty list/dict, treating as success")
                elif not isinstance(result, (list, dict)) and bool(result):
                    export_success = True
                    logger.info(f"Result is truthy value, treating as success")
                    
            # Verify the export was successful by checking if the files exist and have content
            # This is a double-check to ensure we don't clean up prematurely
            if export_success:
                # Verify export files exist and have content
                files_exist = True
                files_have_content = True
                
                if video_export_path and os.path.exists(video_export_path):
                    video_file_size = os.path.getsize(video_export_path)
                    logger.info(f"Video export file exists with size: {video_file_size} bytes")
                    if video_file_size <= 10:  # Practically empty JSON
                        files_have_content = False
                        logger.warning(f"Video export file appears to be empty or minimal: {video_file_size} bytes")
                else:
                    files_exist = False
                    logger.warning(f"Video export file does not exist: {video_export_path}")
                
                if clips_export_path and os.path.exists(clips_export_path):
                    clips_file_size = os.path.getsize(clips_export_path)
                    logger.info(f"Clips export file exists with size: {clips_file_size} bytes")
                    if clips_file_size <= 10:  # Practically empty JSON
                        files_have_content = False
                        logger.warning(f"Clips export file appears to be empty or minimal: {clips_file_size} bytes")
                else:
                    files_exist = False
                    logger.warning(f"Clips export file does not exist: {clips_export_path}")
                
                # Update export_success based on file verification
                if not files_exist:
                    export_success = False
                    logger.warning("Export marked as unsuccessful because export files do not exist")
                elif not files_have_content and len(clips) > 0:  # Only care about empty files if we had clips to export
                    export_success = False
                    logger.warning("Export marked as unsuccessful because export files exist but appear to be empty")
                    
                # If we have no clips but files exist, that's still a success
                if not clips and files_exist:
                    export_success = True
                    logger.info("No clips to export but files were created successfully - marking as success")
                    
                # Final verification of export success
                logger.info(f"Final export success determination after verification: {export_success}")
                if not export_success:
                    logger.warning("Export will be marked as unsuccessful, cleanup will NOT be performed")
                else:
                    logger.info("Export verified as successful, cleanup WILL be performed")
            
            logger.info(f"Export success determination: {export_success}")
            logger.info(f"========== COMPLETED SUPABASE EXPORT for video {video_id} ==========")
            
            # If export was successful, clean up clips from both databases
            if export_success:
                # Before cleanup, verify that clips exist in Supabase by checking the result
                supabase_verification = True
                
                # Try to verify clips were actually created in Supabase
                if isinstance(result, dict) and "clips_created" in result:
                    clips_created = result.get("clips_created", 0)
                    logger.info(f"Supabase reports {clips_created} clips created")
                    
                    # If we had clips to export but none were created in Supabase, that's a problem
                    if len(clips) > 0 and clips_created == 0:
                        supabase_verification = False
                        logger.warning(f"Had {len(clips)} clips to export but Supabase reports 0 clips created")
                
                # Check Supabase verification status
                if supabase_verification:
                    # Skip cleanup to preserve clips in SQLite database for future reference
                    logger.info(f"Export successful and verified, but SKIPPING cleanup to preserve clips in SQLite database")
                    logger.info(f"This ensures clips remain available for future reference and debugging")
                    return {"success": True, "supabase_result": result, "cleanup_skipped": True, 
                            "export_paths": {
                                "video_export_path": video_export_path, 
                                "clips_export_path": clips_export_path
                            },
                            "video_export_path": video_export_path, 
                            "clips_export_path": clips_export_path}
                else:
                    logger.warning("Export appeared successful but Supabase verification failed. Skipping cleanup.")
                    return {"success": False, "supabase_result": result, "error": "Supabase verification failed", 
                            "export_paths": {
                                "video_export_path": video_export_path, 
                                "clips_export_path": clips_export_path
                            },
                            "video_export_path": video_export_path, 
                            "clips_export_path": clips_export_path}
            
            return {"success": export_success, "supabase_result": result, 
                    "video_export_path": video_export_path, 
                    "clips_export_path": clips_export_path}
            
        except Exception as e:
            logger.error(f"Error exporting clips to Supabase: {str(e)}")
            logger.exception(e)
            
            # Even in case of an exception, try to create the export files
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_dir = os.path.join(self.temp_dir, "supabase_export", str(video_id))
                os.makedirs(export_dir, exist_ok=True)
                
                # Create the export file paths
                video_export_path = os.path.join(export_dir, f"recognition_export_{video_id}_{timestamp}.json")
                clips_export_path = os.path.join(export_dir, f"clips_export_{video_id}_{timestamp}.json")
                
                # Write empty files with error information
                with open(video_export_path, 'w') as f:
                    json.dump({"video_id": video_id, "timestamp": timestamp, "events": recognition_events, "error": str(e)}, f)
                
                with open(clips_export_path, 'w') as f:
                    json.dump({"video_id": video_id, "timestamp": timestamp, "clips": [], "error": str(e)}, f)
                
                logger.info(f"Created error export files at:\n - {video_export_path}\n - {clips_export_path}")
                
                return {"success": False, "error": str(e), 
                        "video_export_path": video_export_path, 
                        "clips_export_path": clips_export_path}
            except Exception as inner_e:
                logger.error(f"Failed to create error export files: {str(inner_e)}")
                return {"success": False, "error": f"{str(e)} (and failed to create export files: {str(inner_e)})"}
