import os
import logging
from datetime import datetime
import ffmpeg
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)

class StreamCapture:
    def __init__(self, stream_url: str = settings.PARLIAMENT_TV_URL):
        self.stream_url = stream_url
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
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
        if self._current_process and self._current_process.poll() is None:
            self._current_process.terminate()
            self._current_process.wait()
            logger.info("Stopped capture process")
            self._current_process = None
    
    def is_capturing(self) -> bool:
        """Check if currently capturing."""
        return self._current_process is not None and self._current_process.poll() is None
