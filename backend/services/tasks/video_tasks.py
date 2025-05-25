from celery import shared_task
import logging
from datetime import datetime

from backend.services.video.capture import StreamCapture
from backend.services.video.processor import VideoProcessor
from backend.services.video.storage import StorageManager
from backend.db import models
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)

@shared_task
def start_stream_capture():
    """Start capturing the Parliament TV stream."""
    try:
        capture = StreamCapture()
        output_file = capture.start_capture()
        return {'status': 'started', 'output_file': output_file}
    except Exception as e:
        logger.error(f"Failed to start capture: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

@shared_task
def stop_stream_capture():
    """Stop the current stream capture."""
    try:
        capture = StreamCapture()
        capture.stop_capture()
        return {'status': 'stopped'}
    except Exception as e:
        logger.error(f"Failed to stop capture: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

@shared_task
def create_video_clip(source_file: str, clip_id: int, start_time: str, end_time: str):
    """Create a video clip from the source file."""
    db = SessionLocal()
    try:
        # Get clip from database
        clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip with id {clip_id} not found")
        
        # Update clip status
        clip.status = "PROCESSING"  # Use uppercase to match the enum
        db.commit()
        
        # Create clip
        processor = VideoProcessor()
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        
        output_file = processor.create_clip(source_file, start_dt, end_dt)
        
        # Move to permanent storage
        storage = StorageManager()
        final_path = storage.move_to_permanent_storage(output_file)
        
        # Update clip in database
        clip.storage_path = final_path
        clip.status = "READY"  # Use uppercase to match the enum
        db.commit()
        
        return {
            'status': 'success',
            'clip_id': clip_id,
            'output_file': final_path
        }
        
    except Exception as e:
        logger.error(f"Failed to create clip {clip_id}: {str(e)}")
        if clip:
            clip.status = "failed"
            clip.error_message = str(e)
            db.commit()
        return {'status': 'failed', 'error': str(e)}
        
    finally:
        db.close()

@shared_task
def cleanup_old_captures():
    """Clean up old capture files."""
    try:
        storage = StorageManager()
        storage.cleanup_old_captures()
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to cleanup captures: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
