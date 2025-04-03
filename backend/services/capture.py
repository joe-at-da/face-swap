import os
import subprocess
from datetime import datetime
from typing import Optional

import ffmpeg

from backend.core.config import settings
from backend.core.logging import capture_logger as logger
from backend.db.models.capture import CaptureSession
from backend.services.storage import StorageManager

class CaptureService:
    def __init__(self):
        self.storage = StorageManager()
        self.current_process: Optional[subprocess.Popen] = None
        self.current_session: Optional[CaptureSession] = None

    async def start_capture(self, session: CaptureSession) -> bool:
        """
        Start capturing the Parliament TV stream.
        
        Args:
            session: The CaptureSession database model instance
        
        Returns:
            bool: True if capture started successfully, False otherwise
        """
        if self.current_process:
            logger.warning("Attempted to start capture while another capture is running")
            return False

        try:
            output_path = self.storage.get_temp_path(f"capture_{session.id}.mp4")
            logger.info(f"Starting capture to {output_path}")

            # Prepare FFmpeg command
            stream = ffmpeg.input(settings.PARLIAMENT_TV_URL)
            stream = ffmpeg.output(stream, output_path)
            
            # Start the FFmpeg process
            self.current_process = ffmpeg.run_async(
                stream,
                pipe_stdout=True,
                pipe_stderr=True
            )
            
            # Update session
            self.current_session = session
            session.file_path = output_path
            session.start_time = datetime.utcnow()
            
            logger.info(f"Capture started successfully for session {session.id}")
            return True

        except ffmpeg.Error as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting capture: {str(e)}")
            return False

    async def stop_capture(self) -> bool:
        """
        Stop the current capture session.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if not self.current_process:
            logger.warning("Attempted to stop capture but no capture is running")
            return False

        try:
            logger.info("Stopping capture process")
            self.current_process.terminate()
            self.current_process.wait(timeout=5)
            
            if self.current_session:
                self.current_session.end_time = datetime.utcnow()
                logger.info(f"Capture stopped for session {self.current_session.id}")

            self.current_process = None
            self.current_session = None
            return True

        except subprocess.TimeoutExpired:
            logger.error("Capture process did not terminate gracefully, forcing...")
            self.current_process.kill()
            return True
        except Exception as e:
            logger.error(f"Error stopping capture: {str(e)}")
            return False

    def get_status(self) -> dict:
        """
        Get the current capture status.
        
        Returns:
            dict: Status information including whether capture is running
                 and current session details if available
        """
        is_running = self.current_process is not None and self.current_process.poll() is None
        
        status = {
            "is_running": is_running,
            "current_session": None
        }

        if self.current_session:
            status["current_session"] = {
                "id": self.current_session.id,
                "start_time": self.current_session.start_time,
                "file_path": self.current_session.file_path
            }
            
            if not is_running and self.current_session.file_path:
                try:
                    size = os.path.getsize(self.current_session.file_path)
                    status["current_session"]["file_size"] = size
                except OSError as e:
                    logger.error(f"Error getting file size: {str(e)}")

        return status
