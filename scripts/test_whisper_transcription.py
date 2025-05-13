#!/usr/bin/env python3
"""
Test Whisper Transcription

A simple script to test Whisper transcription on an audio file.
This script ensures paths are consistent and uses a smaller model for faster results.
"""

import os
import json
import logging
import argparse
from pathlib import Path
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_whisper")

def main():
    parser = argparse.ArgumentParser(description="Test Whisper transcription")
    parser.add_argument("--audio-file", default="/app/data/temp/audio_extracts/capture_0279.audio.mp3", 
                        help="Path to the audio file")
    parser.add_argument("--output-dir", default="/app/data/temp", 
                        help="Directory to save the transcription results")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium"], 
                        help="Whisper model size to use")
    
    args = parser.parse_args()
    
    # Validate paths
    audio_file = Path(args.audio_file)
    output_dir = Path(args.output_dir)
    
    if not audio_file.exists():
        logger.error(f"Audio file not found: {audio_file}")
        return 1
    
    logger.info(f"Audio file exists: {audio_file} (Size: {audio_file.stat().st_size / 1024:.2f} KB)")
    
    # Make sure output directory exists
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Output file path
    output_file = output_dir / f"test_transcription_{int(time.time())}.json"
    
    try:
        # Import whisper here to catch any import errors
        try:
            import whisper
            logger.info("Successfully imported whisper")
        except ImportError:
            logger.error("Failed to import whisper. Make sure it's installed.")
            return 1
        
        # Load the model
        logger.info(f"Loading Whisper model: {args.model}")
        start_time = time.time()
        model = whisper.load_model(args.model)
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f} seconds")
        
        # Transcribe the audio
        logger.info(f"Starting transcription with {args.model} model...")
        start_time = time.time()
        result = model.transcribe(str(audio_file))
        transcription_time = time.time() - start_time
        logger.info(f"Transcription completed in {transcription_time:.2f} seconds")
        
        # Format the results
        transcription = {
            "text": result["text"],
            "segments": result["segments"],
            "language": result["language"],
            "audio_file": str(audio_file),
            "model": args.model,
            "transcription_time": transcription_time,
            "timestamp": time.time()
        }
        
        # Save the results
        with open(output_file, "w") as f:
            json.dump(transcription, f, indent=2)
        logger.info(f"Transcription saved to: {output_file}")
        
        # Print a preview of the transcription
        logger.info(f"Transcription preview: {result['text'][:200]}...")
        
        return 0
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
