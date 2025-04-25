from celery import shared_task
import logging
from datetime import datetime, timedelta

from backend.services.video.storage import StorageManager
from backend.db import models
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)

@shared_task
def cleanup_temp_storage(max_age_hours: int = 24):
    """
    Celery task to clean up temporary storage.
    
    Args:
        max_age_hours: Maximum age in hours before removing temporary files
    """
    try:
        storage = StorageManager()
        storage.cleanup_old_captures(max_age_hours=max_age_hours)
        
        # Enforce storage quotas
        quota_stats = storage.enforce_storage_quotas()
        
        logger.info(f"Temporary storage cleanup completed: {quota_stats}")
        return {"status": "success", "stats": quota_stats}
        
    except Exception as e:
        logger.error(f"Failed to clean up temporary storage: {str(e)}")
        return {"status": "failed", "error": str(e)}

@shared_task
def archive_old_media(max_age_days: int = 90):
    """
    Celery task to archive old media files.
    
    Args:
        max_age_days: Maximum age in days before archiving media files
    """
    try:
        storage = StorageManager()
        archived_files = storage.archive_old_media(max_age_days=max_age_days)
        
        logger.info(f"Archived {len(archived_files)} old media files")
        return {"status": "success", "archived_count": len(archived_files)}
        
    except Exception as e:
        logger.error(f"Failed to archive old media: {str(e)}")
        return {"status": "failed", "error": str(e)}

@shared_task
def compress_large_videos(min_size_mb: int = 500, quality: str = "medium"):
    """
    Celery task to compress large video files to save storage space.
    
    Args:
        min_size_mb: Minimum size in MB to consider a video for compression
        quality: Compression quality ('low', 'medium', 'high')
    """
    db = SessionLocal()
    try:
        storage = StorageManager()
        min_size_bytes = min_size_mb * 1024 * 1024
        
        # Get large video clips that haven't been compressed
        large_clips = db.query(models.VideoClip).filter(
            models.VideoClip.status == "ready",
            ~models.VideoClip.storage_path.contains("_compressed")
        ).all()
        
        compressed_count = 0
        bytes_saved = 0
        
        for clip in large_clips:
            try:
                # Check if file exists and is large enough
                if not clip.storage_path:
                    continue
                    
                # Get file size
                import os
                if not os.path.exists(clip.storage_path):
                    logger.warning(f"Video file not found: {clip.storage_path}")
                    continue
                    
                file_size = os.path.getsize(clip.storage_path)
                if file_size < min_size_bytes:
                    continue
                
                # Compress the video
                compressed_path = storage.compress_video(clip.storage_path, quality)
                compressed_size = os.path.getsize(compressed_path)
                
                # Calculate space savings
                saved = file_size - compressed_size
                
                # Only use compressed version if it's significantly smaller
                if saved > (file_size * 0.2):  # At least 20% smaller
                    # Update clip with new path
                    old_path = clip.storage_path
                    clip.storage_path = compressed_path
                    db.commit()
                    
                    # Remove original file
                    os.remove(old_path)
                    
                    compressed_count += 1
                    bytes_saved += saved
                    logger.info(f"Compressed video {clip.id}: saved {saved} bytes ({saved/1024/1024:.2f} MB)")
                else:
                    # Not worth keeping the compressed version
                    os.remove(compressed_path)
                    logger.info(f"Compression not efficient for {clip.id}, keeping original")
                    
            except Exception as e:
                logger.error(f"Failed to compress video {clip.id}: {str(e)}")
        
        return {
            "status": "success", 
            "compressed_count": compressed_count,
            "bytes_saved": bytes_saved,
            "mb_saved": bytes_saved / 1024 / 1024
        }
        
    except Exception as e:
        logger.error(f"Failed to compress large videos: {str(e)}")
        return {"status": "failed", "error": str(e)}
        
    finally:
        db.close()

@shared_task
def create_system_backup(include_media: bool = False):
    """
    Celery task to create a system backup.
    
    Args:
        include_media: Whether to include media files in the backup
    """
    try:
        storage = StorageManager()
        backup_path = storage.create_backup(include_media=include_media)
        
        logger.info(f"Created system backup: {backup_path}")
        return {"status": "success", "backup_path": backup_path}
        
    except Exception as e:
        logger.error(f"Failed to create system backup: {str(e)}")
        return {"status": "failed", "error": str(e)}
