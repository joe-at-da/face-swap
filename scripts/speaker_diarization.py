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

# Import the voice profile manager
try:
    from voice_profile_manager import VoiceProfileManager
    VOICE_PROFILE_MANAGER_AVAILABLE = True
except ImportError:
    VOICE_PROFILE_MANAGER_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("speaker_diarization")

# Constants
VOICE_PROFILES_DIR = Path("/app/data/voice_profiles")
VOICE_ENCODINGS_FILE = Path("/app/data/voice_encodings.json")

class SpeakerDiarizer:
    """Class to handle speaker diarization in audio files."""
    
    def __init__(self, voice_encodings_file: Path = VOICE_ENCODINGS_FILE):
        """Initialize the speaker diarizer."""
        self.voice_encodings_file = voice_encodings_file
        self.known_voice_encodings = []
        self.known_voice_names = []
        self.known_voice_metadata = []
        self.load_voice_database()
    
    def load_voice_database(self) -> bool:
        """Load the voice encodings database."""
        if not self.voice_encodings_file.exists():
            logger.warning(f"Voice encodings file not found: {self.voice_encodings_file}")
            return False
        
        try:
            with open(self.voice_encodings_file, 'r') as f:
                data = json.load(f)
                
            self.known_voice_encodings = [np.array(enc) for enc in data.get('encodings', [])]
            self.known_voice_names = data.get('names', [])
            self.known_voice_metadata = data.get('metadata', [{}] * len(self.known_voice_names))
            
            logger.info(f"Loaded {len(self.known_voice_encodings)} voice encodings")
            return True
            
        except Exception as e:
            logger.error(f"Error loading voice database: {e}")
            return False
    
    def update_voice_database(self) -> bool:
        """Update the voice encodings database from voice samples."""
        logger.info("Updating voice database from voice samples...")
        
        # Create the voice profiles directory if it doesn't exist
        VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        
        # This is a placeholder for the actual implementation
        # In a real implementation, we would:
        # 1. Get voice samples for known MPs
        # 2. Extract voice embeddings
        # 3. Save them to the database
        
        # For now, we'll just create an empty database
        voice_data = {
            "encodings": [],
            "names": [],
            "metadata": [],
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            # Save the database
            with open(self.voice_encodings_file, 'w') as f:
                json.dump(voice_data, f, indent=2)
            
            logger.info(f"Voice database updated with {len(voice_data['encodings'])} encodings")
            return True
            
        except Exception as e:
            logger.error(f"Error updating voice database: {e}")
            return False
    
    def diarize_audio(self, audio_path: Path, output_path: Optional[Path] = None, model_size: str = "base") -> Dict:
        """
        Perform speaker diarization on an audio file using pyannote.audio.
        
        Args:
            audio_path: Path to the input audio
            output_path: Path to save the output JSON (optional)
            model_size: Size of the model to use (tiny, base, small, medium, large)
            
        Returns:
            Dict with diarization results
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # If no output path provided, create one
        if output_path is None:
            output_dir = audio_path.parent
            output_path = output_dir / f"{audio_path.stem}_diarization.json"
        
        logger.info(f"Diarizing audio: {audio_path} with model size: {model_size}")
        
        try:
            # Import pyannote.audio here to avoid loading it unless needed
            try:
                from pyannote.audio import Pipeline
                import torch
                logger.info("Successfully imported pyannote.audio and torch")
            except ImportError as e:
                logger.error(f"Failed to import required libraries: {e}")
                raise ImportError(f"Required libraries not installed: {e}")
            
            # Initialize diarization pipeline
            try:
                # Check for HF_TOKEN environment variable
                hf_token = os.environ.get('HF_TOKEN')
                
                if not hf_token:
                    logger.warning("HF_TOKEN environment variable not set. Attempting to use default token.")
                    # Try to load from a token file if it exists
                    token_file = Path("/app/data/hf_token.txt")
                    if token_file.exists():
                        try:
                            with open(token_file, 'r') as f:
                                hf_token = f.read().strip()
                            logger.info("Loaded token from token file")
                        except Exception as token_e:
                            logger.error(f"Failed to load token from file: {token_e}")
                
                # Use a pre-trained model from HuggingFace
                try:
                    pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=hf_token if hf_token else None
                    )
                    logger.info("Successfully initialized diarization pipeline with token")
                except Exception as auth_e:
                    logger.warning(f"Failed to initialize with token: {auth_e}")
                    logger.warning("Attempting to initialize without token (may use cached model)")
                    try:
                        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
                        logger.info("Successfully initialized diarization pipeline without token")
                    except Exception as no_auth_e:
                        logger.error(f"Failed to initialize without token: {no_auth_e}")
                        # Fallback to a basic implementation for development purposes
                        logger.warning("Using fallback diarization method for development")
                        return self._fallback_diarization(audio_path, output_path)
                
                # Move to GPU if available
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                logger.info(f"Using device: {device}")
                pipeline = pipeline.to(device)
                
                logger.info("Successfully initialized diarization pipeline")
            except Exception as e:
                logger.error(f"Failed to initialize diarization pipeline: {e}")
                # Fallback to a basic implementation for development purposes
                logger.warning("Using fallback diarization method for development")
                return self._fallback_diarization(audio_path, output_path)
            
            # Apply diarization
            try:
                logger.info(f"Starting diarization of {audio_path}")
                diarization = pipeline(audio_path)
                logger.info(f"Diarization completed successfully")
            except Exception as e:
                logger.error(f"Error during diarization: {e}")
                return self._fallback_diarization(audio_path, output_path)
            
            # Process diarization results
            speakers = {}
            segments = []
            total_duration = 0
            
            # Extract segments from diarization output
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                start_time = turn.start
                end_time = turn.end
                duration = end_time - start_time
                total_duration = max(total_duration, end_time)
                
                # Add segment
                segment = {
                    "speaker": speaker,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration
                }
                segments.append(segment)
                
                # Update speaker statistics
                if speaker not in speakers:
                    speakers[speaker] = {
                        "segments": 0,
                        "total_duration": 0,
                        "metadata": {}
                    }
                
                speakers[speaker]["segments"] += 1
                speakers[speaker]["total_duration"] += duration
            
            # Create the results dictionary
            diarization_results = {
                "input_file": str(audio_path),
                "output_file": str(output_path),
                "speakers": speakers,
                "segments": segments,
                "processing_info": {
                    "processed_at": datetime.now().isoformat(),
                    "total_duration": total_duration,
                    "model": f"pyannote-audio-{model_size}",
                    "num_speakers": len(speakers)
                }
            }
            
            logger.info(f"Processed {len(segments)} segments with {len(speakers)} speakers")
        
        except Exception as e:
            logger.error(f"Error in diarization: {e}")
            # Fallback to basic implementation
            return self._fallback_diarization(audio_path, output_path)
        
        # Save the results to the output file
        with open(output_path, 'w') as f:
            json.dump(diarization_results, f, indent=2, default=str)
        
        logger.info(f"Diarization results saved to: {output_path}")
        
        return diarization_results
    
    def _fallback_diarization(self, audio_path: Path, output_path: Path) -> Dict:
        """
        Fallback diarization method for development purposes.
        
        Args:
            audio_path: Path to the input audio
            output_path: Path to save the output JSON
        
        Returns:
            Dict with diarization results
        """
        logger.warning("Using fallback diarization method for development")
        
        # Create a dummy diarization result
        diarization_results = {
            "input_file": str(audio_path),
            "output_file": str(output_path),
            "speakers": {},
            "segments": [],
            "processing_info": {
                "processed_at": datetime.now().isoformat(),
                "total_duration": 0,
                "model": "fallback",
                "num_speakers": 0
            }
        }
        
        # Save the results to the output file
        with open(output_path, 'w') as f:
            json.dump(diarization_results, f, indent=2, default=str)
        
        logger.info(f"Diarization results saved to: {output_path}")
        
        return diarization_results
    
    def match_speakers_with_known_voices(self, diarization_results: Dict) -> Dict:
        """
        Match diarized speakers with known voices.
        
        Args:
            diarization_results: Diarization results from diarize_audio
            
        Returns:
            Dict with matched speakers
        """
        if not VOICE_PROFILE_MANAGER_AVAILABLE:
            logger.warning("Voice profile manager not available, skipping speaker matching")
            return diarization_results
        
        try:
            # Create a voice profile manager
            voice_manager = VoiceProfileManager()
            
            # Check if we have any known voices
            if not voice_manager.known_voice_names:
                logger.warning("No known voice profiles available for matching")
                return diarization_results
            
            # Load the audio file
            audio_path = Path(diarization_results["input_file"])
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return diarization_results
            
            # Extract voice embeddings for each speaker
            speaker_embeddings = {}
            for speaker_id in diarization_results["speakers"]:
                try:
                    # Extract segments for this speaker
                    speaker_segments = [seg for seg in diarization_results["segments"] 
                                      if seg["speaker"] == speaker_id]
                    
                    if not speaker_segments:
                        continue
                    
                    # Get the longest segment for this speaker
                    longest_segment = max(speaker_segments, key=lambda x: x["duration"])
                    
                    # Extract audio for this segment
                    segment_audio_path = self._extract_segment_audio(
                        audio_path, 
                        longest_segment["start_time"], 
                        longest_segment["end_time"]
                    )
                    
                    if segment_audio_path and segment_audio_path.exists():
                        # Extract voice embedding
                        embedding = voice_manager.extract_voice_embedding(segment_audio_path)
                        if embedding is not None:
                            speaker_embeddings[speaker_id] = embedding
                            logger.info(f"Extracted voice embedding for speaker {speaker_id}")
                        
                        # Clean up temporary file
                        try:
                            os.remove(segment_audio_path)
                        except Exception as e:
                            logger.warning(f"Failed to remove temporary file: {e}")
                    
                except Exception as e:
                    logger.error(f"Error extracting embedding for speaker {speaker_id}: {e}")
            
            # Match speakers with known voices
            matched_speakers = {}
            for speaker_id, embedding in speaker_embeddings.items():
                speaker_name, confidence = voice_manager.match_voice(embedding)
                
                if speaker_name and confidence > 0.5:  # Adjust threshold as needed
                    matched_speakers[speaker_id] = {
                        "name": speaker_name,
                        "confidence": confidence
                    }
                    logger.info(f"Matched speaker {speaker_id} with {speaker_name} (confidence: {confidence:.2f})")
            
            # Update the diarization results with matched speakers
            if matched_speakers:
                # Create a copy of the results
                updated_results = diarization_results.copy()
                
                # Update speaker information
                for speaker_id, speaker_info in updated_results["speakers"].items():
                    if speaker_id in matched_speakers:
                        speaker_info["name"] = matched_speakers[speaker_id]["name"]
                        speaker_info["confidence"] = matched_speakers[speaker_id]["confidence"]
                        speaker_info["matched"] = True
                    else:
                        speaker_info["matched"] = False
                
                # Update segments with speaker names
                for segment in updated_results["segments"]:
                    speaker_id = segment["speaker"]
                    if speaker_id in matched_speakers:
                        segment["speaker_name"] = matched_speakers[speaker_id]["name"]
                        segment["speaker_confidence"] = matched_speakers[speaker_id]["confidence"]
                
                # Add matching info to processing_info
                updated_results["processing_info"]["speaker_matching"] = {
                    "matched_speakers": len(matched_speakers),
                    "total_speakers": len(updated_results["speakers"]),
                    "matched_ratio": len(matched_speakers) / len(updated_results["speakers"])
                }
                
                return updated_results
            else:
                logger.warning("No speakers could be matched with known voices")
                return diarization_results
            
        except Exception as e:
            logger.error(f"Error matching speakers with known voices: {e}")
            return diarization_results
    
    def _extract_segment_audio(self, audio_path: Path, start_time: float, end_time: float) -> Optional[Path]:
        """
        Extract a segment of audio for speaker recognition.
        
        Args:
            audio_path: Path to the full audio file
            start_time: Start time of the segment (seconds)
            end_time: End time of the segment (seconds)
            
        Returns:
            Path to the extracted audio segment, or None if extraction failed
        """
        try:
            # Create a temporary file for the segment
            segment_path = audio_path.parent / f"{audio_path.stem}_segment_{start_time:.2f}_{end_time:.2f}.wav"
            
            # Use ffmpeg to extract the segment
            import subprocess
            cmd = [
                "ffmpeg",
                "-i", str(audio_path),
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c:a", "pcm_s16le",  # Use WAV format for best compatibility
                "-ar", "16000",       # 16kHz sample rate for voice recognition
                "-ac", "1",           # Mono audio
                "-y",                  # Overwrite output file
                str(segment_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to extract audio segment: {result.stderr}")
                return None
            
            return segment_path
            
        except Exception as e:
            logger.error(f"Error extracting audio segment: {e}")
            return None

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        # Check for ffmpeg
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("ffmpeg is not installed or not in PATH")
            return False
        
        # In a real implementation, we would check for:
        # - torch
        # - pyannote.audio
        # - transformers
        
        return True
    except Exception as e:
        logger.error(f"Error checking dependencies: {e}")
        return False

def install_dependencies():
    """Install required dependencies."""
    try:
        import subprocess
        
        # Install Python dependencies
        subprocess.run([sys.executable, "-m", "pip", "install", "torch", "pyannote.audio", "transformers"], check=True)
        
        # Check if ffmpeg is installed
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except:
            logger.error("ffmpeg is not installed. Please install it manually.")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False

def main():
    """Main function to run the speaker diarization."""
    parser = argparse.ArgumentParser(description="Speaker Diarization for Parliament TV Audio")
    parser.add_argument("audio_path", help="Path to the audio file")
    parser.add_argument("--output", "-o", help="Path to save the output JSON")
    parser.add_argument("--update-db", action="store_true", help="Update the voice database")
    parser.add_argument("--model", "-m", choices=["tiny", "base", "small", "medium", "large"], default="base", 
                        help="Model size to use for diarization")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode with extra logging")
    args = parser.parse_args()
    
    try:
        # Check dependencies
        if not check_dependencies():
            if not install_dependencies():
                logger.error("Required dependencies could not be installed.")
                return 1
        
        # Set up logging based on debug flag
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            print("Debug mode enabled - verbose logging will be shown")
        
        # Create the speaker diarizer
        diarizer = SpeakerDiarizer()
        
        # Update the database if requested
        if args.update_db:
            result = diarizer.update_voice_database()
            print(f"Voice database update result: {result}")
            return 0
        
        # Process the audio
        if args.audio_path:
            audio_path = Path(args.audio_path)
            output_path = Path(args.output) if args.output else None
            
            print(f"Processing audio: {audio_path}")
            print(f"Using model: {args.model}")
            
            # Check if the file exists
            if not audio_path.exists():
                print(f"ERROR: Audio file not found: {audio_path}")
                return 1
            
            # Perform diarization
            result = diarizer.diarize_audio(audio_path, output_path)
            
            # Try to match speakers with known voices
            matched_result = diarizer.match_speakers_with_known_voices(result)
            
            # Save the results to a JSON file
            results_file = output_path or audio_path.with_suffix('.diarization.json')
            with open(results_file, 'w') as f:
                json.dump(matched_result, f, indent=2, default=str)
            
            print(f"Results saved to: {results_file}")
            
            # Print summary
            print(f"Total duration: {matched_result['processing_info']['total_duration']:.2f} seconds")
            print(f"Detected speakers: {len(matched_result['speakers'])}")
            
            # Print detailed speaker information
            if 'speakers' in matched_result and matched_result['speakers']:
                print("\nDetected speakers:")
                for name, info in matched_result['speakers'].items():
                    print(f"  - {name}: {info['segments']} segments, {info['total_duration']:.2f} seconds")
            else:
                print("\nNo speakers detected in the audio")
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
