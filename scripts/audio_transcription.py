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
import time
import signal
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError

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

def transcribe_audio(audio_file, output_file=None, model_size="medium", language="en"):
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
    
    # Use specified language or auto-detect if set to 'auto'
    if language and language.lower() != 'auto':
        logger.info(f"Using specified language: {language}")
        result = model.transcribe(audio_file, language=language)
    else:
        logger.info("Using automatic language detection")
        result = model.transcribe(audio_file)
        
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Transcription completed in {duration:.2f} seconds with detected language: {result['language']}")
    
    # Format the results with timestamps
    transcription = {
        "text": result["text"],
        "segments": result["segments"],
        "language": result["language"],
        "audio_file": str(audio_file),
        "model": model_size,
        "transcription_time": duration,
        "created_at": datetime.now().isoformat()
    }
    
    # Save the results to a file if specified
    output_path = None
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, "w") as f:
            json.dump(transcription, f, indent=2)
        logger.info(f"Transcription saved to: {output_file}")
    
    return transcription

class TimeoutException(Exception):
    """Exception raised when a function times out"""
    pass

def timeout_handler(signum, frame):
    """Signal handler for timeouts"""
    raise TimeoutException("Speaker diarization process timed out")

def update_progress(progress_file, stage, progress, message=None):
    """
    Update the progress file with the current stage and progress percentage
    
    Args:
        progress_file: Path to the progress file
        stage: Current processing stage (e.g., 'diarization', 'speaker_matching')
        progress: Progress percentage (0-100)
        message: Optional status message
    """
    progress_data = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error updating progress file: {e}")

