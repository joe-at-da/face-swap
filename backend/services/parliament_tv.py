import os
import sys
import json
import time
import shutil
import logging
import tempfile
import subprocess
import re
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
            
            # Run the capture process directly instead of using a thread
            print("DEBUG - Running capture process directly")
            # Hard-code paths to ensure they're never None
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media")
            self.scripts_dir = Path("/app/scripts")
            
            # Create directories if they don't exist
            os.makedirs(str(self.temp_dir), exist_ok=True)
            os.makedirs(str(self.media_dir), exist_ok=True)
            
            # Get the direct stream URL
            direct_stream = stream_info.get("direct_stream")
            
            # Run the capture process directly
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
            
            # Run the capture process directly instead of using a thread
            print("DEBUG - Running capture process directly in start_capture_async")
            
            # CRITICAL FIX: Hard-code paths to ensure they're never None
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media")
            
            # Create directories if they don't exist
            temp_dir_str = str(self.temp_dir)
            media_dir_str = str(self.media_dir)
            
            os.makedirs(temp_dir_str, exist_ok=True)
            os.makedirs(media_dir_str, exist_ok=True)
            
            # Define the output file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(temp_dir_str, f"parliament_capture_{capture_id}_{timestamp}.mp4")
            
            # Build a simple ffmpeg command to capture the stream
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", direct_stream,  # Input stream URL
                "-t", str(duration),  # Duration
                "-c:v", "copy",  # Copy video codec
                "-c:a", "copy",  # Copy audio codec
                output_file  # Output file
            ]
            
            print(f"DEBUG - start_capture_async - Command: {' '.join(cmd)}")
            print(f"DEBUG - start_capture_async - Output file: {output_file}")
            
            try:
                # Run the download process with the original URL and stream info
                # This allows download_stream to properly extract audio URLs
                stream_dict = {
                    'direct_stream': direct_stream,
                    'original_url': url
                }
                print(f"DEBUG - start_capture_async - Passing stream info to download_stream: {stream_dict}")
                download_result = self.download_stream(stream_dict, output_file, duration)
                
                if download_result.get("success"):
                    print(f"DEBUG - run_capture_process - Download successful: {output_file}")
                    
                    # Get a new database session
                    db = next(get_db())
                    
                    # Get the capture from the database
                    db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
                    if db_capture:
                        # Update the capture with the file path and status
                        db_capture.file_path = output_file
                        db_capture.status = "completed"
                        db_capture.end_time = datetime.now()
                        
                        # Save the audio file path if available
                        audio_file_path = download_result.get("audio_file_path")
                        if audio_file_path and os.path.exists(audio_file_path):
                            print(f"DEBUG - run_capture_process - Saving audio file path: {audio_file_path}")
                            # Check if the model has the audio_file_path attribute
                            if hasattr(db_capture, 'audio_file_path'):
                                db_capture.audio_file_path = audio_file_path
                                self.log_capture(db, db_capture.id, "info", f"Audio file saved: {audio_file_path}")
                            else:
                                print(f"WARNING - run_capture_process - CaptureSession model doesn't have audio_file_path attribute")
                                # Try to store it in metadata
                                if not hasattr(db_capture, 'metadata') or db_capture.metadata is None:
                                    db_capture.metadata = {}
                                if isinstance(db_capture.metadata, dict):
                                    db_capture.metadata['audio_file_path'] = audio_file_path
                                    self.log_capture(db, db_capture.id, "info", f"Audio file path stored in metadata: {audio_file_path}")
                        
                        db.commit()
                        
                        # Log the success
                        self.log_capture(db, db_capture.id, "info", f"Capture completed successfully: {output_file}")
                        
                        # Call the callback if provided
                        self.capture_callback(db_capture, output_file)
                    else:
                        print(f"ERROR - run_capture_process - Capture {capture_id} not found in database after download")
                        db_capture.status = "failed"
                        db_capture.error = "Output file not found or empty"
                        db.commit()
                        
                        if callback:
                            callback({
                                "success": False,
                                "error": "Output file not found or empty",
                                "capture_id": capture_id
                            })
                        
                        return False
                else:
                    print(f"DEBUG - start_capture_async - Command failed with return code {result.returncode}")
                    print(f"DEBUG - start_capture_async - Command output: {result.stdout}")
                    print(f"DEBUG - start_capture_async - Command error: {result.stderr}")
                    
                    db_capture.status = "failed"
                    db_capture.error = f"Command failed with return code {result.returncode}: {result.stderr}"
                    db.commit()
                    
                    if callback:
                        callback({
                            "success": False,
                            "error": f"Command failed with return code {result.returncode}: {result.stderr}",
                            "capture_id": capture_id
                        })
                    
                    return False
            except Exception as e:
                print(f"DEBUG - start_capture_async - Exception running command: {str(e)}")
                
                db_capture.status = "failed"
                db_capture.error = f"Exception running command: {str(e)}"
                db.commit()
                
                if callback:
                    callback({
                        "success": False,
                        "error": f"Exception running command: {str(e)}",
                        "capture_id": capture_id
                    })
                
                return False
            
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
            
            # Get the capture ID and duration
            capture_id = db_capture.id
            duration = db_capture.duration or 1800  # Default to 30 minutes
            print(f"DEBUG - capture_id={capture_id}, duration={duration}")
            
            # Get the direct stream URL
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
        """Run the capture process and update the database with the capture status."""
        capture_id = None
        try:
            # CRITICAL FIX: Hard-code paths to ensure they're never None
            print("DEBUG - run_capture_process - Setting hard-coded paths to ensure they're never None")
            self.temp_dir = Path("/app/data/temp")
            self.media_dir = Path("/app/data/media")
            self.scripts_dir = Path("/app/scripts")
            
            # Create directories if they don't exist
            temp_dir_str = str(self.temp_dir)
            media_dir_str = str(self.media_dir)
            
            # Create audio_extracts directory in temp_dir
            audio_extracts_dir = os.path.join(temp_dir_str, "audio_extracts")
            os.makedirs(audio_extracts_dir, exist_ok=True)
            print(f"DEBUG - run_capture_process - Created audio_extracts directory: {audio_extracts_dir}")
            
            scripts_dir_str = str(self.scripts_dir)
            
            print(f"DEBUG - run_capture_process - Creating temp_dir: {temp_dir_str}")
            os.makedirs(temp_dir_str, exist_ok=True)
            
            print(f"DEBUG - run_capture_process - Creating media_dir: {media_dir_str}")
            os.makedirs(media_dir_str, exist_ok=True)
            
            # Get the capture ID and duration
            capture_id = db_capture.id
            duration = db_capture.duration or 1800  # Default to 30 minutes if None
            
            print(f"DEBUG - run_capture_process - capture_id: {capture_id}, direct_stream: {direct_stream}")
            
            # Validate direct_stream
            if direct_stream is None:
                print(f"ERROR - run_capture_process - direct_stream is None for capture {capture_id}")
                self.capture_callback(db_capture, None, "Direct stream URL is None")
                return
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                print(f"Error: Capture {capture_id} not found in database")
                return
                
            # Check if the capture is still active
            if db_capture.status != "active":
                print(f"Capture {capture_id} is no longer active (status: {db_capture.status})")
                return
            
            # Ensure scripts_dir is set
            if self.scripts_dir is None:
                print("ERROR - run_capture_process - scripts_dir is None")
                self.scripts_dir = Path("/app/scripts")
                print(f"DEBUG - run_capture_process - Set default scripts_dir to {self.scripts_dir}")
            
            # Hard-code the script path to ensure it's never None
            script_path = "/app/scripts/parliament_capture_direct.py"
            print(f"DEBUG - run_capture_process - Using script_path: {script_path}")
            
            # If script doesn't exist in scripts_dir, try to find it elsewhere
            if not os.path.exists(script_path):
                print(f"DEBUG - run_capture_process - Script not found at {script_path}, searching in other locations")
                # Try all possible locations for the script
                alt_paths = [
                    "/app/scripts/parliament_capture_direct.py",
                    "/app/backend/scripts/parliament_capture_direct.py",
                    "/Users/joebradley/Veedoo/Development/the-mp/scripts/parliament_capture_direct.py"
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        print(f"DEBUG - run_capture_process - Found script at: {script_path}")
                        break
                else:
                    print("ERROR - run_capture_process - Could not find parliament_capture_direct.py in any location")
                    self.capture_callback(db_capture, None, "Could not find parliament_capture_direct.py script")
                    return
            
            # Check if Python executable is valid
            python_executable = sys.executable
            if not os.path.exists(python_executable):
                print(f"ERROR - run_capture_process - Python executable not found: {python_executable}")
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
                        print(f"DEBUG - run_capture_process - Found Python at: {python_executable}")
                        break
                else:
                    print("ERROR - run_capture_process - Could not find Python executable")
                    self.capture_callback(db_capture, None, "Could not find Python executable")
                    return
            else:
                print(f"DEBUG - run_capture_process - Using Python executable: {python_executable}")
            
            # Ensure temp_dir and media_dir are set and exist
            try:
                # Variables already defined at the beginning of the method, but let's ensure they're still valid
                if not temp_dir_str or not media_dir_str:
                    print("WARNING - run_capture_process - temp_dir_str or media_dir_str is empty, recreating them")
                    temp_dir_str = str(self.temp_dir)
                    media_dir_str = str(self.media_dir)
                
                # Double-check directories exist
                print(f"DEBUG - run_capture_process - Verifying temp_dir: {temp_dir_str}")
                os.makedirs(temp_dir_str, exist_ok=True)
                
                print(f"DEBUG - run_capture_process - Verifying media_dir: {media_dir_str}")
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
                
                # Build the command to call the parliament_capture_direct.py script directly
                # Use the exact parameters that worked in the test
                script_path = "/app/scripts/parliament_capture_direct.py"
                python_executable = "/usr/local/bin/python3"
                
                # Define the output file path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = os.path.join(temp_dir_str, f"parliament_capture_{capture_id}_{timestamp}.mp4")
                
                # Define the audio output file path for later use in capture_callback
                audio_output_file = os.path.join(temp_dir_str, "audio_extracts", f"capture_{capture_id}_audio.mp3")
                
                cmd = [
                    python_executable,
                    script_path,
                    direct_stream,
                    "--capture-id", str(capture_id),
                    "--duration", str(duration),
                    "--temp-dir", temp_dir_str,
                    "--media-dir", media_dir_str,
                    "--output", output_file
                ]
                
                print(f"DEBUG - run_capture_process - Command: {' '.join(cmd)}")
                print(f"DEBUG - run_capture_process - Output file: {output_file}")
                print(f"DEBUG - run_capture_process - Command built successfully: {' '.join(cmd)}")
            except Exception as e:
                print(f"ERROR - run_capture_process - Failed to build command: {str(e)}")
                import traceback
                print(f"ERROR - run_capture_process - Traceback: {traceback.format_exc()}")
                self.capture_callback(db_capture, None, f"Failed to build command: {str(e)}")
                return
            
            # Run the command
            print(f"DEBUG - run_capture_process - Running capture command: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                print(f"DEBUG - run_capture_process - subprocess.run completed, returncode: {result.returncode}")
            except Exception as e:
                print(f"ERROR - run_capture_process - Failed to run subprocess: {str(e)}")
                import traceback
                print(f"ERROR - run_capture_process - Traceback: {traceback.format_exc()}")
                self.capture_callback(db_capture, None, f"Failed to run subprocess: {str(e)}")
                return
            
            # Check if the capture was successful
            if result.returncode == 0:
                print(f"DEBUG - run_capture_process - Command succeeded with output: {result.stdout}")
                # We already know the output file path since we defined it above
                print(f"DEBUG - run_capture_process - Using predefined output file: {output_file}")
                
                if output_file:
                    print(f"DEBUG - run_capture_process - Checking if output file exists: {output_file}")
                    if os.path.exists(output_file):
                        print(f"DEBUG - run_capture_process - Output file exists, size: {os.path.getsize(output_file)}")
                        if os.path.getsize(output_file) > 0:
                            print(f"DEBUG - run_capture_process - Capture successful, output file: {output_file}")
                            self.capture_callback(db_capture, output_file)
                        else:
                            print(f"ERROR - run_capture_process - Output file is empty: {output_file}")
                            self.capture_callback(db_capture, None, "Output file is empty")
                    else:
                        print(f"ERROR - run_capture_process - Output file not found: {output_file}")
                        self.capture_callback(db_capture, None, "Output file not found")
                else:
                    print(f"ERROR - run_capture_process - No output file found in command output")
                    print(f"DEBUG - run_capture_process - Command output: {result.stdout}")
                    self.capture_callback(db_capture, None, "No output file found in command output")
            else:
                print(f"ERROR - run_capture_process - Command failed with return code {result.returncode}")
                print(f"ERROR - run_capture_process - Command output: {result.stdout}")
                print(f"ERROR - run_capture_process - Command error: {result.stderr}")
                self.capture_callback(db_capture, None, f"Command failed with return code {result.returncode}: {result.stderr}")
                
        except Exception as e:
            print(f"ERROR - run_capture_process - Unexpected error: {str(e)}")
            import traceback
            print(f"ERROR - run_capture_process - Traceback: {traceback.format_exc()}")
            
            # Try to get a database session
            try:
                db = next(get_db())
                if capture_id:
                    db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
                    if db_capture:
                        self.capture_callback(db_capture, None, f"Unexpected error: {str(e)}")
            except Exception as db_error:
                print(f"ERROR - run_capture_process - Failed to update database after error: {str(db_error)}")
                import traceback
                print(f"ERROR - run_capture_process - Database error traceback: {traceback.format_exc()}")
        finally:
            # Remove from active_captures
            if capture_id and capture_id in self.active_captures:
                print(f"DEBUG - run_capture_process - Removing capture {capture_id} from active_captures")
                del self.active_captures[capture_id]
                
    def capture_callback(self, db_capture, output_file, error=None):
        """Callback function for when a capture completes or fails."""
        try:
            capture_id = db_capture.id
            print(f"DEBUG - capture_callback - capture_id: {capture_id}, output_file: {output_file}, error: {error}")
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                print(f"Error: Capture {capture_id} not found in database")
                return
            
            # Update the capture status
            if error:
                print(f"DEBUG - capture_callback - Capture {capture_id} failed with error: {error}")
                db_capture.status = "failed"
                db_capture.error = error
                db_capture.stopped_at = datetime.now()
                self.log_capture(db, capture_id, "error", f"Capture failed: {error}")
            else:
                print(f"DEBUG - capture_callback - Capture {capture_id} completed successfully")
                db_capture.status = "completed"
                db_capture.stopped_at = datetime.now()
                db_capture.output_file = output_file
                self.log_capture(db, capture_id, "info", "Capture completed successfully")
                
                # Check if the output file exists
                if output_file and os.path.exists(output_file):
                    print(f"DEBUG - capture_callback - Output file exists: {output_file}")
                    
                    # Define Docker container paths
                    docker_audio_extracts_dir = "/app/data/temp/audio_extracts"
                
                    # Ensure the audio extracts directory exists in the Docker container
                    os.makedirs(docker_audio_extracts_dir, exist_ok=True)
                    print(f"DEBUG - capture_callback - Created Docker audio extracts directory: {docker_audio_extracts_dir}")
                    
                    # Create the correctly formatted audio file path
                    # Format should be: capture_XXXX.audio.mp3 where XXXX is the zero-padded capture ID
                    padded_capture_id = str(capture_id).zfill(4)
                    audio_file_path = os.path.join(docker_audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
                    print(f"DEBUG - capture_callback - Docker ID-based audio path: {audio_file_path}")
                    
                    # Check if the audio file exists
                    if os.path.exists(audio_file_path):
                        print(f"DEBUG - capture_callback - Audio file exists: {audio_file_path}")
                        
                        # The audio file is already at the correct path, just save it in the database
                        print(f"DEBUG - capture_callback - Saving audio file path: {audio_file_path}")
                        
                        # Check if the model has the audio_file_path attribute
                        if hasattr(db_capture, 'audio_file_path'):
                            db_capture.audio_file_path = audio_file_path
                            self.log_capture(db, db_capture.id, "info", f"Audio file saved: {audio_file_path}")
                        else:
                            print(f"WARNING - capture_callback - CaptureSession model does not have audio_file_path attribute")
                    else:
                        print(f"DEBUG - capture_callback - Audio file not found: {audio_file_path}")
                        
                        # Try to find the audio file with alternative patterns
                        print(f"DEBUG - capture_callback - Trying alternative patterns for audio file")
                        # Get padded capture ID (e.g., 0093)
                        padded_capture_id = str(capture_id).zfill(4)
                        
                        alt_patterns = [
                            # Primary pattern we want: capture_XXXX.audio.mp3
                            os.path.join(docker_audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3"),
                            
                            # Alternative patterns that might exist
                            os.path.join(docker_audio_extracts_dir, f"capture_{capture_id}.audio.mp3"),
                            os.path.join(docker_audio_extracts_dir, f"capture_{capture_id}_audio.mp3"),
                            os.path.join(os.path.dirname(output_file), f"capture_{padded_capture_id}.audio.mp3"),
                            f"{output_file}.audio.mp3"
                        ]
                        
                        # Also check in the Docker container's temp directory
                        docker_temp_dir = "/app/data/temp"
                        alt_patterns.extend([
                            os.path.join(docker_temp_dir, f"capture_{padded_capture_id}.audio.mp3"),
                            os.path.join(docker_temp_dir, f"capture_{capture_id}.audio.mp3")
                        ])
                        
                        for pattern in alt_patterns:
                            # Handle glob patterns
                            if '*' in pattern:
                                import glob
                                matching_files = glob.glob(pattern)
                                if matching_files:
                                    pattern = matching_files[0]  # Use the first match
                                    print(f"DEBUG - capture_callback - Found matching file with glob pattern: {pattern}")
                            
                            if os.path.exists(pattern):
                                print(f"DEBUG - capture_callback - Found audio file with alternative pattern: {pattern}")
                                try:
                                    shutil.copy2(pattern, id_based_audio_path)
                                    print(f"DEBUG - capture_callback - Copied audio file to Docker ID-based path: {id_based_audio_path}")
                                    
                                    # Save the audio file path in the database
                                    print(f"DEBUG - capture_callback - Saving audio file path: {id_based_audio_path}")
                                    if hasattr(db_capture, 'audio_file_path'):
                                        db_capture.audio_file_path = id_based_audio_path
                                        self.log_capture(db, db_capture.id, "info", f"Audio file saved: {id_based_audio_path}")
                                    else:
                                        print(f"WARNING - capture_callback - CaptureSession model does not have audio_file_path attribute")
                                    break
                                except Exception as e:
                                    print(f"ERROR - capture_callback - Failed to copy audio file: {str(e)}")
                        else:
                            # If no audio file was found, try to extract audio from the video file
                            print(f"DEBUG - capture_callback - Attempting to extract audio from video file: {output_file}")
                            try:
                                # Make sure the audio_extracts directory exists
                                audio_extracts_dir = "/app/data/temp/audio_extracts"
                                os.makedirs(audio_extracts_dir, exist_ok=True)
                                print(f"DEBUG - capture_callback - Created audio extracts directory: {audio_extracts_dir}")
                                
                                # Create an ID-based audio file name
                                id_based_audio_path = os.path.join(audio_extracts_dir, f"capture_{capture_id}_audio.mp3")
                                print(f"DEBUG - capture_callback - ID-based audio path: {id_based_audio_path}")
                                
                                # Extract audio using ffmpeg
                                cmd = [
                                    "ffmpeg", "-y", "-i", output_file, "-vn", "-acodec", "libmp3lame", "-ab", "192k",
                                    "-ar", "44100", id_based_audio_path
                                ]
                                print(f"DEBUG - capture_callback - Running ffmpeg command: {' '.join(cmd)}")
                                result = subprocess.run(cmd, capture_output=True, text=True)
                                
                                if result.returncode == 0 and os.path.exists(id_based_audio_path):
                                    print(f"DEBUG - capture_callback - Successfully extracted audio to: {id_based_audio_path}")
                                    # Save the audio file path in the database
                                    if hasattr(db_capture, 'audio_file_path'):
                                        db_capture.audio_file_path = id_based_audio_path
                                        self.log_capture(db, db_capture.id, "info", f"Audio extracted from video: {id_based_audio_path}")
                                    else:
                                        print(f"WARNING - capture_callback - CaptureSession model does not have audio_file_path attribute")
                                else:
                                    print(f"WARNING - capture_callback - Failed to extract audio from video: {result.stderr}")
                                    self.log_capture(db, db_capture.id, "warning", "Failed to extract audio from video")
                            except Exception as e:
                                print(f"ERROR - capture_callback - Failed to extract audio from video: {str(e)}")
                                self.log_capture(db, db_capture.id, "warning", f"Failed to extract audio: {str(e)}")
                else:
                    print(f"WARNING - capture_callback - Output file does not exist: {output_file}")
                    self.log_capture(db, db_capture.id, "warning", "Output file does not exist")
        
            # Commit the changes to the database
            db.commit()
            print(f"DEBUG - capture_callback - Database updated for capture {capture_id}")
        
        except Exception as e:
            print(f"ERROR - capture_callback - Failed to update database: {str(e)}")
            import traceback
            print(f"ERROR - capture_callback - Traceback: {traceback.format_exc()}")
    
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
            
            # If script doesn't exist in scripts_dir, try to find it elsewhere
            if not os.path.exists(script_path):
                print(f"DEBUG - extract_stream_url - Script not found at {script_path}, searching in other locations")
                # Try all possible locations for the script
                alt_paths = [
                    "/app/scripts/extract-url.py",
                    "/app/backend/scripts/extract-url.py",
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
            else:
                print(f"DEBUG - extract_stream_url - Using Python executable: {python_executable}")
            
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
    
    def download_stream(self, stream_url: str, output_path: str, duration: int = 1800) -> Dict:
        """Download a stream using ffmpeg."""
        try:
            print(f"DEBUG - download_stream - Downloading stream: {stream_url} to {output_path} for {duration} seconds")
            
            # Validate inputs
            if not stream_url:
                print("ERROR - download_stream - stream_url is empty")
                return {"success": False, "error": "Stream URL is empty"}
            
            if not output_path:
                print("ERROR - download_stream - output_path is empty")
                return {"success": False, "error": "Output path is empty"}
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Create audio_extracts directory if it doesn't exist
            audio_extracts_dir = os.path.join("/app/data/temp", "audio_extracts")
            os.makedirs(audio_extracts_dir, exist_ok=True)
            print(f"DEBUG - download_stream - Created audio_extracts directory: {audio_extracts_dir}")
            
            # Extract capture ID from output path filename
            capture_id = "unknown"
            try:
                filename = os.path.basename(output_path)
                parts = filename.split('_')
                if len(parts) > 1 and parts[1].isdigit():
                    capture_id = parts[1]
                else:
                    capture_id = 'unknown'
            except Exception as e:
                print(f"ERROR - download_stream - Failed to extract capture ID: {str(e)}")
                capture_id = 'unknown'
            
            print(f"DEBUG - download_stream - Extracted capture_id: {capture_id}")
            
            # Initialize variables
            has_audio = False
            main_url = None
            audio_url = None
            
            # Create an ID-based audio file path with the correct format
            # Format should be: capture_XXXX.audio.mp3 where XXXX is the zero-padded capture ID
            padded_capture_id = capture_id.zfill(4) if capture_id.isdigit() else capture_id
            audio_file_path = os.path.join(audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
            print(f"DEBUG - download_stream - Audio file path: {audio_file_path}")
            
            # Determine the video and audio URLs
            if isinstance(stream_url, dict):
                # Handle dictionary input (from extract_stream_url)
                if 'video_url' in stream_url and stream_url.get('video_url'):
                    # We have separate video and audio URLs
                    print(f"DEBUG - download_stream - Using separate video and audio URLs")
                    main_url = stream_url.get('video_url')
                    audio_url = stream_url.get('audio_url')
                elif 'direct_stream' in stream_url:
                    # We have a direct stream URL
                    direct_stream = stream_url.get('direct_stream')
                    if isinstance(direct_stream, dict):
                        # Dictionary with separate video and audio URLs
                        main_url = direct_stream.get('video_url')
                        audio_url = direct_stream.get('audio_url')
                    else:
                        # Single URL for video
                        main_url = direct_stream
                elif 'original_url' in stream_url:
                    # We have an original URL, need to extract stream info
                    original_url = stream_url.get('original_url')
                    print(f"DEBUG - download_stream - Using original URL: {original_url}")
                    
                    # Extract stream info using extract-url.py
                    script_path = os.path.join(self.scripts_dir, "extract-url.py")
                    if os.path.exists(script_path):
                        print(f"DEBUG - download_stream - Using extract-url.py at: {script_path}")
                        extract_cmd = [sys.executable, script_path, original_url]
                        print(f"DEBUG - download_stream - Running extract-url.py: {' '.join(extract_cmd)}")
                        extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
                        
                        if extract_result.returncode == 0:
                            try:
                                stream_info = json.loads(extract_result.stdout)
                                print(f"DEBUG - download_stream - Parsed stream info: {stream_info}")
                                
                                direct_stream = stream_info.get('direct_stream')
                                if isinstance(direct_stream, dict):
                                    # Dictionary with separate video and audio URLs
                                    main_url = direct_stream.get('video_url')
                                    audio_url = direct_stream.get('audio_url')
                                else:
                                    # Single URL for video
                                    main_url = direct_stream
                            except json.JSONDecodeError as e:
                                print(f"ERROR - download_stream - Failed to parse JSON output: {str(e)}")
                        else:
                            print(f"ERROR - download_stream - extract-url.py failed with return code {extract_result.returncode}")
                    else:
                        print(f"ERROR - download_stream - extract-url.py not found at: {script_path}")
            else:
                # Single URL string
                main_url = stream_url
            
            # If we don't have an audio URL but have a video URL, try to derive the audio URL
            if not audio_url and main_url and isinstance(main_url, str):
                if 'video=' in main_url:
                    # Parliament TV format: replace video= with audio_eng=
                    audio_url = main_url.replace('video=', 'audio_eng=')
                    # Make sure we have the right audio format and bitrate
                    audio_url = audio_url.replace('3000000', '64000')
                    print(f"DEBUG - download_stream - Derived audio URL from video URL: {audio_url}")
                elif 'vod-idx-video=' in main_url:
                    # Parliament TV format: vod-idx-video=3000000.m3u8 -> vod-idx-audio_eng=64000.m3u8
                    audio_url = main_url.replace('vod-idx-video=', 'vod-idx-audio_eng=')
                    # Make sure we have the right audio bitrate
                    audio_url = audio_url.replace('3000000', '64000')
                    print(f"DEBUG - download_stream - Derived audio URL from Parliament TV URL: {audio_url}")
                elif 'parliamentlive.tv' in main_url or 'www.parliamentlive.tv' in main_url:
                    # Try to extract stream info using extract-url.py
                    script_path = os.path.join(self.scripts_dir, "extract-url.py")
                    if os.path.exists(script_path):
                        extract_cmd = [sys.executable, script_path, main_url]
                        extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
                        
                        if extract_result.returncode == 0:
                            try:
                                stream_info = json.loads(extract_result.stdout)
                                direct_stream = stream_info.get('direct_stream')
                                if isinstance(direct_stream, dict) and 'audio_url' in direct_stream:
                                    audio_url = direct_stream.get('audio_url')
                                    print(f"DEBUG - download_stream - Found audio URL from extract-url.py: {audio_url}")
                            except json.JSONDecodeError:
                                pass
            
            # Ensure main_url is valid
            if not main_url:
                print("ERROR - download_stream - No valid video URL found")
                return {"success": False, "error": "No valid video URL found"}
            
            # Download audio if available
            if audio_url:
                print(f"DEBUG - download_stream - Downloading audio from: {audio_url}")
                audio_cmd = [
                    "ffmpeg", "-y",
                    "-i", audio_url,
                    "-vn",  # No video
                    "-acodec", "libmp3lame",
                    "-ab", "128k",
                    "-ar", "44100",
                    "-f", "mp3",
                    "-t", str(duration),
                    audio_file_path
                ]
                print(f"DEBUG - download_stream - Audio command: {' '.join(audio_cmd)}")
                audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
                
                if audio_result.returncode == 0 and os.path.exists(audio_file_path) and os.path.getsize(audio_file_path) > 0:
                    print(f"DEBUG - download_stream - Successfully downloaded audio to: {audio_file_path}")
                    has_audio = True
                    
                    # No need to create a separate copy since we're already using the correct naming convention
                    # The audio file is already at the expected path: /app/data/temp/audio_extracts/capture_XXXX.audio.mp3
                    # Just log that we have the audio file at the correct location
                    print(f"DEBUG - download_stream - Audio file is at the correct path: {audio_file_path}")
                else:
                    print(f"ERROR - download_stream - Failed to download audio: {audio_result.stderr}")
            
            # Download the video
            print(f"DEBUG - download_stream - Downloading video from: {main_url}")
            video_cmd = [
                "ffmpeg", "-y",
                "-i", main_url,
                "-c:v", "copy",  # Copy video codec
                "-an",  # No audio - we download it separately
                "-t", str(duration),
                output_path
            ]
            print(f"DEBUG - download_stream - Video command: {' '.join(video_cmd)}")
            video_result = subprocess.run(video_cmd, capture_output=True, text=True)
            
            if video_result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"DEBUG - download_stream - Successfully downloaded video to: {output_path}")
                
                # Return success with audio info
                return {
                    "success": True,
                    "output_file": output_path,
                    "has_audio": has_audio,
                    "audio_file_path": audio_file_path if has_audio else None
                }
            else:
                print(f"ERROR - download_stream - Failed to download video: {video_result.stderr}")
                return {"success": False, "error": f"Failed to download video: {video_result.stderr}"}
            
        except Exception as e:
            print(f"ERROR - download_stream - Unexpected error: {str(e)}")
            import traceback
            print(f"ERROR - download_stream - Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

        except Exception as e:
            print(f"ERROR - download_stream - Unexpected error: {str(e)}")
            import traceback
            print(f"ERROR - download_stream - Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def stop_capture(self, capture_id: int) -> Dict:
        """Stop a running capture."""
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
            
            # Update the capture status
            db_capture.status = "stopped"
            db_capture.stopped_at = datetime.now()
            db.commit()
            
            # Log the stop
            self.log_capture(db, capture_id, "info", "Capture stopped by user")
            
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
