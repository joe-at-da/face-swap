import os
import sys
import json
import time
import signal
import logging
import threading
import subprocess
import shutil
import tempfile
import re
from datetime import datetime, timedelta
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

    def stop_capture(self, capture_id: int) -> Dict:
        """Stop a running capture and download the separate audio stream."""
        logger.info(f"Stopping capture {capture_id}")
        
        try:
            # Check if the capture is active
            if capture_id not in self.active_captures:
                logger.error(f"Capture {capture_id} is not active")
                return {"success": False, "error": f"Capture {capture_id} is not active"}
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return {"success": False, "error": f"Capture {capture_id} not found in database"}
            
            # Find and terminate the ffmpeg process
            logger.info(f"Terminating capture process for {capture_id}")
            
            # Get the thread from active_captures
            capture_info = self.active_captures.get(capture_id, {})
            
            # Find and terminate any running ffmpeg processes for this capture
            try:
                # Format the capture ID with leading zeros (e.g., 0096)
                padded_capture_id = str(capture_id).zfill(4)
                
                # Use ps to find ffmpeg processes containing the capture ID
                ps_cmd = ["ps", "-ef"]
                ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
                
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
                                # Give it a moment to terminate
                                time.sleep(1)
                                # Check if it's still running
                                try:
                                    os.kill(pid, 0)  # This will raise an error if the process is gone
                                    # If we get here, the process is still running, so force kill it
                                    os.kill(pid, signal.SIGKILL)
                                    time.sleep(0.5)  # Give it a moment to die
                                except OSError:
                                    # Process is already gone
                                    pass
                            except ValueError:
                                logger.warning(f"Could not parse PID from: {parts[1]}")
                            except Exception as e:
                                logger.error(f"Error killing process: {str(e)}")
            except Exception as proc_err:
                logger.error(f"Error finding/killing ffmpeg processes: {str(proc_err)}")
            
            # Update the database
            db_capture.status = "completed"
            db_capture.end_time = datetime.now()
            db.commit()
            
            # Log the capture stop
            self.log_capture(db, capture_id, "info", "Capture stopped by user")
            
            # Get the output file path from the database
            output_file = db_capture.file_path
            
            # Check if the output file exists
            if os.path.exists(output_file):
                logger.info(f"Output file exists: {output_file}")
                
                # Download the separate audio stream
                logger.info(f"Downloading separate audio stream for capture {capture_id}")
                
                # Use the audio_extracts_dir from the class initialization
                os.makedirs(str(self.audio_extracts_dir), exist_ok=True)
                
                # Create the audio file path - format: capture_XXXX.mp3 to match video naming
                padded_capture_id = str(capture_id).zfill(4)
                audio_file_path = os.path.join(str(self.audio_extracts_dir), f"capture_{padded_capture_id}.mp3")
                
                try:
                    # Get all URLs from the capture metadata
                    original_url = None
                    video_url = None
                    audio_url = None
                    
                    if hasattr(db_capture, 'metadata') and db_capture.metadata and isinstance(db_capture.metadata, dict):
                        # Get the original URL (the URL entered by the user with time marker)
                        if 'original_url' in db_capture.metadata:
                            original_url = db_capture.metadata['original_url']
                        
                        # Get the direct video and audio URLs if already stored in metadata
                        if 'video_url' in db_capture.metadata:
                            video_url = db_capture.metadata['video_url']
                            logger.info(f"Found video URL in metadata: {video_url}")
                        
                        if 'audio_url' in db_capture.metadata:
                            audio_url = db_capture.metadata['audio_url']
                            logger.info(f"Found audio URL in metadata: {audio_url}")
                    
                    # If original_url is not in metadata, use source_url as fallback
                    if not original_url and hasattr(db_capture, 'source_url') and db_capture.source_url:
                        original_url = db_capture.source_url
                    
                    # If we don't already have an audio URL from metadata, try to extract it
                    if not audio_url and original_url:
                        # Extract the stream URLs from the original URL
                        logger.info(f"Extracting stream URLs from original URL: {original_url}")
                        stream_info = self.extract_stream_url(original_url)
                        
                        # Check if we have separate audio URL
                        if "direct_stream" in stream_info:
                            direct_stream = stream_info["direct_stream"]
                            if isinstance(direct_stream, dict):
                                # Extract both video and audio URLs if available
                                if "audio_url" in direct_stream:
                                    audio_url = direct_stream["audio_url"]
                                    logger.info(f"Extracted audio URL: {audio_url}")
                                
                                if not video_url and "video_url" in direct_stream:
                                    video_url = direct_stream["video_url"]
                                    logger.info(f"Extracted video URL: {video_url}")
                        
                        # If we have an audio URL, download it
                        if audio_url:
                            logger.info(f"Attempting to download audio from URL: {audio_url}")
                            # Use ffmpeg to download the audio
                            cmd = ["ffmpeg", "-y"]
                            
                            # Check if we have a time marker in the metadata
                            start_position = None
                            if "time_marker" in db_capture.metadata:
                                time_marker_seconds = db_capture.metadata.get("time_marker", {}).get("seconds", 0)
                                if time_marker_seconds > 0:
                                    # If we have a time marker, use it as the start position
                                    start_position = time_marker_seconds
                                    logger.info(f"Using time marker as start position for audio: {start_position} seconds")
                            
                            # Add input options - for ffmpeg, it's more efficient to put -ss BEFORE -i for seeking
                            if start_position:
                                # Add seek option to start at the specified position
                                cmd.extend(["-ss", str(start_position)])
                            
                            # Add input file with appropriate options for better stream handling
                            cmd.extend(["-i", audio_url])
                            cmd.extend(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
                            
                            # Add codec options - use aac codec instead of copy for better compatibility
                            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
                            
                            # Get duration from metadata if available
                            if "duration" in db_capture.metadata:
                                duration = db_capture.metadata.get("duration", 300)  # Default to 5 minutes
                                cmd.extend(["-t", str(duration)])
                                logger.info(f"Setting audio capture duration to {duration} seconds")
                            
                            # Add output file
                            cmd.append(audio_file_path)
                            
                            # Log the full command for debugging
                            logger.info(f"Full audio download command: {' '.join(cmd)}")
            
                            logger.info(f"Running ffmpeg to download audio: {audio_file_path}")
                            try:
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
                
                                # Log the output for debugging
                                if result.stdout:
                                    logger.info(f"ffmpeg stdout: {result.stdout[:500]}...")
                                if result.stderr:
                                    logger.info(f"ffmpeg stderr: {result.stderr[:500]}...")
                            except subprocess.TimeoutExpired:
                                logger.error("Audio download timed out after 5 minutes")
                                self.log_capture(db, capture_id, "error", "Audio download timed out after 5 minutes")
                                return {"success": False, "error": "Audio download timed out"}
                            
                            if result.returncode == 0:
                                logger.info(f"Successfully downloaded audio to: {audio_file_path}")
                                
                                # Save the audio file path to the database
                                try:
                                    # Update the metadata
                                    if not db_capture.metadata:
                                        db_capture.metadata = {}
                                    
                                    if isinstance(db_capture.metadata, dict):
                                        # Store all URLs and file paths in metadata for reference
                                        db_capture.metadata["original_url"] = original_url  # The URL entered by the user
                                        db_capture.metadata["video_url"] = video_url  # The direct video stream URL
                                        db_capture.metadata["audio_url"] = audio_url  # The direct audio stream URL
                                        db_capture.metadata["audio_file_path"] = audio_file_path  # Path to downloaded audio file
                                        
                                        # Ensure audio file has same scheduling info as video
                                        if "scheduled_start" in db_capture.metadata:
                                            logger.info(f"Using same scheduled start for audio: {db_capture.metadata['scheduled_start']}")
                                        if "scheduled_end" in db_capture.metadata:
                                            logger.info(f"Using same scheduled end for audio: {db_capture.metadata['scheduled_end']}")
                                    
                                    # Save to database
                                    db_capture.audio_file_path = audio_file_path
                                    db.commit()
                                    
                                    logger.info("Successfully saved audio_file_path to database")
                                except Exception as db_err:
                                    logger.error(f"Failed to save audio file path to database: {str(db_err)}")
                                    self.log_capture(db, capture_id, "error", f"Failed to save audio file path to database: {str(db_err)}")
                            else:
                                logger.error(f"Failed to download audio: {result.stderr}")
                                self.log_capture(db, capture_id, "error", f"Failed to download audio: {result.stderr}")
                        else:
                            logger.error("No audio URL found in stream info")
                            self.log_capture(db, capture_id, "error", "No audio URL found in stream info")
                    else:
                        logger.error("No original URL found for capture")
                        self.log_capture(db, capture_id, "error", "No original URL found for capture")
                except Exception as e:
                    logger.error(f"Failed to extract audio: {str(e)}")
                    self.log_capture(db, capture_id, "error", f"Failed to extract audio: {str(e)}")
                
                # Remove the capture from active_captures
                if capture_id in self.active_captures:
                    del self.active_captures[capture_id]
                
                return {"success": True, "message": f"Capture {capture_id} stopped successfully", "output_file": output_file}
            else:
                logger.error(f"Output file does not exist: {output_file}")
                self.log_capture(db, capture_id, "error", f"Output file does not exist: {output_file}")
                return {"success": False, "error": f"Output file does not exist: {output_file}"}
        except Exception as e:
            logger.error(f"Failed to stop capture: {str(e)}")
            return {"success": False, "error": f"Failed to stop capture: {str(e)}"}
    
    def log_capture(self, db: Session, capture_id: int, level: str, message: str):
        """Log a message for a capture."""
        try:
            log = CaptureLog(
                capture_id=capture_id,
                level=level,
                message=message,
                timestamp=datetime.now()
            )
            db.add(log)
            db.commit()
            logger.info(f"Logged {level} message for capture {capture_id}: {message}")
        except Exception as e:
            logger.error(f"Failed to log message for capture {capture_id}: {str(e)}")
    
    def get_capture_status(self, capture_id: int) -> Dict:
        """Get the status of a capture."""
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                return {"success": False, "error": f"Capture {capture_id} not found"}
            
            # Check if the capture is active
            is_active = capture_id in self.active_captures
            
            # Get the capture status
            status = {
                "id": db_capture.id,
                "status": db_capture.status,
                "started_at": db_capture.started_at.isoformat() if db_capture.started_at else None,
                "completed_at": db_capture.completed_at.isoformat() if db_capture.completed_at else None,
                "stopped_at": db_capture.stopped_at.isoformat() if db_capture.stopped_at else None,
                "duration": db_capture.duration,
                "error": db_capture.error,
                "output_file": db_capture.output_file,
                "is_active": is_active
            }
            
            return {"success": True, "status": status}
            
        except Exception as e:
            logger.error(f"Failed to get status for capture {capture_id}: {str(e)}")
            return {"success": False, "error": f"Failed to get status: {str(e)}"}
    
    def get_capture_logs(self, capture_id: int) -> Dict:
        """Get the logs for a capture."""
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                return {"success": False, "error": f"Capture {capture_id} not found"}
            
            # Get the logs for the capture
            logs = db.query(CaptureLog).filter(CaptureLog.capture_id == capture_id).order_by(CaptureLog.timestamp.asc()).all()
            
            # Format the logs
            formatted_logs = [{
                "id": log.id,
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat()
            } for log in logs]
            
            return {"success": True, "logs": formatted_logs}
            
        except Exception as e:
            logger.error(f"Failed to get logs for capture {capture_id}: {str(e)}")
            return {"success": False, "error": f"Failed to get logs: {str(e)}"}
    
    def test_stream_url(self, url: str) -> Dict:
        """Test if a stream URL is valid and accessible."""
        try:
            logger.info(f"Testing stream URL: {url}")
            
            # Check if ffprobe is available
            ffprobe_path = shutil.which("ffprobe")
            if not ffprobe_path:
                # Try some common locations
                common_paths = [
                    "/usr/bin/ffprobe",
                    "/usr/local/bin/ffprobe",
                    "/opt/homebrew/bin/ffprobe"
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        ffprobe_path = path
                        logger.info(f"ffprobe found at: {ffprobe_path}")
                        break
                else:
                    return {"success": False, "error": "ffprobe not found"}
            
            # Build the command
            cmd = [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "json", url]
            
            # Run the command with a timeout
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    # Stream is valid
                    logger.info(f"Stream URL is valid: {url}")
                    return {"success": True, "message": "Stream URL is valid"}
                else:
                    # Stream is invalid
                    logger.warning(f"Stream URL is invalid: {result.stderr}")
                    return {"success": False, "error": f"Stream URL is invalid: {result.stderr}"}
            except subprocess.TimeoutExpired:
                logger.warning("Timeout while testing stream URL")
                return {"success": False, "error": "Timeout while testing stream URL"}
            
        except Exception as e:
            logger.error(f"Unexpected error testing stream: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def start_capture(self, url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> Dict:
        """Start capturing a Parliament TV stream."""
        logger.info(f"Starting capture for URL: {url}, capture_id: {capture_id}")
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
            
            # Check if we have separate video and audio URLs
            direct_stream = stream_info.get("direct_stream", {})
            video_url = None
            audio_url = None
            
            if isinstance(direct_stream, dict) and "video_url" in direct_stream:
                video_url = direct_stream.get("video_url")
                audio_url = direct_stream.get("audio_url")
                logger.info(f"Found separate video and audio URLs for capture {capture_id}")
            else:
                video_url = direct_stream if isinstance(direct_stream, str) else None
                logger.info(f"Using single stream URL for capture {capture_id}")
            
            if not video_url:
                error_msg = "No valid video stream URL found"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Create the output directory if it doesn't exist
            os.makedirs(str(self.temp_dir), exist_ok=True)
            
            # Create the video file path - format: capture_XXXX.mp4
            padded_capture_id = str(capture_id).zfill(4)
            output_file = os.path.join(str(self.temp_dir), f"capture_{padded_capture_id}.mp4")
            logger.info(f"Output file path: {output_file}")
            
            # Start the ffmpeg process to capture the video
            cmd = ["ffmpeg", "-y"]
            
            # Add options for better handling of HLS streams
            cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls"])
            cmd.extend(["-allowed_extensions", "ALL"])
            
            # Check if we have a time marker in the scheduled start time
            start_position = None
            if "time_marker" in db_capture.metadata:
                time_marker_seconds = db_capture.metadata.get("time_marker", {}).get("seconds", 0)
                if time_marker_seconds > 0:
                    # If we have a time marker, use it as the start position
                    start_position = time_marker_seconds
                    logger.info(f"Using time marker as start position: {start_position} seconds")
            elif scheduled_start:
                logger.info(f"Using scheduled start time but no time marker found")
            
            # Add input options
            if start_position:
                # Add seek option to start at the specified position
                # For ffmpeg, it's more efficient to put -ss BEFORE -i for seeking
                cmd.extend(["-ss", str(start_position)])
            
            # Add input file with appropriate options
            # Make sure video_url is a string, not a dict
            if isinstance(video_url, dict) and "video_url" in video_url:
                actual_video_url = video_url["video_url"]
                logger.info(f"Extracted video_url from dict: {actual_video_url}")
            else:
                actual_video_url = str(video_url)
                logger.info(f"Using video_url directly: {actual_video_url}")
                
            cmd.extend(["-i", actual_video_url])
            
            # Add additional options for better handling of streams
            cmd.extend(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
            
            # Add HLS-specific options
            cmd.extend(["-hls_allow_cache", "1"])
            cmd.extend(["-http_persistent", "1"])
            
            # Add codec options - use copy mode for speed
            cmd.extend(["-c", "copy"])
            
            # Add duration limit
            # For recorded streams with a time marker, this is the exact duration to capture
            # For live streams, this acts as a safety limit
            cmd.extend(["-t", str(duration)])
            logger.info(f"Setting capture duration to {duration} seconds")
            
            # Add output file
            cmd.append(output_file)
            
            logger.info(f"Running ffmpeg to capture video: {output_file}")
            logger.info(f"ffmpeg command: {' '.join(cmd)}")
            
            # Log the full command for debugging
            logger.info(f"Full ffmpeg command: {' '.join(cmd)}")
            
            # Start the ffmpeg process with better error handling
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                logger.info(f"Started ffmpeg process for capture {capture_id} with PID: {process.pid}")
            except Exception as e:
                error_msg = f"Failed to start ffmpeg process: {str(e)}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Store process information
            self.active_captures[capture_id] = {
                "process": process,
                "start_time": datetime.now(),
                "output_file": output_file,
                "video_url": video_url,
                "audio_url": audio_url,
                "original_url": url
            }
            
            # Update the database
            db_capture.status = "active"
            db_capture.file_path = output_file
            
            # Always store a string in source_url, never a dict or object
            # For Parliament TV URLs, this should be the URL with the time marker (e.g., https://parliamentlive.tv/event/index/c63e4bed-0da2-4d85-a742-e5d247a7aceb?in=12:23:30)
            
            # Convert any dict to a string representation of the original URL
            if isinstance(url, dict):
                # If we have the original URL in stream_info, use that
                if stream_info and "original_url" in stream_info:
                    db_capture.source_url = str(stream_info["original_url"])
                # If we have an event_id, construct a URL
                elif stream_info and "event_id" in stream_info:
                    event_id = stream_info["event_id"]
                    db_capture.source_url = f"https://parliamentlive.tv/event/index/{event_id}"
                else:
                    # Last resort fallback
                    db_capture.source_url = "Parliament TV Stream"
            else:
                # If url is already a string, use it directly
                db_capture.source_url = str(url)
            
            # Store the URLs and scheduling info in metadata
            if not db_capture.metadata:
                db_capture.metadata = {}
            
            if isinstance(db_capture.metadata, dict):
                # Store all three URLs in metadata for reference
                # Make sure we store strings for original_url, not dict objects
                if isinstance(url, dict):
                    if stream_info and "original_url" in stream_info:
                        db_capture.metadata["original_url"] = str(stream_info["original_url"])
                    elif stream_info and "event_id" in stream_info:
                        event_id = stream_info["event_id"]
                        db_capture.metadata["original_url"] = f"https://parliamentlive.tv/event/index/{event_id}"
                    else:
                        db_capture.metadata["original_url"] = "Parliament TV Stream"
                else:
                    db_capture.metadata["original_url"] = str(url)  # The URL entered by the user (with time marker if present)
                
                # Store video and audio URLs as strings
                if isinstance(video_url, dict) and "video_url" in video_url:
                    db_capture.metadata["video_url"] = str(video_url["video_url"])
                else:
                    db_capture.metadata["video_url"] = str(video_url)  # The direct video stream URL
                
                # Store audio URL if available
                if isinstance(audio_url, dict) and "audio_url" in audio_url:
                    db_capture.metadata["audio_url"] = str(audio_url["audio_url"])
                elif audio_url:
                    db_capture.metadata["audio_url"] = str(audio_url)  # The direct audio stream URL (if available)
                
                # Store scheduling information
                if scheduled_start:
                    db_capture.metadata["scheduled_start"] = scheduled_start
                if scheduled_end:
                    db_capture.metadata["scheduled_end"] = scheduled_end
            
            db.commit()
            
            # Log the capture start
            self.log_capture(db, capture_id, "info", f"Started capture for URL: {url}")
            
            return {
                "success": True,
                "message": f"Capture {capture_id} started successfully",
                "output_file": output_file,
                "video_url": video_url,
                "audio_url": audio_url
            }
            
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
            if not url or not isinstance(url, str):
                logger.error(f"Invalid URL provided: {url}")
                return {"error": f"Invalid URL provided: {url}"}
                
            # Check if the URL is already a direct stream URL
            if 'cdn.redbee.live' in url or '.m3u8' in url:
                logger.info("URL appears to be a direct stream URL already")
                
                # Determine if this is a video or audio URL
                is_audio = 'audio' in url.lower() and not 'video' in url.lower()
                
                if is_audio:
                    logger.info("URL appears to be an audio stream")
                    # Try to derive the video URL from the audio URL
                    video_url = url.replace('audio', 'video')
                    return {
                        "direct_stream": {
                            "video_url": video_url,
                            "audio_url": url
                        },
                        "event_id": "direct",
                        "time_marker": {"seconds": 0},
                        "original_url": url
                    }
                else:
                    logger.info("URL appears to be a video stream")
                    # Try to derive the audio URL from the video URL
                    audio_url = None
                    if 'video' in url.lower():
                        audio_url = url.replace('video', 'audio')
                        # Check if we need to add bitrate for audio
                        if '_eng=' not in audio_url and '.m3u8' in audio_url:
                            audio_url = audio_url.replace('.m3u8', '_eng=64000.m3u8')
                    
                    if audio_url:
                        return {
                            "direct_stream": {
                                "video_url": url,
                                "audio_url": audio_url
                            },
                            "event_id": "direct",
                            "time_marker": {"seconds": 0},
                            "original_url": url
                        }
                    else:
                        return {
                            "direct_stream": url,
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
                    logger.info("Successfully extracted stream URL")
                    return stream_info
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON output: {str(e)}")
                    return {"error": f"Failed to parse JSON output: {str(e)}"}
            else:
                logger.error(f"Command failed with return code {result.returncode}: {result.stderr}")
                return {"error": f"Command failed with return code {result.returncode}: {result.stderr}"}
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}


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
