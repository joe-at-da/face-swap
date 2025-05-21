"""
Speaker diarization module for identifying speakers in audio files.
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
import subprocess
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import shutil
import uuid
import librosa
import face_recognition
from scipy.spatial.distance import cosine
from pydub import AudioSegment

# Set up logging
logger = logging.getLogger(__name__)

# Voice profiles directory
VOICE_PROFILES_DIR = Path("/app/data/voice_profiles")
VOICE_SAMPLES_DIR = VOICE_PROFILES_DIR / "samples"
VOICE_EMBEDDINGS_DIR = VOICE_PROFILES_DIR / "embeddings"

# Ensure directories exist
VOICE_PROFILES_DIR.mkdir(exist_ok=True, parents=True)
VOICE_SAMPLES_DIR.mkdir(exist_ok=True, parents=True)
VOICE_EMBEDDINGS_DIR.mkdir(exist_ok=True, parents=True)

# Voice profiles database file
VOICE_PROFILES_DB = VOICE_PROFILES_DIR / "profiles.json"


class SpeakerDiarizer:
    """
    Class for performing speaker diarization on audio files.
    Uses voice embeddings to identify speakers from a database of known voices.
    Can also use facial recognition to improve accuracy when video is available.
    """
    
    def __init__(self):
        """Initialize the speaker diarizer."""
        self.known_embeddings = {}
        self.known_face_encodings = {}
        self.known_speakers = {}
        self.load_voice_profiles()
    
    def load_voice_profiles(self):
        """Load voice profiles from the database."""
        if not VOICE_PROFILES_DB.exists():
            logger.warning("Voice profiles database not found. Creating empty database.")
            with open(VOICE_PROFILES_DB, 'w') as f:
                json.dump({"profiles": []}, f)
            return
        
        try:
            with open(VOICE_PROFILES_DB, 'r') as f:
                data = json.load(f)
                profiles = data.get("profiles", [])
            
            for profile in profiles:
                profile_id = profile["id"]
                self.known_speakers[profile_id] = {
                    "name": profile["name"],
                    "role": profile.get("role", ""),
                    "party": profile.get("party", ""),
                }
                
                # Load voice embeddings if they exist
                embedding_file = VOICE_EMBEDDINGS_DIR / f"{profile_id}.npy"
                if embedding_file.exists():
                    self.known_embeddings[profile_id] = np.load(embedding_file)
                else:
                    # Generate embeddings from samples
                    self._generate_embeddings_for_profile(profile_id)
        
        except Exception as e:
            logger.error(f"Error loading voice profiles: {e}")
    
    def _generate_embeddings_for_profile(self, profile_id: str):
        """Generate voice embeddings for a profile from its audio samples."""
        profile_dir = VOICE_SAMPLES_DIR / profile_id
        if not profile_dir.exists():
            logger.warning(f"No samples found for profile {profile_id}")
            return
        
        samples = list(profile_dir.glob("*.mp3"))
        if not samples:
            logger.warning(f"No MP3 samples found for profile {profile_id}")
            return
        
        embeddings = []
        for sample_path in samples:
            try:
                # Extract embedding from audio sample
                embedding = self._extract_voice_embedding(str(sample_path))
                if embedding is not None:
                    embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error extracting embedding from {sample_path}: {e}")
        
        if embeddings:
            # Average the embeddings
            avg_embedding = np.mean(embeddings, axis=0)
            # Normalize
            avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
            # Save
            self.known_embeddings[profile_id] = avg_embedding
            np.save(VOICE_EMBEDDINGS_DIR / f"{profile_id}.npy", avg_embedding)
            
            # Update confidence score in profile
            self._update_profile_confidence(profile_id, len(embeddings))
    
    def _update_profile_confidence(self, profile_id: str, sample_count: int):
        """Update the confidence score for a profile based on sample count."""
        try:
            with open(VOICE_PROFILES_DB, 'r') as f:
                data = json.load(f)
            
            for profile in data.get("profiles", []):
                if profile["id"] == profile_id:
                    # Calculate confidence score based on sample count
                    # More samples = higher confidence, max out at 10 samples
                    confidence = min(sample_count / 10, 1.0)
                    profile["confidence_score"] = confidence
                    break
            
            with open(VOICE_PROFILES_DB, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        except Exception as e:
            logger.error(f"Error updating profile confidence: {e}")
    
    def _extract_voice_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """
        Extract voice embedding from an audio file using librosa.
        
        This is a simplified version. In a production system, you would use
        a specialized voice embedding model like x-vector or d-vector.
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            
            # Take the mean of MFCCs as a simple embedding
            embedding = np.mean(mfccs, axis=1)
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
        
        except Exception as e:
            logger.error(f"Error extracting voice embedding: {e}")
            return None
    
    def _extract_face_encodings(self, video_path: str, segment_start: float, segment_end: float) -> List[np.ndarray]:
        """
        Extract face encodings from video frames during a specific time segment.
        
        Args:
            video_path: Path to the video file
            segment_start: Start time of the segment in seconds
            segment_end: End time of the segment in seconds
            
        Returns:
            List of face encodings found in the frames
        """
        try:
            # Create a temporary directory for frames
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract frames from the video segment
                frame_rate = 1  # Extract 1 frame per second
                frame_cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-ss", str(segment_start),
                    "-to", str(segment_end),
                    "-r", str(frame_rate),
                    "-q:v", "1",
                    f"{temp_dir}/frame_%04d.jpg"
                ]
                
                subprocess.run(frame_cmd, check=True, capture_output=True)
                
                # Process extracted frames
                face_encodings = []
                for frame_path in sorted(Path(temp_dir).glob("frame_*.jpg")):
                    # Load image
                    image = face_recognition.load_image_file(str(frame_path))
                    
                    # Find faces
                    face_locations = face_recognition.face_locations(image)
                    
                    # Get face encodings
                    if face_locations:
                        encodings = face_recognition.face_encodings(image, face_locations)
                        face_encodings.extend(encodings)
                
                return face_encodings
        
        except Exception as e:
            logger.error(f"Error extracting face encodings: {e}")
            return []
    
    def _match_voice_to_profile(self, voice_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Match a voice embedding to a known profile.
        
        Args:
            voice_embedding: Voice embedding to match
            
        Returns:
            Tuple of (profile_id, similarity_score)
        """
        best_match = None
        best_score = 0.0
        
        for profile_id, known_embedding in self.known_embeddings.items():
            # Calculate cosine similarity (1 - cosine distance)
            similarity = 1 - cosine(voice_embedding, known_embedding)
            
            if similarity > best_score and similarity > 0.7:  # Threshold for matching
                best_score = similarity
                best_match = profile_id
        
        return best_match, best_score
    
    def _match_face_to_profile(self, face_encoding: np.ndarray) -> Optional[str]:
        """
        Match a face encoding to a known profile.
        
        Args:
            face_encoding: Face encoding to match
            
        Returns:
            Profile ID if a match is found, None otherwise
        """
        # This is a placeholder. In a real implementation, you would:
        # 1. Maintain a database of face encodings for known speakers
        # 2. Compare the given face encoding with known encodings
        # 3. Return the profile ID of the best match
        
        # For now, we'll return None as we don't have face data
        return None
    
    def diarize(
        self, 
        audio_path: str, 
        transcription: Dict[str, Any], 
        video_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform speaker diarization on an audio file.
        
        Args:
            audio_path: Path to the audio file
            transcription: Transcription data (Whisper format)
            video_path: Optional path to the video file for facial recognition
            
        Returns:
            Updated transcription with speaker information
        """
        logger.info(f"Performing speaker diarization on {audio_path}")
        
        # Check if we have any known speakers
        if not self.known_embeddings:
            logger.warning("No known voice profiles found. Skipping diarization.")
            return transcription
        
        # Create a copy of the transcription to modify
        diarized_transcription = transcription.copy()
        
        # Process each segment
        for i, segment in enumerate(diarized_transcription.get("segments", [])):
            start_time = segment["start"]
            end_time = segment["end"]
            
            # Extract audio segment
            segment_embedding = self._process_audio_segment(audio_path, start_time, end_time)
            
            # Match voice to profile
            profile_id = None
            confidence = 0.0
            
            if segment_embedding is not None:
                profile_id, confidence = self._match_voice_to_profile(segment_embedding)
            
            # If video is available and we have a face, use it to confirm or improve match
            if video_path and os.path.exists(video_path):
                face_encodings = self._extract_face_encodings(video_path, start_time, end_time)
                
                if face_encodings:
                    # Use the first face (assuming main speaker)
                    face_profile_id = self._match_face_to_profile(face_encodings[0])
                    
                    if face_profile_id:
                        # If face and voice match, increase confidence
                        if face_profile_id == profile_id:
                            confidence += 0.2
                        # If face matches someone else with high confidence, override voice match
                        elif confidence < 0.8:
                            profile_id = face_profile_id
                            confidence = 0.8
            
            # Add speaker information to segment
            if profile_id and confidence > 0.7:
                speaker_info = self.known_speakers[profile_id].copy()
                speaker_info["id"] = profile_id
                speaker_info["confidence"] = confidence
                segment["speaker"] = speaker_info
            else:
                # Unknown speaker
                segment["speaker"] = {
                    "id": None,
                    "name": "Unknown Speaker",
                    "confidence": 0.0
                }
        
        return diarized_transcription
    
    def _process_audio_segment(self, audio_path: str, start_time: float, end_time: float) -> Optional[np.ndarray]:
        """
        Process an audio segment and extract voice embedding.
        
        Args:
            audio_path: Path to the audio file
            start_time: Start time of the segment in seconds
            end_time: End time of the segment in seconds
            
        Returns:
            Voice embedding for the segment
        """
        try:
            # Create a temporary file for the segment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Extract segment using ffmpeg
            segment_cmd = [
                "ffmpeg",
                "-i", audio_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-q:a", "0",
                "-map", "a",
                temp_path
            ]
            
            subprocess.run(segment_cmd, check=True, capture_output=True)
            
            # Extract embedding from segment
            embedding = self._extract_voice_embedding(temp_path)
            
            # Clean up
            os.unlink(temp_path)
            
            return embedding
        
        except Exception as e:
            logger.error(f"Error processing audio segment: {e}")
            return None
