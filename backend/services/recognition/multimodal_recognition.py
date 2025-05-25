"""
Multimodal Recognition Service for combining voice and face recognition.

This service integrates voice and facial recognition to improve speaker identification
by combining evidence from both modalities.
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db import models
from backend.db.session import get_db
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class MultimodalRecognitionService:
    """Service for combining voice and face recognition for improved speaker identification."""
    
    def __init__(self):
        """Initialize the multimodal recognition service."""
        self.facial_recognition = FacialRecognitionService()
        self.face_profile_service = FaceProfileService()
        
        # Use Docker container paths as per user preference
        self.base_dir = Path("/app/data")
        self.output_dir = self.base_dir / "multimodal_recognition"
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_video_with_transcription(self, db: Session, video_id: int) -> Dict[str, Any]:
        """
        Process a video with existing transcription to extract faces and link them to speakers.
        
        Args:
            db: Database session
            video_id: ID of the video to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing video with transcription: {video_id}")
            
            # Get the video from the database
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            if not video:
                logger.error(f"Video not found: {video_id}")
                return {"success": False, "error": f"Video not found: {video_id}"}
            
            # Check if the video file exists
            video_path = video.video_path
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            # Check if transcription with speaker diarization exists
            if not video.transcription_results:
                logger.error("Transcription results not found")
                return {"success": False, "error": "Transcription results not found"}
            
            # Parse transcription results
            try:
                transcription = json.loads(video.transcription_results)
                segments = transcription.get("segments", [])
                
                # Check if segments have speaker information
                has_speakers = False
                for segment in segments:
                    if segment.get("speaker") or segment.get("speaker_id") or segment.get("speaker_name"):
                        has_speakers = True
                        break
                
                if not has_speakers:
                    logger.error("No speaker information found in transcription")
                    return {"success": False, "error": "No speaker information found in transcription"}
                
            except Exception as e:
                logger.error(f"Error parsing transcription: {str(e)}")
                return {"success": False, "error": f"Error parsing transcription: {str(e)}"}
            
            # Create output directory for this video
            output_dir = str(self.output_dir / str(video_id))
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract faces from speaker segments
            face_results = self.face_profile_service.extract_faces_from_speaker_segments(
                db=db,
                video_path=video_path,
                speaker_segments=segments,
                output_dir=output_dir
            )
            
            if not face_results["success"]:
                logger.error(f"Error extracting faces: {face_results.get('error', 'Unknown error')}")
                return {"success": False, "error": f"Error extracting faces: {face_results.get('error', 'Unknown error')}"}
            
            # Process each speaker's faces
            speaker_profiles = {}
            
            for segment_result in face_results["results"]:
                speaker_id = segment_result["speaker_id"]
                speaker_name = segment_result["speaker_name"]
                
                # Skip if no faces found for this speaker
                if segment_result["faces_found"] == 0:
                    continue
                
                # Create or get speaker profile
                if speaker_id not in speaker_profiles:
                    # Check if we have a voice profile for this speaker
                    voice_profile = None
                    if hasattr(video, "recognition_results") and video.recognition_results:
                        try:
                            recognition_results = json.loads(video.recognition_results)
                            speakers = recognition_results.get("speakers", [])
                            
                            for speaker in speakers:
                                if speaker.get("id") == speaker_id or speaker.get("name") == speaker_name:
                                    voice_profile_id = speaker.get("voice_profile_id")
                                    if voice_profile_id:
                                        voice_profile = db.query(models.VoiceProfile).filter(
                                            models.VoiceProfile.id == voice_profile_id
                                        ).first()
                                    break
                        except Exception as e:
                            logger.error(f"Error parsing recognition results: {str(e)}")
                    
                    # Check if we already have a face profile linked to this voice profile
                    face_profile = None
                    if voice_profile:
                        face_profile = db.query(models.FaceProfile).filter(
                            models.FaceProfile.voice_profile_id == voice_profile.id
                        ).first()
                    
                    # If no face profile found, create a new one
                    if not face_profile:
                        face_profile = self.face_profile_service.create_face_profile(
                            db=db,
                            name=speaker_name,
                            voice_profile_id=voice_profile.id if voice_profile else None
                        )
                    
                    speaker_profiles[speaker_id] = {
                        "face_profile": face_profile,
                        "voice_profile": voice_profile,
                        "face_samples": []
                    }
                
                # Add face samples for this speaker
                for face_data in segment_result["face_data"]:
                    # Add the face sample to the profile
                    face_sample = self.face_profile_service.add_face_sample(
                        db=db,
                        face_profile_id=speaker_profiles[speaker_id]["face_profile"].id,
                        image_path=face_data["path"],
                        encoding=face_data["encoding"],
                        confidence_score=0.8,  # Default confidence score
                        source_video_id=video_id,
                        timestamp=face_data["timestamp"]
                    )
                    
                    speaker_profiles[speaker_id]["face_samples"].append(face_sample)
            
            # Update the video with face recognition results
            face_recognition_results = {
                "processed_at": datetime.now().isoformat(),
                "speakers": [
                    {
                        "id": speaker_id,
                        "name": speaker_profiles[speaker_id]["face_profile"].name,
                        "face_profile_id": speaker_profiles[speaker_id]["face_profile"].id,
                        "voice_profile_id": speaker_profiles[speaker_id]["voice_profile"].id if speaker_profiles[speaker_id]["voice_profile"] else None,
                        "face_samples": len(speaker_profiles[speaker_id]["face_samples"])
                    }
                    for speaker_id in speaker_profiles
                ]
            }
            
            # Update the video record
            if not video.metadata:
                video.metadata = {}
            
            video.metadata["face_recognition"] = face_recognition_results
            db.commit()
            
            logger.info(f"Completed multimodal processing for video {video_id}")
            
            return {
                "success": True,
                "video_id": video_id,
                "speakers_processed": len(speaker_profiles),
                "total_faces": face_results["total_faces"],
                "face_recognition_results": face_recognition_results
            }
            
        except Exception as e:
            logger.exception(f"Error in multimodal processing: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def identify_speaker_in_frame(self, db: Session, frame_path: str, 
                                threshold: float = 0.6) -> Dict[str, Any]:
        """
        Identify a speaker in a video frame using facial recognition.
        
        Args:
            db: Database session
            frame_path: Path to the video frame
            threshold: Similarity threshold for matching
            
        Returns:
            Dictionary with identification results
        """
        try:
            import face_recognition
            
            logger.info(f"Identifying speaker in frame: {frame_path}")
            
            # Check if the frame exists
            if not os.path.exists(frame_path):
                logger.error(f"Frame file not found: {frame_path}")
                return {"success": False, "error": f"Frame file not found: {frame_path}"}
            
            # Load the image and extract face encoding
            image = face_recognition.load_image_file(frame_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                logger.warning("No face detected in the frame")
                return {"success": False, "error": "No face detected in the frame"}
            
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                logger.warning("Failed to extract face encoding")
                return {"success": False, "error": "Failed to extract face encoding"}
            
            # Use the first face encoding
            face_encoding = face_encodings[0].tolist()
            
            # Match the face with existing profiles
            face_profile, confidence_score = self.face_profile_service.match_face_with_profiles(
                db=db,
                face_encoding=face_encoding,
                threshold=threshold
            )
            
            if not face_profile:
                logger.info("No matching face profile found")
                return {
                    "success": True,
                    "identified": False,
                    "message": "No matching face profile found"
                }
            
            # Get the voice profile if linked
            voice_profile = None
            if face_profile.voice_profile_id:
                voice_profile = db.query(models.VoiceProfile).filter(
                    models.VoiceProfile.id == face_profile.voice_profile_id
                ).first()
            
            logger.info(f"Identified speaker: {face_profile.name} (confidence: {confidence_score:.2f})")
            
            return {
                "success": True,
                "identified": True,
                "face_profile": {
                    "id": face_profile.id,
                    "name": face_profile.name,
                    "role": face_profile.role,
                    "party": face_profile.party,
                    "confidence_score": confidence_score
                },
                "voice_profile": {
                    "id": voice_profile.id,
                    "name": voice_profile.name,
                    "role": voice_profile.role,
                    "party": voice_profile.party
                } if voice_profile else None
            }
            
        except Exception as e:
            logger.exception(f"Error identifying speaker: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def combine_recognition_results(self, voice_results: Dict[str, Any], 
                                  face_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine voice and face recognition results for improved speaker identification.
        
        Args:
            voice_results: Results from voice recognition
            face_results: Results from face recognition
            
        Returns:
            Combined recognition results
        """
        try:
            logger.info("Combining voice and face recognition results")
            
            # Check if both results are valid
            if not voice_results.get("success", False) or not face_results.get("success", False):
                logger.warning("One or both recognition results are invalid")
                
                # Return the successful result if only one failed
                if voice_results.get("success", False):
                    return {
                        "success": True,
                        "source": "voice",
                        "confidence": voice_results.get("confidence_score", 0.0),
                        "profile": voice_results.get("profile", {}),
                        "message": "Face recognition failed, using voice recognition only"
                    }
                elif face_results.get("success", False):
                    return {
                        "success": True,
                        "source": "face",
                        "confidence": face_results.get("confidence_score", 0.0),
                        "profile": face_results.get("face_profile", {}),
                        "message": "Voice recognition failed, using face recognition only"
                    }
                else:
                    return {"success": False, "error": "Both recognition methods failed"}
            
            # Extract profile information
            voice_profile = voice_results.get("profile", {})
            face_profile = face_results.get("face_profile", {})
            voice_profile_id = voice_profile.get("id")
            face_profile_id = face_profile.get("id")
            
            # Extract linked profile IDs
            voice_linked_face_id = voice_profile.get("face_profile_id")
            face_linked_voice_id = face_results.get("voice_profile", {}).get("id") if face_results.get("voice_profile") else None
            
            # Extract names for comparison
            voice_name = voice_profile.get("name", "").lower()
            face_name = face_profile.get("name", "").lower()
            
            # Extract confidence scores
            voice_confidence = voice_results.get("confidence_score", 0.0)
            face_confidence = face_results.get("confidence_score", 0.0)
            
            # Calculate name similarity score (0-1)
            name_similarity = 0.0
            if voice_name and face_name:
                # Simple string similarity
                if voice_name == face_name:
                    name_similarity = 1.0
                elif voice_name in face_name or face_name in voice_name:
                    name_similarity = 0.8
                else:
                    # Calculate Levenshtein distance-based similarity
                    try:
                        import Levenshtein
                        distance = Levenshtein.distance(voice_name, face_name)
                        max_len = max(len(voice_name), len(face_name))
                        name_similarity = 1.0 - (distance / max_len) if max_len > 0 else 0.0
                    except ImportError:
                        # Fallback if Levenshtein is not available
                        common_chars = sum(1 for c in voice_name if c in face_name)
                        name_similarity = common_chars / max(len(voice_name), len(face_name)) if max(len(voice_name), len(face_name)) > 0 else 0.0
            
            # Check if profiles are explicitly linked
            explicit_link = (voice_linked_face_id == face_profile_id) or (face_linked_voice_id == voice_profile_id)
            
            # Determine if they are the same person based on multiple factors
            same_person = False
            combined_confidence = 0.0
            reason = ""
            
            if explicit_link:
                # Explicit link between profiles
                same_person = True
                combined_confidence = 0.7 * max(voice_confidence, face_confidence) + 0.3 * min(voice_confidence, face_confidence)
                reason = "Explicit link between voice and face profiles"
            elif name_similarity > 0.8:
                # High name similarity
                same_person = True
                combined_confidence = 0.6 * max(voice_confidence, face_confidence) + 0.4 * min(voice_confidence, face_confidence)
                reason = f"High name similarity ({name_similarity:.2f})"
            elif name_similarity > 0.5 and (voice_confidence > 0.7 and face_confidence > 0.7):
                # Moderate name similarity but high confidence in both
                same_person = True
                combined_confidence = 0.5 * voice_confidence + 0.5 * face_confidence
                reason = f"Moderate name similarity ({name_similarity:.2f}) with high confidence in both"
            else:
                # Different people or uncertain
                same_person = False
                combined_confidence = max(voice_confidence, face_confidence)
                reason = "Different people identified by voice and face recognition"
            
            if same_person:
                logger.info(f"Voice and face recognition agree on the speaker: {reason}")
                
                # Merge profile information
                merged_profile = {}
                
                # Start with the profile that has higher confidence
                if voice_confidence >= face_confidence:
                    merged_profile.update(voice_profile)
                    # Add face information if available
                    if face_profile:
                        merged_profile["face_profile_id"] = face_profile_id
                        merged_profile["face_image_url"] = face_profile.get("image_url")
                        merged_profile["face_confidence"] = face_confidence
                else:
                    merged_profile.update(face_profile)
                    # Add voice information if available
                    if voice_profile:
                        merged_profile["voice_profile_id"] = voice_profile_id
                        merged_profile["voice_confidence"] = voice_confidence
                
                return {
                    "success": True,
                    "source": "multimodal",
                    "confidence": combined_confidence,
                    "profile": merged_profile,
                    "voice_confidence": voice_confidence,
                    "face_confidence": face_confidence,
                    "name_similarity": name_similarity,
                    "reason": reason
                }
            
            # If they identified different people, use the one with higher confidence
            if voice_confidence > face_confidence:
                logger.info(f"Using voice recognition result (higher confidence): {voice_confidence:.2f} vs {face_confidence:.2f}")
                return {
                    "success": True,
                    "source": "voice",
                    "confidence": voice_confidence,
                    "profile": voice_profile,
                    "alternative_profile": face_profile,
                    "name_similarity": name_similarity,
                    "reason": "Voice recognition has higher confidence"
                }
            else:
                logger.info(f"Using face recognition result (higher confidence): {face_confidence:.2f} vs {voice_confidence:.2f}")
                return {
                    "success": True,
                    "source": "face",
                    "confidence": face_confidence,
                    "profile": face_profile,
                    "alternative_profile": voice_profile,
                    "name_similarity": name_similarity,
                    "reason": "Face recognition has higher confidence"
                }
            
        except Exception as e:
            logger.exception(f"Error combining recognition results: {str(e)}")
            return {"success": False, "error": str(e)}
