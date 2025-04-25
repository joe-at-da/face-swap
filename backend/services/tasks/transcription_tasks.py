from celery import shared_task
import logging
from pathlib import Path

from backend.services.video.transcription import TranscriptionService
from backend.db import models
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)

@shared_task
def transcribe_video_clip(clip_id: int, language: str = "en"):
    """
    Celery task to transcribe a video clip.
    
    Args:
        clip_id: ID of the video clip to transcribe
        language: Language code for transcription
    """
    db = SessionLocal()
    try:
        # Get the video clip
        clip = db.query(models.VideoClip).filter(models.VideoClip.id == clip_id).first()
        if not clip:
            logger.error(f"Video clip not found: {clip_id}")
            return {"status": "failed", "error": "Video clip not found"}
            
        # Check if clip has a storage path
        if not clip.storage_path:
            logger.error(f"Video clip has no storage path: {clip_id}")
            return {"status": "failed", "error": "Video clip has no storage path"}
            
        # Check if file exists
        video_path = Path(clip.storage_path)
        if not video_path.exists():
            logger.error(f"Video file not found: {clip.storage_path}")
            return {"status": "failed", "error": "Video file not found"}
        
        # Create or get transcription record
        transcription = db.query(models.Transcription).filter(
            models.Transcription.video_clip_id == clip_id
        ).first()
        
        if not transcription:
            transcription = models.Transcription(
                video_clip_id=clip_id,
                language=language,
                status="processing"
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)
        elif transcription.status != "processing":
            # Update status to processing
            transcription.status = "processing"
            transcription.error_message = None
            db.commit()
        
        # Perform transcription
        service = TranscriptionService()
        result = service.transcribe_video(str(video_path), language)
        
        # Update transcription record
        transcription.text = result["text"]
        transcription.segments = result["segments"]
        transcription.status = "ready"
        db.commit()
        
        logger.info(f"Successfully transcribed video clip {clip_id}")
        return {"status": "success", "transcription_id": transcription.id}
        
    except Exception as e:
        logger.error(f"Failed to transcribe video clip {clip_id}: {str(e)}")
        
        # Update transcription record with error
        if 'transcription' in locals() and transcription:
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            
        return {"status": "failed", "error": str(e)}
        
    finally:
        db.close()
