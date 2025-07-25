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
            # Try to use pyannote.audio for diarization - it's good at detecting speaker changes
            import torch
            from pyannote.audio import Pipeline
            
            # Initialize the diarization pipeline
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=True)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            pipeline = pipeline.to(device)
            
            logger.info(f"Running diarization on device: {device}")
            
            # Run the diarization pipeline
            diarization = pipeline(str(audio_path))
            
            # Process the diarization results
            segments = []
            speech_groups = {}
            current_speech_group = 0
            last_speaker = None
            last_end_time = 0
            
            # Convert pyannote.audio output to our format
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                start_time = turn.start
                end_time = turn.end
                speaker_id = f"SPEAKER_{speaker}"
                
                # Check if we need a new speech group based on speaker change only
                # We no longer consider pauses/gaps for speech group creation
                if speaker_id != last_speaker:
                    current_speech_group += 1
                
                # Create segment with speech group ID
                segment_duration = end_time - start_time
                segment = {
                    "speaker": speaker_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": segment_duration,
                    "speech_group_id": current_speech_group
                }
                segments.append(segment)
                
                # Create or update speech group
                if current_speech_group not in speech_groups:
                    speech_groups[current_speech_group] = {
                        "id": f"speech_group_{current_speech_group}",
                        "speaker": speaker_id,
                        "segments": [],
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": segment_duration
                    }
                else:
                    # Update existing group
                    speech_groups[current_speech_group]["end_time"] = end_time
                    speech_groups[current_speech_group]["duration"] += segment_duration
                
                # Add segment to its group
                speech_groups[current_speech_group]["segments"].append(segment)
                
                # Update tracking variables
                last_speaker = speaker_id
                last_end_time = end_time
            
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
                speakers[speaker_id]["speech_groups"].add(segment["speech_group_id"])
            
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
