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
    
    # Generate a timestamp for the output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Debug the paths
    logger.info(f"temp_dir: {self.temp_dir}, type: {type(self.temp_dir)}")
    logger.info(f"media_dir: {self.media_dir}, type: {type(self.media_dir)}")
    logger.info(f"scripts_dir: {self.scripts_dir}, type: {type(self.scripts_dir)}")
    
    # Ensure all directory paths are Path objects and exist
    # Convert to Path objects if they're strings, or use defaults if None
    if self.temp_dir is None:
        logger.error("temp_dir is None, using default path")
        self.temp_dir = Path("/app/data/temp")
    elif isinstance(self.temp_dir, str):
        self.temp_dir = Path(self.temp_dir)
    
    if self.media_dir is None:
        logger.error("media_dir is None, using default path")
        self.media_dir = Path("/app/data/media/parliament_captures")
    elif isinstance(self.media_dir, str):
        self.media_dir = Path(self.media_dir)
    
    if self.scripts_dir is None:
        logger.error("scripts_dir is None, using default path")
        self.scripts_dir = Path("/app/scripts")
    elif isinstance(self.scripts_dir, str):
        self.scripts_dir = Path(self.scripts_dir)
    
    # Ensure directories exist
    os.makedirs(str(self.temp_dir), exist_ok=True)
    os.makedirs(str(self.media_dir), exist_ok=True)
    
    # Now create the file paths - ensure all paths are strings first to avoid NoneType errors
    temp_dir_str = str(self.temp_dir) if self.temp_dir else "/app/data/temp"
    media_dir_str = str(self.media_dir) if self.media_dir else "/app/data/media/parliament_captures"
    scripts_dir_str = str(self.scripts_dir) if self.scripts_dir else "/app/scripts"
    
    # Create Path objects from the strings
    temp_file = Path(temp_dir_str) / f"parliament_stream_{timestamp}_{capture_id}.mp4"
    output_file = Path(media_dir_str) / f"parliament_capture_{timestamp}_{capture_id}.mp4"
    log_file = Path(temp_dir_str) / f"parliament_capture_log_{timestamp}_{capture_id}.json"
    capture_script = Path(scripts_dir_str) / "parliament_capture_direct.py"
    
    # Log the file paths
    logger.info(f"temp_file: {temp_file}, type: {type(temp_file)}")
    logger.info(f"output_file: {output_file}, type: {type(output_file)}")
    logger.info(f"log_file: {log_file}, type: {type(log_file)}")
    logger.info(f"capture_script: {capture_script}, type: {type(capture_script)}")
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(str(temp_file)), exist_ok=True)
    os.makedirs(os.path.dirname(str(output_file)), exist_ok=True)
    os.makedirs(os.path.dirname(str(log_file)), exist_ok=True)
    
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
    try:
        # Use our improved extract_stream_url method instead of trying to import
        logger.info(f"Calling extract_stream_url with URL: {url}")
        stream_info = self.extract_stream_url(url)
        
        if not stream_info:
            logger.error("extract_stream_url returned None")
            stream_info = {"direct_stream": url}  # Fallback to original URL
            
        logger.info(f"Stream info: {stream_info}")
        direct_stream_url = stream_info.get("direct_stream")
        logger.info(f"Direct stream URL: {direct_stream_url}, type: {type(direct_stream_url)}")
        
        if not direct_stream_url:
            logger.error("direct_stream_url is None or empty, using original URL as fallback")
            direct_stream_url = url
            
    except Exception as e:
        logger.error(f"Error extracting direct stream URL: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # If all else fails, just use the original URL
        direct_stream_url = url
        logger.warning(f"Using original URL as direct stream URL: {direct_stream_url}")
    
    # Ensure direct_stream_url is not None
    if not direct_stream_url:
        logger.error(f"Failed to extract direct stream URL from: {url}")
        return {
            "success": False,
            "error": "Failed to extract direct stream URL from Parliament TV page"
        }
        
    # Validate direct_stream_url is a string
    if not isinstance(direct_stream_url, str):
        logger.error(f"direct_stream_url is not a string: {direct_stream_url}, type: {type(direct_stream_url)}")
        direct_stream_url = str(direct_stream_url) if direct_stream_url is not None else url
        
    logger.info(f"Successfully extracted direct stream URL: {direct_stream_url}")
    
    # Check if the capture script exists
    script_found = False
    if capture_script is not None and os.path.exists(str(capture_script)):
        script_found = True
        logger.info(f"Found capture script at: {capture_script}")
    else:
        logger.error(f"Capture script not found at {capture_script}")
        # Try to find the script in the current directory or parent directories
        alternative_paths = [
            Path("scripts/parliament_capture_direct.py"),
            Path("../scripts/parliament_capture_direct.py"),
            Path("/app/scripts/parliament_capture_direct.py"),
            Path("/scripts/parliament_capture_direct.py"),
            Path(os.path.join(os.getcwd(), "scripts/parliament_capture_direct.py")),
            Path(os.path.join(os.getcwd(), "../scripts/parliament_capture_direct.py"))
        ]
        
        for alt_path in alternative_paths:
            try:
                if os.path.exists(str(alt_path)):
                    logger.info(f"Found alternative script path: {alt_path}")
                    capture_script = alt_path
                    script_found = True
                    break
            except Exception as e:
                logger.error(f"Error checking path {alt_path}: {str(e)}")
        
        if not script_found:
            # Last resort: try to find the script by searching in common directories
            search_dirs = ["/app", "/", ".", "..", "/usr/local", "/usr/local/bin"]
            for search_dir in search_dirs:
                try:
                    if os.path.exists(search_dir):
                        logger.info(f"Searching for script in {search_dir}")
                        for root, dirs, files in os.walk(search_dir, topdown=True, followlinks=False):
                            if "parliament_capture_direct.py" in files:
                                script_path = os.path.join(root, "parliament_capture_direct.py")
                                logger.info(f"Found script at: {script_path}")
                                capture_script = Path(script_path)
                                script_found = True
                                break
                            # Limit depth to avoid excessive searching
                            if root.count(os.sep) - search_dir.count(os.sep) > 3:
                                dirs[:] = []
                    if script_found:
                        break
                except Exception as e:
                    logger.error(f"Error searching in {search_dir}: {str(e)}")
        
        if not script_found:
            logger.error("Could not find parliament_capture_direct.py script")
            return {
                "success": False,
                "error": "Capture script not found"
            }
    
    # Now use parliament_capture_direct.py with the direct stream URL
    # Add extensive logging to debug the NoneType error
    logger.info(f"capture_script: {capture_script}, exists: {os.path.exists(str(capture_script))}")
    logger.info(f"direct_stream_url: {direct_stream_url}, type: {type(direct_stream_url)}")
    logger.info(f"temp_file: {temp_file}, type: {type(temp_file)}")
    logger.info(f"capture_id: {capture_id}, type: {type(capture_id)}")
    
    # Check for None values
    if capture_script is None:
        logger.error("capture_script is None!")
        return {"success": False, "error": "capture_script is None"}
    if direct_stream_url is None:
        logger.error("direct_stream_url is None!")
        return {"success": False, "error": "direct_stream_url is None"}
    if temp_file is None:
        logger.error("temp_file is None!")
        return {"success": False, "error": "temp_file is None"}
    
    # Ensure all arguments are valid and not None
    python_executable = sys.executable if sys.executable else "python"
    capture_script_str = str(capture_script) if capture_script else "/app/scripts/parliament_capture_direct.py"
    direct_stream_url_str = str(direct_stream_url) if direct_stream_url else url
    duration_str = str(duration) if duration else "1800"
    temp_file_str = str(temp_file) if temp_file else f"/app/data/temp/parliament_stream_{timestamp}_{capture_id}.mp4"
    capture_id_str = str(capture_id) if capture_id else "0"
    
    # Create command with validated arguments
    cmd = [
        python_executable,
        capture_script_str,
        direct_stream_url_str,  # Use the direct stream URL instead of the Parliament TV URL
        "--duration", duration_str,
        "--output", temp_file_str,  # Use temp_file for initial capture
        "--capture-id", capture_id_str  # Pass the capture ID for proper file naming
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    logger.info(f"Command types: {[type(c) for c in cmd]}")
    
    # Double-check that all command arguments are strings
    cmd = [str(c) if c is not None else "" for c in cmd]
    
    try:
        # Log the command being run
        cmd_str = ' '.join(str(c) for c in cmd)
        logger.info(f"Running command: {cmd_str}")
        
        # Ensure all command arguments are strings
        cmd = [str(c) for c in cmd]
        
        # Run the capture script
        result = subprocess.run(
            cmd, 
            check=False,  # Don't raise exception on non-zero exit
            capture_output=True, 
            text=True
        )
        
        # Process the output
        stdout = result.stdout
        stderr = result.stderr
        
        # Log the result
        logger.info(f"Command exit code: {result.returncode}")
        logger.info(f"Command stdout: {stdout[:1000]}" + ("..." if len(stdout) > 1000 else ""))
        logger.info(f"Command stderr: {stderr[:1000]}" + ("..." if len(stderr) > 1000 else ""))
        
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
    # Print detailed debugging information
    print(f"DEBUG - start_capture_async called with URL: {url}, type: {type(url)}")
    print(f"DEBUG - capture_id: {capture_id}, type: {type(capture_id)}")
    print(f"DEBUG - duration: {duration}, type: {type(duration)}")
    print(f"DEBUG - callback: {callback is not None}")
    print(f"DEBUG - self.temp_dir: {self.temp_dir}, type: {type(self.temp_dir)}")
    print(f"DEBUG - self.media_dir: {self.media_dir}, type: {type(self.media_dir)}")
    print(f"DEBUG - self.scripts_dir: {self.scripts_dir}, type: {type(self.scripts_dir)}")
    
    # Validate inputs before starting the thread
    logger.info(f"start_capture_async called with URL: {url}, type: {type(url)}")
    logger.info(f"capture_id: {capture_id}, type: {type(capture_id)}")
    logger.info(f"duration: {duration}, type: {type(duration)}")
    logger.info(f"callback: {callback is not None}")
    
    # Ensure URL is not None and is a string
    if url is None:
        error_msg = "URL cannot be None"
        logger.error(error_msg)
        if callback:
            callback({"success": False, "error": error_msg})
        return False
    
    if not isinstance(url, str):
        logger.warning(f"URL is not a string: {url}, type: {type(url)}")
        try:
            url = str(url)
            logger.info(f"Converted URL to string: {url}")
        except Exception as e:
            error_msg = f"Failed to convert URL to string: {str(e)}"
            logger.error(error_msg)
            if callback:
                callback({"success": False, "error": error_msg})
            return False
    
    # Ensure capture_id is not None and is an integer
    if capture_id is None:
        error_msg = "capture_id cannot be None"
        logger.error(error_msg)
        if callback:
            callback({"success": False, "error": error_msg})
        return False
    
    try:
        capture_id = int(capture_id)
    except (ValueError, TypeError) as e:
        error_msg = f"Failed to convert capture_id to integer: {str(e)}"
        logger.error(error_msg)
        if callback:
            callback({"success": False, "error": error_msg})
        return False
    
    # Ensure duration is not None and is an integer
    if duration is None:
        logger.warning("duration is None, using default value of 1800 seconds")
        duration = 1800
    
    try:
        duration = int(duration)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert duration to integer: {str(e)}, using default value of 1800 seconds")
        duration = 1800
    
    # Find the capture script
    try:
        # First check if scripts_dir contains the script
        script_path = None
        if self.scripts_dir is not None:
            potential_script = os.path.join(str(self.scripts_dir), "parliament_capture_direct.py")
            if os.path.exists(potential_script):
                script_path = potential_script
                logger.info(f"Found script at: {script_path}")
        
        # If not found, try alternative locations
        if not script_path:
            alternative_paths = [
                "/app/scripts/parliament_capture_direct.py",
                "scripts/parliament_capture_direct.py",
                "../scripts/parliament_capture_direct.py",
                "/scripts/parliament_capture_direct.py",
                os.path.join(os.getcwd(), "scripts/parliament_capture_direct.py"),
                os.path.join(os.getcwd(), "../scripts/parliament_capture_direct.py")
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    script_path = alt_path
                    logger.info(f"Found script at alternative location: {script_path}")
                    break
        
        # If we still can't find the script, raise an error
        if not script_path:
            error_msg = "Could not find parliament_capture_direct.py script in any location"
            logger.error(error_msg)
            if callback:
                callback({"success": False, "error": error_msg})
            return False
        
        # Store the script path for use in _run_capture
        self._script_path = script_path
        
        # Ensure temp and media directories exist
        os.makedirs(str(self.temp_dir), exist_ok=True)
        os.makedirs(str(self.media_dir), exist_ok=True)
        
        # Start the capture in a separate thread
        self._capture_thread = threading.Thread(
            target=self._run_capture,
            args=(url, capture_id, duration, callback)
        )
        self._capture_thread.daemon = True
        self._capture_thread.start()
        logger.debug("Started capture thread")
        return True
    except Exception as e:
        error_msg = f"Error starting capture thread: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"Unexpected error starting capture: {str(e)}")
        if callback:
            callback({
                "success": False,
                "error": error_msg
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
            "--temp-dir", self.temp_dir,
            "--media-dir", self.media_dir
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
        # Ensure paths are initialized before calling start_capture
        if self.temp_dir is None:
            logger.warning("temp_dir is None, initializing to default path")
            self.temp_dir = Path("/app/data/temp")
            os.makedirs(str(self.temp_dir), exist_ok=True)
            
        if self.media_dir is None:
            logger.warning("media_dir is None, initializing to default path")
            self.media_dir = Path("/app/data/media/parliament_captures")
            os.makedirs(str(self.media_dir), exist_ok=True)
            
        if self.scripts_dir is None:
            logger.warning("scripts_dir is None, initializing to default path")
            self.scripts_dir = Path("/app/scripts")
        
        # Call start_capture with validated inputs
        result = self.start_capture(url, capture_id, duration)
        logger.info(f"Capture thread completed with result: {result}")
        
        if callback:
            logger.info("Calling callback function with result")
            callback(result)
    except Exception as e:
        error_msg = f"Unexpected error in capture thread: {str(e)}"
        logger.error(error_msg)
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Traceback: {tb}")
        print(f"Unexpected error in capture thread: {str(e)}")
        
        if callback:
            callback({"success": False, "error": error_msg})

def extract_stream_url(self, url: str) -> Optional[Dict]:
    """
    Extract the direct stream URL from a Parliament TV event page.
    
    Args:
        url: Parliament TV event URL
        
    Returns:
        Dict containing stream information or None if extraction failed
    """
    logger.info(f"Extracting stream URL from: {url}")
    
    # Check if the URL is already a direct stream URL (ends with .m3u8)
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
