import os
import logging
import signal
import subprocess
import atexit
import threading
import time
from datetime import datetime
from pathlib import Path

import ffmpeg

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Keep track of active processes with their capture IDs
active_processes = {}
# Format: {capture_id: process_object}

# Register a cleanup function to terminate all processes on exit
def cleanup_processes():
    for capture_id, proc in active_processes.items():
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
    active_processes.clear()

# Register the cleanup function
atexit.register(cleanup_processes)

class StreamCapture:
    def __init__(self, stream_url: str = None):
        # CRITICAL FIX: Handle None stream_url
        if stream_url is None:
            # Use a longer Parliament-style video for proper face recognition demo
            # This is a longer video (15+ minutes) suitable for Parliament face recognition
            self.stream_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
            print(f"WARNING - StreamCapture.__init__ - stream_url was None, using Parliament-style video: {self.stream_url}")
        else:
            self.stream_url = stream_url
            print(f"DEBUG - StreamCapture.__init__ - Using stream_url: {self.stream_url}")
        
        # CRITICAL FIX: Hard-code paths to ensure they're never None
        self.temp_dir = Path("/app/data/temp")
        print(f"DEBUG - StreamCapture.__init__ - Using hard-coded temp_dir: {self.temp_dir}")
        
        # Create directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG - StreamCapture.__init__ - temp_dir exists: {self.temp_dir.exists()}")
        
        self._current_process = None
        
    def start_capture(self, output_file: str = None, duration: int = 300, capture_id: int = None):
        """Start capturing the stream to a file."""
        if output_file is None:
            # If capture_id is provided, use it for the filename
            if capture_id is not None:
                # Format with leading zeros (e.g., 0001)
                padded_id = str(capture_id).zfill(4)
                output_file = self.temp_dir / f"capture_{padded_id}.mp4"
            else:
                # Generate a unique filename based on timestamp
                timestamp = int(time.time())
                output_file = self.temp_dir / f"capture_{timestamp}.mp4"
        else:
            # Ensure output_file is a Path object
            output_file = Path(output_file)
        
        # Ensure the output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build the ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", self.stream_url,
            # Add duration limit AFTER the input for limiting output duration
            "-t", str(duration),
            "-c", "copy",
            str(output_file)
        ]
        
        logger.info(f"Starting capture with command: {' '.join(cmd)}")
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store the current process
            self._current_process = process
            
            # Store in active_processes with capture_id as key
            if capture_id is not None:
                active_processes[capture_id] = process
                logger.info(f"Started capture process with PID {process.pid} for capture ID {capture_id}")
                
                # Start a timer to automatically stop the capture after the specified duration
                # Add a small buffer (5 seconds) to allow ffmpeg to finalize the file properly
                def auto_stop_capture():
                    logger.info(f"Auto-stop timer triggered for capture ID {capture_id} after {duration} seconds")
                    time.sleep(duration + 5)  # Wait for the duration plus a small buffer
                    if capture_id in active_processes and active_processes[capture_id].poll() is None:
                        logger.info(f"Auto-stopping capture ID {capture_id} after duration {duration} seconds")
                        self.stop_capture(capture_id)
                
                # Start the auto-stop timer in a separate thread
                auto_stop_thread = threading.Thread(target=auto_stop_capture)
                auto_stop_thread.daemon = True  # Thread will exit when main program exits
                auto_stop_thread.start()
                logger.info(f"Started auto-stop timer for capture ID {capture_id} with duration {duration} seconds")
            else:
                # For backward compatibility
                logger.warning(f"Started capture process with PID {process.pid} but no capture ID was provided")
            
            return str(output_file)
        except Exception as e:
            logger.error(f"Error starting capture: {str(e)}")
            raise
    
    def stop_capture(self, capture_id: int = None):
        """Stop the capture process for the given capture_id or the current process."""
        process_to_stop = None
        
        # If capture_id is provided, try to find the process in active_processes
        if capture_id is not None and capture_id in active_processes:
            process_to_stop = active_processes[capture_id]
            logger.info(f"Found process for capture ID {capture_id}")
        # Otherwise, use the current process of this instance
        elif self._current_process:
            process_to_stop = self._current_process
            logger.info("Using current process of this instance")
        else:
            # If we can't find the process in our tracking, try to find it by looking for ffmpeg processes
            # that match our capture ID pattern
            logger.warning(f"No tracked process found for capture ID {capture_id}, searching for ffmpeg processes")
            try:
                # Format the capture ID with leading zeros (e.g., 0001)
                if capture_id is not None:
                    padded_id = str(capture_id).zfill(4)
                    pattern = f"capture_{padded_id}"
                    
                    # Use ps to find ffmpeg processes containing the capture ID pattern
                    import subprocess
                    ps_cmd = ["ps", "-ef"]
                    ps_result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
                    
                    # Look for ffmpeg processes with this capture ID pattern
                    for line in ps_result.stdout.splitlines():
                        if pattern in line and "ffmpeg" in line:
                            # Extract PID (second column in ps output)
                            parts = line.split()
                            if len(parts) > 1:
                                try:
                                    pid = int(parts[1])
                                    logger.info(f"Found ffmpeg process with PID {pid} for capture ID {capture_id}")
                                    # Send SIGINT directly to this process
                                    os.kill(pid, signal.SIGINT)
                                    logger.info(f"Sent SIGINT to process {pid}")
                                    
                                    # Wait a moment to allow the process to finalize
                                    time.sleep(2)
                                    
                                    # Check if the process is still running
                                    try:
                                        os.kill(pid, 0)  # This will raise an exception if the process doesn't exist
                                        # Process still exists, try SIGTERM
                                        logger.warning(f"Process {pid} did not terminate with SIGINT, trying SIGTERM")
                                        os.kill(pid, signal.SIGTERM)
                                        time.sleep(1)
                                        
                                        # Check again
                                        try:
                                            os.kill(pid, 0)
                                            # Still exists, try SIGKILL
                                            logger.warning(f"Process {pid} did not terminate with SIGTERM, force killing")
                                            os.kill(pid, signal.SIGKILL)
                                        except OSError:
                                            logger.info(f"Process {pid} terminated with SIGTERM")
                                    except OSError:
                                        logger.info(f"Process {pid} terminated with SIGINT")
                                    
                                    return True
                                except ValueError:
                                    logger.warning(f"Could not parse PID from: {parts[1]}")
                                except ProcessLookupError:
                                    logger.warning(f"Process {pid} no longer exists")
                                except Exception as e:
                                    logger.error(f"Error killing process: {str(e)}")
                    
                    logger.warning(f"No ffmpeg processes found for pattern: {pattern}")
                    return False
            except Exception as e:
                logger.error(f"Error searching for ffmpeg processes: {str(e)}")
                return False
        
        if not process_to_stop:
            logger.warning(f"No process found to stop for capture ID {capture_id}")
            return False
        
        try:
            # First check if the process is still running
            if process_to_stop.poll() is None:
                logger.info(f"Process is still running, attempting to gracefully stop")
                
                # For ffmpeg, we need to send SIGINT (Ctrl+C) to allow it to finalize the MP4 file
                # This is critical for MP4 files to ensure the moov atom is written
                try:
                    # Send SIGINT (equivalent to Ctrl+C) which allows ffmpeg to finalize the file
                    os.kill(process_to_stop.pid, signal.SIGINT)
                    logger.info(f"Sent SIGINT to process {process_to_stop.pid}")
                    
                    # Wait with a longer timeout to allow ffmpeg to finalize the file
                    process_to_stop.wait(timeout=10)
                    logger.info("Process terminated gracefully with proper file finalization")
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate after SIGINT, try SIGTERM
                    logger.warning("Process did not terminate with SIGINT, trying SIGTERM")
                    process_to_stop.terminate()
                    
                    try:
                        # Wait with a short timeout
                        process_to_stop.wait(timeout=3)
                        logger.info("Process terminated with SIGTERM")
                    except subprocess.TimeoutExpired:
                        # If it still doesn't terminate, force kill as last resort
                        logger.warning("Process did not terminate with SIGTERM, force killing")
                        process_to_stop.kill()
                        
                        try:
                            # Wait again with a short timeout
                            process_to_stop.wait(timeout=2)
                            logger.info("Process killed successfully")
                        except subprocess.TimeoutExpired:
                            logger.error("Failed to kill process, it may be zombie")
                            # As a last resort, try to kill the process group
                            try:
                                os.killpg(os.getpgid(process_to_stop.pid), signal.SIGKILL)
                                logger.info(f"Killed process group for PID {process_to_stop.pid}")
                            except Exception as e:
                                logger.error(f"Failed to kill process group: {str(e)}")
            else:
                logger.info("Process was already terminated")
            
            # Remove from active processes dictionary
            if capture_id is not None and capture_id in active_processes:
                del active_processes[capture_id]
                logger.info(f"Removed process for capture ID {capture_id} from active processes")
            
            # Also check if it's the current process of this instance
            if process_to_stop == self._current_process:
                self._current_process = None
                logger.info("Cleared current process reference")
            
            logger.info("Stopped capture process successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping capture process: {str(e)}")
            return False
    
    def is_capturing(self) -> bool:
        """Check if currently capturing."""
        return self._current_process is not None and self._current_process.poll() is None
