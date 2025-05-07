#!/usr/bin/env python3
"""
Test script for the transcription service.
This script tests the TranscriptionService directly without going through the API.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Override settings for local testing
from backend.core.config import settings
settings.MEDIA_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/temp")
settings.TEMP_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/temp")

from backend.services.video.transcription import TranscriptionService


def test_transcription(
    audio_path: str, 
    language: str = "en", 
    model_size: str = "base",
    output_dir: str = None
):
    """
    Test the transcription service on an audio file.
    
    Args:
        audio_path: Path to the audio file
        language: Language code for transcription
        model_size: Size of the Whisper model to use
        output_dir: Directory to save the transcription output
    """
    start_time = datetime.now()
    logger.info(f"Starting transcription test for {audio_path}")
    logger.info(f"Language: {language}, Model: {model_size}")
    
    # Create the transcription service
    service = TranscriptionService(model_size=model_size)
    
    # Override output directory if specified
    if output_dir:
        service.output_dir = Path(output_dir)
        service.output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Perform transcription
        result = service.transcribe_video(audio_path, language=language)
        
        # Log the result
        logger.info(f"Transcription completed successfully")
        logger.info(f"Total segments: {len(result['segments'])}")
        logger.info(f"Duration: {result['duration']:.2f} seconds")
        logger.info(f"Output saved to: {result.get('output_file', 'unknown')}")
        
        # Print a sample of the transcription
        logger.info("Sample transcription:")
        logger.info(f"Full text: {result['text'][:200]}...")
        
        # Print first 3 segments
        for i, segment in enumerate(result['segments'][:3]):
            logger.info(f"Segment {i+1}: [{segment['start']:.2f} - {segment['end']:.2f}] {segment['text']}")
        
        # Calculate elapsed time
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Test completed in {elapsed_time:.2f} seconds")
        
        return result
        
    except Exception as e:
        logger.error(f"Transcription test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the transcription service")
    parser.add_argument("audio_path", help="Path to the audio file to transcribe")
    parser.add_argument("--language", "-l", default="en", help="Language code for transcription")
    parser.add_argument("--model", "-m", default="base", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--output-dir", "-o", help="Directory to save the transcription output")
    
    args = parser.parse_args()
    
    test_transcription(
        audio_path=args.audio_path,
        language=args.language,
        model_size=args.model,
        output_dir=args.output_dir
    )
