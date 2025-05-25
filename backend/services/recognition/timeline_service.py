"""
Timeline Service for recognition events.

This service manages the timeline data for recognition events, including face detections,
speaker segments, and correlations between them.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db import models
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class TimelineService:
    """Service for managing recognition timeline events."""
    
    def __init__(self):
        """Initialize the timeline service."""
        logger.info("Initializing TimelineService")
    
    def store_face_detection(self, db: Session, capture_id: int, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a face detection event in the database.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            detection: Face detection data
            
        Returns:
            Dict with storage results
        """
        try:
            logger.info(f"Storing face detection for capture {capture_id}")
            
            # Create a new recognition event
            event = models.RecognitionEvent(
                capture_session_id=capture_id,
                event_type="face",
                start_time=detection.get("timestamp", 0),
                end_time=detection.get("timestamp", 0) + 1.0,  # Assume 1 second duration
                confidence=detection.get("confidence", 0),
                person_id=detection.get("person_id"),
                person_name=detection.get("name", "Unknown"),
                data=detection
            )
            
            db.add(event)
            db.commit()
            
            return {
                "success": True,
                "event_id": event.id,
                "message": "Face detection stored successfully"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing face detection: {str(e)}")
            return {
                "success": False,
                "error": f"Error storing face detection: {str(e)}"
            }
    
    def store_speaker_segment(self, db: Session, capture_id: int, segment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a speaker segment event in the database.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            segment: Speaker segment data
            
        Returns:
            Dict with storage results
        """
        try:
            logger.info(f"Storing speaker segment for capture {capture_id}")
            
            # Create a new recognition event
            event = models.RecognitionEvent(
                capture_session_id=capture_id,
                event_type="speaker",
                start_time=segment.get("start", 0),
                end_time=segment.get("end", 0),
                confidence=segment.get("confidence", 0),
                person_id=segment.get("speaker_id"),
                person_name=segment.get("speaker", "Unknown Speaker"),
                data=segment
            )
            
            db.add(event)
            db.commit()
            
            return {
                "success": True,
                "event_id": event.id,
                "message": "Speaker segment stored successfully"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing speaker segment: {str(e)}")
            return {
                "success": False,
                "error": f"Error storing speaker segment: {str(e)}"
            }
    
    def get_timeline_events(self, db: Session, capture_id: int, event_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get timeline events for a capture session.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            event_type: Optional filter for event type (face, speaker)
            
        Returns:
            Dict with timeline events
        """
        try:
            logger.info(f"Getting timeline events for capture {capture_id}")
            
            # Query the recognition events
            query = db.query(models.RecognitionEvent).filter(
                models.RecognitionEvent.capture_session_id == capture_id
            )
            
            if event_type:
                query = query.filter(models.RecognitionEvent.event_type == event_type)
            
            # Order by start time
            events = query.order_by(models.RecognitionEvent.start_time).all()
            
            # Format the events for the timeline
            timeline_data = []
            for event in events:
                timeline_data.append({
                    "id": event.id,
                    "type": event.event_type,
                    "start": event.start_time,
                    "end": event.end_time,
                    "confidence": event.confidence,
                    "person_id": event.person_id,
                    "person_name": event.person_name,
                    "data": event.data
                })
            
            return {
                "success": True,
                "video_id": capture_id,
                "timeline": timeline_data,
                "count": len(timeline_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting timeline events: {str(e)}")
            return {
                "success": False,
                "error": f"Error getting timeline events: {str(e)}",
                "timeline": []
            }
    
    def update_timeline_data(self, db: Session, capture_id: int) -> Dict[str, Any]:
        """
        Update the timeline data for a capture session based on recognition events.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            
        Returns:
            Dict with update results
        """
        try:
            logger.info(f"Updating timeline data for capture {capture_id}")
            
            # Get the capture session
            capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
            if not capture:
                return {
                    "success": False,
                    "error": f"Capture session not found: {capture_id}"
                }
            
            # Get all recognition events for this capture
            timeline_data = self.get_timeline_events(db, capture_id)
            
            if not timeline_data.get("success", False):
                return timeline_data
            
            # Store the timeline data in the capture session
            capture.timeline_data = json.dumps(make_json_serializable(timeline_data))
            db.commit()
            
            return {
                "success": True,
                "message": f"Timeline data updated successfully for capture {capture_id}",
                "timeline": timeline_data.get("timeline", [])
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating timeline data: {str(e)}")
            return {
                "success": False,
                "error": f"Error updating timeline data: {str(e)}"
            }
    
    def find_correlations(self, db: Session, capture_id: int) -> Dict[str, Any]:
        """
        Find correlations between face and speaker events.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            
        Returns:
            Dict with correlation results
        """
        try:
            logger.info(f"Finding correlations for capture {capture_id}")
            
            # Get face events
            face_data = self.get_timeline_events(db, capture_id, "face")
            if not face_data.get("success", False):
                return face_data
            
            # Get speaker events
            speaker_data = self.get_timeline_events(db, capture_id, "speaker")
            if not speaker_data.get("success", False):
                return speaker_data
            
            face_events = face_data.get("timeline", [])
            speaker_events = speaker_data.get("timeline", [])
            
            # Find correlations
            correlations = []
            for face_item in face_events:
                for speaker_item in speaker_events:
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
                                "face_name": face_item["person_name"],
                                "speaker_name": speaker_item["person_name"],
                                "start": overlap_start,
                                "end": overlap_end,
                                "confidence": 0.8 if same_person else 0.5,
                                "same_person": same_person
                            })
            
            return {
                "success": True,
                "video_id": capture_id,
                "correlations": correlations,
                "count": len(correlations)
            }
            
        except Exception as e:
            logger.error(f"Error finding correlations: {str(e)}")
            return {
                "success": False,
                "error": f"Error finding correlations: {str(e)}",
                "correlations": []
            }
