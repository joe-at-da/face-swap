"""
Celery tasks for recognition processing (voice and facial).
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from backend.db.session import SessionLocal
from backend.db import models
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Import celery app
try:
    from backend.services.celery_app import celery_app
except ImportError:
    # Mock celery for development without Celery
    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                wrapper.delay = lambda *args, **kwargs: func(*args, **kwargs)
                return wrapper
            return decorator
    celery_app = MockCelery()

@celery_app.task(name="process_video_with_facial_recognition")
def process_video_with_facial_recognition(capture_id: int) -> Dict[str, Any]:
    """
    Process a video with facial recognition to detect and identify speakers.
    
    Args:
        capture_id: ID of the capture session to process
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting facial recognition processing for capture: {capture_id}")
    
    # Initialize services
    facial_recognition = FacialRecognitionService()
    face_profile_service = FaceProfileService()
    multimodal_service = MultimodalRecognitionService()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Get the capture session
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture session not found: {capture_id}")
            return {"success": False, "error": f"Capture session not found: {capture_id}"}
        
        # Check if the video file exists
        video_path = capture.file_path
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            
            # Update metadata with error
            metadata = capture.metadata or {}
            metadata["facial_recognition_status"] = "failed"
            metadata["facial_recognition_error"] = "Video file not found"
            capture.metadata = metadata
            db.commit()
            
            return {"success": False, "error": "Video file not found"}
        
        # Check if transcription exists
        if not capture.transcription_results:
            logger.warning(f"No transcription results found for capture: {capture_id}")
            
            # Try to find a transcription record
            transcription = db.query(models.ParliamentTranscription).filter(
                models.ParliamentTranscription.capture_id == capture_id,
                models.ParliamentTranscription.status == "ready"
            ).first()
            
            if transcription and transcription.segments:
                logger.info(f"Found transcription record for capture: {capture_id}")
                # Use the transcription record
                capture.transcription_results = transcription.segments
                db.commit()
            else:
                # Update metadata with error
                metadata = capture.metadata or {}
                metadata["facial_recognition_status"] = "failed"
                metadata["facial_recognition_error"] = "No transcription results found"
                capture.metadata = metadata
                db.commit()
                
                return {"success": False, "error": "No transcription results found"}
        
        # Process the video with multimodal recognition
        logger.info(f"Processing video with multimodal recognition: {capture_id}")
        results = multimodal_service.process_video_with_transcription(db=db, video_id=capture_id)
        
        if not results["success"]:
            logger.error(f"Error in multimodal processing: {results.get('error', 'Unknown error')}")
            
            # Update metadata with error
            metadata = capture.metadata or {}
            metadata["facial_recognition_status"] = "failed"
            metadata["facial_recognition_error"] = results.get("error", "Unknown error")
            capture.metadata = metadata
            db.commit()
            
            return {"success": False, "error": results.get("error", "Unknown error")}
        
        # Update metadata with results
        metadata = capture.metadata or {}
        metadata["facial_recognition_status"] = "completed"
        metadata["facial_recognition_completed_at"] = datetime.now().isoformat()
        metadata["facial_recognition_results"] = make_json_serializable(results)
        capture.metadata = metadata
        db.commit()
        
        logger.info(f"Facial recognition processing completed for capture: {capture_id}")
        
        return {
            "success": True,
            "capture_id": capture_id,
            "message": "Facial recognition processing completed",
            "results": results
        }
    except Exception as e:
        logger.exception(f"Error processing video with facial recognition: {str(e)}")
        
        try:
            # Update metadata with error
            metadata = capture.metadata or {}
            metadata["facial_recognition_status"] = "failed"
            metadata["facial_recognition_error"] = str(e)
            capture.metadata = metadata
            db.commit()
        except Exception as db_error:
            logger.error(f"Error updating metadata: {str(db_error)}")
        
        return {"success": False, "error": str(e)}
    finally:
        # Close the database session
        db.close()

@celery_app.task(name="link_voice_and_face_profiles")
def link_voice_and_face_profiles(voice_profile_id: int, face_profile_id: int) -> Dict[str, Any]:
    """
    Link a voice profile with a face profile.
    
    Args:
        voice_profile_id: ID of the voice profile
        face_profile_id: ID of the face profile
        
    Returns:
        Dictionary with linking results
    """
    logger.info(f"Linking voice profile {voice_profile_id} with face profile {face_profile_id}")
    
    # Initialize services
    face_profile_service = FaceProfileService()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Link the profiles
        success = face_profile_service.link_face_to_voice_profile(
            db=db,
            face_profile_id=face_profile_id,
            voice_profile_id=voice_profile_id
        )
        
        if not success:
            logger.error(f"Failed to link profiles: {voice_profile_id} and {face_profile_id}")
            return {"success": False, "error": "Failed to link profiles"}
        
        logger.info(f"Successfully linked voice profile {voice_profile_id} with face profile {face_profile_id}")
        
        return {
            "success": True,
            "voice_profile_id": voice_profile_id,
            "face_profile_id": face_profile_id,
            "message": "Profiles linked successfully"
        }
    except Exception as e:
        logger.exception(f"Error linking profiles: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        # Close the database session
        db.close()

@celery_app.task(name="extract_faces_from_video")
def extract_faces_from_video(video_id: int, interval: float = 1.0, min_confidence: float = 0.6) -> Dict[str, Any]:
    """
    Extract faces from a video file.
    
    Args:
        video_id: ID of the video to process
        interval: Interval in seconds between frame processing
        min_confidence: Minimum confidence score for face detection
        
    Returns:
        Dictionary with extraction results
    """
    logger.info(f"Extracting faces from video: {video_id}")
    
    # Initialize services
    face_profile_service = FaceProfileService()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return {"success": False, "error": f"Video not found: {video_id}"}
        
        # Check if the video file exists
        video_path = video.file_path
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": "Video file not found"}
        
        # Create output directory
        output_dir = f"/app/data/face_profiles/extracted/{video_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract faces
        results = face_profile_service.extract_faces_from_video(
            video_path=video_path,
            output_dir=output_dir,
            interval=interval,
            min_confidence=min_confidence
        )
        
        if not results["success"]:
            logger.error(f"Error extracting faces: {results.get('error', 'Unknown error')}")
            return {"success": False, "error": results.get("error", "Unknown error")}
        
        # Update metadata with results
        metadata = video.metadata or {}
        metadata["face_extraction"] = {
            "completed_at": datetime.now().isoformat(),
            "faces_found": results["faces_found"],
            "frames_processed": results["frames_processed"],
            "output_dir": results["output_dir"]
        }
        video.metadata = metadata
        db.commit()
        
        logger.info(f"Face extraction completed for video: {video_id}")
        
        return {
            "success": True,
            "video_id": video_id,
            "faces_found": results["faces_found"],
            "frames_processed": results["frames_processed"],
            "output_dir": results["output_dir"]
        }
    except Exception as e:
        logger.exception(f"Error extracting faces: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        # Close the database session
        db.close()
