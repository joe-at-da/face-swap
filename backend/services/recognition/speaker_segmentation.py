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
from backend.services.recognition.face_profile_service import FaceProfileService

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
                    # Helper function to check if a transcript appears to end with sentence-ending punctuation
                    def is_sentence_complete(text):
                        """Check if text appears to end with sentence-ending punctuation."""
                        if not text:
                            return True
                        # Check for sentence-ending punctuation
                        return text.rstrip().endswith(('.', '!', '?', ':', '"', '"'))
                    
                    # Check if current segment's transcript is a complete sentence
                    sentence_complete = is_sentence_complete(current_segment.get("transcript", ""))
                    
                    # Use extended gap threshold for incomplete sentences
                    threshold = 120 if not sentence_complete else 60  # 2 minutes for incomplete sentences
                    
                    if timestamp - current_segment["end_time"] < threshold or not sentence_complete:
                        # Update end time and confidence if needed
                        current_segment["end_time"] = timestamp
                        if confidence > current_segment["confidence"]:
                            current_segment["confidence"] = confidence
                            current_segment["recognition_method"] = recognition_method
                        
                        # Append transcript if available
                        if event.get("transcript"):
                            current_segment["transcript"] += " " + event["transcript"]
                    else:
                        # Gap too large, add current segment and start a new one
                        speaker_segments.append(current_segment)
                        current_segment = self._create_new_segment(
                            speaker_id, timestamp, confidence, recognition_method, event.get("transcript", "")
                        )
                else:
                    # New speaker or first segment
                    if current_segment:
                        speaker_segments.append(current_segment)
                        
                    current_segment = self._create_new_segment(
                        speaker_id, timestamp, confidence, recognition_method, event.get("transcript", "")
                    )
            
            # Add the last segment if exists
            if current_segment:
                speaker_segments.append(current_segment)
                
            # Filter out segments that are too short (less than 3 seconds)
            speaker_segments = [s for s in speaker_segments if s["end_time"] - s["start_time"] >= 3]
            
            # Sort segments by start time
            speaker_segments.sort(key=lambda x: x["start_time"])
            
            # Post-process segments to further avoid splitting sentences
            def post_process_segments(segments):
                """Post-process segments to avoid splitting sentences."""
                result = []
                i = 0
                while i < len(segments) - 1:
                    current = segments[i]
                    next_seg = segments[i + 1]
                    
                    # Helper function to check if a transcript appears to end with sentence-ending punctuation
                    def is_sentence_complete(text):
                        """Check if text appears to end with sentence-ending punctuation."""
                        if not text:
                            return True
                        # Check for sentence-ending punctuation
                        return text.rstrip().endswith(('.', '!', '?', ':', '"', '"'))
                    
                    # If same speaker and current segment doesn't end with sentence-ending punctuation
                    if (current["speaker_id"] == next_seg["speaker_id"] and 
                        not is_sentence_complete(current.get("transcript", ""))):
                        
                        # Merge with next segment if gap is reasonable (within 2 minutes)
                        if next_seg["start_time"] - current["end_time"] <= 120:  # 2 minute max
                            merged = current.copy()
                            merged["end_time"] = next_seg["end_time"]
                            
                            # Merge transcripts if available
                            if next_seg.get("transcript") and merged.get("transcript"):
                                merged["transcript"] += " " + next_seg["transcript"]
                            elif next_seg.get("transcript"):
                                merged["transcript"] = next_seg["transcript"]
                                
                            merged["confidence"] = max(current["confidence"], next_seg["confidence"])
                            
                            result.append(merged)
                            i += 2  # Skip both segments as they're now merged
                            continue
                            
                    result.append(current)
                    i += 1
                    
                # Add the last segment if we didn't merge it
                if i == len(segments) - 1:
                    result.append(segments[i])
                    
                return result

            # Apply post-processing to further merge segments with incomplete sentences
            speaker_segments = post_process_segments(speaker_segments)
                
            return {
                "success": True,
                "video_id": video_id,
                "segments": speaker_segments,
                "segment_count": len(speaker_segments)
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
