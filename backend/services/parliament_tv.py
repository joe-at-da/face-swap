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
        
        logger.info(f"Initialized with paths: temp={self.temp_dir}, media={self.media_dir}, scripts={self.scripts_dir}")
        
        # Create directories if they don't exist
        try:
            os.makedirs(str(self.temp_dir), exist_ok=True)
            os.makedirs(str(self.media_dir), exist_ok=True)
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
                
                # Define paths
                audio_extracts_dir = "/app/data/temp/audio_extracts"
                os.makedirs(audio_extracts_dir, exist_ok=True)
                
                # Create the audio file path - format: capture_XXXX.audio.mp3
                padded_capture_id = str(capture_id).zfill(4)
                audio_file_path = os.path.join(audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
                
                try:
                    # Get the original URL from the capture metadata
                    original_url = None
                    if hasattr(db_capture, 'metadata') and db_capture.metadata:
                        if isinstance(db_capture.metadata, dict) and 'original_url' in db_capture.metadata:
                            original_url = db_capture.metadata['original_url']
                    
                    # If original_url is not in metadata, use source_url
                    if not original_url and hasattr(db_capture, 'source_url') and db_capture.source_url:
                        original_url = db_capture.source_url
                    
                    # If we have an original URL, extract the audio URL
                    if original_url:
                        # Extract the stream URLs from the original URL
                        logger.info(f"Extracting stream URLs from original URL: {original_url}")
                        stream_info = self.extract_stream_url(original_url)
                        
                        # Check if we have separate audio URL
                        audio_url = None
                        if "direct_stream" in stream_info:
                            direct_stream = stream_info["direct_stream"]
                            if isinstance(direct_stream, dict) and "audio_url" in direct_stream:
                                audio_url = direct_stream["audio_url"]
                        
                        # If we have an audio URL, download it
                        if audio_url:
                            # Use ffmpeg to download the audio
                            cmd = ["ffmpeg", "-y", "-i", audio_url, "-c:a", "copy", audio_file_path]
            
                            # Log the command
                            logger.info(f"Audio download command: {' '.join(cmd)}")
                            
                            logger.info(f"Running ffmpeg to download audio: {audio_file_path}")
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                logger.info(f"Successfully downloaded audio to: {audio_file_path}")
                                
                                # Save the audio file path to the database
                                try:
                                    # Update the metadata
                                    if not db_capture.metadata:
                                        db_capture.metadata = {}
                                    
                                    if isinstance(db_capture.metadata, dict):
                                        db_capture.metadata["audio_file_path"] = audio_file_path
                                        
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
            
            # Add input options
            cmd.extend(["-i", video_url])
            
            # Add codec options
            cmd.extend(["-c", "copy"])
            
            # Add duration limit (as a safety measure)
            cmd.extend(["-t", str(duration)])
            
            # Add output file
            cmd.append(output_file)
            
            logger.info(f"Running ffmpeg to capture video: {output_file}")
            logger.info(f"ffmpeg command: {' '.join(cmd)}")
            
            # Start the ffmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
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
            db_capture.source_url = url
            
            # Store the URLs and scheduling info in metadata
            if not db_capture.metadata:
                db_capture.metadata = {}
            
            if isinstance(db_capture.metadata, dict):
                db_capture.metadata["video_url"] = video_url
                if audio_url:
                    db_capture.metadata["audio_url"] = audio_url
                db_capture.metadata["original_url"] = url
                
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
            
            # Check if the URL is already a direct stream URL
            if url and ('cdn.redbee.live' in url or '.m3u8' in url):
                logger.info("URL appears to be a direct stream URL already")
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
