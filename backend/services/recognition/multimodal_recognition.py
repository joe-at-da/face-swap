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
from backend.services.recognition.timeline_service import TimelineService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class MultimodalRecognitionService:
    """Service for combining voice and face recognition for improved speaker identification."""
    
    def __init__(self):
        """Initialize the multimodal recognition service."""
        self.facial_recognition = FacialRecognitionService()
        self.face_profile_service = FaceProfileService()
        self.timeline_service = TimelineService()
        
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
            faces_by_speaker = {}
            faces_by_time = {}
            all_faces = []
            
            # Process each segment to extract faces
            for segment in segments:
                speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                if end_time <= start_time:
                    continue
                
                # Calculate segment duration and adjust sampling rate based on duration
                duration = end_time - start_time
                
                # For short segments (< 5s), extract 1-2 frames
                # For medium segments (5-15s), extract a frame every 2-3 seconds
                # For long segments (> 15s), extract a frame every 3-5 seconds
                if duration < 5:
                    interval = max(1.0, duration / 2)  # 1-2 frames for short segments
                elif duration < 15:
                    interval = 2.5  # Frame every 2-3 seconds for medium segments
                else:
                    interval = 4.0  # Frame every 3-5 seconds for long segments
                
                # Extract frames at calculated intervals within this segment
                for timestamp in np.arange(start_time, end_time, interval):
                    # Extract frame at this timestamp
                    frame_filename = f"frame_{video_id}_{timestamp:.2f}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    
                    # Extract the frame using ffmpeg if it doesn't exist
                    if not os.path.exists(frame_path):
                        try:
                            cmd = [
                                "ffmpeg",
                                "-ss", str(timestamp),
                                "-i", video_path,
                                "-vframes", "1",
                                "-q:v", "2",
                                frame_path,
                                "-y"
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Error extracting frame at {timestamp}: {str(e)}")
                            continue
                    
                    # Identify speaker in this frame
                    result = self.identify_speaker_in_frame(db, frame_path)
                    
                    if result.get("success", False):
                        # Store the face detection result
                        face_profile = result.get("face_profile", {})
                        confidence = result.get("confidence_score", 0.0)
                        
                        # Create face detection entry
                        face_detection = {
                            "timestamp": timestamp,
                            "frame_path": frame_path,
                            "frame_url": f"/api/v1/media/frames/{os.path.basename(frame_path)}",
                            "face_profile": face_profile,
                            "confidence": confidence,
                            "speaker": speaker,
                            "text": segment.get("text", ""),
                            "segment_id": segment.get("id"),
                            "segment_start": start_time,
                            "segment_end": end_time
                        }
                        
                        # Add to all faces list
                        all_faces.append(face_detection)
                        
                        # Add to faces by speaker
                        if speaker not in faces_by_speaker:
                            faces_by_speaker[speaker] = []
                        
                        faces_by_speaker[speaker].append(face_detection)
                        
                        # Add to faces by time
                        faces_by_time[timestamp] = face_detection
            
            # Create a timeline of speakers with face detections
            timeline = []
            for timestamp, data in sorted(faces_by_time.items()):
                timeline.append({
                    "timestamp": timestamp,
                    "speaker": data["speaker"],
                    "face_profile": data["face_profile"],
                    "confidence": data["confidence"],
                    "frame_path": data["frame_path"],
                    "frame_url": data["frame_url"],
                    "text": data["text"]
                })
            
            # Create a mapping of speakers to face profiles using a more sophisticated algorithm
            speaker_to_face_profile = {}
            for speaker, faces in faces_by_speaker.items():
                if not faces:
                    continue
                
                # Group faces by profile ID
                profiles = {}
                for face in faces:
                    profile_id = face.get("face_profile", {}).get("id")
                    if not profile_id:
                        continue
                    
                    if profile_id not in profiles:
                        profiles[profile_id] = {
                            "profile": face.get("face_profile", {}),
                            "count": 0,
                            "total_confidence": 0.0,
                            "frames": [],
                            "timestamps": []
                        }
                    
                    profiles[profile_id]["count"] += 1
                    profiles[profile_id]["total_confidence"] += face.get("confidence", 0.0)
                    profiles[profile_id]["frames"].append(face.get("frame_path"))
                    profiles[profile_id]["timestamps"].append(face.get("timestamp"))
                
                # Calculate weighted scores for each profile
                for profile_id, data in profiles.items():
                    # Calculate average confidence
                    avg_confidence = data["total_confidence"] / data["count"] if data["count"] > 0 else 0.0
                    
                    # Calculate temporal consistency (how well distributed the detections are)
                    timestamps = sorted(data["timestamps"])
                    if len(timestamps) > 1:
                        time_span = max(timestamps) - min(timestamps)
                        time_consistency = min(1.0, time_span / 60.0)  # Normalize to max of 1.0 for spans of 60s or more
                    else:
                        time_consistency = 0.0
                    
                    # Calculate final weighted score
                    # Weight: 60% count, 30% confidence, 10% temporal consistency
                    data["weighted_score"] = (
                        0.6 * (data["count"] / len(faces)) + 
                        0.3 * avg_confidence + 
                        0.1 * time_consistency
                    )
                    data["avg_confidence"] = avg_confidence
                    data["time_consistency"] = time_consistency
                
                # Find the profile with the highest weighted score
                best_profile_id = None
                best_score = 0.0
                
                for profile_id, data in profiles.items():
                    if data["weighted_score"] > best_score:
                        best_profile_id = profile_id
                        best_score = data["weighted_score"]
                
                if best_profile_id:
                    best_data = profiles[best_profile_id]
                    speaker_to_face_profile[speaker] = {
                        "profile": best_data["profile"],
                        "count": best_data["count"],
                        "confidence": best_data["avg_confidence"],
                        "time_consistency": best_data["time_consistency"],
                        "weighted_score": best_data["weighted_score"],
                        "best_frames": best_data["frames"][:5]  # Include up to 5 best frames
                    }
            
            # Create voice recognition data from transcription segments
            voice_segments = []
            for segment in segments:
                speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                voice_segment = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "speaker": speaker,
                    "text": segment.get("text", ""),
                    "confidence": segment.get("confidence", 0.5),
                    "segment_id": segment.get("id")
                }
                
                # Add face profile information if available
                if speaker in speaker_to_face_profile:
                    voice_segment["face_profile"] = speaker_to_face_profile[speaker]["profile"]
                    voice_segment["face_confidence"] = speaker_to_face_profile[speaker]["confidence"]
                
                voice_segments.append(voice_segment)
            
            # Update the transcription segments with face profile information
            for segment in segments:
                speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
                
                if speaker in speaker_to_face_profile:
                    segment["face_profile"] = speaker_to_face_profile[speaker]["profile"]
                    segment["face_confidence"] = speaker_to_face_profile[speaker]["confidence"]
                    segment["face_detection_count"] = speaker_to_face_profile[speaker]["count"]
            
            # Create integrated recognition results
            integrated_results = {
                "faces": all_faces,  # All individual face detections
                "voices": voice_segments,  # All voice segments with speaker info
                "speaker_face_mapping": speaker_to_face_profile,  # Mapping of speakers to their best face profile
                "timeline": timeline,  # Timeline of face detections
                "transcription": transcription,  # Original transcription with added face info
                "metadata": {
                    "video_id": video_id,
                    "processed_at": datetime.now().isoformat(),
                    "faces_count": len(all_faces),
                    "speakers_count": len(speaker_to_face_profile),
                    "segments_count": len(segments)
                }
            }
            
            # Store face detections in the timeline service
            for face in all_faces:
                face_detection = {
                    "timestamp": face["timestamp"],
                    "confidence": face["confidence"],
                    "name": face["face_profile"].get("name", "Unknown"),
                    "person_id": face["face_profile"].get("id"),
                    "frame_path": face["frame_path"],
                    "frame_url": face["frame_url"],
                    "speaker": face["speaker"],
                    "text": face["text"]
                }
                self.timeline_service.store_face_detection(db, video_id, face_detection)
            
            # Store speaker segments in the timeline service
            for voice in voice_segments:
                speaker_segment = {
                    "start": voice["start_time"],
                    "end": voice["end_time"],
                    "speaker": voice["speaker"],
                    "speaker_id": voice.get("face_profile", {}).get("id"),
                    "confidence": voice["confidence"],
                    "text": voice["text"],
                    "segment_id": voice["segment_id"]
                }
                self.timeline_service.store_speaker_segment(db, video_id, speaker_segment)
            
            # Update the timeline data using the timeline service
            timeline_result = self.timeline_service.update_timeline_data(db, video_id)
            
            # Find correlations between face and voice events
            correlations_result = self.timeline_service.find_correlations(db, video_id)
            
            # Add timeline data to the integrated results
            integrated_results["timeline"] = timeline_result.get("timeline", [])
            integrated_results["correlations"] = correlations_result.get("correlations", [])
            
            # Save the results to the database
            video.recognition_results = json.dumps(make_json_serializable(integrated_results))
            
            db.commit()
            
            logger.info(f"Completed multimodal processing for video {video_id}")
            
            return {
                "success": True,
                "video_id": video_id,
                "faces_count": len(all_faces),
                "speakers_count": len(speaker_to_face_profile),
                "segments_count": len(segments),
                "events_count": len(recognition_events),
                "correlations_count": len(correlations),
                "timeline": recognition_events[:10],  # Return just the first 10 events to avoid large response
                "speaker_face_mapping": speaker_to_face_profile
            }
            
        except Exception as e:
            logger.exception(f"Error in multimodal processing: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def identify_speaker_in_frame(self, db: Session, frame_path: str, threshold: float = 0.6) -> Dict[str, Any]:
        """
        Identify a speaker in a video frame using facial recognition.
        
        Args:
            db: Database session
            frame_path: Path to the frame image
            threshold: Confidence threshold for face recognition
            
        Returns:
            Dictionary with identification results
        """
        try:
            logger.info(f"Identifying speaker in frame: {frame_path}")
            
            # Check if the frame file exists
            if not os.path.exists(frame_path):
                logger.error(f"Frame file not found: {frame_path}")
                return {"success": False, "error": f"Frame file not found: {frame_path}"}
            
            # Detect and identify faces in the frame
            face_results = self.facial_recognition.identify_faces_in_image(
                image_path=frame_path,
                threshold=threshold,
                db=db
            )
            
            if not face_results["success"]:
                logger.error(f"Error identifying faces: {face_results.get('error', 'Unknown error')}")
                return {"success": False, "error": f"Error identifying faces: {face_results.get('error', 'Unknown error')}"}
            
            # If no faces found, return empty result
            if len(face_results["faces"]) == 0:
                logger.info("No faces found in the frame")
                return {"success": True, "faces_found": 0}
            
            # Get the face with the highest confidence
            best_face = None
            best_confidence = 0.0
            
            for face in face_results["faces"]:
                confidence = face.get("confidence", 0.0)
                if confidence > best_confidence:
                    best_face = face
                    best_confidence = confidence
            
            # Get the face profile
            face_profile = best_face.get("face_profile", {})
            
            # Check if the face profile has a linked voice profile
            voice_profile = None
            if face_profile and face_profile.get("id"):
                face_profile_obj = db.query(models.FaceProfile).filter(
                    models.FaceProfile.id == face_profile.get("id")
                ).first()
                
                if face_profile_obj and face_profile_obj.voice_profile_id:
                    voice_profile = db.query(models.VoiceProfile).filter(
                        models.VoiceProfile.id == face_profile_obj.voice_profile_id
                    ).first()
            
            return {
                "success": True,
                "faces_found": len(face_results["faces"]),
                "face_profile": face_profile,
                "voice_profile": voice_profile.to_dict() if voice_profile else None,
                "confidence_score": best_confidence
            }
            
        except Exception as e:
            logger.exception(f"Error identifying speaker in frame: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def calculate_speaker_confidence(self, face_data: Dict[str, Any], voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence score for speaker identification based on both face and voice recognition.
        
        Args:
            face_data: Face recognition data including confidence scores
            voice_data: Voice recognition data including confidence scores
            
        Returns:
            Dictionary with combined confidence scores and metadata
        """
        try:
            # Extract basic confidence scores
            face_confidence = face_data.get("confidence", 0.0)
            voice_confidence = voice_data.get("confidence", 0.0)
            
            # Extract profile information
            face_profile = face_data.get("face_profile", {})
            voice_profile = voice_data.get("voice_profile", {})
            
            # Extract names for comparison
            face_name = face_profile.get("name", "").lower() if face_profile else ""
            voice_name = voice_profile.get("name", "").lower() if voice_profile else ""
            
            # Calculate base confidence scores
            base_confidence = {
                "face": face_confidence,
                "voice": voice_confidence,
                "combined": 0.0  # Will be calculated below
            }
            
            # Calculate name similarity score (0-1)
            name_similarity = 0.0
            if face_name and voice_name:
                # Simple string similarity
                if face_name == voice_name:
                    name_similarity = 1.0
                elif face_name in voice_name or voice_name in face_name:
                    name_similarity = 0.8
                else:
                    # Simple character overlap similarity
                    common_chars = sum(1 for c in face_name if c in voice_name)
                    name_similarity = common_chars / max(len(face_name), len(voice_name)) if max(len(face_name), len(voice_name)) > 0 else 0.0
            
            # Check for explicit links between profiles
            face_profile_id = face_profile.get("id") if face_profile else None
            voice_profile_id = voice_profile.get("id") if voice_profile else None
            
            face_linked_voice_id = face_profile.get("voice_profile_id") if face_profile else None
            voice_linked_face_id = voice_profile.get("face_profile_id") if voice_profile else None
            
            explicit_link = (face_linked_voice_id == voice_profile_id) or (voice_linked_face_id == face_profile_id)
            
            # Calculate confidence boosters/penalties
            boosters = {
                "explicit_link": 0.2 if explicit_link else 0.0,
                "name_match": 0.15 * name_similarity,
                "high_individual_confidence": 0.1 if (face_confidence > 0.8 and voice_confidence > 0.8) else 0.0
            }
            
            # Calculate penalties
            penalties = {
                "name_mismatch": 0.2 if (face_name and voice_name and name_similarity < 0.3) else 0.0,
                "low_face_confidence": 0.1 if face_confidence < 0.5 else 0.0,
                "low_voice_confidence": 0.1 if voice_confidence < 0.5 else 0.0
            }
            
            # Calculate total boosters and penalties
            total_boosters = sum(boosters.values())
            total_penalties = sum(penalties.values())
            
            # Calculate base combined confidence (weighted average)
            if face_confidence > 0 or voice_confidence > 0:
                # If we have both face and voice, weight them 60/40
                if face_confidence > 0 and voice_confidence > 0:
                    base_combined = 0.6 * face_confidence + 0.4 * voice_confidence
                # If we only have one, use that one
                else:
                    base_combined = face_confidence if face_confidence > 0 else voice_confidence
            else:
                base_combined = 0.0
            
            # Apply boosters and penalties to get final confidence
            final_confidence = min(1.0, max(0.0, base_combined + total_boosters - total_penalties))
            
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
            
            # Create detailed result
            result = {
                "success": True,
                "confidence": {
                    "face": face_confidence,
                    "voice": voice_confidence,
                    "base_combined": base_combined,
                    "final": final_confidence,
                    "level": confidence_level
                },
                "factors": {
                    "boosters": boosters,
                    "penalties": penalties
                },
                "metadata": {
                    "name_similarity": name_similarity,
                    "explicit_link": explicit_link,
                    "face_name": face_name,
                    "voice_name": voice_name
                }
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Error calculating speaker confidence: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "confidence": {
                    "face": face_data.get("confidence", 0.0),
                    "voice": voice_data.get("confidence", 0.0),
                    "final": max(face_data.get("confidence", 0.0), voice_data.get("confidence", 0.0))
                }
            }
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
