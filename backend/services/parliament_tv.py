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
        # Set up paths
        self.data_dir = os.environ.get("DATA_DIR", "/app/data")
        self.temp_storage_path = os.environ.get("TEMP_STORAGE_PATH", "/app/data/temp")
        self.media_storage_path = os.environ.get("MEDIA_STORAGE_PATH", "/app/data/media")
        
        # Convert to Path objects for easier manipulation
        self.temp_dir = Path(self.temp_storage_path) if self.temp_storage_path else None
        self.media_dir = Path(self.media_storage_path) if self.media_storage_path else None
        self.scripts_dir = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        
        # Debug paths
        print(f"Temp dir: {self.temp_dir}")
        print(f"Media dir: {self.media_dir}")
        print(f"Scripts dir: {self.scripts_dir}")
        
        # Initialize active captures dictionary
        self.active_captures = {}
        
        # Create directories
        if self.temp_dir:
            os.makedirs(str(self.temp_dir), exist_ok=True)
        if self.media_dir:
            os.makedirs(str(self.media_dir), exist_ok=True)

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
            logger.exception(f"Error starting capture: {str(e)}")
            return {"success": False, "error": f"Error starting capture: {str(e)}"}

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
            logger.exception(f"Error starting async capture: {str(e)}")
            return False

    def start_capture_thread(self, db_capture, stream_info):
        """Start a thread to capture the Parliament TV stream."""
        try:
            print(f"Starting capture thread for {db_capture.id}")
            capture_id = db_capture.id
            direct_stream = stream_info.get("direct_stream")
            
            # Validate inputs
            if not direct_stream:
                print(f"Error: No direct stream URL found for capture {capture_id}")
                return False
            
            if not self.temp_dir or not self.media_dir or not self.scripts_dir:
                print(f"Error: Invalid directories for capture {capture_id}")
                print(f"temp_dir: {self.temp_dir}, media_dir: {self.media_dir}, scripts_dir: {self.scripts_dir}")
                return False
            
            # Create a thread to run the capture process
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
            print(f"Error starting capture thread: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    def run_capture_process(self, db_capture, direct_stream):
        """Run the capture process and update the database."""
        try:
            capture_id = db_capture.id
            duration = db_capture.duration or 1800  # Default to 30 minutes
            
            # Ensure paths are valid before using them
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
                
            # Run the improved capture script
            cmd = [
                sys.executable,
                os.path.join(str(self.scripts_dir), "parliament_capture_direct.py"),
                direct_stream,
                "--capture-id", str(capture_id),
                "--duration", str(duration),
                "--temp-dir", str(self.temp_dir),
                "--media-dir", str(self.media_dir)
            ]
            
            print(f"Running capture command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the capture was successful
            if result.returncode == 0:
                # Parse the output to get the output file path
                output_file = None
                for line in result.stdout.splitlines():
                    if line.startswith("Output file:"):
                        output_file = line.replace("Output file:", "").strip()
                        break
                
                if output_file and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    print(f"Capture successful, output file: {output_file}")
                    self.capture_callback(db_capture, output_file)
                else:
                    print(f"Capture failed, output file not found or empty: {output_file}")
                    print(f"Command output: {result.stdout}")
                    self.capture_callback(db_capture, None, "Output file not found or empty")
            else:
                # Capture failed
                print(f"Capture failed with return code {result.returncode}")
                print(f"Command output: {result.stdout}")
                print(f"Command error: {result.stderr}")
                self.capture_callback(db_capture, None, f"Capture failed: {result.stderr}")
        except Exception as e:
            print(f"Error in capture process: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self.capture_callback(db_capture, None, f"Exception in capture process: {str(e)}")
        finally:
            # Remove from active_captures
            if capture_id in self.active_captures:
                del self.active_captures[capture_id]

    def stop_capture(self, capture_id: int) -> Dict:
        """
        Stop a running capture.
        
        Args:
            capture_id: The ID of the capture to stop
            
        Returns:
            A dictionary with the result
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
            logger.exception(f"Error stopping capture {capture_id}: {str(e)}")
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
            logger.exception(f"Error getting active captures: {str(e)}")
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
        
        try:
            # Check if the URL is already a direct stream URL
            if url.endswith('.m3u8'):
                stream_info = {"direct_stream": url}
                return stream_info
            
            # Use the extract-url.py script to extract the direct stream URL
            cmd = [
                sys.executable,
                os.path.join(str(self.scripts_dir), "extract-url.py"),
                url
            ]
            
            logger.info(f"Running extract-url command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to get the direct stream URL
                try:
                    stream_info = json.loads(result.stdout)
                    logger.info(f"Extracted stream info: {stream_info}")
                    return stream_info
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse extract-url output as JSON: {result.stdout}")
                    return {}
            else:
                logger.error(f"extract-url command failed with return code {result.returncode}")
                logger.error(f"Command output: {result.stdout}")
                logger.error(f"Command error: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.exception(f"Error extracting stream URL: {str(e)}")
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
            logger.exception(f"Error logging capture message: {str(e)}")

    def capture_callback(self, db_capture, output_file, error=None):
        """
        Callback function called when a capture is complete.
        
        Args:
            db_capture: The capture database object
            output_file: Path to the output file, or None if the capture failed
            error: Error message if the capture failed
        """
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            capture_id = db_capture.id
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            
            if not db_capture:
                print(f"Error: Capture {capture_id} not found in database")
                return
            
            if error:
                # Capture failed
                db_capture.status = "failed"
                db_capture.error_message = error
                self.log_capture(db, capture_id, "error", error)
            else:
                # Capture succeeded
                db_capture.status = "completed"
                db_capture.output_file = output_file
                self.log_capture(db, capture_id, "info", f"Capture completed successfully, output file: {output_file}")
            
            # Update the capture in the database
            db_capture.completed_at = datetime.now()
            db.commit()
            
        except Exception as e:
            print(f"Error in capture_callback: {str(e)}")
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
