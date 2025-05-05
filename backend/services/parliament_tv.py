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
        # CRITICAL FIX: Hard-code paths to ensure they're never None
        print("DEBUG - Setting hard-coded paths in __init__ to ensure they're never None")
        self.temp_dir = Path("/app/data/temp")
        self.media_dir = Path("/app/data/media")
        self.scripts_dir = Path("/app/scripts")
        
        # Print debug info about paths
        print(f"Temp dir: {self.temp_dir}")
        print(f"Media dir: {self.media_dir}")
        print(f"Scripts dir: {self.scripts_dir}")
        
        # Create directories if they don't exist
        try:
            os.makedirs(str(self.temp_dir), exist_ok=True)
            print(f"Created temp_dir: {self.temp_dir}")
        except Exception as e:
            print(f"ERROR - Failed to create temp_dir: {str(e)}")
            
        try:
            os.makedirs(str(self.media_dir), exist_ok=True)
            print(f"Created media_dir: {self.media_dir}")
        except Exception as e:
            print(f"ERROR - Failed to create media_dir: {str(e)}")
        
        # Initialize active captures dictionary
        self.active_captures = {}

    def stop_capture(self, capture_id: int) -> Dict:
        """Stop a running capture."""
        print("*"*80)
        print(f"AUDIO EXTRACTION FIX - STOP_CAPTURE CALLED FOR CAPTURE {capture_id}")
        print("*"*80)
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
            print(f"DEBUG - stop_capture - Attempting to terminate capture process for {capture_id}")
            
            # Get the thread from active_captures
            capture_info = self.active_captures.get(capture_id, {})
            capture_thread = capture_info.get("thread")
            
            # Find and terminate any running ffmpeg processes for this capture
            try:
                # Use ps to find ffmpeg processes containing the capture ID
                ps_cmd = ["ps", "-ef"]
                ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
                
                # Look for ffmpeg processes with this capture ID
                # Format the capture ID with leading zeros (e.g., 0096)
                padded_capture_id = str(capture_id).zfill(4)
                for line in ps_result.stdout.splitlines():
                    if f"capture_{padded_capture_id}" in line and "ffmpeg" in line:
                        print(f"DEBUG - stop_capture - Found ffmpeg process for capture {capture_id}: {line}")
                        # Extract PID (second column in ps output)
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                print(f"DEBUG - stop_capture - Terminating process with PID {pid}")
                                # Try to terminate gracefully first
                                os.kill(pid, signal.SIGTERM)
                                # Give it a moment to terminate
                                time.sleep(1)
                                # Check if it's still running
                                try:
                                    os.kill(pid, 0)  # This will raise an error if process doesn't exist
                                    print(f"DEBUG - stop_capture - Process {pid} still running, sending SIGKILL")
                                    # If still running, force kill
                                    os.kill(pid, signal.SIGKILL)
                                except OSError:
                                    print(f"DEBUG - stop_capture - Process {pid} terminated successfully")
                            except ValueError:
                                print(f"DEBUG - stop_capture - Could not parse PID from: {parts[1]}")
                            except OSError as e:
                                print(f"DEBUG - stop_capture - Error killing process {pid}: {str(e)}")
            except Exception as proc_err:
                print(f"DEBUG - stop_capture - Error finding/killing ffmpeg processes: {str(proc_err)}")
            
            # Update the capture status
            db_capture.status = "stopped"
            db_capture.stopped_at = datetime.now()
            db.commit()
            
            # Log the stop
            self.log_capture(db, capture_id, "info", "Capture stopped by user")
            
            # Get the output file path from the database
            output_file = db_capture.file_path
            print(f"DEBUG - stop_capture - Output file path: {output_file}")
            
            # Check if the output file exists
            if os.path.exists(output_file):
                print(f"DEBUG - stop_capture - Output file exists: {output_file}")
                
                # Call capture_callback to extract audio
                print(f"DEBUG - stop_capture - Calling capture_callback to extract audio")
                self.capture_callback(db_capture, output_file)
                print(f"DEBUG - stop_capture - Audio extraction completed")
            else:
                print(f"ERROR - stop_capture - Output file does not exist: {output_file}")
                self.log_capture(db, capture_id, "error", f"Output file does not exist: {output_file}")
            
            # Remove from active_captures
            del self.active_captures[capture_id]
            
            return {"success": True, "message": f"Capture {capture_id} stopped successfully"}
            
        except Exception as e:
            logger.error(f"Failed to stop capture {capture_id}: {str(e)}")
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
            print(f"DEBUG - test_stream_url - Testing stream URL: {url}")
            
            # Check if ffprobe is installed
            try:
                result = subprocess.run(["which", "ffprobe"], capture_output=True, text=True)
                if result.returncode != 0:
                    print("ERROR - test_stream_url - ffprobe not found")
                    return {"success": False, "error": "ffprobe not found"}
                ffprobe_path = result.stdout.strip()
                print(f"DEBUG - test_stream_url - ffprobe found at: {ffprobe_path}")
            except Exception as e:
                print(f"ERROR - test_stream_url - Failed to check for ffprobe: {str(e)}")
                return {"success": False, "error": f"Failed to check for ffprobe: {str(e)}"}
            
            # Build the ffprobe command
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", url]
            print(f"DEBUG - test_stream_url - ffprobe command: {' '.join(cmd)}")
            
            # Run the command with a timeout
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                print(f"DEBUG - test_stream_url - ffprobe returned with code: {result.returncode}")
                
                # Check if the command was successful
                if result.returncode == 0:
                    print(f"DEBUG - test_stream_url - Stream URL is valid: {url}")
                    return {"success": True, "message": "Stream URL is valid"}
                else:
                    print(f"ERROR - test_stream_url - ffprobe failed with return code {result.returncode}")
                    print(f"ERROR - test_stream_url - ffprobe output: {result.stdout}")
                    print(f"ERROR - test_stream_url - ffprobe error: {result.stderr}")
                    return {"success": False, "error": f"Stream URL is invalid: {result.stderr}"}
            except subprocess.TimeoutExpired:
                print("ERROR - test_stream_url - ffprobe timed out")
                return {"success": False, "error": "Timeout while testing stream URL"}
                
        except Exception as e:
            print(f"ERROR - test_stream_url - Unexpected error: {str(e)}")
            import traceback
            print(f"ERROR - test_stream_url - Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def extract_stream_url(self, url: str) -> Dict:
        """Extract the direct stream URL from a Parliament TV event URL."""
        try:
            print(f"DEBUG - extract_stream_url - Extracting stream URL from: {url}")
            
            # Check if the URL is already a direct stream URL
            if url and ('cdn.redbee.live' in url or '.m3u8' in url):
                print(f"DEBUG - extract_stream_url - URL appears to be a direct stream URL already: {url}")
                return {
                    "direct_stream": url,
                    "event_id": "direct",
                    "time_marker": {"seconds": 0},
                    "original_url": url
                }
            
            # CRITICAL FIX: Hard-code script path to ensure it's never None
            script_path = "/app/scripts/extract-url.py"
            print(f"DEBUG - extract_stream_url - script_path: {script_path}")
            
            # Verify the script exists
            if not os.path.exists(script_path):
                print(f"ERROR - extract_stream_url - Script not found at {script_path}, checking alternatives")
                # Try alternative locations
                alt_paths = [
                    "/app/backend/scripts/extract-url.py",
                    "/app/scripts/extract-url.py",
                    "/Users/joebradley/Veedoo/Development/the-mp/scripts/extract-url.py"
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        print(f"DEBUG - extract_stream_url - Found script at: {script_path}")
                        break
                else:
                    print("ERROR - extract_stream_url - Could not find extract-url.py in any location")
                    return {"error": "Could not find extract-url.py script"}
            
            # Check if Python executable is valid
            python_executable = sys.executable
            if not os.path.exists(python_executable):
                print(f"ERROR - extract_stream_url - Python executable not found: {python_executable}")
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
                        print(f"DEBUG - extract_stream_url - Found Python at: {python_executable}")
                        break
                else:
                    print("ERROR - extract_stream_url - Could not find Python executable")
                    return {"error": "Could not find Python executable"}
            
            # Build the command
            cmd = [python_executable, script_path, url]
            print(f"DEBUG - extract_stream_url - Command: {' '.join(cmd)}")
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"DEBUG - extract_stream_url - Command returned with code: {result.returncode}")
            
            # Check if the command was successful
            if result.returncode == 0:
                print(f"DEBUG - extract_stream_url - Command output: {result.stdout}")
                try:
                    # Parse the JSON output
                    stream_info = json.loads(result.stdout)
                    print(f"DEBUG - extract_stream_url - Parsed stream info: {stream_info}")
                    return stream_info
                except json.JSONDecodeError as e:
                    print(f"ERROR - extract_stream_url - Failed to parse JSON output: {str(e)}")
                    return {"error": f"Failed to parse JSON output: {str(e)}"}
            else:
                print(f"ERROR - extract_stream_url - Command failed with return code {result.returncode}")
                print(f"ERROR - extract_stream_url - Command output: {result.stdout}")
                print(f"ERROR - extract_stream_url - Command error: {result.stderr}")
                return {"error": f"Command failed with return code {result.returncode}: {result.stderr}"}
                
        except Exception as e:
            print(f"ERROR - extract_stream_url - Unexpected error: {str(e)}")
            import traceback
            print(f"ERROR - extract_stream_url - Traceback: {traceback.format_exc()}")
            return {"error": f"Unexpected error: {str(e)}"}


# Initialize the Parliament TV capture service
parliament_tv_capture = ParliamentTVCapture()


# Module-level functions for API endpoints
def start_capture(url: str, capture_id: int, duration: int = 1800) -> Dict:
    """Start capturing a Parliament TV stream."""
    return parliament_tv_capture.start_capture(url, capture_id, duration)


def start_capture_async(url: str, capture_id: int, duration: int = 1800) -> bool:
    """Start capturing a Parliament TV stream asynchronously."""
    return parliament_tv_capture.start_capture_async(url, capture_id, duration)


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
