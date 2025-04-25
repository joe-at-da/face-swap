import os
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import subprocess

from backend.core.config import settings

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH)
        self.media_dir = Path(settings.MEDIA_STORAGE_PATH)
        self.archive_dir = Path(settings.MEDIA_STORAGE_PATH) / "archive"
        self.backup_dir = Path(settings.MEDIA_STORAGE_PATH) / "backup"
        
        # Storage quotas in bytes (default: 10GB for media, 2GB for temp)
        self.media_quota = getattr(settings, "MEDIA_STORAGE_QUOTA", 10 * 1024 * 1024 * 1024)
        self.temp_quota = getattr(settings, "TEMP_STORAGE_QUOTA", 2 * 1024 * 1024 * 1024)
        
        # Create directories if they don't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    def get_storage_stats(self) -> Dict:
        """Get detailed storage usage statistics."""
        temp_size = sum(f.stat().st_size for f in self.temp_dir.glob('**/*') if f.is_file())
        media_size = sum(f.stat().st_size for f in self.media_dir.glob('**/*') if f.is_file())
        archive_size = sum(f.stat().st_size for f in self.archive_dir.glob('**/*') if f.is_file())
        backup_size = sum(f.stat().st_size for f in self.backup_dir.glob('**/*') if f.is_file())
        
        temp_files = list(self.temp_dir.glob('*'))
        media_files = list(self.media_dir.glob('*'))
        archive_files = list(self.archive_dir.glob('*'))
        backup_files = list(self.backup_dir.glob('*'))
        
        # Calculate quota usage percentages
        temp_quota_pct = (temp_size / self.temp_quota) * 100 if self.temp_quota > 0 else 0
        media_quota_pct = (media_size / self.media_quota) * 100 if self.media_quota > 0 else 0
        
        return {
            'temp_storage_bytes': temp_size,
            'media_storage_bytes': media_size,
            'archive_storage_bytes': archive_size,
            'backup_storage_bytes': backup_size,
            'total_storage_bytes': temp_size + media_size + archive_size + backup_size,
            'temp_files_count': len(temp_files),
            'media_files_count': len(media_files),
            'archive_files_count': len(archive_files),
            'backup_files_count': len(backup_files),
            'temp_quota_percentage': round(temp_quota_pct, 2),
            'media_quota_percentage': round(media_quota_pct, 2),
            'temp_quota_bytes': self.temp_quota,
            'media_quota_bytes': self.media_quota
        }
        
    def compress_video(self, video_path: str, quality: str = "medium") -> str:
        """
        Compress a video file to reduce storage size.
        
        Args:
            video_path: Path to the video file
            quality: Compression quality ('low', 'medium', 'high')
            
        Returns:
            Path to the compressed video file
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Define compression settings based on quality
        settings = {
            "low": {"crf": "28", "preset": "veryfast"},
            "medium": {"crf": "23", "preset": "medium"},
            "high": {"crf": "18", "preset": "slow"}
        }
        
        # Use settings for the requested quality or default to medium
        compression = settings.get(quality, settings["medium"])
        
        # Create output filename
        output_file = video_path.with_stem(f"{video_path.stem}_compressed")
        
        try:
            # Use ffmpeg for compression
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-c:v", "libx264", "-crf", compression["crf"],
                "-preset", compression["preset"],
                "-c:a", "aac", "-b:a", "128k",
                "-y", str(output_file)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Compressed {video_path} to {output_file}")
            return str(output_file)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to compress video: {e.stderr.decode() if e.stderr else str(e)}")
            raise
            
    def archive_old_media(self, max_age_days: int = 90) -> List[str]:
        """
        Archive media files older than max_age_days to the archive directory.
        
        Args:
            max_age_days: Maximum age in days before archiving
            
        Returns:
            List of archived file paths
        """
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        archived_files = []
        
        for file_path in self.media_dir.glob("**/*"):
            # Skip directories and non-media files
            if not file_path.is_file() or file_path.suffix.lower() not in [".mp4", ".mov", ".avi", ".webm"]:
                continue
                
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if mtime < cutoff_time:
                    # Create archive path with same relative structure
                    rel_path = file_path.relative_to(self.media_dir)
                    archive_path = self.archive_dir / rel_path
                    
                    # Create parent directories if needed
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move file to archive
                    shutil.move(str(file_path), str(archive_path))
                    logger.info(f"Archived old media file: {file_path} -> {archive_path}")
                    archived_files.append(str(archive_path))
                    
            except Exception as e:
                logger.error(f"Failed to archive {file_path}: {str(e)}")
                
        return archived_files
        
    def enforce_storage_quotas(self) -> Dict:
        """
        Enforce storage quotas by removing oldest temporary files if needed.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = self.get_storage_stats()
        cleanup_stats = {"temp_files_removed": 0, "temp_bytes_freed": 0}
        
        # Check if temp storage exceeds quota
        if stats["temp_storage_bytes"] > self.temp_quota:
            # Get all temp files with their modification times
            temp_files = []
            for file_path in self.temp_dir.glob("**/*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    size = file_path.stat().st_size
                    temp_files.append((file_path, mtime, size))
            
            # Sort by modification time (oldest first)
            temp_files.sort(key=lambda x: x[1])
            
            # Remove oldest files until under quota
            bytes_to_free = stats["temp_storage_bytes"] - (self.temp_quota * 0.9)  # Free to 90% of quota
            bytes_freed = 0
            
            for file_path, _, size in temp_files:
                if bytes_freed >= bytes_to_free:
                    break
                    
                try:
                    file_path.unlink()
                    bytes_freed += size
                    cleanup_stats["temp_files_removed"] += 1
                    cleanup_stats["temp_bytes_freed"] += size
                    logger.info(f"Removed temp file to enforce quota: {file_path} ({size} bytes)")
                except Exception as e:
                    logger.error(f"Failed to remove temp file {file_path}: {str(e)}")
        
        return cleanup_stats
        
    def create_backup(self, include_media: bool = False) -> str:
        """
        Create a backup of important data.
        
        Args:
            include_media: Whether to include media files in the backup
            
        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.tar.gz"
        
        # Create temporary directory for backup contents
        temp_backup_dir = self.temp_dir / f"backup_{timestamp}"
        temp_backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy database dumps or other important data here
            # This is a placeholder for actual backup logic
            
            # Include media files if requested
            if include_media:
                media_backup_dir = temp_backup_dir / "media"
                media_backup_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy media files (limit to recent ones to avoid huge backups)
                recent_cutoff = datetime.now() - timedelta(days=7)  # Last 7 days
                for file_path in self.media_dir.glob("**/*"):
                    if file_path.is_file():
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if mtime >= recent_cutoff:
                            rel_path = file_path.relative_to(self.media_dir)
                            dest_path = media_backup_dir / rel_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(file_path), str(dest_path))
            
            # Create tar archive
            cmd = ["tar", "-czf", str(backup_file), "-C", str(temp_backup_dir.parent), temp_backup_dir.name]
            subprocess.run(cmd, check=True, capture_output=True)
            
            logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            raise
            
        finally:
            # Clean up temporary directory
            if temp_backup_dir.exists():
                shutil.rmtree(str(temp_backup_dir))
