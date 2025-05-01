import os
import sys
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from backend.core.config import settings

logger = logging.getLogger(__name__)

class ParliamentTVCapture:
    def __init__(self, temp_dir=None, media_dir=None, scripts_dir=None):
        """
        Initialize the Parliament TV capture service.
        
        Args:
            temp_dir: Directory to store temporary files
            media_dir: Directory to store media files
            scripts_dir: Directory containing the capture scripts
        """
        try:
            # Initialize path variables with fallbacks to ensure they're never None
            # First try the provided parameters, then environment variables, then default paths
            if temp_dir:
                self.temp_dir = Path(temp_dir)
            elif os.environ.get("TEMP_STORAGE_PATH"):
                self.temp_dir = Path(os.environ.get("TEMP_STORAGE_PATH"))
            else:
                self.temp_dir = Path("/tmp")
            
            if media_dir:
                self.media_dir = Path(media_dir)
            elif os.environ.get("MEDIA_STORAGE_PATH"):
                self.media_dir = Path(os.environ.get("MEDIA_STORAGE_PATH"))
            else:
                self.media_dir = Path("/media")
            
            # For scripts_dir, try multiple approaches to find a valid path
            if scripts_dir:
                self.scripts_dir = Path(scripts_dir)
            elif os.environ.get("DATA_DIR"):
                self.scripts_dir = Path(os.environ.get("DATA_DIR")) / "scripts"
            else:
                # Try several common locations
                potential_paths = [
                    Path("/app/scripts"),
                    Path(os.getcwd()) / "scripts",
                    Path(os.getcwd()).parent / "scripts",
                    Path("/scripts")
                ]
                
                for path in potential_paths:
                    if path.exists():
                        self.scripts_dir = path
                        break
                else:
                    # If none of the paths exist, use a default but create the directory
                    self.scripts_dir = Path("/app/scripts")
                    os.makedirs(str(self.scripts_dir), exist_ok=True)
            
            # Log the initialized paths
            logger.info(f"Initialized ParliamentTVCapture with paths:")
            logger.info(f"  temp_dir: {self.temp_dir}")
            logger.info(f"  media_dir: {self.media_dir}")
            logger.info(f"  scripts_dir: {self.scripts_dir}")
            
            # Ensure the directories exist
            os.makedirs(str(self.temp_dir), exist_ok=True)
            os.makedirs(str(self.media_dir), exist_ok=True)
            os.makedirs(str(self.scripts_dir), exist_ok=True)
            
            # Keep track of active capture processes
            self._current_process = None
            self._capture_thread = None
            self.active_captures = {}
            
            # Log initialization success
            logger.info("ParliamentTVCapture service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ParliamentTVCapture: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Set default values to prevent NoneType errors
            self.scripts_dir = Path("/app/scripts")
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media/parliament_captures")
            self._current_process = None
            self._capture_thread = None
            self.active_captures = {}
            
            # Create directories
            os.makedirs(str(self.temp_dir), exist_ok=True)
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
                return {
                    "success": False,
                    "error": "Failed to extract stream URL"
                }
            
            direct_stream = stream_info.get("direct_stream")
            logger.info(f"Extracted direct stream URL: {direct_stream}")
            
            # Test the stream URL
            if not self.test_stream_url(direct_stream):
                logger.error(f"Stream URL is not valid: {direct_stream}")
                return {
                    "success": False,
                    "error": "Stream URL is not valid"
                }
            
            # Generate a unique filename based on capture ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.media_dir, f"parliament_capture_{capture_id}_{timestamp}.mp4")
            
            # Run the capture script
            cmd = [
                sys.executable,
                os.path.join(self.scripts_dir, "parliament_capture_direct.py"),
                direct_stream,
                "--output", output_file,
                "--duration", str(duration),
                "--capture-id", str(capture_id)
            ]
            
            logger.info(f"Running capture command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the capture was successful
            if result.returncode == 0:
                # Parse the output to extract the output file path
                output_file = None
                for line in result.stdout.splitlines():
                    if line.startswith("Output file:"):
                        output_file = line.replace("Output file:", "").strip()
                        break
                
                if output_file and os.path.exists(output_file):
                    logger.info(f"Capture completed successfully. Output file: {output_file}")
                    return {
                        "success": True,
                        "output_file": output_file
                    }
                else:
                    logger.error("Capture completed but output file not found")
                    return {
                        "success": False,
                        "error": "Output file not found"
                    }
            else:
                logger.error(f"Capture failed with return code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return {
                    "success": False,
                    "error": f"Capture failed: {result.stderr}"
                }
        except Exception as e:
            logger.error(f"Error in start_capture: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }

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
                if callback:
                    callback(capture_id, None, "Failed to extract stream URL")
                return False
            
            # Create a thread to run the capture
            capture_thread = threading.Thread(
                target=self._run_capture,
                args=(url, capture_id, duration, callback),
                daemon=True
            )
            
            # Store the thread
            self._capture_thread = capture_thread
            
            # Start the thread
            capture_thread.start()
            
            logger.info(f"Capture thread started for {url}")
            return True
        except Exception as e:
            logger.error(f"Error starting async capture: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if callback:
                callback(capture_id, None, {
                    "success": False,
                    "error": str(e)
                })
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
            
            # Ensure directories exist
            os.makedirs(self.temp_dir, exist_ok=True)
            os.makedirs(self.media_dir, exist_ok=True)
            
            # Create a thread to run the capture
            capture_thread = threading.Thread(
                target=self.run_capture_process,
                args=(db_capture, direct_stream),
                daemon=True
            )
            
            # Store the thread in active_captures
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
            
            # Run the improved capture script
            cmd = [
                sys.executable,
                os.path.join(self.scripts_dir, "parliament_capture_direct.py"),
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
                    print(f"Capture successful for {capture_id}, output file: {output_file}")
                    # Update the database
                    self.capture_callback(db_capture, output_file)
                else:
                    print(f"Capture failed for {capture_id}: Output file not found or empty")
                    self.capture_callback(db_capture, None, "Output file not found or empty")
            else:
                # Capture failed
                print(f"Capture failed for {capture_id}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
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

    def _run_capture(self, url: str, capture_id: int, duration: int, callback=None):
        """
        Run the capture process in a separate thread.
        
        Args:
            url: Parliament TV event URL
            capture_id: The ID of the capture in the database
            duration: Maximum duration to capture in seconds
            callback: Optional callback function to call with the result
        """
        try:
            # Start the capture
            result = self.start_capture(url, capture_id, duration)
            
            # Call the callback if provided
            if callback:
                if result.get("success"):
                    callback(capture_id, result.get("output_file"))
                else:
                    callback(capture_id, None, result.get("error"))
        except Exception as e:
            logger.error(f"Error in _run_capture: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if callback:
                callback(capture_id, None, str(e))

    def extract_stream_url(self, url: str) -> Optional[Dict]:
        """
        Extract the direct stream URL from a Parliament TV event page.
        
        Args:
            url: Parliament TV event URL
            
        Returns:
            Dict containing stream information or None if extraction failed
        """
        logger.info(f"Extracting stream URL from: {url}")
        
        # Check if the URL is already a direct stream URL
        if url.endswith('.m3u8'):
            logger.info(f"URL appears to be a direct stream URL already: {url}")
            return {"direct_stream": url}
        
        # Ensure scripts_dir and temp_dir are set
        if self.scripts_dir is None:
            logger.error("scripts_dir is None, using default path")
            self.scripts_dir = Path("/app/scripts")
        
        if self.temp_dir is None:
            logger.error("temp_dir is None, using default path")
            self.temp_dir = Path("/app/data/temp")
            os.makedirs(str(self.temp_dir), exist_ok=True)
        
        extract_script = self.scripts_dir / "extract_direct_stream.py"
        output_file = self.temp_dir / f"stream_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Check if extract_script exists
        if not os.path.exists(str(extract_script)):
            logger.error(f"Extract script not found at {extract_script}")
            # Try alternative paths
            alternative_paths = [
                Path("scripts/extract_direct_stream.py"),
                Path("../scripts/extract_direct_stream.py"),
                Path("/app/scripts/extract_direct_stream.py")
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(str(alt_path)):
                    logger.info(f"Found alternative script path: {alt_path}")
                    extract_script = alt_path
                    break
            else:
                logger.error("Could not find extract_direct_stream.py script")
                # Fallback to a hardcoded test stream if extraction fails
                logger.warning("Using a fallback direct stream URL")
                return {"direct_stream": url}  # Return the original URL as fallback
        
        cmd = [
            sys.executable,
            str(extract_script),
            url,
            "--output", str(output_file)
        ]
        
        try:
            logger.info(f"Running extract command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Read the output file
            if os.path.exists(str(output_file)):
                with open(output_file, 'r') as f:
                    stream_info = json.load(f)
                
                # Validate that direct_stream is in the result
                if 'direct_stream' not in stream_info or not stream_info['direct_stream']:
                    logger.error("No direct_stream found in extracted stream info")
                    return {"direct_stream": url}  # Return the original URL as fallback
                
                logger.info(f"Stream URL extraction completed. Direct stream URL: {stream_info.get('direct_stream')}")
                return stream_info
            else:
                logger.error(f"Output file not found: {output_file}")
                return {"direct_stream": url}  # Return the original URL as fallback
        except subprocess.CalledProcessError as e:
            logger.error(f"Stream URL extraction failed: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            return {"direct_stream": url}  # Return the original URL as fallback
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error reading stream info: {e}")
            return {"direct_stream": url}  # Return the original URL as fallback
        except Exception as e:
            logger.error(f"Unexpected error in extract_stream_url: {str(e)}")
            return {"direct_stream": url}  # Return the original URL as fallback

    def test_stream_url(self, stream_url: str) -> bool:
        """
        Test if a stream URL is valid by downloading a small segment.
        
        Args:
            stream_url: Stream URL to test
            
        Returns:
            True if the stream URL is valid, False otherwise
        """
        logger.info(f"Testing stream URL: {stream_url}")
        
        test_script = self.scripts_dir / "test_stream_url.sh"
        
        cmd = [
            str(test_script),
            stream_url
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return "Success! The stream URL is valid." in result.stdout
        except subprocess.CalledProcessError:
            return False
            
    def capture_callback(self, db_capture, output_file, error=None):
        """Callback function for when a capture is completed."""
        try:
            capture_id = db_capture.id
            print(f"Capture callback for {capture_id}")
            
            if output_file:
                print(f"Capture successful: {output_file}")
                # Update the database with the output file
                db_capture.status = "completed"
                db_capture.output_file = output_file
                db_capture.completed_at = datetime.now()
            else:
                print(f"Capture failed: {error}")
                # Update the database with the error
                db_capture.status = "failed"
                db_capture.error = error
                
            # Save the changes to the database
            db_capture.save()
            print(f"Database updated for capture {capture_id}")
        except Exception as e:
            print(f"Error in capture_callback: {str(e)}")
            import traceback
            print(traceback.format_exc())
