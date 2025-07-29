#!/usr/bin/env python3
"""
Speaker Diarization for Parliament TV Audio

This script performs speaker diarization on Parliament TV audio files,
identifying different speakers and when they are speaking.

Usage:
    python speaker_diarization.py <audio_file> [--output OUTPUT_FILE] [--model MODEL_SIZE]

Example:
    python speaker_diarization.py /app/data/temp/audio_extracts/capture_0312.audio.mp3 --output /app/data/temp/diarized_0312.json
"""

import os
import sys
import json
import time
import argparse
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# We no longer need voice profile manager since we only care about voice changes
VOICE_PROFILE_MANAGER_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("speaker_diarization")

# Constants
# These constants are kept for backward compatibility but are no longer used
# since we've simplified the system to only detect voice changes, not identify speakers
VOICE_PROFILES_DIR = Path("/app/data/voice_profiles")
VOICE_ENCODINGS_FILE = Path("/app/data/voice_encodings.json")

class SpeakerDiarizer:
    """Class to handle speaker diarization in audio files."""
    
    def __init__(self, voice_encodings_file: Path = VOICE_ENCODINGS_FILE):
        """Initialize the speaker diarizer.
        
        We've simplified this to only detect voice changes, not identify speakers.
        """
        # We keep the voice_encodings_file parameter for backward compatibility
        # but we don't actually use it anymore
        self.voice_encodings_file = voice_encodings_file
        # These are kept as empty lists for backward compatibility
        self.known_voice_encodings = []
        self.known_voice_names = []
        self.known_voice_metadata = []
    
    def load_voice_database(self) -> bool:
        """Simplified stub for loading voice encodings database.
        We don't need voice profiles since we only care about voice changes."""
        logger.info("Voice database loading skipped - we only care about voice changes, not speaker identity")
        return False
    
    def update_voice_database(self) -> bool:
        """Simplified stub for updating voice encodings database.
        We don't need voice profiles since we only care about voice changes.
        
        Returns:
            bool: Always False since we don't need voice profiles
        """
        logger.info("Voice database update skipped - we only care about voice changes, not speaker identity")
        return False
    
    # We've simplified the speaker diarization to only detect voice changes
    # No speaker identification or voice profile matching is performed
    
    def _create_diarization_results(self, audio_path: Path, output_path: Path) -> Dict:
        """
        Create diarization results by analyzing the audio content.
        Simply detect when voice changes and create speech groups accordingly.
        
        Args:
            audio_path: Path to the input audio
            output_path: Path to save the output JSON
            
        Returns:
            Dict with diarization results
        """
        logger.info(f"Starting speaker diarization on: {audio_path}")
        
        # Get audio duration
        try:
            audio_duration = self._get_audio_duration(audio_path)
            logger.info(f"Audio duration: {audio_duration} seconds")
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            audio_duration = 600  # Default to 10 minutes
        
        # Maximum gap between segments from same speaker to still be considered same speech group
        # We only care about speaker changes, not pauses
        
        try:
            # Use an improved approach for speaker segmentation
            # This doesn't require Hugging Face authentication
            import librosa
            import numpy as np
            from scipy.signal import medfilt
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics.pairwise import cosine_similarity
            
            logger.info("Using improved speaker segmentation without Hugging Face dependency")
            
            # Get audio duration first to determine if we need chunking
            audio_duration = self._get_audio_duration(audio_path)
            logger.info(f"Audio duration: {audio_duration} seconds")
            
            # For very long audio files (over 60 minutes), use chunking to avoid memory issues
            MAX_CHUNK_DURATION = 60 * 60  # 60 minutes in seconds
            
            if audio_duration > MAX_CHUNK_DURATION:
                logger.info(f"Long audio detected ({audio_duration/60:.1f} minutes). Using chunked processing.")
                return self._process_long_audio(audio_path, output_path, audio_duration, MAX_CHUNK_DURATION)
                
            # For shorter files, load the entire audio
            logger.info("Loading entire audio file into memory")
            y, sr = librosa.load(str(audio_path), sr=None)
            
            # Parameters for analysis - balanced window size for accurate speaker change detection
            window_size = 2.0   # 2.0 second windows for analysis (balanced between precision and stability)
            step_size = 0.5     # 0.5 second steps between windows (balanced resolution)
            
            # We'll use dynamic thresholding instead of a fixed threshold
            # This adapts to the specific audio characteristics
            
            # Convert window and step size to samples
            window_samples = int(window_size * sr)
            step_samples = int(step_size * sr)
            
            # Calculate number of windows
            n_windows = max(1, int((len(y) - window_samples) / step_samples) + 1)
            logger.info(f"Analyzing with {n_windows} windows of {window_size}s each")
            
            # Skip if audio is too short
            # Extract features for each window
            window_features = []
            window_times = []
            
            # Function to extract features focused on voice characteristics
            def extract_features(window_audio, sr):
                # MFCCs capture vocal tract characteristics (voice identity)
                mfcc = librosa.feature.mfcc(y=window_audio, sr=sr, n_mfcc=13)
                
                # Spectral contrast (voice timbre)
                contrast = librosa.feature.spectral_contrast(y=window_audio, sr=sr)
                
                # Chroma features (pitch content)
                chroma = librosa.feature.chroma_stft(y=window_audio, sr=sr)
                
                # Combine and flatten features - focusing on voice identity characteristics
                # rather than energy or pause-based features
                features = np.concatenate([
                    np.mean(mfcc, axis=1),      # Voice identity
                    np.mean(contrast, axis=1),  # Voice timbre
                    np.mean(chroma, axis=1)     # Pitch content
                ])
                
                return features.tolist()  # Convert to Python list
            
            for i in range(n_windows):
                start_sample = i * step_samples
                end_sample = start_sample + window_samples
                
                if end_sample <= len(y):
                    window_audio = y[start_sample:end_sample]
                    window_time = float(start_sample / sr)  # Convert to Python float
                    
                    # Process all windows, don't skip based on silence
                    
                    # Extract features for this window
                    features = extract_features(window_audio, sr)
                    
                    window_features.append(features)
                    window_times.append(window_time)
            
            # Convert to numpy array for processing
            window_features = np.array(window_features)
            
            # Standardize features
            if len(window_features) > 1:
                from sklearn.preprocessing import StandardScaler
                scaler = StandardScaler()
                window_features = scaler.fit_transform(window_features)
            
            # Calculate similarity between adjacent windows
            similarities = []
            for i in range(1, len(window_features)):
                # Use cosine similarity directly
                from sklearn.metrics.pairwise import cosine_similarity
                sim = float(cosine_similarity([window_features[i-1]], [window_features[i]])[0][0])
                similarities.append(sim)
            
            # Apply median filter to smooth out similarities
            if len(similarities) > 5:
                similarities = medfilt(similarities, 5).tolist()  # Increased filter size for better smoothing
            
            # Use dynamic thresholding - find local minima in similarity
            from scipy.signal import find_peaks
            # Invert similarities to find peaks (which are actually dips in similarity)
            inv_similarities = [1.0 - sim for sim in similarities]  # Python list comprehension
            
            # Skip energy-based detection as it relies on pauses/volume changes
            # Focus purely on voice characteristics through feature comparison
            
            # Find peaks with balanced adaptive thresholding
            # Calculate average similarity for reference
            avg_similarity = float(np.mean(similarities)) if similarities else 0.9
            
            # Use a balanced adaptive multiplier that scales based on average similarity
            # Higher threshold for more similar audio to avoid false positives
            adaptive_multiplier = 1.8 if avg_similarity > 0.9 else 1.5
            
            # Balanced prominence threshold - not too sensitive, not too strict
            prominence = max(0.12, float(np.std(inv_similarities) * adaptive_multiplier))
            
            # Use a more conservative minimum distance between peaks
            # With step_size of 0.5, this allows peaks to be as close as 3 seconds apart
            min_distance = int(3.0/step_size)
            
            # Find peaks with these adaptive parameters
            peaks, peak_properties = find_peaks(np.array(inv_similarities), 
                                              prominence=prominence, 
                                              distance=min_distance)
            
            # Log detailed information about the parameters used
            logger.info(f"Average similarity between adjacent windows: {avg_similarity:.3f}")
            logger.info(f"Using prominence threshold: {prominence:.3f} for peak detection")
            logger.info(f"Using minimum distance between peaks: {min_distance} windows ({min_distance * step_size:.2f} seconds)")
            
            # Focus on general algorithm performance, not specific timestamps
            logger.info(f"Total windows analyzed: {len(window_times)}")
            logger.info(f"Window size: {window_size:.1f}s, Step size: {step_size:.2f}s")
            
            # Log basic information about detected peaks
            if hasattr(peak_properties, 'get') and 'prominences' in peak_properties:
                all_prominences = peak_properties['prominences']
                logger.info(f"Found {len(all_prominences)} peaks with average prominence: {np.mean(all_prominences):.3f}")
                        
            # No special handling for specific timestamps - rely on the algorithm to detect changes naturally
            
            # Sort peaks by position
            peaks = np.sort(peaks)
            
            # These peaks represent potential speaker changes
            # Convert to regular Python list
            change_indices = [int(idx) for idx in peaks.tolist()]
            
            # Convert indices to timestamps (using Python native types)
            change_times = [float(window_times[i+1]) for i in change_indices]  # +1 because we're comparing i-1 and i
            
            logger.info(f"Detected {len(change_times)} speaker changes")
            if change_times:  # Use Python's truthiness check
                logger.info(f"Changes at seconds: {[f'{t:.1f}' for t in change_times]}")
                
            # Calculate average similarity for debugging
            avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
            logger.info(f"Average similarity between adjacent windows: {avg_similarity:.3f}")
            logger.info(f"Using prominence threshold: {prominence:.3f} for peak detection")
            
            # Create segments based on detected speaker changes
            segments = []
            speech_groups = {}
            
            # Add start and end points to create complete segments
            all_change_points = [0.0] + change_times + [float(audio_duration)]
            logger.info(f"Creating {len(all_change_points)-1} segments between change points")
            
            # Process each segment between change points
            for i in range(len(all_change_points) - 1):
                start_time = all_change_points[i]
                end_time = all_change_points[i + 1]
                segment_duration = end_time - start_time
                
                # Skip very short segments (less than 0.5 seconds)
                if segment_duration < 0.5:
                    logger.info(f"Skipping very short segment: {start_time:.1f}-{end_time:.1f} ({segment_duration:.1f}s)")
                    continue
                
                # Each segment gets its own speech group ID
                speech_group_id = i + 1
                speaker_id = f"SPEAKER_{speech_group_id}"
                
                # Create segment with Python native types
                segment = {
                    "speaker": speaker_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": segment_duration,
                    "speech_group_id": speech_group_id
                }
                segments.append(segment)
                
                # Create speech group with Python native types
                speech_groups[speech_group_id] = {
                    "speaker": speaker_id,
                    "segments": [segment],
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": segment_duration
                }
                
                # We already set last_speaker above, no need to set it again
                # And we don't use last_end_time anymore since we're not using pauses
            
            # Create a simple speakers dictionary - we don't really care about speaker identities
            # but the rest of the code expects this structure
            speakers = {}
            for segment in segments:
                speaker_id = segment["speaker"]
                if speaker_id not in speakers:
                    speakers[speaker_id] = {
                        "segments": 0,
                        "total_duration": 0,
                        "metadata": {},
                        "speech_groups": set()
                    }
                
                speakers[speaker_id]["segments"] += 1
                speakers[speaker_id]["total_duration"] += segment["duration"]
                # Add the speech group ID to the set (convert to int first to avoid numpy type issues)
                speakers[speaker_id]["speech_groups"].add(int(segment["speech_group_id"]))
            
            logger.info(f"Diarization completed: found {len(segments)} segments in {len(speech_groups)} speech groups")
            
        except Exception as e:
            logger.error(f"Error in diarization: {e}")
            raise  # Re-raise the exception instead of using fallbacks
        
        # Convert speech_groups from dict to list for JSON serialization
        speech_groups_list = list(speech_groups.values()) if isinstance(speech_groups, dict) else []
        
        # Convert speech_groups sets to lists for JSON serialization
        for speaker_id, speaker_data in speakers.items():
            if isinstance(speaker_data["speech_groups"], set):
                speaker_data["speech_groups"] = list(speaker_data["speech_groups"])
        
        # Group segments by speech_group_id
        speech_groups = {}
        for segment in segments:
            group_id = segment["speech_group_id"]
            if group_id not in speech_groups:
                speech_groups[group_id] = {
                    "speaker": segment["speaker"],
                    "segments": [],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "duration": segment["duration"]
                }
            else:
                # Update group information
                speech_groups[group_id]["end_time"] = segment["end_time"]
                speech_groups[group_id]["duration"] += segment["duration"]
            
            # Add segment to its group
            speech_groups[group_id]["segments"].append(segment)
        
        # Create the results dictionary
        diarization_results = {
            "input_file": str(audio_path),
            "output_file": str(output_path),
            "speakers": speakers,
            "segments": segments,
            "speech_groups": speech_groups,
            "processing_info": {
                "processed_at": datetime.now().isoformat(),
                "total_duration": audio_duration,
                "model": "basic",
                "num_speakers": len(speakers),
                "num_speech_groups": len(speech_groups)
            }
        }
        
        logger.info(f"Created diarization with {len(speakers)} speakers and {len(segments)} segments")
        
        # Save the results to a JSON file
        try:
            with open(output_path, 'w') as f:
                json.dump(diarization_results, f, indent=2)
            logger.info(f"Diarization results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving diarization results: {e}")
        
        # Apply basic speaker identification
        try:
            self._basic_speaker_identification(diarization_results)
        except Exception as e:
            logger.error(f"Error applying speaker identification: {e}")
        
        return diarization_results
        
    def diarize_audio(self, audio_path: Path, output_path: Path = None, model: str = None) -> Dict:
        """Diarize an audio file - detect speaker changes and create speech groups.
        
        Args:
            audio_path: Path to the audio file
            output_path: Path to save the diarization results (optional)
            model: Model to use for diarization (optional)
            
        Returns:
            Dict with diarization results
        """
        logger.info(f"Diarizing audio: {audio_path}")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Set default output path if not provided
        if output_path is None:
            output_path = audio_path.with_suffix(".diarization.json")
            
        # Check if output file already exists - if so, we can skip processing
        if os.path.exists(output_path):
            logger.info(f"Diarization file already exists: {output_path}")
            try:
                with open(output_path, 'r') as f:
                    existing_results = json.load(f)
                    
                # Verify the file has the expected structure
                if "segments" in existing_results and "speakers" in existing_results:
                    logger.info(f"Using existing diarization results with {len(existing_results.get('segments', []))} segments")
                    return existing_results
                else:
                    logger.warning(f"Existing diarization file has invalid structure, will reprocess")
            except Exception as e:
                logger.warning(f"Error reading existing diarization file: {str(e)}, will reprocess")
        
        # Create diarization results with proper speech groups
        # We only care about detecting when voice changes, not who is speaking
        diarization_results = self._create_diarization_results(audio_path, output_path)
        
        # Add simple display names to speakers for UI purposes
        # This doesn't affect the actual diarization or speech groups
        for speaker_id, speaker_info in diarization_results["speakers"].items():
            # Just use a simple naming scheme
            if speaker_id.startswith("SPEAKER_"):
                # Extract number from speaker ID
                import re
                match = re.search(r'\d+', speaker_id)
                if match:
                    number = match.group(0)
                    speaker_name = f"Speaker {number}"
                else:
                    speaker_name = "Unknown Speaker"
            else:
                speaker_name = f"Speaker {speaker_id[-4:]}"
            
            # Add display name but keep original ID
            speaker_info["name"] = speaker_name
        
        # Update segments with speaker names
        for segment in diarization_results["segments"]:
            speaker_id = segment["speaker"]
            segment["speaker_name"] = diarization_results["speakers"][speaker_id]["name"]
        
        return diarization_results
    
    def match_speakers_with_known_voices(self, diarization_results: Dict) -> Dict:
        """
        Simplified stub for speaker matching - we don't care about speaker identification,
        only about detecting when voice changes.
        
        Args:
            diarization_results: Diarization results from diarize_audio
            
        Returns:
            Dict with diarization results (unchanged)
        """
        logger.info("Speaker identification skipped - we only care about voice changes, not speaker identity")
        return diarization_results
    
    def _match_speakers_with_voice_profiles(self, diarization_results: Dict) -> Dict:
        """
        Simplified stub for voice profile matching - we don't care about speaker identification,
        only about detecting when voice changes.
        
        Args:
            diarization_results: Diarization results from diarize_audio
            
        Returns:
            Dict with diarization results (unchanged)
        """
        logger.info("Voice profile matching skipped - we only care about voice changes, not speaker identity")
        return diarization_results
    
    def _check_voice_profile_manager_available(self) -> bool:
        """
        Check if the voice profile manager is available.
        
        Returns:
            False - we don't need voice profile manager anymore
        """
        return False
    
    def _get_database_uri(self) -> str:
        """
        Simplified stub for getting database URI.
        We don't need database access since we only care about voice changes.
        
        Returns:
            Empty string since we don't need database access
        """
        logger.info("Database access skipped - we only care about voice changes, not speaker identity")
        return ""
    
    def _process_long_audio(self, audio_path: Path, output_path: Path, audio_duration: float, chunk_size: float) -> Dict:
        """
        Process a long audio file by splitting it into chunks, processing each chunk,
        and then merging the results.
        
        Args:
            audio_path: Path to the audio file
            output_path: Path to save the output
            audio_duration: Total duration of the audio in seconds
            chunk_size: Maximum duration of each chunk in seconds
            
        Returns:
            Dict with merged diarization results
        """
        import librosa
        import numpy as np
        import tempfile
        import subprocess
        from pathlib import Path
        
        logger.info(f"Processing long audio file in chunks of {chunk_size/60:.1f} minutes")
        
        # Create a temporary directory for chunk files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Calculate number of chunks needed
            num_chunks = int(np.ceil(audio_duration / chunk_size))
            logger.info(f"Splitting audio into {num_chunks} chunks")
            
            all_segments = []
            all_speech_groups = {}
            next_speech_group_id = 1
            
            # Process each chunk
            for i in range(num_chunks):
                chunk_start = i * chunk_size
                chunk_end = min((i + 1) * chunk_size, audio_duration)
                chunk_duration = chunk_end - chunk_start
                
                logger.info(f"Processing chunk {i+1}/{num_chunks}: {chunk_start:.1f}s to {chunk_end:.1f}s ({chunk_duration/60:.1f} minutes)")
                
                # Create chunk file path
                chunk_file = temp_dir_path / f"chunk_{i}.wav"
                chunk_output = temp_dir_path / f"chunk_{i}_diarization.json"
                
                # Extract chunk using ffmpeg
                cmd = [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-ss", str(chunk_start),
                    "-t", str(chunk_duration),
                    "-i", str(audio_path),
                    str(chunk_file)
                ]
                
                try:
                    # Extract the chunk with ffmpeg
                    subprocess.run(cmd, check=True)
                    logger.info(f"Created chunk file: {chunk_file}")
                    
                    # Process this chunk
                    logger.info(f"Loading chunk {i+1}/{num_chunks} into memory")
                    y, sr = librosa.load(str(chunk_file), sr=None)
                    
                    # Process this chunk with our standard diarization logic
                    chunk_results = self._process_audio_chunk(y, sr, chunk_file, chunk_output, chunk_start)
                    
                    # Adjust timestamps by adding chunk_start offset
                    chunk_segments = chunk_results.get("segments", [])
                    chunk_speech_groups = chunk_results.get("speech_groups", {})
                    
                    # Add segments with adjusted timestamps
                    for segment in chunk_segments:
                        # Adjust segment timestamps
                        segment["start_time"] += chunk_start
                        segment["end_time"] += chunk_start
                        
                        # Update speech group ID to avoid conflicts
                        old_group_id = segment["speech_group_id"]
                        segment["speech_group_id"] = next_speech_group_id
                        
                        # Update speaker ID to match new group ID
                        segment["speaker"] = f"SPEAKER_{next_speech_group_id}"
                        
                        all_segments.append(segment)
                        
                        # Create corresponding speech group
                        all_speech_groups[next_speech_group_id] = {
                            "speaker": segment["speaker"],
                            "segments": [segment],
                            "start_time": segment["start_time"],
                            "end_time": segment["end_time"],
                            "duration": segment["duration"]
                        }
                        
                        next_speech_group_id += 1
                    
                    logger.info(f"Processed chunk {i+1}/{num_chunks}: found {len(chunk_segments)} segments")
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
                    raise
            
            # Create speakers dictionary
            speakers = {}
            for segment in all_segments:
                speaker_id = segment["speaker"]
                if speaker_id not in speakers:
                    speakers[speaker_id] = {
                        "segments": 0,
                        "total_duration": 0,
                        "metadata": {},
                        "speech_groups": set()
                    }
                
                speakers[speaker_id]["segments"] += 1
                speakers[speaker_id]["total_duration"] += segment["duration"]
                speakers[speaker_id]["speech_groups"].add(int(segment["speech_group_id"]))
            
            # Convert speech_groups sets to lists for JSON serialization
            for speaker_id, speaker_data in speakers.items():
                if isinstance(speaker_data["speech_groups"], set):
                    speaker_data["speech_groups"] = list(speaker_data["speech_groups"])
            
            # Create the final results dictionary
            diarization_results = {
                "input_file": str(audio_path),
                "output_file": str(output_path),
                "speakers": speakers,
                "segments": all_segments,
                "speech_groups": all_speech_groups,
                "processing_info": {
                    "processed_at": datetime.now().isoformat(),
                    "total_duration": audio_duration,
                    "model": "basic",
                    "num_speakers": len(speakers),
                    "num_speech_groups": len(all_speech_groups),
                    "chunked_processing": True,
                    "num_chunks": num_chunks
                }
            }
            
            logger.info(f"Chunked processing complete: found {len(all_segments)} segments in {len(all_speech_groups)} speech groups")
            
            # Save the results to a JSON file
            try:
                with open(output_path, 'w') as f:
                    json.dump(diarization_results, f, indent=2)
                logger.info(f"Diarization results saved to: {output_path}")
            except Exception as e:
                logger.error(f"Error saving diarization results: {e}")
            
            return diarization_results
    
    def _process_audio_chunk(self, y, sr, audio_path, output_path, time_offset=0.0):
        """
        Process a single audio chunk with our standard diarization logic.
        
        Args:
            y: Audio data
            sr: Sample rate
            audio_path: Path to the audio chunk file (for logging)
            output_path: Path to save the output for this chunk
            time_offset: Time offset in seconds for this chunk
            
        Returns:
            Dict with diarization results for this chunk
        """
        import numpy as np
        import librosa
        from scipy.signal import medfilt
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics.pairwise import cosine_similarity
        from scipy.signal import find_peaks
        
        logger.info(f"Processing audio chunk: {audio_path}")
        
        # Parameters for analysis - balanced window size for accurate speaker change detection
        window_size = 2.0   # 2.0 second windows for analysis (balanced between precision and stability)
        step_size = 0.5     # 0.5 second steps between windows (balanced resolution)
        
        # Convert window and step size to samples
        window_samples = int(window_size * sr)
        step_samples = int(step_size * sr)
        
        # Calculate number of windows
        n_windows = max(1, int((len(y) - window_samples) / step_samples) + 1)
        logger.info(f"Analyzing with {n_windows} windows of {window_size}s each")
        
        # Extract features for each window
        window_features = []
        window_times = []
        
        # Function to extract features focused on voice characteristics
        def extract_features(window_audio, sr):
            # MFCCs capture vocal tract characteristics (voice identity)
            mfcc = librosa.feature.mfcc(y=window_audio, sr=sr, n_mfcc=13)
            
            # Spectral contrast (voice timbre)
            contrast = librosa.feature.spectral_contrast(y=window_audio, sr=sr)
            
            # Chroma features (pitch content)
            chroma = librosa.feature.chroma_stft(y=window_audio, sr=sr)
            
            # Combine and flatten features - focusing on voice identity characteristics
            features = np.concatenate([
                np.mean(mfcc, axis=1),      # Voice identity
                np.mean(contrast, axis=1),  # Voice timbre
                np.mean(chroma, axis=1)     # Pitch content
            ])
            
            return features.tolist()
        
        for i in range(n_windows):
            start_sample = i * step_samples
            end_sample = start_sample + window_samples
            
            if end_sample <= len(y):
                window_audio = y[start_sample:end_sample]
                window_time = float(start_sample / sr)  # Convert to Python float
                
                # Extract features for this window
                features = extract_features(window_audio, sr)
                
                window_features.append(features)
                window_times.append(window_time)
        
        # Convert to numpy array for processing
        window_features = np.array(window_features)
        
        # Standardize features
        if len(window_features) > 1:
            scaler = StandardScaler()
            window_features = scaler.fit_transform(window_features)
        
        # Calculate similarity between adjacent windows
        similarities = []
        for i in range(1, len(window_features)):
            # Use cosine similarity directly
            sim = float(cosine_similarity([window_features[i-1]], [window_features[i]])[0][0])
            similarities.append(sim)
        
        # Apply median filter to smooth out similarities
        if len(similarities) > 5:
            similarities = medfilt(similarities, 5).tolist()  # Increased filter size for better smoothing
        
        # Invert similarities to find peaks (which are actually dips in similarity)
        inv_similarities = [1.0 - sim for sim in similarities]
        
        # Calculate average similarity for reference
        avg_similarity = float(np.mean(similarities)) if similarities else 0.9
        
        # Use a balanced adaptive multiplier that scales based on average similarity
        adaptive_multiplier = 1.8 if avg_similarity > 0.9 else 1.5
        
        # Balanced prominence threshold - not too sensitive, not too strict
        prominence = max(0.12, float(np.std(inv_similarities) * adaptive_multiplier))
        
        # Use a more conservative minimum distance between peaks
        min_distance = int(3.0/step_size)
        
        # Find peaks with these adaptive parameters
        peaks, peak_properties = find_peaks(np.array(inv_similarities), 
                                           prominence=prominence, 
                                           distance=min_distance)
        
        # Log detailed information about the parameters used
        logger.info(f"Average similarity between adjacent windows: {avg_similarity:.3f}")
        logger.info(f"Using prominence threshold: {prominence:.3f} for peak detection")
        logger.info(f"Using minimum distance between peaks: {min_distance} windows ({min_distance * step_size:.2f} seconds)")
        
        # Sort peaks by position
        peaks = np.sort(peaks)
        
        # These peaks represent potential speaker changes
        change_indices = [int(idx) for idx in peaks.tolist()]
        
        # Convert indices to timestamps
        change_times = [float(window_times[i+1]) for i in change_indices]  # +1 because we're comparing i-1 and i
        
        logger.info(f"Detected {len(change_times)} speaker changes")
        
        # Calculate chunk duration
        chunk_duration = len(y) / sr
        
        # Create segments based on detected speaker changes
        segments = []
        speech_groups = {}
        
        # Add start and end points to create complete segments
        all_change_points = [0.0] + change_times + [float(chunk_duration)]
        logger.info(f"Creating {len(all_change_points)-1} segments between change points")
        
        # Process each segment between change points
        for i in range(len(all_change_points) - 1):
            start_time = all_change_points[i]
            end_time = all_change_points[i + 1]
            segment_duration = end_time - start_time
            
            # Skip very short segments (less than 0.5 seconds)
            if segment_duration < 0.5:
                logger.info(f"Skipping very short segment: {start_time:.1f}-{end_time:.1f} ({segment_duration:.1f}s)")
                continue
            
            # Each segment gets its own speech group ID
            speech_group_id = i + 1
            speaker_id = f"SPEAKER_{speech_group_id}"
            
            # Create segment with Python native types
            segment = {
                "speaker": speaker_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration": segment_duration,
                "speech_group_id": speech_group_id
            }
            segments.append(segment)
            
            # Create speech group with Python native types
            speech_groups[speech_group_id] = {
                "speaker": speaker_id,
                "segments": [segment],
                "start_time": start_time,
                "end_time": end_time,
                "duration": segment_duration
            }
        
        # Create a simple speakers dictionary
        speakers = {}
        for segment in segments:
            speaker_id = segment["speaker"]
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "segments": 0,
                    "total_duration": 0,
                    "metadata": {},
                    "speech_groups": set()
                }
            
            speakers[speaker_id]["segments"] += 1
            speakers[speaker_id]["total_duration"] += segment["duration"]
            speakers[speaker_id]["speech_groups"].add(int(segment["speech_group_id"]))
        
        # Convert speech_groups sets to lists for JSON serialization
        for speaker_id, speaker_data in speakers.items():
            if isinstance(speaker_data["speech_groups"], set):
                speaker_data["speech_groups"] = list(speaker_data["speech_groups"])
        
        # Create the results dictionary
        diarization_results = {
            "input_file": str(audio_path),
            "output_file": str(output_path),
            "speakers": speakers,
            "segments": segments,
            "speech_groups": speech_groups,
            "processing_info": {
                "processed_at": datetime.now().isoformat(),
                "total_duration": chunk_duration,
                "model": "basic",
                "num_speakers": len(speakers),
                "num_speech_groups": len(speech_groups),
                "time_offset": time_offset
            }
        }
        
        return diarization_results
    
    # Class-level constant for chunk duration
    MAX_CHUNK_DURATION = 60 * 60  # 60 minutes in seconds
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get the duration of an audio file using ffprobe.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            # Try to get audio duration using ffprobe
            import subprocess
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.warning(f"Failed to get audio duration: {result.stderr}")
                return 600  # Default to 10 minutes
        except Exception as e:
            logger.error(f"Error getting audio duration with ffprobe: {e}")
            return 600  # Default to 10 minutes
    
    def _basic_speaker_identification(self, diarization_results: Dict) -> Dict:
        """
        Simplified basic speaker identification.
        Just assigns simple display names based on speaker IDs.
        
        Args:
            diarization_results: Diarization results from diarize_audio
            
        Returns:
            Dict with basic speaker identification
        """
        try:
            # Create a copy of the results
            updated_results = diarization_results.copy()
            
            # Generate simple speaker names based on IDs
            for speaker_id, speaker_info in updated_results["speakers"].items():
                # Just use a simple naming scheme based on the ID
                if speaker_id.startswith("SPEAKER_"):
                    # Extract number from speaker ID
                    import re
                    match = re.search(r'\d+', speaker_id)
                    if match:
                        number = match.group(0)
                        speaker_name = f"Speaker {number}"
                    else:
                        speaker_name = "Unknown Speaker"
                else:
                    # Use last few characters of ID
                    speaker_name = f"Speaker {speaker_id[-4:] if len(speaker_id) > 4 else speaker_id}"
                
                # Update speaker info with display name but keep original ID
                speaker_info["name"] = speaker_name
            
            # Update segments with speaker names
            for segment in updated_results["segments"]:
                speaker_id = segment["speaker"]
                segment["speaker_name"] = updated_results["speakers"][speaker_id]["name"]
            
            return updated_results
        except Exception as e:
            logger.error(f"Error in basic speaker identification: {e}")
            return diarization_results
    
    # _extract_segment_audio method removed since we no longer need it for speaker identification

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        # Check if ffmpeg is installed
        import subprocess
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            logger.info("ffprobe is installed")
        except:
            logger.error("ffprobe is not installed. Please install ffmpeg.")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking dependencies: {e}")
        return False

