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
    """Service for capturing Parliament TV streams with facial recognition."""
    
    def __init__(self):
        """Initialize the Parliament TV capture service."""
        # Use absolute paths for scripts directory
        self.scripts_dir = Path("/app/scripts")
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)
        self.media_dir = Path(settings.MEDIA_STORAGE_PATH) / "parliament_captures"
        
        # Create directories if they don't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        # Keep track of active capture processes
        self._current_process = None
        self._capture_thread = None
    
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
        
        # Generate a timestamp for the output file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Set up file paths - ALWAYS include the capture_id in the filename
        temp_file = self.temp_dir / f"parliament_stream_{timestamp}_{capture_id}.mp4"
        output_file = self.media_dir / f"parliament_capture_{timestamp}_{capture_id}.mp4"
        log_file = self.temp_dir / f"parliament_capture_log_{timestamp}_{capture_id}.json"
        capture_script = self.scripts_dir / "parliament_capture_direct.py"
        
        # Log the file paths for debugging
        logger.info(f"Temporary file path: {temp_file}")
        logger.info(f"Output file path: {output_file}")
        logger.info(f"Log file path: {log_file}")
        
        # Ensure the directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        # Add extensive logging to diagnose the issue
        logger.info(f"URL being passed to capture script: {url}")
        logger.info(f"URL type: {type(url)}")
        
        # Validate that the URL is not empty and is a proper URL
        if not url or not isinstance(url, str):
            logger.error(f"Invalid URL provided to start_capture: {url}")
            return {
                "success": False,
                "error": f"Invalid URL provided: {url}"
            }
        
        # Check if the URL is the Big Buck Bunny test URL
        if "commondatastorage.googleapis.com" in url and "BigBuckBunny" in url:
            logger.error(f"Detected Big Buck Bunny test URL: {url}")
            logger.error("This suggests the URL extraction failed and fell back to the test video")
            return {
                "success": False,
                "error": "URL extraction failed and fell back to test video. Please check the Parliament TV URL."
            }
        
        # Validate that the URL is a proper Parliament TV URL
        if not ("parliamentlive.tv" in url or "parliament.tv" in url):
            logger.error(f"URL does not appear to be a Parliament TV URL: {url}")
            return {
                "success": False,
                "error": f"The URL provided does not appear to be a valid Parliament TV URL: {url}"
            }
        
        # First extract the direct stream URL
        from scripts.extract_direct_stream import extract_direct_stream_url
        
        logger.info(f"Extracting direct stream URL from: {url}")
        direct_stream_url = extract_direct_stream_url(url)
        
        if not direct_stream_url:
            logger.error(f"Failed to extract direct stream URL from: {url}")
            return {
                "success": False,
                "error": "Failed to extract direct stream URL from Parliament TV page"
            }
            
        logger.info(f"Successfully extracted direct stream URL: {direct_stream_url}")
        
        # Now use parliament_capture_direct.py with the direct stream URL
        cmd = [
            sys.executable,
            str(capture_script),
            direct_stream_url,  # Use the direct stream URL instead of the Parliament TV URL
            "--duration", str(duration),
            "--output", str(temp_file),  # Use temp_file for initial capture
            "--capture-id", str(capture_id)  # Pass the capture ID for proper file naming
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Run the capture script
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            # Process the output
            stdout = result.stdout.decode('utf-8')
            stderr = result.stderr.decode('utf-8')
            
            logger.info(f"Capture process completed with return code: {result.returncode}")
            logger.info(f"STDOUT: {stdout}")
            
            if result.returncode != 0:
                logger.error(f"Capture process failed with return code: {result.returncode}")
                logger.error(f"STDERR: {stderr}")
                return {
                    "success": False,
                    "error": f"Capture process failed with return code: {result.returncode}",
                    "stdout": stdout,
                    "stderr": stderr
                }
            
            # Try to parse JSON output from the script
            output_file_path = None
            json_data = None
            
            # Look for JSON in the output
            for line in stdout.split('\n'):
                if line.strip().startswith('{') and line.strip().endswith('}'): 
                    try:
                        json_data = json.loads(line.strip())
                        logger.info(f"Found JSON output: {json_data}")
                        if json_data.get('output_file'):
                            output_file_path = json_data.get('output_file')
                            break
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, try the old method
            if not output_file_path:
                for line in stdout.split('\n'):
                    if line.startswith('Output file:'):
                        output_file_path = line.split('Output file:')[1].strip()
                        break
            
            if not output_file_path:
                logger.error("Could not find output file path in capture process output")
                return {
                    "success": False,
                    "error": "Could not find output file path in capture process output",
                    "stdout": stdout,
                    "stderr": stderr
                }
            
            logger.info(f"Parliament TV capture completed successfully. Output file: {output_file_path}")
            return {
                "success": True,
                "output_file": output_file_path
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Capture process failed with exit code {e.returncode}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            return {
                "success": False,
                "error": f"Capture process failed with exit code {e.returncode}",
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        except Exception as e:
            logger.error(f"Unexpected error during capture: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def start_capture_async(self, url: str, capture_id: int, duration: int = 1800, callback=None) -> None:
        """
        Start capturing a Parliament TV stream asynchronously.
        
        Args:
            url: Parliament TV event URL
            capture_id: The ID of the capture in the database
            duration: Maximum duration to capture in seconds (default: 30 minutes)
            callback: Optional callback function to call with the result
        """
        def capture_thread():
            result = self.start_capture(url, capture_id, duration)
            if callback:
                callback(result)
        
        self._capture_thread = threading.Thread(target=capture_thread)
        self._capture_thread.daemon = True
        self._capture_thread.start()
    
    def extract_stream_url(self, url: str) -> Optional[Dict]:
        """
        Extract the direct stream URL from a Parliament TV event page.
        
        Args:
            url: Parliament TV event URL
            
        Returns:
            Dict containing stream information or None if extraction failed
        """
        logger.info(f"Extracting stream URL from: {url}")
        
        extract_script = self.scripts_dir / "extract_direct_stream.py"
        output_file = self.temp_dir / f"stream_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        cmd = [
            sys.executable,
            str(extract_script),
            url,
            "--output", str(output_file)
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Read the output file
            with open(output_file, 'r') as f:
                stream_info = json.load(f)
            
            logger.info(f"Stream URL extraction completed. Direct stream URL: {stream_info.get('direct_stream')}")
            return stream_info
        except subprocess.CalledProcessError as e:
            logger.error(f"Stream URL extraction failed: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            return None
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error reading stream info: {e}")
            return None
    
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
