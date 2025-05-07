import logging
import time
from pathlib import Path
from typing import Dict, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from backend.core.celery_app import celery_app
from backend.db.database import SessionLocal
from backend.db import models
from backend.services.video.transcription import TranscriptionService

logger = logging.getLogger(__name__)

@shared_task
def transcribe_parliament_capture(
    capture_id: int, 
    transcription_id: int, 
    language: str = "en", 
    model_size: str = "base"
):
    """
    Celery task to transcribe a Parliament TV capture.
    
    Args:
        capture_id: ID of the capture session
        transcription_id: ID of the transcription record
        language: Language code for transcription
        model_size: Size of the Whisper model to use
    """
    db = SessionLocal()
    start_time = time.time()
    logger.info(f"Starting Parliament TV transcription task for capture {capture_id} with language {language}")
    
    try:
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture session not found: {capture_id}")
            return {"status": "failed", "error": "Capture session not found"}
            
        # Get the transcription record
        transcription = db.query(models.ParliamentTranscription).filter(
            models.ParliamentTranscription.id == transcription_id
        ).first()
        
        if not transcription:
            logger.error(f"Transcription record not found: {transcription_id}")
            return {"status": "failed", "error": "Transcription record not found"}
        
        # Check if audio file exists
        audio_path = capture.audio_file_path
        if not audio_path or not Path(audio_path).exists():
            error_msg = f"Audio file not found for capture {capture_id}"
            logger.error(error_msg)
            
            # Update transcription record with error
            transcription.status = "failed"
            transcription.error_message = error_msg
            db.commit()
            
            return {"status": "failed", "error": error_msg}
        
        # Check for speaker identification data
        speaker_data = None
        speaker_id = db.query(models.SpeakerIdentification).filter(
            models.SpeakerIdentification.capture_id == capture_id,
            models.SpeakerIdentification.status == "completed"
        ).first()
        
        if speaker_id and speaker_id.results:
            logger.info(f"Found speaker identification data for capture {capture_id}")
            speaker_data = speaker_id.results
        
        # Perform transcription
        service = TranscriptionService(model_size=model_size)
        result = service.transcribe_video(
            str(audio_path), 
            language=language,
            speaker_data=speaker_data
        )
        
        # Update transcription record
        transcription.text = result["text"]
        transcription.segments = result["segments"]
        transcription.status = "ready"
        transcription.output_file_path = result.get("source_file")
        db.commit()
        
        # Calculate duration
        elapsed_time = time.time() - start_time
        logger.info(f"Successfully transcribed Parliament TV capture {capture_id} in {elapsed_time:.2f} seconds")
        
        # Update metadata in capture session
        if not capture.metadata:
            capture.metadata = {}
        
        capture.metadata["transcription"] = {
            "id": transcription.id,
            "language": language,
            "duration": elapsed_time,
            "segments_count": len(result["segments"]),
            "has_speaker_data": speaker_data is not None,
            "model": model_size
        }
        db.commit()
        
        return {
            "status": "success", 
            "transcription_id": transcription.id,
            "duration": elapsed_time,
            "segments_count": len(result["segments"]),
            "has_speaker_data": speaker_data is not None
        }
        
    except Exception as e:
        logger.error(f"Failed to transcribe Parliament TV capture {capture_id}: {str(e)}")
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
