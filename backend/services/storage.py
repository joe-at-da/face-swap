import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.core.config import settings
from backend.core.logging import storage_logger as logger

class StorageManager:
    def __init__(self):
        """Initialize storage paths and ensure they exist."""
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)
        self.media_dir = Path(settings.MEDIA_STORAGE_PATH)
        
        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Storage manager initialized with temp_dir={self.temp_dir}, media_dir={self.media_dir}")

    def get_temp_path(self, filename: str) -> str:
        """Get a path for a temporary file."""
        return str(self.temp_dir / filename)

    def get_media_path(self, filename: str) -> str:
        """Get a path for a permanent media file."""
        return str(self.media_dir / filename)

    def move_to_permanent(self, temp_path: str, permanent_filename: str) -> Optional[str]:
        """
        Move a file from temporary storage to permanent storage.
        
        Args:
            temp_path: Path to the temporary file
            permanent_filename: Desired filename in permanent storage
        
        Returns:
            str: Path to the permanent file if successful, None otherwise
        """
        try:
            if not os.path.exists(temp_path):
                logger.error(f"Temporary file not found: {temp_path}")
                return None

            permanent_path = self.get_media_path(permanent_filename)
            logger.info(f"Moving {temp_path} to {permanent_path}")
            
            shutil.move(temp_path, permanent_path)
            return permanent_path

        except Exception as e:
            logger.error(f"Error moving file to permanent storage: {str(e)}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from either temporary or permanent storage.
        
        Args:
            file_path: Path to the file to delete
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found for deletion: {file_path}")
                return False

            os.remove(file_path)
            logger.info(f"Successfully deleted file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

    def cleanup_old_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than the specified age.
        
        Args:
            max_age_hours: Maximum age of files in hours before deletion
        
        Returns:
            int: Number of files deleted
        """
        deleted_count = 0
        current_time = datetime.now()

        try:
            for file_path in self.temp_dir.glob("*"):
                if not file_path.is_file():
                    continue

                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() > max_age_hours * 3600:
                    if self.delete_file(str(file_path)):
                        deleted_count += 1

            logger.info(f"Cleanup completed. Deleted {deleted_count} old temporary files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during temporary file cleanup: {str(e)}")
            return deleted_count
