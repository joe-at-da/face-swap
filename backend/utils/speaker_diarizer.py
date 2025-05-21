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
from scipy import linalg

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
    Also implements unsupervised speaker change detection using BIC segmentation.
    """
    
    def __init__(self):
        """Initialize the speaker diarizer."""
        self.known_embeddings = {}
        self.known_face_encodings = {}
        self.known_speakers = {}
        self.min_segment_duration = 5.0  # Much higher: Require at least 5 seconds between speaker changes
        self.bic_lambda = 3.0  # Much higher: BIC penalty parameter (higher = fewer speaker changes)
        self.similarity_threshold = 0.5  # Much lower: Threshold for considering segments from same speaker
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
        
        # Create a copy of the transcription to modify
        diarized_transcription = transcription.copy()
        
        # SPECIAL CASE: Check if this is likely a single speaker throughout
        segments = diarized_transcription.get("segments", [])
        total_duration = 0
        if segments:
            total_duration = segments[-1]["end"] - segments[0]["start"]
        
        # For short clips (under 2 minutes) with few segments, assume single speaker
        if total_duration < 120 and len(segments) < 10:
            logger.info(f"Short clip detected ({total_duration:.1f}s, {len(segments)} segments). Treating as single speaker.")
            # Assign all segments to Speaker 1
            for segment in segments:
                segment["speaker"] = {
                    "id": None,
                    "name": "Speaker 1",
                    "confidence": 0.9
                }
            return diarized_transcription
        
        # Detect speaker changes using BIC segmentation
        speaker_changes = self._detect_speaker_changes(audio_path)
        logger.info(f"Detected {len(speaker_changes)} speaker changes at: {speaker_changes}")
        
        # Group segments by speaker using detected change points
        current_speaker_id = 1
        last_speaker_id = None
        
        # Speaker memory system - track embeddings for each speaker ID
        speaker_embeddings = {}  # speaker_id -> list of embeddings
        speaker_segments = {}    # speaker_id -> count of segments
        
        # Process each segment
        for i, segment in enumerate(diarized_transcription.get("segments", [])):
            start_time = segment["start"]
            end_time = segment["end"]
            segment_middle = (start_time + end_time) / 2
            
            # Check if this segment crosses a speaker change point
            crosses_change = any(start_time < change < end_time for change in speaker_changes)
            
            # Extract audio segment embedding
            segment_embedding = self._process_audio_segment(audio_path, start_time, end_time)
            if segment_embedding is None:
                # Skip speaker analysis if we couldn't get an embedding
                continue
            
            # Initialize speaker variables
            profile_id = None
            confidence = 0.0
            best_speaker_id = None
            best_similarity = -1.0
            
            # Try to match with known profiles if we have embeddings
            if self.known_embeddings:
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
            
            # Try to match with existing speakers in our memory
            for speaker_id, embeddings in speaker_embeddings.items():
                # Use average of all embeddings for this speaker
                avg_embedding = np.mean(embeddings, axis=0)
                similarity = 1 - cosine(avg_embedding, segment_embedding)
                
                # Keep track of best match
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_speaker_id = speaker_id
            
            # Determine if this is a new speaker
            is_new_speaker = False
            
            # If segment crosses a BIC change point, more likely to be a new speaker
            if crosses_change and best_similarity < 0.85:  # Higher threshold when crossing change point
                is_new_speaker = True
            # If no good match with existing speakers
            elif best_speaker_id is None:
                is_new_speaker = True
            
            # Assign speaker ID
            if is_new_speaker:
                current_speaker_id = max(speaker_embeddings.keys(), default=0) + 1
                speaker_embeddings[current_speaker_id] = [segment_embedding]
                speaker_segments[current_speaker_id] = 1
            else:
                # Use the best matching speaker
                current_speaker_id = best_speaker_id
                # Add this embedding to the speaker's history (up to 5 most recent)
                speaker_embeddings[current_speaker_id].append(segment_embedding)
                if len(speaker_embeddings[current_speaker_id]) > 5:
                    speaker_embeddings[current_speaker_id].pop(0)  # Remove oldest
                speaker_segments[current_speaker_id] += 1
            
            last_speaker_id = current_speaker_id
            
            # Add speaker information to segment
            if profile_id and confidence > 0.7:
                # Known speaker
                speaker_info = self.known_speakers[profile_id].copy()
                speaker_info["id"] = profile_id
                speaker_info["confidence"] = confidence
                segment["speaker"] = speaker_info
            else:
                # Unknown speaker with numeric ID
                segment["speaker"] = {
                    "id": None,
                    "name": f"Speaker {current_speaker_id}",
                    "confidence": 0.0
                }
        
        # Post-processing: Force adjacent segments with similar text to have the same speaker
        self._post_process_speakers(diarized_transcription)
        
        return diarized_transcription
        
    def _post_process_speakers(self, transcription: Dict[str, Any]) -> None:
        """
        Post-process speaker assignments to ensure consistency.
        
        This function enforces rules like:
        1. Adjacent segments with very short gaps should have the same speaker
        2. Short segments surrounded by the same speaker should be merged
        
        Args:
            transcription: Transcription data with speaker assignments
        """
        segments = transcription.get("segments", [])
        if len(segments) <= 1:
            return
            
        # First pass: Assign the most frequent speaker ID to all segments
        # For short recordings, this is the most reliable approach
        if len(segments) < 10 and segments[-1]["end"] - segments[0]["start"] < 60:
            # Count speaker occurrences
            speaker_counts = {}
            for segment in segments:
                speaker_name = segment.get("speaker", {}).get("name", "Unknown")
                speaker_counts[speaker_name] = speaker_counts.get(speaker_name, 0) + 1
            
            # Find most frequent speaker
            most_frequent = max(speaker_counts.items(), key=lambda x: x[1])[0]
            
            # Assign all segments to the most frequent speaker
            for segment in segments:
                segment["speaker"] = {
                    "id": None,
                    "name": most_frequent,
                    "confidence": 0.9
                }
            
            return
            
        # For longer recordings, use a more nuanced approach
        # Second pass: Ensure adjacent segments with short gaps have the same speaker
        MAX_GAP = 1.0  # Maximum gap in seconds to consider segments as adjacent
        
        for i in range(1, len(segments)):
            prev_segment = segments[i-1]
            curr_segment = segments[i]
            
            # Check if segments are close in time
            time_gap = curr_segment["start"] - prev_segment["end"]
            
            if time_gap < MAX_GAP:
                # If gap is small, use the same speaker for both segments
                prev_speaker = prev_segment.get("speaker", {}).get("name", "Unknown")
                curr_speaker = curr_segment.get("speaker", {}).get("name", "Unknown")
                
                # If they already have the same speaker, continue
                if prev_speaker == curr_speaker:
                    continue
                    
                # Otherwise, use the speaker with higher confidence or the first one
                prev_confidence = prev_segment.get("speaker", {}).get("confidence", 0.0)
                curr_confidence = curr_segment.get("speaker", {}).get("confidence", 0.0)
                
                if prev_confidence >= curr_confidence:
                    # Use previous speaker for current segment
                    curr_segment["speaker"] = prev_segment["speaker"]
                else:
                    # Use current speaker for previous segment
                    prev_segment["speaker"] = curr_segment["speaker"]
    
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
            
    def _detect_speaker_changes(self, audio_path: str, window_size: float = 2.0, step_size: float = 0.5) -> List[float]:
        """
        Detect speaker changes in an audio file using BIC segmentation.
        
        Args:
            audio_path: Path to the audio file
            window_size: Size of the analysis window in seconds
            step_size: Step size for sliding window in seconds
            
        Returns:
            List of timestamps where speaker changes occur
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Convert window and step size to samples
            window_samples = int(window_size * sr)
            step_samples = int(step_size * sr)
            
            change_points = []
            
            # Slide window through audio
            for i in range(0, len(y) - window_samples, step_samples):
                # Skip if we're too close to the beginning or end
                if i < window_samples or i > len(y) - 2 * window_samples:
                    continue
                    
                # Get two adjacent windows
                window1 = y[i - window_samples:i]
                window2 = y[i:i + window_samples]
                
                # Compute MFCC features for both windows
                mfcc1 = librosa.feature.mfcc(y=window1, sr=sr, n_mfcc=13)
                mfcc2 = librosa.feature.mfcc(y=window2, sr=sr, n_mfcc=13)
                
                # Compute BIC score
                bic_score = self._compute_bic(mfcc1.T, mfcc2.T)
                
                # If BIC score is above threshold, mark as change point
                if bic_score > 0:
                    change_time = i / sr
                    # Only add if it's not too close to an existing change point
                    if not change_points or min(abs(change_time - cp) for cp in change_points) > self.min_segment_duration:
                        change_points.append(change_time)
            
            return sorted(change_points)
            
        except Exception as e:
            logger.error(f"Error detecting speaker changes: {e}")
            return []
    
    def _compute_bic(self, X1: np.ndarray, X2: np.ndarray) -> float:
        """
        Compute BIC score for two feature matrices.
        
        Args:
            X1: Feature matrix for first window
            X2: Feature matrix for second window
            
        Returns:
            BIC score (positive value indicates different speakers)
        """
        # Combine the two windows
        X = np.vstack((X1, X2))
        
        # Compute covariance matrices
        n1 = X1.shape[0]
        n2 = X2.shape[0]
        n = n1 + n2
        d = X1.shape[1]  # Feature dimension
        
        cov1 = np.cov(X1, rowvar=False) + 1e-10 * np.eye(d)
        cov2 = np.cov(X2, rowvar=False) + 1e-10 * np.eye(d)
        cov = np.cov(X, rowvar=False) + 1e-10 * np.eye(d)
        
        # Compute BIC
        bic = 0.5 * (n * np.log(np.linalg.det(cov)) - n1 * np.log(np.linalg.det(cov1)) - n2 * np.log(np.linalg.det(cov2)))
        
        # Apply penalty
        penalty = 0.5 * self.bic_lambda * (d + 0.5 * d * (d + 1)) * np.log(n)
        
        return bic - penalty
