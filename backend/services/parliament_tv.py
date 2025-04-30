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
    
    def start_capture(self, url: str, duration: int = 300, enable_facial_recognition: bool = True) -> Dict:
        """
        Start capturing a Parliament TV stream.
        
        Args:
            url: Parliament TV event URL
            duration: Maximum duration to capture in seconds
            enable_facial_recognition: Enable facial recognition to stop when speaker is no longer present
            
        Returns:
            Dict containing capture information including output file path
        """
        logger.info(f"Starting Parliament TV capture for URL: {url}")
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.media_dir / f"parliament_capture_{timestamp}.mp4"
        log_file = self.temp_dir / f"parliament_capture_log_{timestamp}.json"
        
        # Build the command
        capture_script = self.scripts_dir / "parliament_capture_direct.py"
        
        cmd = [
            sys.executable,
            str(capture_script),
            url,
            "--duration", str(duration),
            "--output", str(output_file)
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
            
            # Parse the JSON output
            try:
                output = json.loads(result.stdout)
                
                # Save the output to a log file
                with open(log_file, 'w') as f:
                    json.dump(output, f, indent=2)
                
                logger.info(f"Parliament TV capture completed successfully. Output file: {output.get('output_file')}")
                return output
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse capture output as JSON: {e}")
                logger.error(f"Output: {result.stdout}")
                return {
                    "success": False,
                    "error": "Failed to parse capture output",
                    "stdout": result.stdout,
                    "stderr": result.stderr
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
    
    def start_capture_async(self, url: str, duration: int = 300, enable_facial_recognition: bool = True, callback=None) -> None:
        """
        Start capturing a Parliament TV stream asynchronously.
        
        Args:
            url: Parliament TV event URL
            duration: Maximum duration to capture in seconds
            enable_facial_recognition: Enable facial recognition to stop when speaker is no longer present
            callback: Optional callback function to call with the result
        """
        def capture_thread():
            result = self.start_capture(url, duration, enable_facial_recognition)
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
