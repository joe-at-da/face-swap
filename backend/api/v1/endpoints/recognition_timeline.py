"""
API endpoints for recognition timeline data combining face and voice recognition.
"""

import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
import logging
from typing import Optional, List, Dict, Any

from backend.db.session import get_db
from backend.db import models
from backend.api import deps
from backend.services.recognition.timeline_service import TimelineService
from backend.services.utils import make_json_serializable
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.recognition.facial_recognition import FacialRecognitionService

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the timeline service
timeline_service = TimelineService()

# Create router
router = APIRouter()

# Initialize services
multimodal_service = MultimodalRecognitionService()
facial_recognition = FacialRecognitionService()

@router.get("/{capture_id}")
def get_recognition_timeline(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Get the recognition timeline for a capture session."""
    logger.info(f"Getting recognition timeline for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id_int).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Check if timeline data exists in the capture session
        if capture.timeline_data:
            try:
                timeline_data = json.loads(capture.timeline_data)
                return timeline_data
            except json.JSONDecodeError:
                logger.error(f"Invalid timeline data JSON for capture {capture_id}")
        
        # If no timeline data exists, generate it from recognition events
        timeline_result = timeline_service.get_timeline_events(db, capture_id_int)
        
        # If no events exist, try to create timeline from legacy data
        if not timeline_result.get("success", False) or len(timeline_result.get("timeline", [])) == 0:
            # Check if recognition results exist in the old format
            if capture.recognition_results:
                try:
                    recognition_data = json.loads(capture.recognition_results)
                    
                    # Check if transcription results exist
                    transcription_data = None
                    if capture.transcription_results:
                        try:
                            transcription_data = json.loads(capture.transcription_results)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid transcription results JSON for capture {capture_id}")
                    
                    # Create timeline from recognition and transcription data
                    timeline = create_timeline(recognition_data, transcription_data)
                    
                    # Store the timeline data for future use
                    timeline_data = {
                        "success": True,
                        "video_id": capture_id,
                        "timeline": timeline
                    }
                    
                    # Update the timeline data in the capture session
                    capture.timeline_data = json.dumps(make_json_serializable(timeline_data))
                    db.commit()
                    
                    return timeline_data
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid recognition results JSON for capture {capture_id}")
            
            return {
                "success": False,
                "error": "No recognition data found for this capture session",
                "timeline": [],
                "correlations": []
            }
        
        # Update the timeline data in the capture session if it doesn't exist
        if not capture.timeline_data:
            capture.timeline_data = json.dumps(make_json_serializable(timeline_result))
            db.commit()
        
        return timeline_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition timeline: {str(e)}")


def create_timeline(recognition_data, transcription_data=None):
    """Create a timeline from recognition and transcription data."""
    timeline = []
    
    # Process face recognition data
    if "faces" in recognition_data:
        for face in recognition_data["faces"]:
            if "timestamp" in face and "name" in face:
                timeline.append({
                    "type": "face",
                    "start": face["timestamp"],
                    "end": face["timestamp"] + 1.0,  # Assume 1 second duration
                    "person_name": face["name"],
                    "confidence": face.get("confidence", 0.0),
                    "data": {
                        "box": face.get("box", None),
                        "face_id": face.get("face_id"),
                        "person_id": face.get("person_id")
                    }
                })
    
    # Process voice recognition data
    if "voices" in recognition_data:
        for voice in recognition_data["voices"]:
            if "start_time" in voice and "end_time" in voice and "speaker" in voice:
                timeline.append({
                    "type": "speaker",
                    "start": voice["start_time"],
                    "end": voice["end_time"],
                    "person_name": voice["speaker"],
                    "confidence": voice.get("confidence", 0.0),
                    "data": {
                        "speaker_id": voice.get("speaker_id"),
                        "person_id": voice.get("person_id")
                    }
                })
    
    # Process transcription data if available
    if transcription_data and "segments" in transcription_data:
        for segment in transcription_data["segments"]:
            if "start" in segment and "end" in segment and "text" in segment:
                speaker = segment.get("speaker", "Unknown")
                if not speaker and "speaker_id" in segment:
                    speaker = f"Speaker {segment['speaker_id']}"
                
                timeline.append({
                    "type": "transcript",
                    "start": segment["start"],
                    "end": segment["end"],
                    "person_name": speaker,
                    "data": {
                        "text": segment["text"],
                        "speaker_id": segment.get("speaker_id"),
                        "words": segment.get("words", [])
                    }
                })
    
    # Sort the timeline by start time
    timeline.sort(key=lambda x: x.get("start", 0))
    
    return timeline


def find_correlations(recognition_data):
    """Find correlations between face and voice recognition."""
    correlations = []
    
    # Check if both face and voice data exist
    if "faces" not in recognition_data or "voices" not in recognition_data:
        return correlations
    
    faces = recognition_data["faces"]
    voices = recognition_data["voices"]
    
    # For each voice segment, find faces that appear during that time
    for voice in voices:
        if "start_time" not in voice or "end_time" not in voice or "speaker" not in voice:
            continue
        
        voice_start = voice["start_time"]
        voice_end = voice["end_time"]
        voice_speaker = voice["speaker"]
        voice_id = voice.get("speaker_id") or voice.get("id")
        
        # Find faces that appear during this voice segment
        for face in faces:
            if "timestamp" not in face or "name" not in face:
                continue
            
            face_time = face["timestamp"]
            face_name = face["name"]
            face_id = face.get("face_id") or face.get("id")
            
            # Check if the face appears during the voice segment
            if voice_start <= face_time <= voice_end:
                # Check if they are the same person
                same_person = face_name.lower() == voice_speaker.lower()
                
                correlations.append({
                    "face_id": face_id,
                    "speaker_id": voice_id,
                    "face_name": face_name,
                    "speaker_name": voice_speaker,
                    "start": face_time,
                    "end": min(face_time + 1.0, voice_end),  # Assume max 1 second duration
                    "confidence": 0.8 if same_person else 0.5,
                    "same_person": same_person
                })
    
    return correlations


@router.get("/{capture_id}/correlations")
def get_recognition_correlations(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Get correlations between face and speaker events."""
    logger.info(f"Getting recognition correlations for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        # Get correlations from timeline service
        result = timeline_service.get_correlations(db, capture_id_int)
        
        if not result.get("success", False):
            return {
                "success": False,
                "error": result.get("error", "Failed to get correlations")
            }
        
        return {
            "success": True,
            "correlations": result.get("correlations", []),
            "face_count": result.get("face_count", 0),
            "speaker_count": result.get("speaker_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition correlations: {str(e)}")


@router.post("/{capture_id}/update-correlations")
def update_correlations(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Update correlations between face and speaker events using the enhanced algorithm.
    
    This endpoint triggers a full recalculation of correlations between face and voice recognition events
    using the enhanced correlation detection algorithm. The algorithm considers:
    
    1. Temporal overlap between face detections and speaker segments
    2. Name similarity between detected persons
    3. Explicit links between profiles
    4. Individual recognition confidence scores
    5. Extended time window for potential matches
    
    Returns updated correlations with detailed confidence metrics and correlation types.
    """
    logger.info(f"Updating correlations for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id_int).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Get the timeline data
        timeline_result = timeline_service.get_timeline_events(db, capture_id_int)
        
        if not timeline_result.get("success", False):
            return {
                "success": False,
                "error": "No timeline data found for this capture session"
            }
        
        # Get face and speaker events
        timeline_events = timeline_result.get("timeline", [])
        face_events = [event for event in timeline_events if event.get("type") == "face"]
        speaker_events = [event for event in timeline_events if event.get("type") == "speaker"]
        
        if not face_events or not speaker_events:
            return {
                "success": False,
                "error": "Insufficient data: Need both face and speaker events to find correlations"
            }
        
        # Find correlations using the enhanced algorithm
        correlations = timeline_service.find_correlations({
            "face_events": face_events,
            "speaker_events": speaker_events
        })
        
        # Update the correlations in the timeline data
        if timeline_result.get("timeline_id"):
            timeline_record = db.query(models.RecognitionTimeline).filter(
                models.RecognitionTimeline.id == timeline_result.get("timeline_id")
            ).first()
            
            if timeline_record:
                # Update the correlations field
                timeline_record.correlations = json.dumps(make_json_serializable(correlations))
                db.commit()
        
        return {
            "success": True,
            "message": "Correlations updated successfully",
            "correlations": correlations,
            "face_count": len(face_events),
            "speaker_count": len(speaker_events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating correlations: {str(e)}")


@router.post("/{capture_id}/correlations/update-confidence", response_model=Dict[str, Any])
def update_correlation_confidence(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Update correlation confidence scores with enhanced algorithm.
    
    This endpoint applies an improved confidence scoring algorithm to existing correlations between
    face and voice recognition events. The enhanced algorithm considers:
    
    1. Name similarity between face and voice profiles
    2. Explicit links between profiles
    3. Individual confidence scores from each recognition system
    4. Temporal overlap between events
    5. Various boosters and penalties based on recognition quality
    
    Returns updated correlations with detailed confidence metrics.
    """
    logger.info(f"Updating correlation confidence for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid capture ID")
        
        # Update the correlation confidence
        update_result = timeline_service.update_correlation_confidence(db, capture_id_int)
        
        if not update_result["success"]:
            raise HTTPException(status_code=400, detail=update_result.get("error", "Unknown error"))
        
        # Return the updated correlations
        return update_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating correlation confidence: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating correlation confidence: {str(e)}")


# The get_recognition_correlations endpoint is now implemented above using the timeline_service directly

'''  
# This code is commented out to avoid duplication
@router.get("/{capture_id}/correlations")
def get_recognition_correlations_old(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Get correlations between face and voice recognition."""
    logger.info(f"Getting recognition correlations for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id_int).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Use the timeline service to find correlations
        correlations_result = timeline_service.find_correlations(db, capture_id_int)
        
        # If no correlations found, try to find them from legacy data
        if not correlations_result.get("success", False) or len(correlations_result.get("correlations", [])) == 0:
            # Check if recognition results exist in the old format
            if capture.recognition_results:
                try:
                    recognition_data = json.loads(capture.recognition_results)
                    
                    # Find correlations between face and voice recognition
                    correlations = find_correlations(recognition_data)
                    
                    return {
                        "success": True,
                        "video_id": capture_id,
                        "correlations": correlations
                    }
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid recognition results JSON for capture {capture_id}")
            
            return {
                "success": False,
                "error": "No recognition data found for this capture session",
                "correlations": []
            }
        
        return correlations_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition correlations: {str(e)}")
'''


@router.post("/{capture_id}/update")
def update_recognition_timeline(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Update the recognition timeline for a capture session."""
    logger.info(f"Updating recognition timeline for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id_int).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Use the timeline service to update the timeline data
        update_result = timeline_service.update_timeline_data(db, capture_id_int)
        
        # If no timeline data exists, try to create it from legacy data
        if not update_result.get("success", False):
            # Check if recognition results exist in the old format
            if capture.recognition_results:
                try:
                    recognition_data = json.loads(capture.recognition_results)
                    
                    # Check if transcription results exist
                    transcription_data = None
                    if capture.transcription_results:
                        try:
                            transcription_data = json.loads(capture.transcription_results)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid transcription results JSON for capture {capture_id}")
                    
                    # Create timeline from recognition and transcription data
                    timeline = create_timeline(recognition_data, transcription_data)
                    
                    # Find correlations between face and voice recognition
                    correlations = find_correlations(recognition_data)
                    
                    # Combine timeline and correlations
                    result = {
                        "success": True,
                        "video_id": capture_id,
                        "timeline": timeline,
                        "correlations": correlations
                    }
                    
                    # Store the timeline data for future use
                    capture.timeline_data = json.dumps(make_json_serializable(result))
                    db.commit()
                    
                    return result
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid recognition results JSON for capture {capture_id}")
                    return {
                        "success": False,
                        "error": "Invalid recognition results format"
                    }
            
            return {
                "success": False,
                "error": "No recognition data found for this capture session"
            }
        
        return update_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating recognition timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating recognition timeline: {str(e)}")


@router.post("/{capture_id}/process")
def process_video_recognition(capture_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Process a video for face and voice recognition."""
    logger.info(f"Processing video recognition for capture: {capture_id}")
    
    try:
        # Get the capture session
        try:
            capture_id_int = int(capture_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid capture ID: {capture_id}")
        
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id_int).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Check if the video file exists
        if not capture.video_path:
            return {
                "success": False,
                "error": "No video file found for this capture session"
            }
        
        # Process the video for face recognition
        face_result = facial_recognition.identify_speakers(capture.video_path)
        
        if face_result.get("success", False):
            # Store the face detection results
            capture.face_detection_results = json.dumps(make_json_serializable(face_result))
            db.commit()
            
            # If we have transcription data, try to process with multimodal recognition
            if capture.transcription_results:
                multimodal_result = multimodal_service.process_video_with_transcription(db, capture_id_int)
                
                if multimodal_result.get("success", False):
                    # Update the timeline data
                    update_result = timeline_service.update_timeline_data(db, capture_id_int)
                    
                    return {
                        "success": True,
                        "message": "Video processed successfully with multimodal recognition",
                        "face_result": face_result,
                        "multimodal_result": multimodal_result,
                        "timeline": update_result.get("timeline", [])
                    }
            
            # Update the timeline data
            update_result = timeline_service.update_timeline_data(db, capture_id_int)
            
            return {
                "success": True,
                "message": "Video processed successfully with face recognition",
                "face_result": face_result,
                "timeline": update_result.get("timeline", [])
            }
        
        return {
            "success": False,
            "error": "Failed to process video for face recognition",
            "face_result": face_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing video recognition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing video recognition: {str(e)}")

