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
        
        try:
            stream = ffmpeg.input(self.stream_url)
            stream = ffmpeg.output(stream, str(output_file), acodec='copy', vcodec='copy')
            
            self._current_process = ffmpeg.run_async(stream)
            logger.info(f"Started capture to {output_file}")
            return str(output_file)
            
        except ffmpeg.Error as e:
            logger.error(f"Failed to start capture: {e.stderr.decode() if e.stderr else str(e)}")
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