def install_dependencies():
    """Install required dependencies."""
    try:
        # Check if ffmpeg is installed
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except:
            logger.error("ffmpeg is not installed. Please install it manually.")
            return False
        # Install Python dependencies
        subprocess.run([sys.executable, "-m", "pip", "install", "torch", "transformers"], check=True)
        
        return True
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False

def main():
    """Main function to run the speaker diarization."""
    parser = argparse.ArgumentParser(description="Speaker Diarization for Parliament TV Audio")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("--output", help="Path to save the output JSON")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Model size to use for diarization")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if output file exists")
    parser.add_argument("--chunk-size", type=int, default=3600, help="Maximum chunk size in seconds for long audio files")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode with extra logging")
    parser.add_argument("--update-db", action="store_true", help="Update the voice database")
    args = parser.parse_args()
    
    try:
        # Check dependencies
        if not check_dependencies():
            logger.error("Required dependencies are missing.")
            return 1
        
        # Set up logging based on debug flag
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            print("Debug mode enabled - verbose logging will be shown")
        
        # Create the diarizer
        diarizer = SpeakerDiarizer()
        
        # Update the database if requested
        if args.update_db:
            result = diarizer.update_voice_database()
            print(f"Voice database update result: {result}")
            return 0
        
        # Set environment variable to increase memory limit for librosa
        os.environ['LIBROSA_CACHE_DIR'] = '/tmp/librosa_cache'
        os.environ['LIBROSA_CACHE_LEVEL'] = '10'
        
        # Process the audio file
        audio_path = Path(args.audio_file)
        output_path = Path(args.output) if args.output else None
        
        # Check if the file exists
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return 1
        
        # Override the default chunk size if specified
        if args.chunk_size > 0:
            # Monkey patch the MAX_CHUNK_DURATION in the diarizer
            diarizer.MAX_CHUNK_DURATION = args.chunk_size
            logger.info(f"Using custom chunk size: {args.chunk_size} seconds")
        
        # Force reprocessing if requested
        if args.force and output_path and output_path.exists():
            logger.info(f"Forcing reprocessing of {audio_path}")
            try:
                output_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete existing output file: {e}")
        
        # Perform diarization
        try:
            result = diarizer.diarize_audio(
                audio_path,
                output_path=output_path,
                model=args.model
            )
            
            # Try to match speakers with known voices
            matched_result = diarizer.match_speakers_with_known_voices(result)
            
            # Save the results to a JSON file if not already saved
            results_file = output_path or audio_path.with_suffix('.diarization.json')
            
            # Print summary
            print(f"\nDiarization completed successfully")
            print(f"Total duration: {matched_result['processing_info']['total_duration']:.2f} seconds")
            print(f"Detected speakers: {len(matched_result['speakers'])}")
            print(f"Results saved to: {results_file}")
            
            # Print detailed speaker information
            if 'speakers' in matched_result and matched_result['speakers']:
                print("\nDetected speakers:")
                for name, info in matched_result['speakers'].items():
                    print(f"  - {name}: {info['segments']} segments, {info['total_duration']:.2f} seconds")
            else:
                print("\nNo speakers detected in the audio")
                
            return 0
            
        except Exception as e:
            logger.error(f"Error during diarization: {e}")
            return 1
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
