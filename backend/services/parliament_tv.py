import os
import sys
import json
import time
import signal
import logging
import shlex
import threading
import subprocess
import shutil
import tempfile
import re
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models.capture import CaptureSession as Capture
from backend.db.models.capture_log import CaptureLog

logger = logging.getLogger(__name__)

class ParliamentTVCapture:
    def __init__(self):
        """Initialize the Parliament TV capture service."""
        # Define standard paths
        self.temp_dir = Path("/app/data/temp")
        self.media_dir = Path("/app/data/media")
        self.scripts_dir = Path("/app/scripts")
        self.audio_extracts_dir = Path("/app/data/temp/audio_extracts")
        
        logger.info(f"Initialized with paths: temp={self.temp_dir}, media={self.media_dir}, scripts={self.scripts_dir}, audio={self.audio_extracts_dir}")
        
        # Create directories if they don't exist
        try:
            os.makedirs(str(self.temp_dir), exist_ok=True)
            os.makedirs(str(self.media_dir), exist_ok=True)
            os.makedirs(str(self.audio_extracts_dir), exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directories: {str(e)}")
        
        # Initialize active captures dictionary
        self.active_captures = {}
        
        # Start background task to check for completed captures
        try:
            # Create and start a daemon thread that will run in the background
            completion_thread = threading.Thread(
                target=self._check_active_captures_periodically,
                daemon=True  # This ensures the thread will exit when the main program exits
            )
            completion_thread.start()
            logger.info("Started background task to check for completed captures")
        except Exception as e:
            logger.error(f"Failed to start background task: {str(e)}")
        
    def _start_background_task(self):
        """Start a background task to periodically check for captures that should be completed."""
        try:
            # Create and start a daemon thread that will run in the background
            completion_thread = threading.Thread(
                target=self._check_active_captures_periodically,
                daemon=True  # This ensures the thread will exit when the main program exits
            )
            completion_thread.start()
            logger.info("Started background task to check for completed captures")
        except Exception as e:
            logger.error(f"Failed to start background task: {str(e)}")
    
    def _check_active_captures_periodically(self):
        """Periodically check for active captures that should be completed."""
        check_interval = 10  # Check every 10 seconds
        
        while True:
            db = None
            try:
                # Get a database session
                db = next(get_db())
                
                # Query all active captures
                active_captures = db.query(Capture).filter(Capture.status == "active").all()
                
                if active_captures:
                    logger.info(f"Checking {len(active_captures)} active captures for completion")
                    
                    # Check each active capture
                    for capture in active_captures:
                        try:
                            self.check_capture_completion(db, capture)
                        except Exception as e:
                            logger.error(f"Error checking capture {capture.id} for completion: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error in background capture check: {str(e)}")
            finally:
                # Always close the database session to release the connection back to the pool
                if db is not None:
                    try:
                        db.close()
                        logger.debug("Database session closed successfully in background task")
                    except Exception as e:
                        logger.error(f"Error closing database session: {str(e)}")
            
            # Sleep for the check interval
            time.sleep(check_interval)
    
    def check_capture_completion(self, db: Session, db_capture: Capture) -> None:
        """Check if a capture has completed based on its duration and scheduled end time.
        If completed, update its status and trigger audio extraction.
        """
        # Only check active captures
        if db_capture.status != "active":
            return
            
        # Get the current time with timezone awareness if needed
        now = datetime.now()
        if db_capture.scheduled_end and db_capture.scheduled_end.tzinfo:
            # If scheduled_end has timezone, make sure now has the same timezone
            # Use timezone.utc (imported at the top) instead of pytz
            now = now.replace(tzinfo=timezone.utc) if not now.tzinfo else now
        
        # Check if the capture has a scheduled end time and if it has passed
        if db_capture.scheduled_end and now >= db_capture.scheduled_end:
            logger.info(f"Capture {db_capture.id} has reached its scheduled end time, marking as completed")
            db_capture.status = "completed"
            db_capture.end_time = now
            
            # Log the file path for verification
            if hasattr(db_capture, 'file_path') and db_capture.file_path:
                logger.info(f"Capture {db_capture.id} video file path: {db_capture.file_path}")
                if os.path.exists(db_capture.file_path):
                    file_size = os.path.getsize(db_capture.file_path)
                    logger.info(f"Video file exists with size: {file_size} bytes")
                else:
                    logger.warning(f"Video file does not exist at path: {db_capture.file_path}")
            
            db.commit()
            
            # Trigger audio extraction
            logger.info(f"Automatically triggering audio extraction for completed capture {db_capture.id}")
            try:
                audio_result = self.extract_audio(db, db_capture.id)
                logger.info(f"Audio extraction result: {audio_result}")
            except Exception as e:
                logger.error(f"Failed to extract audio for capture {db_capture.id}: {str(e)}")
            return
            
        # Check if the capture has been running for its specified duration
        if db_capture.start_time and hasattr(db_capture, 'duration') and db_capture.duration:
            # Convert duration to integer if it's not already
            try:
                duration_seconds = int(db_capture.duration)
                expected_end_time = db_capture.start_time + timedelta(seconds=duration_seconds)
                
                # Handle timezone awareness for comparison
                if db_capture.start_time.tzinfo and not now.tzinfo:
                    # Use timezone.utc directly (already imported at the top)
                    now = now.replace(tzinfo=timezone.utc)
                
                if now >= expected_end_time:
                    logger.info(f"Capture {db_capture.id} has reached its duration ({duration_seconds}s), marking as completed")
                    db_capture.status = "completed"
                    db_capture.end_time = now
                    
                    # Log the file path for verification
                    if hasattr(db_capture, 'file_path') and db_capture.file_path:
                        logger.info(f"Capture {db_capture.id} video file path: {db_capture.file_path}")
                        if os.path.exists(db_capture.file_path):
                            file_size = os.path.getsize(db_capture.file_path)
                            logger.info(f"Video file exists with size: {file_size} bytes")
                        else:
                            logger.warning(f"Video file does not exist at path: {db_capture.file_path}")
                    
                    db.commit()
                    
                    # Trigger audio extraction
                    logger.info(f"Automatically triggering audio extraction for completed capture {db_capture.id}")
                    try:
                        audio_result = self.extract_audio(db, db_capture.id)
                        logger.info(f"Audio extraction result: {audio_result}")
                    except Exception as e:
                        logger.error(f"Failed to extract audio for capture {db_capture.id}: {str(e)}")
                    return
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not convert duration to integer for capture {db_capture.id}: {str(e)}")
                return

    def stop_capture(self, capture_id: int) -> Dict:
        """Stop a running capture and download the separate audio stream."""
        logger.info(f"Stopping capture {capture_id}")
        
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return {"success": False, "error": f"Capture {capture_id} not found in database"}
            
            # Find and terminate the ffmpeg process
            logger.info(f"Terminating capture process for {capture_id}")
            
            # Format the capture ID with leading zeros (e.g., 0096)
            padded_capture_id = str(capture_id).zfill(4)
            
            # Find and terminate any running ffmpeg processes for this capture
            try:
                # Use ps to find ffmpeg processes containing the capture ID
                ps_cmd = ["ps", "-ef"]
                ps_result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
                
                # Keep track of whether we found and killed any processes
                processes_killed = False
                
                # Look for ffmpeg processes with this capture ID
                for line in ps_result.stdout.splitlines():
                    if f"capture_{padded_capture_id}" in line and "ffmpeg" in line:
                        # Extract PID (second column in ps output)
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                logger.info(f"Terminating process with PID {pid}")
                                # First try to terminate gracefully
                                os.kill(pid, signal.SIGTERM)
                                processes_killed = True
                            except ValueError:
                                logger.warning(f"Could not parse PID from: {parts[1]}")
                            except ProcessLookupError:
                                logger.warning(f"Process {pid} no longer exists")
                            except Exception as e:
                                logger.error(f"Error killing process: {str(e)}")
                
                # If we killed any processes, give them a moment to terminate
                if processes_killed:
                    time.sleep(1)
                    
                    # Check if any processes are still running and force kill them
                    ps_result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
                    for line in ps_result.stdout.splitlines():
                        if f"capture_{padded_capture_id}" in line and "ffmpeg" in line:
                            parts = line.split()
                            if len(parts) > 1:
                                try:
                                    pid = int(parts[1])
                                    logger.warning(f"Process {pid} did not terminate gracefully, forcing kill")
                                    os.kill(pid, signal.SIGKILL)
                                except Exception as e:
                                    logger.error(f"Error force killing process: {str(e)}")
            except subprocess.TimeoutExpired:
                logger.error("Process search timed out")
            except Exception as proc_err:
                logger.error(f"Error finding/killing ffmpeg processes: {str(proc_err)}")
            
            # Format the capture ID with leading zeros
            padded_capture_id = str(capture_id).zfill(4)
            
            # Define the output file path
            output_file = os.path.join(str(self.temp_dir), f"capture_{padded_capture_id}.mp4")
            
            # Check if the MP4 file exists
            if os.path.exists(output_file):
                logger.info(f"Found MP4 file: {output_file}")
                
                # Verify the MP4 file has a valid video stream
                verify_video_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    output_file
                ]
                
                # Verify the MP4 file has a valid audio stream
                verify_audio_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    output_file
                ]
                
                try:
                    # Check video stream
                    verify_video_process = subprocess.run(
                        verify_video_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    # Check audio stream
                    verify_audio_process = subprocess.run(
                        verify_audio_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    video_valid = verify_video_process.returncode == 0
                    audio_valid = verify_audio_process.returncode == 0
                    
                    if video_valid and audio_valid:
                        logger.info(f"MP4 file has valid video and audio streams: {output_file}")
                    elif video_valid:
                        logger.warning(f"MP4 file has video but no audio stream: {output_file}")
                    elif audio_valid:
                        logger.warning(f"MP4 file has audio but no video stream: {output_file}")
                    else:
                        logger.error(f"MP4 file has neither valid video nor audio streams: {output_file}")
                        logger.error(f"Video error: {verify_video_process.stderr}")
                        logger.error(f"Audio error: {verify_audio_process.stderr}")
                except Exception as e:
                    logger.error(f"Error verifying MP4 file: {str(e)}")
                    
                # Parliament TV has separate audio and video streams - no need to extract audio from video
                # Audio will be handled separately via the dedicated audio URL

            else:
                logger.warning(f"MP4 file not found: {output_file}")
                
            # Update the file path in the database if it's not already set
            if not db_capture.file_path:
                db_capture.file_path = output_file
                db.commit()
                logger.info(f"Updated database with file path: {output_file}")
                
            # Update the capture in the database
            db_capture.status = "completed"
            db_capture.end_time = datetime.now()
            db.commit()
            
            # Remove the capture from active_captures
            if capture_id in self.active_captures:
                del self.active_captures[capture_id]
            
            # Log the success
            self.log_capture(db, capture_id, "info", "Capture completed successfully")
            
            # Parliament TV has separate audio and video streams
            # Audio extraction is handled separately via a dedicated endpoint
            # Do NOT attempt to extract audio from video files
            
            logger.info(f"Capture {capture_id} stopped successfully")
            return {"success": True, "file_path": db_capture.file_path if hasattr(db_capture, 'file_path') else None}
        except Exception as e:
            logger.error(f"Error stopping capture: {str(e)}")
    
    def start_capture(self, url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> Dict:
        """
        Start capturing a Parliament TV video stream.
        
        IMPORTANT: This method ONLY handles video capture. Audio is handled separately.
        Parliament TV provides completely separate audio and video streams.
        """
        logger.info(f"Starting video capture for URL: {url}, capture_id: {capture_id}")
        logger.info(f"Scheduled start: {scheduled_start}, Scheduled end: {scheduled_end}")
        
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                error_msg = f"Capture {capture_id} not found in database"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Extract the stream URL
            stream_info = self.extract_stream_url(url)
            if "error" in stream_info:
                error_msg = f"Failed to extract stream URL: {stream_info['error']}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Get the video and audio URLs
            video_url = stream_info.get("video_url")
            audio_url = stream_info.get("audio_url")
            
            logger.info(f"Stream info: {stream_info}")
            
            # Verify we have a valid video URL for video capture
            if not video_url:
                # If we don't have a video URL but we have the original URL, check if it's a video URL
                if "original_url" in stream_info and stream_info["original_url"] and "video" in stream_info["original_url"].lower():
                    logger.warning(f"No video_url found in stream_info, using original URL")
                    video_url = stream_info["original_url"]
                else:
                    logger.error(f"No valid video URL found in stream_info")
                    error_msg = "No valid video stream URL found"
                    logger.error(error_msg)
                    self.log_capture(db, capture_id, "error", error_msg)
                    return {"success": False, "error": error_msg}
            # Log the URLs we found
            if video_url and audio_url:
                logger.info(f"Found separate video and audio URLs for capture {capture_id}")
                logger.info(f"Video URL: {video_url}")
                logger.info(f"Audio URL: {audio_url}")
            elif video_url:
                logger.info(f"Found only video URL for capture {capture_id}")
                logger.info(f"Video URL: {video_url}")
                logger.warning("No audio URL found - audio must be captured separately")
            
            # Create the output directory if it doesn't exist
            os.makedirs(str(self.temp_dir), exist_ok=True)
            
            try:
                # Ensure the directory has proper permissions
                os.chmod(str(self.temp_dir), 0o777)  # rwx for all users
                logger.info(f"Set permissions on directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Could not set permissions on directory: {e}")
                
            # Create the video file path
            padded_capture_id = str(capture_id).zfill(4)
            output_filename = f"capture_{padded_capture_id}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            logger.info(f"Output file path: {output_path}")
            
            # Start the ffmpeg process to capture the video
            cmd = ["ffmpeg", "-y"]
            
            # Add essential options for HLS streams
            cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
            cmd.extend(["-http_persistent", "1"])
            cmd.extend(["-allowed_extensions", "ALL"])
            
            # Check if we have a time marker in the scheduled start time
            start_position = None
        
            # First check if time_marker is in the stream_info
            if "time_marker" in stream_info and stream_info["time_marker"] and "seconds" in stream_info["time_marker"]:
                time_marker_seconds = stream_info["time_marker"]["seconds"]
                if time_marker_seconds > 0:
                    start_position = time_marker_seconds
                    logger.info(f"Using time marker from stream_info: {start_position} seconds")
            
            # Always update the metadata with the URLs - this is critical for later audio extraction
            # Create a fresh metadata dictionary
            new_metadata = {}

            # If we have existing metadata, try to copy it
            if db_capture.metadata is not None:
                # Check if it's an SQLAlchemy MetaData object (special case)
                if str(type(db_capture.metadata)) == "<class 'sqlalchemy.sql.schema.MetaData'>":
                    logger.warning("Found SQLAlchemy MetaData object - creating fresh metadata dictionary")
                    # We can't use this object, so we'll create a fresh dictionary
                    # Force reset the metadata to an empty dict to avoid SQLAlchemy MetaData object issues
                    db_capture.metadata = {}
                    db.commit()
                    logger.info("Reset metadata to empty dictionary to avoid SQLAlchemy MetaData object issues")
                # Handle regular objects with __dict__
                elif hasattr(db_capture.metadata, '__dict__'):
                    try:
                        for key, value in db_capture.metadata.__dict__.items():
                            # Skip internal attributes
                            if not key.startswith('_'):
                                new_metadata[key] = value
                        logger.info(f"Copied metadata from object.__dict__: {list(new_metadata.keys())}")
                    except Exception as e:
                        logger.warning(f"Could not copy from __dict__: {e}")
                # Handle dictionary-like objects
                elif hasattr(db_capture.metadata, 'items'):
                    try:
                        for key, value in db_capture.metadata.items():
                            new_metadata[key] = value
                        logger.info(f"Copied metadata from dict-like object: {list(new_metadata.keys())}")
                    except Exception as e:
                        logger.warning(f"Could not copy from dict-like object: {e}")
                # Try direct conversion as last resort
                else:
                    try:
                        temp_dict = dict(db_capture.metadata)
                        for key, value in temp_dict.items():
                            new_metadata[key] = value
                        logger.info(f"Converted metadata to dictionary: {list(new_metadata.keys())}")
                    except Exception as e:
                        logger.warning(f"Could not convert metadata to dictionary: {e}")
        
            # Store video and audio URLs separately in metadata
            new_metadata["video_url"] = video_url
            if audio_url:
                new_metadata["audio_url"] = audio_url
                logger.info(f"Saved audio URL in metadata: {audio_url}")
            else:
                logger.warning("No audio URL available to save in metadata")
                
            # Store time marker if available
            if "time_marker" in stream_info and stream_info["time_marker"]:
                new_metadata["time_marker"] = stream_info["time_marker"]
                
            # Update the metadata with the new dictionary
            try:
                # First try the normal way - force it to be a proper JSON dictionary
                import json
                metadata_json_str = json.dumps(new_metadata)
                metadata_dict = json.loads(metadata_json_str)
                db_capture.metadata = metadata_dict
                
                # Log the metadata to verify it's correctly formatted
                logger.info(f"Updated metadata for capture {capture_id} with keys: {list(metadata_dict.keys())}")
                if 'audio_url' in metadata_dict:
                    logger.info(f"Verified audio_url in metadata: {metadata_dict['audio_url']}")
                
                # If we have an audio URL, also update it directly in the database as a fallback
                if audio_url:
                    # Use a direct SQL query to update the metadata JSON
                    from sqlalchemy import text
                    # Need to properly format the JSON string for PostgreSQL
                    audio_url_json = json.dumps(audio_url)
                    # Use string formatting for the path
                    stmt = text("UPDATE capture_sessions SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{""audio_url""}', cast(:audio_url_json AS jsonb)) WHERE id = :id")
                    db.execute(stmt, {"id": capture_id, "audio_url_json": audio_url_json})
                    logger.info(f"Updated audio_url directly in database using SQL for capture {capture_id}")
            except Exception as e:
                logger.error(f"Error updating metadata: {e}")
                # If the normal way fails, try a direct SQL update as a last resort
                try:
                    from sqlalchemy import text
                    # Convert the metadata to a JSON string
                    import json
                    metadata_json = json.dumps(new_metadata)
                    # Update the metadata directly in the database
                    # For PostgreSQL, we need to cast the string to jsonb
                    stmt = text("UPDATE capture_sessions SET metadata = cast(:metadata_json AS jsonb) WHERE id = :id")
                    db.execute(stmt, {"id": capture_id, "metadata_json": metadata_json})
                    logger.info(f"Updated metadata directly in database using SQL for capture {capture_id}")
                except Exception as e2:
                    logger.error(f"Failed to update metadata even with direct SQL: {e2}")
                    # Continue anyway, we'll try to handle this in the audio extraction endpoint
            
            # Commit the changes to ensure metadata is saved
            db.commit()
            
            # Double-check that the audio URL was saved correctly
            if audio_url:
                logger.info(f"Verifying audio URL in metadata: {db_capture.metadata.get('audio_url', 'NOT FOUND')}")
                
            # Check for time marker in metadata if not found in stream_info
            if not start_position and db_capture.metadata and "time_marker" in db_capture.metadata:
                time_marker_seconds = db_capture.metadata.get("time_marker", {}).get("seconds", 0)
                if time_marker_seconds > 0:
                    # If we have a time marker, use it as the start position
                    start_position = time_marker_seconds
                    logger.info(f"Using time marker from metadata: {start_position} seconds")
            elif not start_position and scheduled_start:
                logger.info(f"Using scheduled start time but no time marker found")
        
            # Add seek option to start at the specified position
            if start_position:
                # For ffmpeg, it's more efficient to put -ss BEFORE -i for seeking
                cmd.extend(["-ss", str(start_position)])
                logger.info(f"Added seek option to ffmpeg command: -ss {start_position}")
                
            # Ensure video_url is a valid string
            if not video_url or not isinstance(video_url, str):
                error_msg = f"Invalid or missing video URL: {video_url}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
                
            # Use the video_url directly - it's already been validated as a string
            actual_video_url = video_url
            logger.info(f"Using video URL: {actual_video_url}")
            
            # Add network-related options to handle Parliament TV URLs
            cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
            cmd.extend(["-http_persistent", "1"])
            cmd.extend(["-allowed_extensions", "ALL"])
            cmd.extend(["-reconnect", "1"])
            cmd.extend(["-reconnect_streamed", "1"])
            cmd.extend(["-reconnect_delay_max", "5"])
            cmd.extend(["-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"])
                
            # Add input file for video
            cmd.extend(["-i", actual_video_url])
            
            # For Parliament TV, audio and video are completely separate streams
            # We only capture video here - audio is handled separately
            logger.info(f"Using video URL for video capture only: {actual_video_url}")
            
            # Add options to handle HLS streams better
            cmd.extend(["-live_start_index", "0"])
            cmd.extend(["-avoid_negative_ts", "make_zero"])
            cmd.extend(["-correct_ts_overflow", "1"])
            cmd.extend(["-timeout", "5000000"])  # Add a longer timeout
            
            # DO NOT try to use audio from video stream - audio is handled separately
            logger.info("Parliament TV has separate audio and video streams - not using audio from video")
            
            # Add additional options for better handling of streams
            cmd.extend(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
            
            # Add HLS-specific options
            cmd.extend(["-hls_allow_cache", "1"])
            cmd.extend(["-http_persistent", "1"])
            
            # Use proper codec options to ensure we have a valid MP4 file
            # Instead of just copying the video stream, use a specific codec to ensure compatibility
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"])
            # Don't try to process audio in the video capture - we'll handle audio separately
            cmd.extend(["-an"])
            
            # Use a direct approach to create an MP4 file with the moov atom at the beginning
            output_file = os.path.join(str(self.temp_dir), f"capture_{padded_capture_id}.mp4")
            
            # If we have a separate audio URL, add it as a second input
            if audio_url and isinstance(audio_url, str):
                logger.info(f"Adding separate audio input: {audio_url}")
                cmd.extend(["-i", audio_url])
                
                # Map video from first input and audio from second input
                cmd.extend(["-map", "0:v:0"])  # Map the first video stream from first input
                cmd.extend(["-map", "1:a:0"])  # Map the first audio stream from second input
            else:
                # If no separate audio URL, just map the video stream
                cmd.extend(["-map", "0:v:0"])  # Map the first video stream
                # Don't map audio - we'll extract it separately later
            
            # Use MP4 format with faststart to ensure the moov atom is at the beginning
            cmd.extend(["-f", "mp4"])
            cmd.extend(["-movflags", "+faststart"])
            
            # Store the output file path in the database
            # Make sure we're using a consistent output path
            output_file = str(output_path)  # Use the same output path throughout
            db_capture.file_path = output_file
            db.commit()
            
            # Add duration limit - place it BEFORE the output file but AFTER input options
            # For recorded streams with a time marker, this is the exact duration to capture
            # For live streams, this acts as a safety limit
            cmd.extend(["-t", str(duration)])
            logger.info(f"Setting capture duration to {duration} seconds")
            
            # Avoid negative timestamps
            cmd.extend(["-avoid_negative_ts", "make_zero"])
            
            # Add output file - this must be the last parameter and should not be duplicated
            # Remove any existing output file in the command to avoid duplication
            if str(output_path) in cmd:
                cmd.remove(str(output_path))
            cmd.append(str(output_path))
            
            # Log the full command for debugging
            logger.info(f"Full ffmpeg command: {' '.join(cmd)}")
            
            # Create the output directory if it doesn't exist
            os.makedirs(os.path.dirname(str(output_path)), exist_ok=True)
            
            # Start the ffmpeg process with better error handling
            try:
                # First, test if the stream is accessible
                logger.info(f"Testing stream accessibility for URL: {actual_video_url}")
                test_result = self.test_stream_url(actual_video_url)
                
                if not test_result.get("success", False):
                    error_msg = f"Stream URL is not accessible: {test_result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    self.log_capture(db, capture_id, "error", error_msg)
                    return {"success": False, "error": error_msg}
                
                logger.info(f"Stream URL test successful: {test_result.get('message', '')}")
                
                # Log the time marker if available
                if start_position:
                    logger.info(f"Using time marker for seeking: {start_position} seconds")
                
                # Create a log file for ffmpeg output
                log_file_path = os.path.join(self.temp_dir, f"ffmpeg_log_{capture_id}.txt")
                
                logger.info(f"Stream URL is accessible, starting capture process")
                logger.info(f"Full command: {' '.join(cmd)}")
                
                # Use a different approach to run ffmpeg in the background without shell=True
                # We'll use subprocess.Popen with preexec_fn to detach the process
                
                # Open log file for the process
                log_file = open(log_file_path, 'w')
                
                # Log what we're about to do
                logger.info(f"Starting ffmpeg process with command: {' '.join(cmd)}")
                logger.info(f"Redirecting output to: {log_file_path}")
                
                # Start the process in the background with process group detached
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setpgrp,  # This detaches the process from the parent
                    close_fds=True,         # Close file descriptors
                    shell=False             # CRITICAL: Avoid shell parsing issues with URLs
                )
                
                logger.info(f"Started ffmpeg process for capture {capture_id} in the background")
                
                # Store information in the active_captures dictionary
                self.active_captures[capture_id] = {
                    "start_time": datetime.now(),
                    "scheduled_end": scheduled_end,
                    "output_file": str(output_path)
                }
                
                # Touch the output file to ensure it exists with proper permissions
                try:
                    with open(output_path, 'w') as f:
                        pass
                    os.chmod(output_path, 0o666)  # rw for all users
                    logger.info(f"Created empty output file with proper permissions: {output_path}")
                except Exception as e:
                    logger.warning(f"Could not create empty output file: {e}")
                
                # Update the database
                db_capture.video_file = str(output_path)
                db_capture.status = "active"
                db_capture.start_time = datetime.now()
                db_capture.end_time = None
                db.commit()
                
                # Log the capture start
                self.log_capture(db, capture_id, "info", f"Started capture for URL: {url}")
                
                return {
                    "success": True,
                    "message": f"Capture {capture_id} started successfully",
                    "output_file": str(output_path),
                    "video_url": actual_video_url,
                    "audio_url": audio_url
                }
            
            except subprocess.TimeoutExpired:
                error_msg = "Timeout while testing stream URL"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Failed to start ffmpeg process: {str(e)}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return {"success": False, "error": f"Failed to start capture: {str(e)}"}
    
    def start_capture_async(self, url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> bool:
        """Start capturing a Parliament TV stream asynchronously."""
        logger.info(f"Starting async capture for URL: {url}, capture_id: {capture_id}")
        
        try:
            # Start the capture in a separate thread
            thread = threading.Thread(
                target=self.start_capture,
                args=(url, capture_id, duration, scheduled_start, scheduled_end)
            )
            thread.daemon = True
            thread.start()
            
            # Store the thread
            if capture_id in self.active_captures:
                self.active_captures[capture_id]["thread"] = thread
            else:
                self.active_captures[capture_id] = {"thread": thread}
            
            return True
        except Exception as e:
            logger.error(f"Failed to start async capture: {str(e)}")
            return False
    
    def extract_stream_url(self, url: str) -> Dict:
        """Extract the direct stream URL from a Parliament TV event URL."""
        try:
            logger.info(f"Extracting stream URL from: {url}")
            
            # Validate URL
            if not url:
                logger.error(f"Invalid URL provided: {url}")
                return {"error": f"Invalid URL provided: {url}"}
                
            # Check if the URL is already a dictionary with direct stream URLs
            if isinstance(url, dict) and "video_url" in url:
                logger.info(f"Direct stream URL is already a dictionary: {url}")
                video_url = url.get("video_url")
                audio_url = url.get("audio_url")
                return {
                    "video_url": video_url,
                    "audio_url": audio_url,
                    "event_id": "direct",
                    "time_marker": {"seconds": 0},
                    "original_url": url.get("original_url", "Direct Stream")
                }
            
            # Check if the URL is already a direct stream URL
            if isinstance(url, str) and ('.m3u8' in url or 'cdn.redbee.live' in url):
                logger.info("URL appears to be a direct stream URL already")
                
                # Parliament TV has completely separate audio and video streams
                is_audio = 'audio' in url.lower() and not 'video' in url.lower()
                
                if is_audio:
                    logger.info("URL appears to be an audio stream")
                    return {
                        "video_url": None,
                        "audio_url": url,
                        "event_id": "direct",
                        "time_marker": {"seconds": 0},
                        "original_url": url
                    }
                else:
                    logger.info("URL appears to be a video stream")
                    # For Parliament TV, if we have a direct video URL, try to construct the audio URL
                    # This is a common pattern in Parliament TV URLs
                    audio_url = None
                    if 'video=' in url and '.m3u8' in url:
                        # Replace video=XXXXX.m3u8 with audio_eng=64000.m3u8
                        # Use regex to handle any video bitrate, not just 3000000
                        import re
                        audio_url = re.sub(r'video=[0-9]+\.m3u8', 'audio_eng=64000.m3u8', url)
                        logger.info(f"Constructed audio URL: {audio_url}")
                    
                    return {
                        "video_url": url,
                        "audio_url": audio_url,
                        "event_id": "direct",
                        "time_marker": {"seconds": 0},
                        "original_url": url
                    }
            
            # Set script path
            script_path = "/app/scripts/extract-url.py"
            
            # Verify the script exists
            if not os.path.exists(script_path):
                logger.warning(f"Script not found at {script_path}, checking alternatives")
                # Try alternative locations
                alt_paths = [
                    "/app/backend/scripts/extract-url.py",
                    "/app/scripts/extract-url.py",
                    "/Users/joebradley/Veedoo/Development/the-mp/scripts/extract-url.py"
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        logger.info(f"Found script at: {script_path}")
                        break
                else:
                    logger.error("Could not find extract-url.py in any location")
                    return {"error": "Could not find extract-url.py script"}
            
            # Check if Python executable is valid
            python_executable = sys.executable
            if not os.path.exists(python_executable):
                logger.warning(f"Python executable not found: {python_executable}")
                # Try to find python executable
                alt_python_paths = [
                    "/usr/bin/python3",
                    "/usr/bin/python",
                    "/usr/local/bin/python3",
                    "/usr/local/bin/python"
                ]
                for alt_path in alt_python_paths:
                    if os.path.exists(alt_path):
                        python_executable = alt_path
                        logger.info(f"Found Python at: {python_executable}")
                        break
                else:
                    logger.error("Could not find Python executable")
                    return {"error": "Could not find Python executable"}
            
            # Build and run the command
            cmd = [python_executable, script_path, url]
            logger.info(f"Running extract-url command for: {url}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the command was successful
            if result.returncode == 0:
                try:
                    # Parse the JSON output
                    stream_info = json.loads(result.stdout)
                    logger.info(f"Successfully extracted stream URL: {stream_info}")
                    
                    # Convert old format to new format if needed
                    if "direct_stream" in stream_info:
                        logger.info(f"Converting old format with direct_stream to new format")
                        direct_stream = stream_info["direct_stream"]
                        if isinstance(direct_stream, dict) and "video_url" in direct_stream:
                            # Extract video_url and audio_url from nested dict
                            return {
                                "video_url": direct_stream.get("video_url"),
                                "audio_url": direct_stream.get("audio_url"),
                                "event_id": stream_info.get("event_id"),
                                "time_marker": stream_info.get("time_marker"),
                                "original_url": stream_info.get("original_url")
                            }
                        else:
                            # If direct_stream is a string, it's the video URL
                            return {
                                "video_url": direct_stream if isinstance(direct_stream, str) else None,
                                "audio_url": None,
                                "event_id": stream_info.get("event_id"),
                                "time_marker": stream_info.get("time_marker"),
                                "original_url": stream_info.get("original_url")
                            }
                    else:
                        # Already in the new format or different structure
                        return {
                            "video_url": stream_info.get("video_url") or stream_info.get("url"),
                            "audio_url": stream_info.get("audio_url"),
                            "event_id": stream_info.get("event_id"),
                            "time_marker": stream_info.get("time_marker"),
                            "original_url": stream_info.get("original_url") or url
                        }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON output: {str(e)}")
                    return {"error": f"Failed to parse JSON output: {str(e)}"}
            else:
                logger.error(f"Command failed with return code {result.returncode}: {result.stderr}")
                return {"error": f"Command failed with return code {result.returncode}: {result.stderr}"}
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}

    def log_capture(self, db: Session, capture_id: int, level: str, message: str):
        """Log a message for a capture."""
        try:
            # Create a new log entry
            log = CaptureLog(
                capture_id=capture_id,
                level=level,
                message=message,
                timestamp=datetime.now()
            )
            db.add(log)
            db.commit()
            logger.debug(f"Added log for capture {capture_id}: [{level}] {message}")
        except Exception as e:
            logger.error(f"Failed to add log for capture {capture_id}: {str(e)}")
            # Don't raise the exception, just log it
    def test_stream_url(self, url: str) -> Dict:
        """Test if a stream URL is valid and accessible.
        
        Args:
            url: The URL to test
            
        Returns:
            Dict: Dictionary with success status and optional error message
        """
        try:
            # Use ffprobe to check if the stream is valid
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                url
            ]
            
            # Run the command with a timeout
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5  # 5 second timeout
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                return {"success": True}
            else:
                error_msg = f"Stream URL test failed: {url}. Error: {result.stderr}"
                logger.warning(error_msg)
                return {"success": False, "error": error_msg}
        except subprocess.TimeoutExpired:
            error_msg = f"Stream URL test timed out: {url}"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Error testing stream URL: {url}. Error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    def get_metadata(self, capture_id: int) -> Dict:
        """Get metadata for a capture session"""
        logger.info(f"Getting metadata for capture {capture_id}")
        
        # Create a new session for this query
        try:
            db_session = next(get_db())
            try:
                # Get the capture session from the database
                db_capture = db_session.query(Capture).filter(Capture.id == capture_id).first()
                if not db_capture:
                    logger.error(f"Capture session {capture_id} not found when getting metadata")
                    return {}
                
                # Extract metadata from the capture session
                metadata = {}
                if db_capture.metadata:
                    if isinstance(db_capture.metadata, dict):
                        metadata = db_capture.metadata
                        logger.info(f"Found metadata dictionary with keys: {list(metadata.keys())}")
                    elif hasattr(db_capture.metadata, '__dict__'):
                        # Handle object-like metadata
                        try:
                            for key, value in db_capture.metadata.__dict__.items():
                                if not key.startswith('_'):
                                    metadata[key] = value
                            logger.info(f"Extracted metadata from object.__dict__: {list(metadata.keys())}")
                        except Exception as e:
                            logger.error(f"Error extracting from metadata.__dict__: {str(e)}")
                    else:
                        # Try to convert to dict
                        try:
                            metadata = dict(db_capture.metadata)
                            logger.info(f"Converted metadata to dictionary: {list(metadata.keys())}")
                        except Exception as e:
                            logger.error(f"Could not convert metadata to dictionary: {str(e)}")
                
                # If we have audio_url in metadata, add it to a 'media' list for compatibility
                if 'audio_url' in metadata and 'media' not in metadata:
                    metadata['media'] = [{
                        'type': 'audio',
                        'url': metadata['audio_url']
                    }]
                    logger.info(f"Added audio_url to media list: {metadata['audio_url']}")
                
                return metadata
            finally:
                db_session.close()
                logger.debug(f"Closed database session after getting metadata for capture {capture_id}")
        except Exception as e:
            logger.error(f"Error getting metadata for capture {capture_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def extract_audio(self, db: Session, capture_id: int) -> Dict:
        """Extract audio from Parliament TV - AUDIO ONLY, NEVER FROM VIDEO"""
        logger.info(f"========== STARTING AUDIO EXTRACTION for capture {capture_id} ===========")
        
        # Create a new database session for this extraction to avoid connection pool issues
        try_new_session = False
        if db is None:
            try_new_session = True
            try:
                db = next(get_db())
                logger.info(f"Created new database session for audio extraction of capture {capture_id}")
            except Exception as e:
                logger.error(f"Failed to create new database session: {str(e)}")
                return {"success": False, "error": f"Database connection error: {str(e)}"}
        
        # Get the capture session from the database
        db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
        if not db_capture:
            logger.error(f"Capture session {capture_id} not found")
            if try_new_session:
                db.close()
            return {"success": False, "error": f"Capture session {capture_id} not found"}
        
        logger.info(f"Found capture session {capture_id} with status: {db_capture.status}")
        
        # Try to find audio URLs in the metadata
        audio_urls = []
        try:
            metadata = self.get_metadata(capture_id)
            logger.info(f"Retrieved metadata for capture {capture_id}")
            
            if metadata and 'media' in metadata:
                logger.info(f"Found {len(metadata['media'])} media items in metadata")
                for media_item in metadata['media']:
                    logger.info(f"Media item type: {media_item.get('type')}")
                    if media_item.get('type') == 'audio':
                        audio_urls.append(media_item.get('url'))
                        logger.info(f"Found audio URL in metadata: {media_item.get('url')}")
            else:
                logger.warning(f"No 'media' key found in metadata or metadata is empty")
                
                # Check for direct audio_url in metadata
                if db_capture.metadata and isinstance(db_capture.metadata, dict):
                    audio_url = db_capture.metadata.get("audio_url")
                    if audio_url:
                        audio_urls.append(audio_url)
                        logger.info(f"Found audio_url in metadata dictionary: {audio_url}")
                elif db_capture.metadata and hasattr(db_capture.metadata, 'audio_url'):
                    audio_url = db_capture.metadata.audio_url
                    if audio_url:
                        audio_urls.append(audio_url)
                        logger.info(f"Found audio_url as attribute: {audio_url}")
            
            if not audio_urls:
                logger.warning(f"No audio URLs found in metadata for capture {capture_id}")
                # Log the structure of metadata for debugging
                logger.info(f"Metadata structure: {str(metadata)[:1000]}..." if metadata and len(str(metadata)) > 1000 else f"Metadata structure: {metadata}")
                logger.warning(f"DB Capture metadata format: {type(db_capture.metadata)}")
                if db_capture.metadata:
                    logger.warning(f"DB Capture metadata content: {str(db_capture.metadata)[:1000]}..." if len(str(db_capture.metadata)) > 1000 else db_capture.metadata)
        except Exception as e:
            logger.error(f"Error retrieving metadata for capture {capture_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Select the first audio URL if available
        audio_url = audio_urls[0] if audio_urls else None
        logger.info(f"Selected audio URL for extraction: {audio_url}")
        
        # If no audio URL, we can't proceed - NEVER fall back to video
        if not audio_url:
            logger.error("No audio URL found in metadata - cannot extract audio")
            error_result = {"success": False, "error": "No audio URL found in metadata"}
            # Close the database connection if we created it
            if try_new_session and db is not None:
                try:
                    db.close()
                    logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                except Exception as e:
                    logger.error(f"Error closing database session: {str(e)}")
            return error_result
        
        # Format the capture ID with leading zeros
        padded_capture_id = str(capture_id).zfill(4)
        logger.info(f"Using padded capture ID: {padded_capture_id}")
        
        # Define the output audio file path
        audio_dir = os.path.join(str(self.temp_dir), "audio_extracts")
        os.makedirs(audio_dir, exist_ok=True)
        audio_file = os.path.join(audio_dir, f"capture_{padded_capture_id}.audio.mp3")
        logger.info(f"Audio output file will be: {audio_file}")
        
        # Check if the directory exists and is writable
        if os.path.exists(audio_dir):
            logger.info(f"Audio directory exists: {audio_dir}")
            try:
                test_file = os.path.join(audio_dir, ".test_write")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logger.info(f"Audio directory is writable")
            except Exception as e:
                logger.warning(f"Audio directory may not be writable: {str(e)}")
        else:
            logger.warning(f"Audio directory does not exist: {audio_dir}")
        
        # Create the ffmpeg command - DIRECT FROM AUDIO URL ONLY
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-i", audio_url,  # Input audio URL
            "-c:a", "libmp3lame",  # Use MP3 codec
            "-q:a", "2",  # Quality setting for audio
            "-vn",  # No video
            audio_file  # Output file
        ]
        
        logger.info(f"FFmpeg command for audio extraction: {' '.join(cmd)}")
        logger.info(f"Audio URL: {audio_url}")
        logger.info(f"Output file: {audio_file}")
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(audio_file), exist_ok=True)
        
        # Execute the command
        try:
            # Run the command with a timeout
            logger.info(f"Running audio extraction command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Log command output regardless of success/failure for debugging
            logger.info(f"FFmpeg stdout: {result.stdout[:500]}..." if len(result.stdout) > 500 else f"FFmpeg stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"FFmpeg stderr: {result.stderr[:500]}..." if len(result.stderr) > 500 else f"FFmpeg stderr: {result.stderr}")
            
            if result.returncode == 0:
                logger.info(f"Audio extraction successful for capture {capture_id}")
                # Verify the file was created
                if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                    logger.info(f"Audio file created successfully: {audio_file} (size: {os.path.getsize(audio_file)} bytes)")
                    
                    # Update the database with the audio file path
                    try:
                        db_capture.audio_file_path = audio_file
                        db.commit()
                        logger.info(f"Updated database with audio file path for capture {capture_id}")
                    except Exception as e:
                        logger.error(f"Failed to update database with audio file path: {str(e)}")
                    
                    result = {"success": True, "message": "Audio extraction completed successfully", "audio_file": audio_file}
                    # Close the database connection if we created it
                    if try_new_session and db is not None:
                        try:
                            db.close()
                            logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                        except Exception as e:
                            logger.error(f"Error closing database session: {str(e)}")
                    return result
                else:
                    logger.error(f"Audio file was not created or is empty: {audio_file}")
                    # Check directory permissions
                    output_dir = os.path.dirname(audio_file)
                    if not os.access(output_dir, os.W_OK):
                        logger.error(f"No write permission to directory: {output_dir}")
                    error_result = {"success": False, "error": "Audio file was not created or is empty"}
                    # Close the database connection if we created it
                    if try_new_session and db is not None:
                        try:
                            db.close()
                            logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                        except Exception as e:
                            logger.error(f"Error closing database session: {str(e)}")
                    return error_result
            else:
                logger.error(f"Audio extraction failed for capture {capture_id}: {result.stderr}")
                error_result = {"success": False, "error": "Audio extraction failed: " + result.stderr}
                # Close the database connection if we created it
                if try_new_session and db is not None:
                    try:
                        db.close()
                        logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                    except Exception as e:
                        logger.error(f"Error closing database session: {str(e)}")
                return error_result
        except subprocess.TimeoutExpired:
            error_msg = f"Audio extraction timed out for capture {capture_id} after 300 seconds"
            logger.error(error_msg)
            error_result = {"success": False, "error": error_msg}
            # Close the database connection if we created it
            if try_new_session and db is not None:
                try:
                    db.close()
                    logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                except Exception as e:
                    logger.error(f"Error closing database session: {str(e)}")
            return error_result
        except Exception as e:
            error_msg = f"Error executing audio extraction command for capture {capture_id}: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            error_result = {"success": False, "error": error_msg}
            # Close the database connection if we created it
            if try_new_session and db is not None:
                try:
                    db.close()
                    logger.debug(f"Closed database session for audio extraction of capture {capture_id}")
                except Exception as e:
                    logger.error(f"Error closing database session: {str(e)}")
            return error_result


# Initialize the Parliament TV capture service
parliament_tv_capture = ParliamentTVCapture()


# Module-level functions for API endpoints
def start_capture(url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> Dict:
    """Start capturing a Parliament TV stream."""
    return parliament_tv_capture.start_capture(url, capture_id, duration, scheduled_start, scheduled_end)


def start_capture_async(url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> bool:
    """Start capturing a Parliament TV stream asynchronously."""
    return parliament_tv_capture.start_capture_async(url, capture_id, duration, scheduled_start, scheduled_end)


def stop_capture(capture_id: int) -> Dict:
    """Stop a running capture."""
    return parliament_tv_capture.stop_capture(capture_id)


def get_capture_status(capture_id: int) -> Dict:
    """Get the status of a capture."""
    return parliament_tv_capture.get_capture_status(capture_id)


def get_capture_logs(capture_id: int) -> Dict:
    """Get the logs for a capture."""
    return parliament_tv_capture.get_capture_logs(capture_id)


def extract_stream_url(url: str) -> Dict:
    """Extract the direct stream URL from a Parliament TV event URL."""
    return parliament_tv_capture.extract_stream_url(url)


def test_stream_url(url: str) -> Dict:
    """Test if a stream URL is valid and accessible."""
    return parliament_tv_capture.test_stream_url(url)


def extract_audio(db: Session, capture_id: int) -> Dict:
    """Extract audio from the dedicated audio stream URL. Never extracts from video files."""
    return parliament_tv_capture.extract_audio(db, capture_id)
