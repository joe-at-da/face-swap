import os
import logging
import signal
import subprocess
import atexit
from datetime import datetime
from pathlib import Path

import ffmpeg

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Keep track of all active capture processes
active_processes = []

# Register a cleanup function to terminate all processes on exit
def cleanup_processes():
    for proc in active_processes:
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
    def __init__(self, stream_url: str = settings.PARLIAMENT_TV_URL):
        self.stream_url = stream_url
        
        # CRITICAL FIX: Hard-code paths to ensure they're never None
        self.temp_dir = Path("/app/data/temp")
        print(f"DEBUG - StreamCapture.__init__ - Using hard-coded temp_dir: {self.temp_dir}")
        
        # Create directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG - StreamCapture.__init__ - temp_dir exists: {self.temp_dir.exists()}")
        
        self._current_process = None
        
    def start_capture(self) -> str:
        """Start capturing the stream. Returns the output filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.temp_dir / f"capture_{timestamp}.mp4"
        
        # Add a timeout for the connection
        connection_timeout = 30  # seconds
        
        try:
            # Try to connect to the stream with a timeout
            logger.info(f"Attempting to connect to stream: {self.stream_url}")
            
            # Use a more robust ffmpeg command with error handling
            stream = ffmpeg.input(self.stream_url, timeout=connection_timeout)
            stream = ffmpeg.output(
                stream, 
                str(output_file), 
                acodec='copy', 
                vcodec='copy',
                f='mp4',  # Force mp4 format
                # Add error handling flags
                reconnect=1,
                reconnect_at_eof=1,
                reconnect_streamed=1,
                reconnect_delay_max=5
            )
            
            # Start the process
            self._current_process = ffmpeg.run_async(stream)
            
            # Add to global list of active processes
            active_processes.append(self._current_process)
            
            logger.info(f"Successfully started capture to {output_file}")
            return str(output_file)
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Failed to start capture: {error_message}")
            # Create a small log file to record the error
            error_log_file = self.temp_dir / f"error_log_{timestamp}.txt"
            with open(error_log_file, 'w') as f:
                f.write(f"Error capturing from {self.stream_url}: {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting capture: {str(e)}")
            raise
    
    def stop_capture(self):
        """Stop the current capture process."""
        if self._current_process:
            try:
                # First try to terminate gracefully
                if self._current_process.poll() is None:
                    self._current_process.terminate()
                    try:
                        # Wait with timeout to avoid hanging
                        self._current_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # If it doesn't terminate in time, force kill
                        self._current_process.kill()
                        self._current_process.wait()
                
                # Remove from active processes list
                if self._current_process in active_processes:
                    active_processes.remove(self._current_process)
                
                logger.info("Stopped capture process")
            except Exception as e:
                logger.error(f"Error stopping capture process: {str(e)}")
            finally:
                self._current_process = None
    
    def is_capturing(self) -> bool:
        """Check if currently capturing."""
        return self._current_process is not None and self._current_process.poll() is None