def run_with_timeout(func, args=None, kwargs=None, timeout_seconds=1800):
    """
    Run a function with a timeout
    
    Args:
        func: Function to run
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        timeout_seconds: Timeout in seconds
        
    Returns:
        Result of the function or None if it times out
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    
    result = [None]
    exception = [None]
    
    def worker():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker)
        try:
            future.result(timeout=timeout_seconds)
            if exception[0] is not None:
                raise exception[0]
            return result[0]
        except TimeoutError:
            logger.error(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
            raise TimeoutException(f"Function {func.__name__} timed out after {timeout_seconds} seconds")

def perform_speaker_diarization(audio_file, transcription, output_file=None, video_path=None, max_duration=1800):
    """
    Perform speaker diarization on the audio file using the speaker diarization module.
    
    Args:
        audio_file: Path to the audio file
        transcription: Transcription data
        output_file: Path to save the diarization results
        video_path: Path to the video file for facial recognition integration
        max_duration: Maximum duration in seconds for the diarization process
        
    Returns:
        Dict with diarization results
    """
    # Import our speaker diarizer
    try:
        from backend.utils.speaker_diarizer import SpeakerDiarizer
    except ImportError:
        logger.error("Could not import SpeakerDiarizer. Make sure the module is installed.")
        # Return the original transcription without diarization
        return transcription
    
    # Create a progress file if output_file is specified
    progress_file = None
    if output_file:
        progress_file = str(Path(output_file).with_suffix('.progress.json'))
        update_progress(progress_file, "initializing", 0, "Initializing speaker diarization")
    
    try:
        logger.info("Starting speaker diarization...")
        if progress_file:
            update_progress(progress_file, "processing", 10, "Processing audio for speaker diarization")
        
        # Initialize the speaker diarizer
        diarizer = SpeakerDiarizer()
        
        # Check if we have any voice profiles
        if not diarizer.known_embeddings:
            logger.warning("No voice profiles found. Skipping diarization.")
            return transcription
        
        if progress_file:
            update_progress(progress_file, "identifying_speakers", 30, "Identifying speakers")
        
        # Perform diarization using our speaker diarizer
        diarization = run_with_timeout(
            diarizer.diarize,
            args=[audio_file, transcription, video_path],
            timeout_seconds=max_duration
        )
        
        if diarization is None:
            logger.error(f"Speaker diarization timed out after {max_duration} seconds")
            # Return the original transcription without diarization
            return transcription
        
        # Extract unique speakers from the segments
        speakers = []
        speaker_ids = set()
        
        for segment in diarization.get("segments", []):
            if "speaker" in segment and segment["speaker"].get("id") is not None:
                speaker_id = segment["speaker"]["id"]
                if speaker_id not in speaker_ids:
                    speaker_ids.add(speaker_id)
                    speakers.append({
                        "id": speaker_id,
                        "name": segment["speaker"]["name"],
                        "role": segment["speaker"].get("role", ""),
                        "party": segment["speaker"].get("party", "")
                    })
        
        # Add unknown speaker if needed
        if "Unknown Speaker" not in [s["name"] for s in speakers]:
            speakers.append({
                "id": "unknown",
                "name": "Unknown Speaker",
                "role": "",
                "party": ""
            })
        
        # Add speakers to the diarization results
        diarization["speakers"] = speakers
        
        # Add combined results for easier processing
        combined_results = {
            "transcript": diarization.get("text", ""),
            "speakers": speakers,
            "segments": []
        }
        
        # Combine segments by speaker for easier reading
        current_speaker_id = None
        current_text = ""
        current_start = 0
        current_end = 0
        
        for segment in diarization.get("segments", []):
            speaker_info = segment.get("speaker", {})
            speaker_id = speaker_info.get("id")
            
            if current_speaker_id is None:
                # First segment
                current_speaker_id = speaker_id
                current_text = segment.get("text", "")
                current_start = segment.get("start", 0)
                current_end = segment.get("end", 0)
            elif speaker_id == current_speaker_id:
                # Same speaker, combine segments
                current_text += " " + segment.get("text", "")
                current_end = segment.get("end", current_end)
            else:
                # New speaker, add the previous combined segment
                speaker_name = next((s["name"] for s in speakers if s["id"] == current_speaker_id), "Unknown Speaker")
                combined_results["segments"].append({
                    "speaker_id": current_speaker_id,
                    "speaker_name": speaker_name,
                    "text": current_text,
                    "start": current_start,
                    "end": current_end
                })
                
                # Start a new combined segment
                current_speaker_id = speaker_id
                current_text = segment.get("text", "")
                current_start = segment.get("start", 0)
                current_end = segment.get("end", 0)
        
        # Add the last combined segment
        if current_speaker_id is not None:
            speaker_name = next((s["name"] for s in speakers if s["id"] == current_speaker_id), "Unknown Speaker")
            combined_results["segments"].append({
                "speaker_id": current_speaker_id,
                "speaker_name": speaker_name,
                "text": current_text,
                "start": current_start,
                "end": current_end
            })
        
        # Add the combined results to the diarization
        diarization["combined_results"] = combined_results
        
        # Save the results to a file if specified
        if output_file:
            with open(output_file, "w") as f:
                json.dump(diarization, f, indent=2)
            logger.info(f"Combined diarization results saved to: {output_file}")
            
            if progress_file:
                update_progress(progress_file, "completed", 100, "Speaker diarization completed successfully")
        
        return diarization
    
    except Exception as e:
        logger.error(f"Error in speaker diarization: {e}")
        if progress_file:
            update_progress(progress_file, "error", 50, f"Error in speaker diarization: {str(e)[:100]}")
        
        # Fall back to basic speaker assignment
        diarization = {
            "audio_file": audio_file,
            "speakers": [],
            "segments": [],
            "error": str(e)
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
            
            if progress_file:
                update_progress(progress_file, "completed_with_errors", 100, "Speaker diarization completed with errors, using fallback")
        
        return diarization

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("--output", help="Path to save the transcription results")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size to use")
    parser.add_argument("--language", default="en", help="Language code for transcription (e.g., 'en' for English, 'auto' for automatic detection)")
    parser.add_argument("--diarize", action="store_true", help="Perform speaker diarization")
    parser.add_argument("--diarize-output", help="Path to save the diarization results")
    parser.add_argument("--video-path", help="Path to the video file for facial recognition integration")
    parser.add_argument("--timeout", type=int, default=1800, help="Maximum duration in seconds for the diarization process")
    
    args = parser.parse_args()
    
    # Validate the audio file
    is_valid, message = validate_audio_file(args.audio_file)
    if not is_valid:
        logger.error(message)
        return 1
    
    try:
        # Transcribe the audio
        transcription = transcribe_audio(args.audio_file, args.output, args.model, args.language)
        
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
