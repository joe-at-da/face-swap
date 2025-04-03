import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

from backend.core.config import settings

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)
        self.media_dir = Path(settings.MEDIA_STORAGE_PATH)
        
        # Create directories if they don't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_old_captures(self, max_age_hours: int = 24):
        """Remove temporary capture files older than max_age_hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in self.temp_dir.glob("capture_*.mp4"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mtime < cutoff_time:
                    file_path.unlink()
                    logger.info(f"Removed old capture file: {file_path}")
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
    
    def move_to_permanent_storage(self, temp_path: str) -> str:
        """
        Move a file from temporary storage to permanent storage.
        Returns the new file path.
        """
        temp_path = Path(temp_path)
        if not temp_path.exists():
            raise FileNotFoundError(f"Source file not found: {temp_path}")
            
        # Create new filename in media directory
        new_path = self.media_dir / temp_path.name
        
        try:
            shutil.move(str(temp_path), str(new_path))
            logger.info(f"Moved {temp_path} to {new_path}")
            return str(new_path)
        except Exception as e:
            logger.error(f"Failed to move file {temp_path}: {str(e)}")
            raise
    
    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        temp_size = sum(f.stat().st_size for f in self.temp_dir.glob('**/*') if f.is_file())
        media_size = sum(f.stat().st_size for f in self.media_dir.glob('**/*') if f.is_file())
        
        return {
            'temp_storage_bytes': temp_size,
            'media_storage_bytes': media_size,
            'temp_files': len(list(self.temp_dir.glob('*'))),
            'media_files': len(list(self.media_dir.glob('*')))
        }
