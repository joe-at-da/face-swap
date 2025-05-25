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
    
    def update_correlation_confidence(self, db: Session, capture_id: int) -> Dict[str, Any]:
        """
        Update existing correlations with enhanced confidence scoring.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            
        Returns:
            Dict with updated correlation results
        """
        try:
            logger.info(f"Updating correlation confidence for capture {capture_id}")
            
            # Get the capture session
            capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
            if not capture:
                logger.error(f"Capture session not found: {capture_id}")
                return {"success": False, "error": f"Capture session not found: {capture_id}"}
            
            # Check if timeline data exists
            if not capture.timeline_data:
                logger.error(f"No timeline data found for capture {capture_id}")
                return {"success": False, "error": f"No timeline data found for capture {capture_id}"}
            
            # Parse timeline data
            try:
                timeline_data = json.loads(capture.timeline_data)
                correlations = timeline_data.get("correlations", [])
                
                if not correlations:
                    logger.info(f"No correlations found for capture {capture_id}")
                    return {"success": True, "message": f"No correlations found for capture {capture_id}", "correlations": []}
                
                # Get all events to use for confidence calculation
                events = self.get_timeline_events(db, capture_id)
                if not events.get("success", False):
                    return events
                
                event_map = {}
                for event in events.get("timeline", []):
                    event_map[event["id"]] = event
                
                # Update confidence scores for each correlation
                updated_correlations = []
                for correlation in correlations:
                    face_id = correlation.get("face_id")
                    speaker_id = correlation.get("speaker_id")
                    
                    face_event = event_map.get(face_id)
                    speaker_event = event_map.get(speaker_id)
                    
                    if not face_event or not speaker_event:
                        # Skip if events not found
                        updated_correlations.append(correlation)
                        continue
                    
                    # Calculate enhanced confidence
                    face_name = face_event["person_name"].lower() if face_event["person_name"] else ""
                    speaker_name = speaker_event["person_name"].lower() if speaker_event["person_name"] else ""
                    
                    # Calculate name similarity score (0-1)
                    name_similarity = 0.0
                    if face_name and speaker_name:
                        # Simple string similarity
                        if face_name == speaker_name:
                            name_similarity = 1.0
                        elif face_name in speaker_name or speaker_name in face_name:
                            name_similarity = 0.8
                        else:
                            # Simple character overlap similarity
                            common_chars = sum(1 for c in face_name if c in speaker_name)
                            name_similarity = common_chars / max(len(face_name), len(speaker_name)) if max(len(face_name), len(speaker_name)) > 0 else 0.0
                    
                    # Check for explicit links between profiles
                    explicit_link = False
                    if face_event.get("person_id") and speaker_event.get("person_id"):
                        explicit_link = face_event["person_id"] == speaker_event["person_id"]
                    
                    # Extract confidence scores
                    face_confidence = face_event.get("confidence", 0.5)
                    speaker_confidence = speaker_event.get("confidence", 0.5)
                    
                    # Calculate overlap duration
                    overlap_start = max(face_event["start"], speaker_event["start"])
                    overlap_end = min(face_event["end"], speaker_event["end"])
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    # Calculate confidence boosters/penalties
                    boosters = {
                        "explicit_link": 0.2 if explicit_link else 0.0,
                        "name_match": 0.15 * name_similarity,
                        "high_individual_confidence": 0.1 if (face_confidence > 0.8 and speaker_confidence > 0.8) else 0.0,
                        "temporal_overlap": min(0.1, overlap_duration / 5.0)  # Up to 0.1 boost for longer overlaps
                    }
                    
                    # Calculate penalties
                    penalties = {
                        "name_mismatch": 0.2 if (face_name and speaker_name and name_similarity < 0.3) else 0.0,
                        "low_face_confidence": 0.1 if face_confidence < 0.5 else 0.0,
                        "low_speaker_confidence": 0.1 if speaker_confidence < 0.5 else 0.0
                    }
                    
                    # Calculate total boosters and penalties
                    total_boosters = sum(boosters.values())
                    total_penalties = sum(penalties.values())
                    
                    # Calculate base combined confidence (weighted average)
                    base_combined = 0.6 * face_confidence + 0.4 * speaker_confidence
                    
                    # Apply boosters and penalties to get final confidence
                    final_confidence = min(1.0, max(0.0, base_combined + total_boosters - total_penalties))
                    
                    # Determine if same person based on confidence and other factors
                    same_person = explicit_link or name_similarity > 0.7 or final_confidence > 0.7
                    
                    # Determine confidence level category
                    confidence_level = "unknown"
                    if final_confidence >= 0.9:
                        confidence_level = "very_high"
                    elif final_confidence >= 0.75:
                        confidence_level = "high"
                    elif final_confidence >= 0.6:
                        confidence_level = "medium"
                    elif final_confidence >= 0.4:
                        confidence_level = "low"
                    else:
                        confidence_level = "very_low"
                    
                    # Update correlation with enhanced confidence
                    updated_correlation = correlation.copy()
                    updated_correlation.update({
                        "confidence": final_confidence,
                        "confidence_level": confidence_level,
                        "same_person": same_person,
                        "name_similarity": name_similarity,
                        "explicit_link": explicit_link,
                        "factors": {
                            "boosters": boosters,
                            "penalties": penalties,
                            "face_confidence": face_confidence,
                            "speaker_confidence": speaker_confidence,
                            "base_combined": base_combined
                        }
                    })
                    
                    updated_correlations.append(updated_correlation)
                
                # Update timeline data
                timeline_data["correlations"] = updated_correlations
                capture.timeline_data = json.dumps(make_json_serializable(timeline_data))
                db.commit()
                
                return {
                    "success": True,
                    "message": f"Updated correlation confidence for {len(updated_correlations)} correlations",
                    "correlations": updated_correlations
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing timeline data: {str(e)}")
                return {"success": False, "error": f"Error parsing timeline data: {str(e)}"}
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating correlation confidence: {str(e)}")
            return {"success": False, "error": f"Error updating correlation confidence: {str(e)}"}
    
    def find_correlations(self, recognition_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find correlations between face and speaker events.
        
        Args:
            recognition_data: Dictionary containing face_events and speaker_events lists
            
        Returns:
            List of correlation objects with confidence scores and match details
        """
        try:
            logger.info("Finding correlations between face and speaker events")
            
            # Get face and speaker events from the input data
            face_items = recognition_data.get("face_events", [])
            speaker_items = recognition_data.get("speaker_events", [])
            
            if not face_items or not speaker_items:
                logger.warning("Insufficient data for correlation: missing face or speaker events")
                return []
            
            # Initialize correlations list
            correlations = []
            
            # Group face detections by person
            face_by_person = {}
            for face_item in face_items:
                person_id = face_item.get("person_id")
                person_name = face_item.get("person_name", "Unknown")
                key = str(person_id) if person_id else person_name
                
                if key not in face_by_person:
                    face_by_person[key] = []
                
                face_by_person[key].append(face_item)
            
            # Group speaker segments by person
            speaker_by_person = {}
            for speaker_item in speaker_items:
                person_id = speaker_item.get("person_id")
                person_name = speaker_item.get("person_name", "Unknown Speaker")
                key = str(person_id) if person_id else person_name
                
                if key not in speaker_by_person:
                    speaker_by_person[key] = []
                
                speaker_by_person[key].append(speaker_item)
            
            # First, try to match based on person_id (explicit links)
            for person_key in face_by_person:
                if person_key in speaker_by_person and person_key.isdigit():  # Matching by ID
                    face_detections = face_by_person[person_key]
                    speaker_segments = speaker_by_person[person_key]
                    
                    for face_item in face_detections:
                        face_time = face_item["start_time"]
                        face_confidence = face_item["confidence"]
                        
                        for speaker_item in speaker_segments:
                            speaker_start = speaker_item["start_time"]
                            speaker_end = speaker_item["end_time"]
                            speaker_confidence = speaker_item["confidence"]
                            
                            # Check for temporal overlap with extended window
                            # Allow face detection to be slightly outside speaker segment (up to 2 seconds)
                            extended_start = speaker_start - 2.0
                            extended_end = speaker_end + 2.0
                            
                            if extended_start <= face_time <= extended_end:
                                # Calculate precise temporal overlap
                                overlap_start = max(face_time, speaker_start)
                                overlap_end = min(face_time + 1.0, speaker_end)  # Assume face detection spans 1 second
                                overlap_duration = max(0, overlap_end - overlap_start)
                                
                                # For explicit links, use higher base confidence
                                base_combined = 0.7 * face_confidence + 0.3 * speaker_confidence
                                
                                # Calculate boosters for explicit links
                                boosters = {
                                    "explicit_link": 0.3,  # Strong boost for explicit ID match
                                    "high_individual_confidence": 0.1 if (face_confidence > 0.8 and speaker_confidence > 0.8) else 0.0,
                                    "temporal_overlap": min(0.1, overlap_duration / 3.0)  # Up to 0.1 boost for longer overlaps
                                }
                                
                                # Calculate penalties
                                penalties = {
                                    "low_face_confidence": 0.1 if face_confidence < 0.5 else 0.0,
                                    "low_speaker_confidence": 0.1 if speaker_confidence < 0.5 else 0.0,
                                    "outside_segment": 0.1 if overlap_duration == 0 else 0.0  # Penalty if no actual overlap
                                }
                                
                                # Calculate final confidence
                                total_boosters = sum(boosters.values())
                                total_penalties = sum(penalties.values())
                                final_confidence = min(1.0, max(0.0, base_combined + total_boosters - total_penalties))
                                
                                # Determine confidence level category
                                confidence_level = self._get_confidence_level(final_confidence)
                                
                                correlations.append({
                                    "face_id": face_item["id"],
                                    "speaker_id": speaker_item["id"],
                                    "face_name": face_item["person_name"],
                                    "speaker_name": speaker_item["person_name"],
                                    "start": overlap_start if overlap_duration > 0 else face_time,
                                    "end": overlap_end if overlap_duration > 0 else face_time + 1.0,
                                    "confidence": final_confidence,
                                    "confidence_level": confidence_level,
                                    "same_person": True,  # Explicit link means same person
                                    "match_type": "explicit_id",
                                    "factors": {
                                        "boosters": boosters,
                                        "penalties": penalties,
                                        "face_confidence": face_confidence,
                                        "speaker_confidence": speaker_confidence,
                                        "base_combined": base_combined
                                    }
                                })
            
            # Now try to match based on name similarity for remaining faces
            for face_item in face_items:
                face_time = face_item["start_time"]
                face_name = face_item["person_name"]
                face_confidence = face_item["confidence"]
                face_id = face_item["id"]
                
                # Skip if this face is already correlated with explicit ID match
                if any(corr["face_id"] == face_id for corr in correlations):
                    continue
                
                for speaker_item in speaker_items:
                    speaker_start = speaker_item["start_time"]
                    speaker_end = speaker_item["end_time"]
                    speaker_name = speaker_item["person_name"]
                    speaker_confidence = speaker_item["confidence"]
                    speaker_id = speaker_item["id"]
                    
                    # Skip if this speaker is already correlated with this face
                    if any(corr["face_id"] == face_id and corr["speaker_id"] == speaker_id for corr in correlations):
                        continue
                    
                    # Check for temporal overlap with extended window
                    extended_start = speaker_start - 1.5
                    extended_end = speaker_end + 1.5
                    
                    if extended_start <= face_time <= extended_end:
                        # Calculate name similarity
                        import difflib
                        name_similarity = difflib.SequenceMatcher(None, face_name, speaker_name).ratio()
                        
                        # Calculate precise temporal overlap
                        overlap_start = max(face_time, speaker_start)
                        overlap_end = min(face_time + 1.0, speaker_end)
                        overlap_duration = max(0, overlap_end - overlap_start)
                        
                        # Calculate boosters
                        boosters = {
                            "name_similarity": self._calculate_name_similarity_boost(name_similarity),
                            "high_individual_confidence": 0.1 if (face_confidence > 0.8 and speaker_confidence > 0.8) else 0.0,
                            "temporal_overlap": min(0.15, overlap_duration / 2.0),  # Up to 0.15 boost for longer overlaps
                            "perfect_overlap": 0.1 if (speaker_start <= face_time <= speaker_end) else 0.0  # Boost if face is perfectly within segment
                        }
                        
                        # Calculate penalties
                        penalties = {
                            "name_mismatch": 0.3 if (face_name and speaker_name and name_similarity < 0.3) else 0.0,
                            "low_face_confidence": 0.15 if face_confidence < 0.5 else 0.0,
                            "low_speaker_confidence": 0.15 if speaker_confidence < 0.5 else 0.0,
                            "outside_segment": 0.2 if overlap_duration == 0 else 0.0  # Stronger penalty if no actual overlap
                        }
                        
                        # Calculate base combined confidence (weighted average)
                        base_combined = 0.6 * face_confidence + 0.4 * speaker_confidence
                        
                        # Apply boosters and penalties to get final confidence
                        total_boosters = sum(boosters.values())
                        total_penalties = sum(penalties.values())
                        final_confidence = min(1.0, max(0.0, base_combined + total_boosters - total_penalties))
                        
                        # Determine if same person based on confidence and other factors
                        same_person = name_similarity > 0.7 or final_confidence > 0.7
                        
                        # Determine confidence level category
                        confidence_level = self._get_confidence_level(final_confidence)
                        
                        # Only add if confidence is above threshold
                        if final_confidence >= 0.4 or name_similarity > 0.6:
                            correlations.append({
                                "face_id": face_item["id"],
                                "speaker_id": speaker_item["id"],
                                "face_name": face_item["person_name"],
                                "speaker_name": speaker_item["person_name"],
                                "start": overlap_start if overlap_duration > 0 else face_time,
                                "end": overlap_end if overlap_duration > 0 else face_time + 1.0,
                                "confidence": final_confidence,
                                "confidence_level": confidence_level,
                                "same_person": same_person,
                                "name_similarity": name_similarity,
                                "match_type": "name_similarity",
                                "factors": {
                                    "boosters": boosters,
                                    "penalties": penalties,
                                    "face_confidence": face_confidence,
                                    "speaker_confidence": speaker_confidence,
                                    "base_combined": base_combined
                                }
                            })
            
            # Sort correlations by confidence (highest first)
            correlations.sort(key=lambda x: x["confidence"], reverse=True)
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error finding correlations: {str(e)}")
            return []
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Helper method to determine confidence level category."""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        elif confidence >= 0.4:
            return "low"
        else:
            return "very_low"
            
    def _calculate_name_similarity_boost(self, similarity: float) -> float:
        """Calculate boost based on name similarity."""
        if similarity > 0.9:  # Almost perfect match
            return 0.3
        elif similarity > 0.8:  # Very good match
            return 0.25
        elif similarity > 0.7:  # Good match
            return 0.2
        elif similarity > 0.6:  # Moderate match
            return 0.15
        elif similarity > 0.5:  # Weak match
            return 0.1
        else:
            return 0.0
            
    def get_correlations(self, db: Session, capture_id: int) -> Dict[str, Any]:
        """
        Get correlations between face and speaker events for a capture session.
        
        Args:
            db: Database session
            capture_id: ID of the capture session
            
        Returns:
            Dict with correlation results
        """
        try:
            logger.info(f"Getting correlations for capture {capture_id}")
            
            # First check if we have a timeline record with correlations
            timeline = db.query(models.RecognitionTimeline).filter(
                models.RecognitionTimeline.capture_session_id == capture_id
            ).first()
            
            if timeline and timeline.correlations:
                try:
                    correlations_data = json.loads(timeline.correlations)
                    
                    # Get face and speaker counts
                    face_events = db.query(models.RecognitionEvent).filter(
                        models.RecognitionEvent.capture_session_id == capture_id,
                        models.RecognitionEvent.event_type == "face"
                    ).count()
                    
                    speaker_events = db.query(models.RecognitionEvent).filter(
                        models.RecognitionEvent.capture_session_id == capture_id,
                        models.RecognitionEvent.event_type == "speaker"
                    ).count()
                    
                    return {
                        "success": True,
                        "correlations": correlations_data,
                        "face_count": face_events,
                        "speaker_count": speaker_events
                    }
                except json.JSONDecodeError:
                    logger.error(f"Invalid correlations JSON for timeline {timeline.id}")
            
            # If no correlations found in timeline, try to generate them
            # Get the timeline events
            timeline_result = self.get_timeline_events(db, capture_id)
            
            if not timeline_result.get("success", False):
                return {
                    "success": False,
                    "error": "No timeline events found for this capture session",
                    "correlations": []
                }
            
            # Get face and speaker events
            timeline_events = timeline_result.get("timeline", [])
            face_events = [event for event in timeline_events if event.get("type") == "face"]
            speaker_events = [event for event in timeline_events if event.get("type") == "speaker"]
            
            if not face_events or not speaker_events:
                return {
                    "success": False,
                    "error": "Insufficient data: Need both face and speaker events to find correlations",
                    "correlations": []
                }
            
            # Find correlations
            correlations_result = self.find_correlations({
                "face_events": face_events,
                "speaker_events": speaker_events
            })
            
            return {
                "success": True,
                "correlations": correlations_result,
                "face_count": len(face_events),
                "speaker_count": len(speaker_events)
            }
            
        except Exception as e:
            logger.error(f"Error getting correlations: {str(e)}")
            return {
                "success": False,
                "error": f"Error getting correlations: {str(e)}",
                "correlations": []
            }
