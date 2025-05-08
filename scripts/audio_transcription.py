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
from pathlib import Path
from datetime import datetime
import subprocess

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

def perform_speaker_diarization(audio_file, transcription, output_file=None):
    """
    Perform speaker diarization on the audio file.
    This is a placeholder for future implementation.
    
    Args:
        audio_file: Path to the audio file
        transcription: Transcription data
        output_file: Path to save the diarization results
        
    Returns:
        Dict with diarization results
    """
    logger.info(f"Speaker diarization not yet implemented")
    
    # Placeholder for future implementation
    diarization = {
        "audio_file": audio_file,
        "speakers": [],
        "segments": []
    }
    
    # For now, we'll just assign all segments to "Speaker 1"
    for segment in transcription["segments"]:
        diarization["segments"].append({
            "speaker": "Speaker 1",
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })
    
    # Add a placeholder speaker
    diarization["speakers"].append({
        "id": 1,
        "name": "Speaker 1"
    })
    
    # Save the results to a file if specified
    if output_file:
        with open(output_file, "w") as f:
            json.dump(diarization, f, indent=2)
        logger.info(f"Diarization saved to: {output_file}")
    
    return diarization

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("--output", help="Path to save the transcription results")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper model size to use")
    parser.add_argument("--diarize", action="store_true", help="Perform speaker diarization")
    parser.add_argument("--diarize-output", help="Path to save the diarization results")
    
    args = parser.parse_args()
    
    # Check if the audio file exists
    if not os.path.exists(args.audio_file):
        logger.error(f"Audio file not found: {args.audio_file}")
        return 1
    
    try:
        # Transcribe the audio
        transcription = transcribe_audio(args.audio_file, args.output, args.model)
        
        # Perform speaker diarization if requested
        if args.diarize:
            diarize_output = args.diarize_output or (args.output.replace(".json", "_diarized.json") if args.output else None)
            perform_speaker_diarization(args.audio_file, transcription, diarize_output)
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
