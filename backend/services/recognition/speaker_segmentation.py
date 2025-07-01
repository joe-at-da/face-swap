#!/usr/bin/env python
"""
Speaker segmentation module for Parliament TV recognition.

This module implements the 60-second pause rule for segmenting speaker clips:
- Consecutive speech segments by the same MP are merged if less than 60 seconds apart
- A new clip is created when a different MP speaks or the same MP resumes after a longer pause
- Transcripts are extracted per clip based on start/end timestamps
- Confidence scores are derived from recognition results
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.db import models
from backend.services.recognition.face_profile import FaceProfileService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeakerSegmentation:
    """Speaker segmentation service for Parliament TV recognition."""
    
    def __init__(self, db: Session):
        """Initialize the speaker segmentation service."""
        self.db = db
        self.face_profile_service = FaceProfileService()
    
    def identify_speaking_segments(self, video_id: int, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process recognition results to identify speaking segments based on the 60-second pause rule.
        
        Args:
            video_id: ID of the video to process
            recognition_results: Recognition results from the database
            
        Returns:
            Dict with speaking segments information
        """
        try:
            # Extract events from recognition results
            events = recognition_results.get("events", [])
            if not events:
                return {"success": False, "error": "No recognition events found"}
            
            # Sort events by timestamp
            events.sort(key=lambda x: x.get("timestamp", 0))
            
            # Group events by speaker
            speaker_segments = []
            current_segment = None
            
            for event in events:
                # Skip events without face or voice recognition
                if not event.get("face_recognition") and not event.get("voice_recognition"):
                    continue
                    
                # Get speaker information
                speaker_id, confidence, recognition_method = self._get_speaker_info(event)
                
                # If no speaker identified, skip this event
                if not speaker_id:
                    continue
                    
                timestamp = event.get("timestamp", 0)
                
                # Check if this is a new segment or continuation of current segment
                if current_segment and current_segment["speaker_id"] == speaker_id:
                    # Check if the pause is less than 60 seconds
                    if timestamp - current_segment["end_time"] < 60:
                        # Update end time of current segment
                        current_segment["end_time"] = timestamp
                        # Update confidence if higher
                        if confidence > current_segment["confidence"]:
                            current_segment["confidence"] = confidence
                            current_segment["recognition_method"] = recognition_method
                        # Add transcript if available
                        if event.get("transcript"):
                            current_segment["transcript"] += " " + event["transcript"]
                    else:
                        # Pause is more than 60 seconds, create a new segment
                        speaker_segments.append(current_segment)
                        current_segment = self._create_new_segment(speaker_id, timestamp, confidence, 
                                                                recognition_method, event.get("transcript", ""))
                else:
                    # New speaker or first segment
                    if current_segment:
                        speaker_segments.append(current_segment)
                        
                    current_segment = self._create_new_segment(speaker_id, timestamp, confidence, 
                                                            recognition_method, event.get("transcript", ""))
            
            # Add the last segment if exists
            if current_segment:
                speaker_segments.append(current_segment)
                
            # Filter out segments that are too short (less than 3 seconds)
            filtered_segments = [s for s in speaker_segments if (s["end_time"] - s["start_time"]) >= 3]
                
            return {
                "success": True,
                "video_id": video_id,
                "segments": filtered_segments,
                "segment_count": len(filtered_segments)
            }
            
        except Exception as e:
            logger.exception(f"Error identifying speaking segments: {str(e)}")
            return {"success": False, "error": f"Error identifying speaking segments: {str(e)}"}
    
    def _get_speaker_info(self, event: Dict[str, Any]) -> Tuple[Optional[int], float, str]:
        """
        Extract speaker information from a recognition event.
        
        Args:
            event: Recognition event
            
        Returns:
            Tuple of (speaker_id, confidence, recognition_method)
        """
        speaker_id = None
        confidence = 0.0
        recognition_method = None
        
        # Check face recognition first
        if event.get("face_recognition"):
            face_encoding = event["face_recognition"].get("encoding")
            if face_encoding:
                # Match face with MP profiles
                profile, score = self.face_profile_service.match_face_with_profiles(
                    db=self.db, 
                    face_encoding=face_encoding
                )
                if profile and score > 0.6:  # Confidence threshold
                    speaker_id = profile.mp_id
                    confidence = score
                    recognition_method = "facial"
        
        # Check voice recognition if no face match or if face match has low confidence
        if (not speaker_id or confidence < 0.7) and event.get("voice_recognition"):
            voice_profile_id = event["voice_recognition"].get("profile_id")
            voice_score = event["voice_recognition"].get("confidence", 0.0)
            
            if voice_profile_id and voice_score > 0.7:  # Confidence threshold
                # Get MP ID from voice profile
                voice_profile = self.db.query(models.VoiceProfile).filter(
                    models.VoiceProfile.id == voice_profile_id
                ).first()
                
                if voice_profile and voice_profile.mp_id:
                    # If we already have a face match, use combined recognition
                    if speaker_id and speaker_id == voice_profile.mp_id:
                        # Boost confidence for matching face and voice
                        confidence = max(confidence, voice_score) + 0.1
                        recognition_method = "combined"
                    # Otherwise use voice recognition if it's better than face
                    elif not speaker_id or voice_score > confidence:
                        speaker_id = voice_profile.mp_id
                        confidence = voice_score
                        recognition_method = "voice"
        
        return speaker_id, confidence, recognition_method
    
    def _create_new_segment(self, speaker_id: int, timestamp: float, confidence: float, 
                          recognition_method: str, transcript: str) -> Dict[str, Any]:
        """
        Create a new speaker segment.
        
        Args:
            speaker_id: ID of the speaker
            timestamp: Timestamp of the event
            confidence: Confidence score
            recognition_method: Recognition method (facial, voice, combined)
            transcript: Transcript text
            
        Returns:
            Dict with segment information
        """
        return {
            "speaker_id": speaker_id,
            "start_time": timestamp,
            "end_time": timestamp,
            "confidence": confidence,
            "recognition_method": recognition_method,
            "transcript": transcript
        }
