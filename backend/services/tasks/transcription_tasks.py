from celery import shared_task
import logging
from pathlib import Path

from backend.services.video.transcription import TranscriptionService
from backend.db import models
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)

@shared_task
def transcribe_video_clip(clip_id: int, language: str = "en", model_size: str = "base"):
    """
    Celery task to transcribe a video clip.
    
    Args:
        clip_id: ID of the video clip to transcribe
        language: Language code for transcription
        model_size: Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
    """
    db = SessionLocal()
    start_time = time.time()
    logger.info(f"Starting transcription task for clip {clip_id} with language {language} and model {model_size}")
    
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
        
        # Check for speaker identification data
        speaker_data = None
        speaker_id = db.query(models.SpeakerIdentification).filter(
            models.SpeakerIdentification.video_clip_id == clip_id,
            models.SpeakerIdentification.status == "completed"
        ).first()
        
        if speaker_id and speaker_id.results:
            logger.info(f"Found speaker identification data for clip {clip_id}")
            speaker_data = speaker_id.results
        
        # Perform transcription
        service = TranscriptionService(model_size=model_size)
        result = service.transcribe_video(
            str(video_path), 
            language=language,
            speaker_data=speaker_data
        )
        
        # Update transcription record
        transcription.text = result["text"]
        transcription.segments = result["segments"]
        transcription.status = "ready"
        db.commit()
        
        # Calculate duration
        elapsed_time = time.time() - start_time
        logger.info(f"Successfully transcribed video clip {clip_id} in {elapsed_time:.2f} seconds")
        
        return {
            "status": "success", 
            "transcription_id": transcription.id,
            "duration": elapsed_time,
            "segments_count": len(result["segments"]),
            "has_speaker_data": speaker_data is not None
        }
        
    except Exception as e:
        logger.error(f"Failed to transcribe video clip {clip_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update transcription record with error
        if 'transcription' in locals() and transcription:
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
            
        return {"status": "failed", "error": str(e)}
        
    finally:
        db.close()
