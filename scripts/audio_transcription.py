#!/usr/bin/env python3
"""
Audio Transcription for Parliament TV Videos

This script transcribes audio files from Parliament TV videos using speech recognition.
It generates timestamped transcriptions that can be used for searching and analysis.

Usage:
    python audio_transcription.py <audio_file> [--output OUTPUT_FILE] [--model MODEL_SIZE]

Example:
    python audio_transcription.py /app/data/temp/audio_extracts/capture_0270.audio.mp3 --output /app/data/transcriptions/capture_0270_transcript.json

Models:
    - tiny: Fastest, least accurate
    - base: Fast, reasonable accuracy
    - small: Good balance of speed and accuracy
    - medium: Better accuracy, slower
    - large: Best accuracy, slowest
"""

import os
import json
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audio_transcription")

def check_whisper_installed():
    """Check if OpenAI Whisper is installed, install if not."""
    try:
        import whisper
        logger.info("OpenAI Whisper is already installed")
        return True
    except ImportError:
        logger.info("Installing OpenAI Whisper...")
        try:
            subprocess.check_call(["pip", "install", "openai-whisper"])
            logger.info("OpenAI Whisper installed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to install OpenAI Whisper: {e}")
            return False

def validate_audio_file(file_path):
    """Validate that the audio file exists and contains valid audio data."""
    # Check if the file exists
    if not os.path.exists(file_path):
        return False, f"Audio file not found: {file_path}"
    
    # Check if the file has content
    if os.path.getsize(file_path) == 0:
        return False, f"Audio file is empty: {file_path}"
    
    # Try to get audio file info using ffprobe
    try:
        cmd = [
            "ffprobe", 
            "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"Failed to probe audio file: {result.stderr}"
        
        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        
        # Check if there are any audio streams
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        if not audio_streams:
            return False, f"No audio streams found in file: {file_path}"
        
        return True, "Audio file is valid"
    except Exception as e:
        return False, f"Error validating audio file: {str(e)}"

def transcribe_audio(audio_file, output_file=None, model_size="medium"):
    """
    Transcribe an audio file using Whisper model.
    
    Args:
        audio_file: Path to the audio file
        output_file: Path to save the transcription results
        model_size: Size of the Whisper model to use
        
    Returns:
        Dict with transcription results
    """
    logger.info(f"Transcribing audio file: {audio_file}")
    logger.info(f"Using model size: {model_size}")
    
    if not check_whisper_installed():
        raise ImportError("OpenAI Whisper is required but could not be installed")
    
    import whisper
    
    # Load the Whisper model
    logger.info(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    # Transcribe the audio
    logger.info("Starting transcription...")
    start_time = datetime.now()
    result = model.transcribe(audio_file)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Transcription completed in {duration:.2f} seconds")
    
    # Format the results with timestamps
    transcription = {
        "text": result["text"],
        "segments": result["segments"],
        "language": result["language"],
        "audio_file": audio_file,
        "model": model_size,
        "transcription_time": duration,
        "created_at": datetime.now().isoformat()
    }
    
    # Save the results to a file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, "w") as f:
            json.dump(transcription, f, indent=2)
        logger.info(f"Transcription saved to: {output_file}")
    
    return transcription

def perform_speaker_diarization(audio_file, transcription, output_file=None, video_path=None):
    """
    Perform speaker diarization on the audio file using the speaker diarization module.
    
    Args:
        audio_file: Path to the audio file
        transcription: Transcription data
        output_file: Path to save the diarization results
        video_path: Optional path to the video file for facial recognition integration
        
    Returns:
        Dict with diarization results
    """
    try:
        # Add the scripts directory to the path if needed
        script_dir = Path(__file__).parent.absolute()
        if str(script_dir) not in sys.path:
            sys.path.append(str(script_dir))
        
        # Import the speaker diarization module
        try:
            from speaker_diarization import SpeakerDiarizer
            from voice_profile_manager import VoiceProfileManager
        except ImportError as e:
            logger.error(f"Failed to import speaker diarization modules: {e}")
            raise ImportError(f"Speaker diarization modules not available: {e}")
        
        logger.info(f"Performing speaker diarization on: {audio_file}")
        
        # Initialize the speaker diarizer
        diarizer = SpeakerDiarizer()
        
        # Update the voice database
        logger.info("Updating voice database...")
        diarizer.update_voice_database()
        
        # Perform diarization
        logger.info("Running speaker diarization...")
        audio_path = Path(audio_file)
        diarization_results = diarizer.diarize_audio(audio_path)
        
        # Match speakers with known voices
        logger.info("Matching speakers with known voices...")
        diarization_results = diarizer.match_speakers_with_known_voices(diarization_results)
        
        # Combine with transcription
        logger.info("Combining diarization with transcription...")
        
        # Import the voice recognition service for combining results
        try:
            # Add the backend directory to the path
            backend_dir = script_dir.parent / "backend"
            if str(backend_dir) not in sys.path:
                sys.path.append(str(backend_dir))
                
            from services.recognition.voice_recognition import VoiceRecognitionService
            voice_service = VoiceRecognitionService()
            
            # Combine transcription with speakers
            combined_results = voice_service.combine_transcription_with_speakers(
                transcription, diarization_results
            )
            
            # If video path is provided, try to combine with facial recognition
            if video_path and os.path.exists(video_path):
                logger.info(f"Integrating with facial recognition from video: {video_path}")
                try:
                    # Get facial recognition results from the video
                    from services.recognition.facial_recognition import FacialRecognitionService
                    facial_service = FacialRecognitionService()
                    
                    # Process video for facial recognition
                    facial_results = facial_service.process_video(Path(video_path))
                    
                    # Combine audio and video recognition results
                    if facial_results:
                        logger.info("Combining audio and video recognition results...")
                        combined_results = voice_service.combine_recognition_results(
                            combined_results, facial_results
                        )
                except Exception as e:
                    logger.error(f"Error in facial recognition integration: {e}")
                    # Continue without facial recognition
        except Exception as e:
            logger.error(f"Error combining results: {e}")
            # Fall back to basic combination
            combined_results = {
                "audio_file": audio_file,
                "speakers": diarization_results.get("speakers", []),
                "segments": []
            }
            
            # Combine segments from transcription with speaker info
            for segment in transcription["segments"]:
                segment_start = segment["start"]
                segment_end = segment["end"]
                
                # Find matching diarization segment
                speaker_id = None
                speaker_name = None
                
                for diar_segment in diarization_results.get("segments", []):
                    # Check for overlap
                    if (diar_segment["start"] <= segment_end and 
                        diar_segment["end"] >= segment_start):
                        speaker_id = diar_segment.get("speaker")
                        break
                
                # Find speaker name if we have an ID
                if speaker_id:
                    for speaker in diarization_results.get("speakers", []):
                        if speaker.get("id") == speaker_id:
                            speaker_name = speaker.get("name")
                            break
                
                # Add the combined segment
                combined_results["segments"].append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "speaker": speaker_id or "unknown",
                    "speaker_name": speaker_name or "Unknown Speaker"
                })
        
        # Save the results to a file if specified
        if output_file:
            with open(output_file, "w") as f:
                json.dump(combined_results, f, indent=2)
            logger.info(f"Combined diarization results saved to: {output_file}")
        
        return combined_results
    
    except Exception as e:
        logger.error(f"Error in speaker diarization: {e}")
        # Fall back to basic speaker assignment
        diarization = {
            "audio_file": audio_file,
            "speakers": [],
            "segments": []
        }
        
        # Assign all segments to "Unknown Speaker"
        for segment in transcription["segments"]:
            diarization["segments"].append({
                "speaker": "unknown",
                "speaker_name": "Unknown Speaker",
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"]
            })
        
        # Add a placeholder speaker
        diarization["speakers"].append({
            "id": "unknown",
            "name": "Unknown Speaker"
        })
        
        # Save the results to a file if specified
        if output_file:
            with open(output_file, "w") as f:
                json.dump(diarization, f, indent=2)
            logger.info(f"Fallback diarization saved to: {output_file}")
        
        return diarization

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("--output", help="Path to save the transcription results")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size to use")
    parser.add_argument("--diarize", action="store_true", help="Perform speaker diarization")
    parser.add_argument("--diarize-output", help="Path to save the diarization results")
    parser.add_argument("--video-path", help="Path to the video file for facial recognition integration")
    
    args = parser.parse_args()
    
    # Validate the audio file
    is_valid, message = validate_audio_file(args.audio_file)
    if not is_valid:
        logger.error(message)
        return 1
    
    try:
        # Transcribe the audio
        transcription = transcribe_audio(args.audio_file, args.output, args.model)
        
        # Perform speaker diarization if requested
        if args.diarize:
            diarize_output = args.diarize_output or (args.output.replace(".json", "_diarized.json") if args.output else None)
            combined_results = perform_speaker_diarization(
                args.audio_file, 
                transcription, 
                diarize_output,
                args.video_path
            )
            
            # Update the original transcription file with the combined results
            if args.output and os.path.exists(args.output):
                # Load the original transcription
                with open(args.output, 'r') as f:
                    original_data = json.load(f)
                
                # Add the speaker information to the original transcription
                original_data["speakers"] = combined_results.get("speakers", [])
                
                # Update segments with speaker information
                for i, segment in enumerate(original_data.get("segments", [])):
                    if i < len(combined_results.get("segments", [])):
                        combined_segment = combined_results["segments"][i]
                        segment["speaker"] = combined_segment.get("speaker")
                        segment["speaker_name"] = combined_segment.get("speaker_name")
                        segment["speaker_confidence"] = combined_segment.get("speaker_confidence")
                        segment["matched_with_video"] = combined_segment.get("matched_with_video", False)
                
                # Add combined results if available
                if "combined_results" in combined_results:
                    original_data["combined_results"] = combined_results["combined_results"]
                
                # Save the updated transcription
                with open(args.output, 'w') as f:
                    json.dump(original_data, f, indent=2)
                logger.info(f"Updated transcription with speaker information: {args.output}")
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
