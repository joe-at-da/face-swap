"""
Face Profile Service for managing face profiles and samples.

This service provides functionality for creating, updating, and managing face profiles
and integrating them with voice profiles for improved speaker identification.
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
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class FaceProfileService:
    """Service for managing face profiles for speaker identification."""
    
    def __init__(self):
        """Initialize the face profile service."""
        # Use Docker container paths as per user preference
        self.base_dir = Path("/app/data")
        self.face_profiles_dir = self.base_dir / "face_profiles"
        self.face_samples_dir = self.base_dir / "face_profiles/samples"
        
        # Create directories if they don't exist
        self.face_profiles_dir.mkdir(parents=True, exist_ok=True)
        self.face_samples_dir.mkdir(parents=True, exist_ok=True)
    
    def create_face_profile(self, db: Session, name: str, role: Optional[str] = None, 
                          party: Optional[str] = None, voice_profile_id: Optional[int] = None) -> models.FaceProfile:
        """
        Create a new face profile.
        
        Args:
            db: Database session
            name: Name of the speaker
            role: Role of the speaker (e.g., MP, Minister)
            party: Political party of the speaker
            voice_profile_id: ID of the linked voice profile
            
        Returns:
            The created face profile
        """
        logger.info(f"Creating face profile for {name}")
        
        # Create the face profile
        face_profile = models.FaceProfile(
            name=name,
            role=role,
            party=party,
            voice_profile_id=voice_profile_id,
            profile_metadata={
                "created_at": datetime.now().isoformat(),
                "sample_count": 0
            }
        )
        
        db.add(face_profile)
        db.commit()
        db.refresh(face_profile)
        
        # Create a directory for this profile's samples
        profile_samples_dir = self.face_samples_dir / str(face_profile.id)
        profile_samples_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created face profile for {name} with ID {face_profile.id}")
        
        return face_profile
    
    def add_face_sample(self, db: Session, face_profile_id: int, image_path: str, 
                       encoding: Optional[List[float]] = None, confidence_score: Optional[float] = None,
                       source_video_id: Optional[int] = None, timestamp: Optional[float] = None,
                       frame_number: Optional[int] = None) -> models.FaceSample:
        """
        Add a face sample to a profile.
        
        Args:
            db: Database session
            face_profile_id: ID of the face profile
            image_path: Path to the face image
            encoding: Facial embedding for this sample
            confidence_score: Confidence score for this sample
            source_video_id: ID of the source video
            timestamp: Timestamp in the video where the face was found
            frame_number: Frame number in the video
            
        Returns:
            The created face sample
        """
        logger.info(f"Adding face sample to profile {face_profile_id}")
        
        # Create the face sample
        face_sample = models.FaceSample(
            face_profile_id=face_profile_id,
            image_path=image_path,
            encoding=encoding,
            confidence_score=confidence_score,
            source_video_id=source_video_id,
            timestamp=timestamp,
            frame_number=frame_number,
            sample_metadata={
                "created_at": datetime.now().isoformat()
            }
        )
        
        db.add(face_sample)
        db.commit()
        db.refresh(face_sample)
        
        # Update the profile's sample count
        face_profile = db.query(models.FaceProfile).filter(models.FaceProfile.id == face_profile_id).first()
        if face_profile:
            metadata = face_profile.profile_metadata or {}
            metadata["sample_count"] = metadata.get("sample_count", 0) + 1
            metadata["updated_at"] = datetime.now().isoformat()
            face_profile.profile_metadata = metadata
            db.commit()
        
        logger.info(f"Added face sample to profile {face_profile_id} with ID {face_sample.id}")
        
        return face_sample
    
    def get_face_profile(self, db: Session, profile_id: int) -> Optional[models.FaceProfile]:
        """
        Get a face profile by ID.
        
        Args:
            db: Database session
            profile_id: ID of the face profile
            
        Returns:
            The face profile or None if not found
        """
        return db.query(models.FaceProfile).filter(models.FaceProfile.id == profile_id).first()
    
    def get_face_profiles(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.FaceProfile]:
        """
        Get all face profiles.
        
        Args:
            db: Database session
            skip: Number of profiles to skip
            limit: Maximum number of profiles to return
            
        Returns:
            List of face profiles
        """
        return db.query(models.FaceProfile).offset(skip).limit(limit).all()
    
    def get_face_samples(self, db: Session, profile_id: int) -> List[models.FaceSample]:
        """
        Get all face samples for a profile.
        
        Args:
            db: Database session
            profile_id: ID of the face profile
            
        Returns:
            List of face samples
        """
        return db.query(models.FaceSample).filter(models.FaceSample.face_profile_id == profile_id).all()
    
    def extract_faces_from_video(self, video_path: str, output_dir: Optional[str] = None, 
                            interval: float = 3.0, min_confidence: float = 0.6,
                            prioritize_center: bool = True, select_best_frames: bool = True,
                            min_face_size: int = 200, min_face_area: int = 40000,
                            roi_scale: float = 0.6, detection_interval: int = 150) -> Dict[str, Any]:
        """
        Extract faces from a video file with optimized detection for parliamentary videos.
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save extracted face images
            interval: Interval in seconds between frame processing (increased from default 1.0 to 3.0)
            min_confidence: Minimum confidence score for face detection
            prioritize_center: Whether to prioritize faces in the center of the frame
            select_best_frames: Whether to select the best quality frames
            min_face_size: Minimum width and height for detected faces (in pixels)
            min_face_area: Minimum area for detected faces (in square pixels)
            roi_scale: Scale factor for region of interest (0-1)
            detection_interval: Frame interval for forced detection when using tracking
            
        Returns:
            Dictionary with extraction results
        """
        from .optimized_face_detection import OptimizedFaceDetector
        try:
            logger.info(f"Extracting faces from video: {video_path} with optimized detection")
            
            # Create output directory if not provided
            if not output_dir:
                output_dir = str(self.face_profiles_dir / "extracted")
                os.makedirs(output_dir, exist_ok=True)
            
            # Use the optimized face detector
            detector = OptimizedFaceDetector()
            return detector.extract_faces_from_video(
                video_path=video_path,
                output_dir=output_dir,
                interval=interval,
                min_confidence=min_confidence,
                prioritize_center=prioritize_center,
                select_best_frames=select_best_frames,
                min_face_size=min_face_size,
                min_face_area=min_face_area,
                roi_scale=roi_scale,
                detection_interval=detection_interval
            )
            
        except Exception as e:
            logger.error(f"Error extracting faces: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}            
            
    def _group_similar_faces(self, faces, similarity_threshold=0.6):
        """
        Group similar faces to identify distinct people in a segment.
        
        Args:
            faces: List of face data dictionaries
            similarity_threshold: Threshold for considering faces as the same person
            
        Returns:
            List of lists, where each inner list contains faces of the same person
        """
        if not faces:
            return []
            
        # Extract encodings
        encodings = [np.array(face["encoding"]) for face in faces]
        
        # Initialize groups
        groups = []
        assigned = [False] * len(faces)
        
        for i in range(len(faces)):
            if assigned[i]:
                continue
                
            # Start a new group
            current_group = [faces[i]]
            assigned[i] = True
            
            # Find similar faces
            for j in range(i + 1, len(faces)):
                if assigned[j]:
                    continue
                    
                # Calculate similarity
                similarity = 1 - np.linalg.norm(encodings[i] - encodings[j])
                
                if similarity >= similarity_threshold:
                    current_group.append(faces[j])
                    assigned[j] = True
            
            groups.append(current_group)
        
        return groups
    
    def match_face_with_profiles(self, db: Session, face_encoding: List[float], 
                               threshold: float = 0.6) -> Tuple[Optional[models.FaceProfile], float]:
        """
        Match a face encoding with existing profiles.
        
        Args:
            db: Database session
            face_encoding: Facial embedding to match
            threshold: Similarity threshold for matching
            
        Returns:
            Tuple of (matched profile, confidence score) or (None, 0.0) if no match
        """
        try:
            import numpy as np
            import face_recognition
            
            # Convert the input encoding to numpy array
            face_encoding_np = np.array(face_encoding)
            
            # Get all face profiles
            face_profiles = self.get_face_profiles(db)
            
            best_match = None
            best_score = 0.0
            
            for profile in face_profiles:
                # Skip profiles without samples
                samples = self.get_face_samples(db, profile.id)
                if not samples:
                    continue
                
                # Compare with each sample
                for sample in samples:
                    if not sample.encoding:
                        continue
                    
                    # Convert sample encoding to numpy array
                    sample_encoding_np = np.array(sample.encoding)
                    
                    # Calculate face distance
                    face_distance = face_recognition.face_distance([sample_encoding_np], face_encoding_np)[0]
                    
                    # Convert distance to similarity score (1 - distance)
                    similarity_score = 1.0 - min(face_distance, 1.0)
                    
                    # Update best match if this is better
                    if similarity_score > threshold and similarity_score > best_score:
                        best_match = profile
                        best_score = similarity_score
            
            return best_match, best_score
            
        except Exception as e:
            logger.error(f"Error matching face: {str(e)}")
            return None, 0.0
    
    def link_face_to_voice_profile(self, db: Session, face_profile_id: int, 
                                 voice_profile_id: int) -> bool:
        """
        Link a face profile to a voice profile.
        
        Args:
            db: Database session
            face_profile_id: ID of the face profile
            voice_profile_id: ID of the voice profile
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the face profile
            face_profile = self.get_face_profile(db, face_profile_id)
            if not face_profile:
                logger.error(f"Face profile not found: {face_profile_id}")
                return False
            
            # Get the voice profile
            voice_profile = db.query(models.VoiceProfile).filter(models.VoiceProfile.id == voice_profile_id).first()
            if not voice_profile:
                logger.error(f"Voice profile not found: {voice_profile_id}")
                return False
            
            # Link the profiles
            face_profile.voice_profile_id = voice_profile_id
            
            # Update metadata
            metadata = face_profile.profile_metadata or {}
            metadata["linked_to_voice_profile"] = {
                "id": voice_profile_id,
                "name": voice_profile.name,
                "linked_at": datetime.now().isoformat()
            }
            face_profile.profile_metadata = metadata
            
            db.commit()
            
            logger.info(f"Linked face profile {face_profile_id} to voice profile {voice_profile_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error linking profiles: {str(e)}")
            return False
    
    def extract_faces_from_speaker_segments(self, db: Session, video_path: str, 
                                         speaker_segments: List[Dict[str, Any]],
                                         output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract faces from video segments where specific speakers are talking.
        
        Args:
            db: Database session
            video_path: Path to the video file
            speaker_segments: List of speaker segments with start/end times
            output_dir: Directory to save extracted face images
            
        Returns:
            Dictionary with extraction results
        """
        try:
            import cv2
            import face_recognition
            
            logger.info(f"Extracting faces from speaker segments in video: {video_path}")
            
            # Create output directory if not provided
            if not output_dir:
                output_dir = str(self.face_profiles_dir / "speaker_faces")
                os.makedirs(output_dir, exist_ok=True)
            
            # Open the video file
            video = cv2.VideoCapture(video_path)
            if not video.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return {"success": False, "error": "Could not open video file"}
            
            # Get video properties
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            logger.info(f"Video properties: FPS={fps}, Frames={frame_count}, Duration={duration:.2f}s")
            
            # Process each speaker segment
            results = []
            
            for segment in speaker_segments:
                speaker_id = segment.get("speaker", {}).get("id") or segment.get("speaker_id")
                speaker_name = segment.get("speaker", {}).get("name") or segment.get("speaker_name", "Unknown")
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                if start_time >= end_time or start_time < 0 or end_time > duration:
                    logger.warning(f"Invalid segment times: {start_time} - {end_time}")
                    continue
                
                logger.info(f"Processing segment for speaker {speaker_name} ({start_time}s - {end_time}s)")
                
                # Calculate frame range
                start_frame = int(start_time * fps)
                end_frame = int(end_time * fps)
                
                # Process frames in this segment
                faces_found = 0
                face_data = []
                current_frame = start_frame
                
                while current_frame <= end_frame:
                    ret, frame = video.read()
                    if not ret:
                        break
                    
                    # Process every 5th frame to avoid too many similar faces
                    if (current_frame - start_frame) % 5 == 0:
                        # Convert BGR to RGB (face_recognition uses RGB)
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Find faces in the frame
                        face_locations = face_recognition.face_locations(rgb_frame)
                        if face_locations:
                            # Get face encodings
                            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                            
                            # Save each face
                            for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                                top, right, bottom, left = face_location
                                face_image = frame[top:bottom, left:right]
                                
                                # Save the face image
                                timestamp = current_frame / fps
                                face_filename = f"speaker_{speaker_id}_{current_frame}_{i}_{timestamp:.2f}.jpg"
                                face_path = os.path.join(output_dir, face_filename)
                                cv2.imwrite(face_path, face_image)
                                
                                # Store face data
                                face_data.append({
                                    "speaker_id": speaker_id,
                                    "speaker_name": speaker_name,
                                    "frame": current_frame,
                                    "timestamp": timestamp,
                                    "location": face_location,
                                    "encoding": face_encoding.tolist(),
                                    "path": face_path
                                })
                                
                                faces_found += 1
                    
                    current_frame += 1
                
                # Add segment results
                results.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "faces_found": faces_found,
                    "face_data": face_data
                })
                
                logger.info(f"Found {faces_found} faces for speaker {speaker_name}")
            
            video.release()
            
            # Calculate total faces found
            total_faces = sum(r["faces_found"] for r in results)
            
            logger.info(f"Completed speaker face extraction. Found {total_faces} faces across {len(results)} segments")
            
            return {
                "success": True,
                "total_faces": total_faces,
                "segments_processed": len(results),
                "results": results,
                "output_dir": output_dir
            }
            
        except Exception as e:
            logger.error(f"Error extracting speaker faces: {str(e)}")
            return {"success": False, "error": str(e)}
