import os
import sys
import json
import time
import logging
import threading
import subprocess
from datetime import datetime
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

    def start_capture(self, url: str, capture_id: int, duration: int = 1800) -> Dict:
        """
        Start capturing a Parliament TV stream with facial recognition.
        
        Args:
            url: The URL of the Parliament TV event
            capture_id: The ID of the capture in the database
            duration: Maximum duration to capture in seconds (default: 30 minutes)
            
        Returns:
            A dictionary with the capture result
        """
        logger.info(f"Starting Parliament TV capture for URL: {url}")
        
        try:
            # Extract the direct stream URL
            stream_info = self.extract_stream_url(url)
            if not stream_info or not stream_info.get("direct_stream"):
                logger.error(f"Failed to extract stream URL from {url}")
                return {"success": False, "error": "Failed to extract stream URL"}
            
            direct_stream = stream_info.get("direct_stream")
            logger.info(f"Extracted direct stream URL: {direct_stream}")
            
            # Test the stream URL
            stream_test = self.test_stream_url(direct_stream)
            if not stream_test.get("success"):
                logger.error(f"Stream URL test failed: {stream_test.get('error')}")
                return {"success": False, "error": f"Stream URL test failed: {stream_test.get('error')}"}
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return {"success": False, "error": f"Capture {capture_id} not found in database"}
            
            # Update the capture with the direct stream URL
            db_capture.stream_url = direct_stream
            db_capture.status = "active"
            db_capture.started_at = datetime.now()
            db.commit()
            
            # Log the start of the capture
            self.log_capture(db, db_capture.id, "info", f"Starting capture for URL: {url}")
            self.log_capture(db, db_capture.id, "info", f"Direct stream URL: {direct_stream}")
            
            # Run the capture process
            result = self.run_capture_process(db_capture, direct_stream)
            
            return {"success": True, "message": "Capture started successfully", "capture_id": capture_id}
            
        except Exception as e:
            print(f"Unexpected error starting capture: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            self.capture_callback(db_capture, None, f"Failed to start capture: {str(e)}")
            return {"success": False, "error": f"Failed to start capture: {str(e)}"}

    def start_capture_async(self, url: str, capture_id: int, duration: int = 1800, callback=None) -> bool:
        """
        Start capturing a Parliament TV stream asynchronously.
        
        Args:
            url: Parliament TV event URL
            capture_id: The ID of the capture in the database
            duration: Maximum duration to capture in seconds (default: 30 minutes)
            callback: Optional callback function to call with the result
            
        Returns:
            bool: True if the capture thread was started successfully, False otherwise
        """
        try:
            logger.info(f"Starting async capture for URL: {url}")
            
            # Extract the direct stream URL
            stream_info = self.extract_stream_url(url)
            if not stream_info or not stream_info.get("direct_stream"):
                logger.error(f"Failed to extract stream URL from {url}")
                return False
            
            direct_stream = stream_info.get("direct_stream")
            logger.info(f"Extracted direct stream URL: {direct_stream}")
            
            # Test the stream URL
            stream_test = self.test_stream_url(direct_stream)
            if not stream_test.get("success"):
                logger.error(f"Stream URL test failed: {stream_test.get('error')}")
                return False
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return False
            
            # Update the capture with the direct stream URL
            db_capture.stream_url = direct_stream
            db_capture.status = "active"
            db_capture.started_at = datetime.now()
            db.commit()
            
            # Log the start of the capture
            self.log_capture(db, db_capture.id, "info", f"Starting async capture for URL: {url}")
            self.log_capture(db, db_capture.id, "info", f"Direct stream URL: {direct_stream}")
            
            # Start the capture thread
            return self.start_capture_thread(db_capture, stream_info)
            
        except Exception as e:
            print(f"Unexpected error starting async capture: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            return False

    def start_capture_thread(self, db_capture, stream_info):
        """Start a thread to capture the Parliament TV stream."""
        try:
            print(f"Starting capture thread for {db_capture.id}")
            print(f"DEBUG - db_capture type: {type(db_capture)}, id: {db_capture.id}")
            print(f"DEBUG - stream_info type: {type(stream_info)}, content: {stream_info}")
            
            # CRITICAL FIX: Hard-code paths to ensure they're never None
            print("DEBUG - Setting hard-coded paths in start_capture_thread to ensure they're never None")
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media")
            self.scripts_dir = Path("/app/scripts")
            
            # Create directories if they don't exist
            print(f"DEBUG - Creating directories in start_capture_thread")
            try:
                os.makedirs(str(self.temp_dir), exist_ok=True)
                print(f"DEBUG - Created temp_dir: {self.temp_dir}")
            except Exception as e:
                print(f"ERROR - Failed to create temp_dir: {str(e)}")
                
            try:
                os.makedirs(str(self.media_dir), exist_ok=True)
                print(f"DEBUG - Created media_dir: {self.media_dir}")
            except Exception as e:
                print(f"ERROR - Failed to create media_dir: {str(e)}")
            
            capture_id = db_capture.id
            direct_stream = stream_info.get("direct_stream")
            print(f"DEBUG - direct_stream: {direct_stream}")
            
            # Validate inputs
            if not direct_stream:
                print(f"Error: No direct stream URL found for capture {capture_id}")
                return False
            
            # Ensure directories are valid
            if self.temp_dir is None:
                print(f"Warning: temp_dir is None, using default /tmp")
                self.temp_dir = Path("/tmp")
                os.makedirs(str(self.temp_dir), exist_ok=True)
                
            if self.media_dir is None:
                print(f"Warning: media_dir is None, using default /tmp")
                self.media_dir = Path("/tmp")
                os.makedirs(str(self.media_dir), exist_ok=True)
                
            if self.scripts_dir is None:
                print(f"Warning: scripts_dir is None, using default /app/scripts")
                self.scripts_dir = Path("/app/scripts")
                
            # Validate directories after ensuring they exist
            if not os.path.exists(str(self.temp_dir)) or not os.path.exists(str(self.media_dir)):
                print(f"Error: Directories do not exist for capture {capture_id} even after creation attempt")
                print(f"temp_dir: {self.temp_dir}, media_dir: {self.media_dir}, scripts_dir: {self.scripts_dir}")
                return False
            
            # Debug directory paths before thread creation
            print(f"DEBUG - Before thread creation - temp_dir: {self.temp_dir}, exists: {os.path.exists(str(self.temp_dir)) if self.temp_dir else False}")
            print(f"DEBUG - Before thread creation - media_dir: {self.media_dir}, exists: {os.path.exists(str(self.media_dir)) if self.media_dir else False}")
            print(f"DEBUG - Before thread creation - scripts_dir: {self.scripts_dir}, exists: {os.path.exists(str(self.scripts_dir)) if self.scripts_dir else False}")
            
            # Check if script exists
            script_path = os.path.join(str(self.scripts_dir), "parliament_capture_direct.py")
            print(f"DEBUG - Script path: {script_path}, exists: {os.path.exists(script_path)}")
            
            # Create a thread to run the capture process
            print(f"DEBUG - Creating capture thread with args: db_capture.id={db_capture.id}, direct_stream={direct_stream}")
            capture_thread = threading.Thread(
                target=self.run_capture_process,
                args=(db_capture, direct_stream),
                daemon=True
            )
            
            # Store the thread in the active_captures dictionary
            self.active_captures[capture_id] = {
                "thread": capture_thread,
                "start_time": datetime.now(),
                "stream_url": direct_stream
            }
            
            # Start the thread
            capture_thread.start()
            
            print(f"Capture thread started for {capture_id}")
            return True
        except Exception as e:
            print(f"Unexpected error starting capture thread: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            return False

    def run_capture_process(self, db_capture, direct_stream):
        """Run the capture process and update the database."""
        try:
            print(f"DEBUG - run_capture_process started with db_capture.id={db_capture.id}, direct_stream={direct_stream}")
            
            # CRITICAL FIX: Hard-code paths to ensure they're never None
            print("DEBUG - Setting hard-coded paths to ensure they're never None")
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media")
            self.scripts_dir = Path("/app/scripts")
            
            # Create directories if they don't exist
            print(f"DEBUG - run_capture_process - Creating temp_dir: {temp_dir_str}")
            os.makedirs(temp_dir_str, exist_ok=True)
            
            print(f"DEBUG - run_capture_process - Creating media_dir: {media_dir_str}")
            os.makedirs(media_dir_str, exist_ok=True)
            
            # Verify directories exist after creation
            if not os.path.exists(temp_dir_str):
                print(f"ERROR - run_capture_process - Failed to create temp_dir: {temp_dir_str}")
                self.capture_callback(db_capture, None, f"Failed to create temp directory: {temp_dir_str}")
                return
            
            if not os.path.exists(media_dir_str):
                print(f"ERROR - run_capture_process - Failed to create media_dir: {media_dir_str}")
                self.capture_callback(db_capture, None, f"Failed to create media directory: {media_dir_str}")
                return
            
            print(f"DEBUG - run_capture_process - Directories created successfully")
            print(f"DEBUG - run_capture_process - temp_dir: {temp_dir_str}, exists: {os.path.exists(temp_dir_str)}")
            print(f"DEBUG - run_capture_process - media_dir: {media_dir_str}, exists: {os.path.exists(media_dir_str)}")
            
            # Build the command
        """
        logger.info(f"Stopping capture {capture_id}")
        
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return {"success": False, "error": f"Capture {capture_id} not found in database"}
            
            # Check if the capture is active
            if db_capture.status != "active":
                logger.warning(f"Capture {capture_id} is not active (status: {db_capture.status})")
                return {"success": True, "message": f"Capture {capture_id} is already stopped"}
            
            # Stop the capture thread if it exists
            if capture_id in self.active_captures:
                # The thread will clean up itself when it exits
                logger.info(f"Stopping capture thread for {capture_id}")
                # We can't force stop a thread in Python, but we can mark the capture as stopped
                # and the thread will exit when it checks the status
                db_capture.status = "stopped"
                db.commit()
                
                # Log the stop
                self.log_capture(db, capture_id, "info", "Capture stopped by user")
                
                # Wait for the thread to exit (it should check the status and exit)
                # We'll give it a few seconds to exit gracefully
                for _ in range(5):
                    if capture_id not in self.active_captures:
                        break
                    time.sleep(1)
                
                # If the thread is still running, we'll remove it from the active_captures dictionary
                if capture_id in self.active_captures:
                    del self.active_captures[capture_id]
                
                logger.info(f"Capture {capture_id} stopped")
                return {"success": True, "message": f"Capture {capture_id} stopped"}
            else:
                # The capture is active in the database but not in our active_captures dictionary
                # This could happen if the server was restarted while a capture was running
                logger.warning(f"Capture {capture_id} is active in the database but not in active_captures")
                
                # Update the capture status in the database
                db_capture.status = "stopped"
                db.commit()
                
                # Log the stop
                self.log_capture(db, capture_id, "info", "Capture stopped (not in active_captures)")
                
                logger.info(f"Capture {capture_id} marked as stopped in the database")
                return {"success": True, "message": f"Capture {capture_id} marked as stopped in the database"}
                
        except Exception as e:
            print(f"Unexpected error stopping capture: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Error stopping capture: {str(e)}"}

    def get_active_captures(self) -> List[Dict]:
        """
        Get a list of active captures.
        
        Returns:
            A list of dictionaries with information about active captures
        """
        try:
            # Get a database session
            db = next(get_db())
            
            # Get all active captures from the database
            db_captures = db.query(Capture).filter(Capture.status == "active").all()
            
            # Convert to a list of dictionaries
            captures = []
            for db_capture in db_captures:
                capture_info = {
                    "id": db_capture.id,
                    "url": db_capture.url,
                    "stream_url": db_capture.stream_url,
                    "status": db_capture.status,
                    "started_at": db_capture.started_at.isoformat() if db_capture.started_at else None,
                    "duration": db_capture.duration,
                    "active_thread": db_capture.id in self.active_captures
                }
                captures.append(capture_info)
            
            return captures
            
        except Exception as e:
            print(f"Unexpected error getting active captures: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            return []

    def extract_stream_url(self, url: str) -> Dict:
        """
        Extract the direct stream URL from a Parliament TV event URL.
        
        Args:
            url: The URL of the Parliament TV event
            
        Returns:
            A dictionary with the direct stream URL and other information
        """
        logger.info(f"Extracting stream URL from {url}")
        print(f"DEBUG - extract_stream_url - URL: {url}")
        
        try:
            # Validate URL
            if url is None:
                logger.error("URL is None in extract_stream_url")
                print("ERROR - extract_stream_url - URL is None")
                return {}
                
            if not isinstance(url, str):
                logger.error(f"URL is not a string in extract_stream_url: {type(url)}")
                print(f"ERROR - extract_stream_url - URL is not a string: {type(url)}")
                return {}
                
            # Check if the URL is already a direct stream URL
            if url.endswith('.m3u8'):
                stream_info = {"direct_stream": url}
                logger.info(f"URL is already a direct stream: {url}")
                print(f"DEBUG - extract_stream_url - URL is already a direct stream: {url}")
                return stream_info
            
            # Verify scripts_dir exists
            if self.scripts_dir is None:
                logger.error("scripts_dir is None in extract_stream_url")
                print("ERROR - extract_stream_url - scripts_dir is None")
                # Set a default scripts directory
                self.scripts_dir = "/app/scripts"
                logger.info(f"Set default scripts_dir to {self.scripts_dir}")
                print(f"DEBUG - extract_stream_url - Set default scripts_dir to {self.scripts_dir}")
            
            # Check if extract-url.py exists
            script_path = os.path.join(str(self.scripts_dir), "extract-url.py")
            if not os.path.exists(script_path):
                logger.error(f"extract-url.py not found at {script_path}")
                print(f"ERROR - extract_stream_url - extract-url.py not found at {script_path}")
                # Try to find the script in other locations
                alternative_paths = [
                    "/app/backend/scripts/extract-url.py",
                    "/app/scripts/extract-url.py"
                ]
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        logger.info(f"Found extract-url.py at alternative location: {script_path}")
                        print(f"DEBUG - extract_stream_url - Found extract-url.py at alternative location: {script_path}")
                        break
                else:
                    logger.error("extract-url.py not found in any location")
                    print("ERROR - extract_stream_url - extract-url.py not found in any location")
                    return {}
            
            # Use the extract-url.py script to extract the direct stream URL
            cmd = [
                sys.executable,
                script_path,
                url
            ]
            
            logger.info(f"Running extract-url command: {' '.join(cmd)}")
            print(f"DEBUG - extract_stream_url - Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to get the direct stream URL
                try:
                    if not result.stdout:
                        logger.error("extract-url.py returned empty output")
                        print("ERROR - extract_stream_url - extract-url.py returned empty output")
                        return {}
                        
                    stream_info = json.loads(result.stdout)
                    
                    # Validate stream_info
                    if not stream_info:
                        logger.error("extract-url.py returned empty JSON")
                        print("ERROR - extract_stream_url - extract-url.py returned empty JSON")
                        return {}
                        
                    if "direct_stream" not in stream_info:
                        logger.error(f"direct_stream not found in extract-url.py output: {stream_info}")
                        print(f"ERROR - extract_stream_url - direct_stream not found in extract-url.py output: {stream_info}")
                        return {}
                        
                    logger.info(f"Extracted stream info: {stream_info}")
                    print(f"DEBUG - extract_stream_url - Extracted stream info: {stream_info}")
                    return stream_info
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse extract-url output as JSON: {result.stdout}")
                    print(f"ERROR - extract_stream_url - Failed to parse extract-url output as JSON: {result.stdout}")
                    return {}
            else:
                logger.error(f"extract-url command failed with return code {result.returncode}")
                logger.error(f"Command output: {result.stdout}")
                logger.error(f"Command error: {result.stderr}")
                print(f"ERROR - extract_stream_url - extract-url command failed with return code {result.returncode}")
                print(f"ERROR - extract_stream_url - Command output: {result.stdout}")
                print(f"ERROR - extract_stream_url - Command error: {result.stderr}")
                return {}
                
        except Exception as e:
            print(f"Unexpected error extracting stream URL: {str(e)}")
            import traceback
            print(f"ERROR - extract_stream_url - Traceback: {traceback.format_exc()}")
            return {}

    def test_stream_url(self, url: str) -> Dict:
        """
        Test if a stream URL is valid and accessible.
        
        Args:
            url: The URL of the stream to test
            
        Returns:
            A dictionary with the test result
        """
        logger.info(f"Testing stream URL: {url}")
        
        try:
            # Make a HEAD request to the URL
            response = requests.head(url, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Stream URL test successful: {url}")
                return {"success": True, "message": "Stream URL is valid and accessible"}
            else:
                logger.warning(f"Stream URL test failed with status code {response.status_code}: {url}")
                return {"success": False, "error": f"Stream URL returned status code {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Stream URL test failed with exception: {str(e)}")
            return {"success": False, "error": f"Error testing stream URL: {str(e)}"}

    def log_capture(self, db: Session, capture_id: int, level: str, message: str) -> None:
        """
        Log a message for a capture.
        
        Args:
            db: Database session
            capture_id: The ID of the capture
            level: Log level (info, warning, error)
            message: Log message
        """
        try:
            # Create a new log entry
            log = CaptureLog(
                capture_id=capture_id,
                level=level,
                message=message,
                timestamp=datetime.now()
            )
            
            # Add to the database
            db.add(log)
            db.commit()
            
        except Exception as e:
            print(f"Unexpected error logging capture message: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")

    def capture_callback(self, db_capture, file_path, error_message=None):
        """Callback function for when a capture is complete."""
        try:
            print(f"DEBUG - capture_callback called with db_capture.id={db_capture.id}, file_path={file_path}, error_message={error_message}")
            
            # Get a new session
            db = next(get_db())
            
            # Get the capture session
            capture_id = db_capture.id
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            
            if not db_capture:
                print(f"Error: Capture session {capture_id} not found")
                return
            
            # Update the capture session
            if error_message:
                db_capture.status = "error"
                db_capture.error_message = error_message
                print(f"Error capturing stream: {error_message}")
                
                # Create a log entry for the error
                log_entry = CaptureLog(
                    capture_id=capture_id,
                    message=f"Error: {error_message}",
                    level="ERROR"
                )
                db.add(log_entry)
            else:
                db_capture.status = "completed"
                db_capture.file_path = file_path
                print(f"Capture completed: {file_path}")
                
                # Create a log entry for the completion
                log_entry = CaptureLog(
                    capture_id=capture_id,
                    message=f"Capture completed: {file_path}",
                    level="INFO"
                )
                db.add(log_entry)
            
            # Remove the capture from the active_captures dictionary
            if capture_id in self.active_captures:
                del self.active_captures[capture_id]
            
            # Commit the changes
            db.commit()
            
        except Exception as e:
            print(f"Unexpected error in capture callback: {str(e)}")
            import traceback
            print(f"ERROR - Callback traceback: {traceback.format_exc()}")
            import traceback
            print(traceback.format_exc())

# Create a singleton instance
parliament_tv_capture = ParliamentTVCapture()

# For backwards compatibility
def start_capture(url: str, capture_id: int, duration: int = 1800) -> Dict:
    return parliament_tv_capture.start_capture(url, capture_id, duration)

def start_capture_async(url: str, capture_id: int, duration: int = 1800, callback=None) -> bool:
    return parliament_tv_capture.start_capture_async(url, capture_id, duration, callback)

def stop_capture(capture_id: int) -> Dict:
    return parliament_tv_capture.stop_capture(capture_id)

def get_active_captures() -> List[Dict]:
    return parliament_tv_capture.get_active_captures()

def extract_stream_url(url: str) -> Dict:
    return parliament_tv_capture.extract_stream_url(url)

def test_stream_url(url: str) -> Dict:
    return parliament_tv_capture.test_stream_url(url)
