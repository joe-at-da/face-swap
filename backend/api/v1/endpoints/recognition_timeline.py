"""
API endpoints for recognition timeline data combining face and voice recognition.
"""

import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
multimodal_service = MultimodalRecognitionService()

@router.get("/{capture_id}", response_model=Dict[str, Any])
async def get_recognition_timeline(
    capture_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get timeline data combining face and voice recognition results.
    
    This endpoint provides a unified timeline view of:
    - Face detections with timestamps
    - Speaker segments with timestamps
    - Correlations between faces and voices
    """
    try:
        logger.info(f"Getting recognition timeline for capture: {capture_id}")
        
        # Get the capture from the database
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found: {capture_id}")
        
        # Initialize timeline data
        timeline_data = []
        
        # Get face recognition results
        face_results = {}
        if capture.recognition_results:
            try:
                face_results = json.loads(capture.recognition_results)
            except Exception as e:
                logger.error(f"Error parsing face recognition results: {str(e)}")
        
        # Get voice recognition results (from transcription with speaker diarization)
        voice_results = {}
        if capture.transcription_results:
            try:
                voice_results = json.loads(capture.transcription_results)
            except Exception as e:
                logger.error(f"Error parsing transcription results: {str(e)}")
        
        # Extract face detections
        faces = face_results.get("faces", [])
        
        # If no faces found but we have recognition results, try to extract from other formats
        if not faces and capture.status == "completed" and capture.recognition_results:
            try:
                # Try to parse recognition results to extract face data
                if isinstance(capture.recognition_results, str):
                    recognition_data = json.loads(capture.recognition_results)
                else:
                    recognition_data = capture.recognition_results
                
                # Check for speakers in recognition results
                speakers = recognition_data.get("speakers", [])
                for speaker in speakers:
                    if speaker.get("face_detections") or speaker.get("faceDetections"):
                        face_detections = speaker.get("face_detections") or speaker.get("faceDetections", [])
                        for detection in face_detections:
                            faces.append({
                                "id": detection.get("id", str(uuid.uuid4())),
                                "timestamp": detection.get("timestamp", 0),
                                "start_time": detection.get("start_time", detection.get("startTime", 0)),
                                "end_time": detection.get("end_time", detection.get("endTime", 0)),
                                "person_id": speaker.get("profile_id", speaker.get("profileId", None)),
                                "name": speaker.get("name", "Unknown Speaker"),
                                "filename": detection.get("filename", None)
                            })
                
                # Check for unidentified faces
                unidentified = recognition_data.get("unidentified_faces", recognition_data.get("unidentifiedFaces", []))
                for face in unidentified:
                    faces.append({
                        "id": face.get("id", str(uuid.uuid4())),
                        "timestamp": face.get("timestamp", 0),
                        "start_time": face.get("start_time", face.get("startTime", 0)),
                        "end_time": face.get("end_time", face.get("endTime", 0)),
                        "person_id": None,
                        "name": "Unknown Person",
                        "filename": face.get("filename", None)
                    })
            except Exception as e:
                logger.error(f"Error extracting face data from recognition results: {str(e)}")
                # Continue with empty faces list
        
        # Process actual face detections if available
        for face in faces:
            person_id = face.get("person_id") or face.get("profile_id")
            name = face.get("name", "Unknown")
            
            for detection in face.get("detections", []):
                timestamp = detection.get("timestamp")
                if timestamp is not None:
                    # Calculate approximate end time (assuming 1 second duration)
                    end_time = timestamp + 1.0
                    
                    timeline_data.append({
                        "type": "face",
                        "id": face.get("id", ""),
                        "person_id": person_id,
                        "name": name,
                        "start": timestamp,
                        "end": end_time,
                        "confidence": face.get("confidence", 0),
                        "image_path": detection.get("image_path", "")
                    })
        
        # Extract speaker segments
        segments = voice_results.get("segments", [])
        for segment in segments:
            speaker = segment.get("speaker", "")
            speaker_id = segment.get("speaker_id", "")
            
            if speaker or speaker_id:
                timeline_data.append({
                    "type": "speaker",
                    "id": speaker_id,
                    "person_id": speaker_id,
                    "name": speaker or f"Speaker {speaker_id}",
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "confidence": segment.get("speaker_confidence", 0),
                    "text": segment.get("text", "")
                })
        
        # Sort by start time
        timeline_data.sort(key=lambda x: x["start"])
        
        # Find correlations between faces and speakers
        correlations = []
        for face_item in [item for item in timeline_data if item["type"] == "face"]:
            for speaker_item in [item for item in timeline_data if item["type"] == "speaker"]:
                # Check for temporal overlap
                if (face_item["start"] <= speaker_item["end"] and 
                    face_item["end"] >= speaker_item["start"]):
                    
                    # Calculate overlap
                    overlap_start = max(face_item["start"], speaker_item["start"])
                    overlap_end = min(face_item["end"], speaker_item["end"])
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    # Only consider significant overlaps
                    if overlap_duration > 0.3:
                        # Check if they refer to the same person
                        same_person = False
                        if face_item["person_id"] and speaker_item["person_id"]:
                            same_person = face_item["person_id"] == speaker_item["person_id"]
                        
                        correlations.append({
                            "face_id": face_item["id"],
                            "speaker_id": speaker_item["id"],
                            "face_name": face_item["name"],
                            "speaker_name": speaker_item["name"],
                            "start": overlap_start,
                            "end": overlap_end,
                            "confidence": 0.8 if same_person else 0.5,
                            "same_person": same_person
                        })
        
        return {
            "success": True,
            "video_id": capture_id,
            "timeline": timeline_data,
            "correlations": correlations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition timeline: {str(e)}")
