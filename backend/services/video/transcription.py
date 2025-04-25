import os
import logging
import json
from pathlib import Path
import subprocess
from typing import Dict, List, Optional, Tuple

from backend.core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Service for transcribing video content using speech recognition."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_size: Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model_size = model_size
        self.output_dir = Path(settings.MEDIA_STORAGE_PATH) / "transcriptions"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def transcribe_video(self, video_path: str, language: str = "en") -> Dict:
        """
        Transcribe a video file using Whisper speech recognition.
        
        Args:
            video_path: Path to the video file
            language: Language code (default: 'en' for English)
            
        Returns:
            Dictionary containing transcription data with timestamps
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Create output filename based on input video
        output_file = self.output_dir / f"{video_path.stem}_transcription.json"
        
        try:
            # Use whisper CLI for transcription
            # This is a placeholder - in production, you'd use the whisper API directly
            result = self._run_whisper(str(video_path), language)
            
            # Save transcription to file
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Transcription saved to {output_file}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise
    
    def _run_whisper(self, video_path: str, language: str) -> Dict:
        """
        Run Whisper speech recognition on a video file.
        This is a mock implementation for development.
        
        Args:
            video_path: Path to the video file
            language: Language code
            
        Returns:
            Dictionary with transcription data
        """
        # In a real implementation, you would call the Whisper API here
        # For now, we'll return a mock result
        logger.info(f"Mock transcribing {video_path} with language {language}")
        
        # Mock transcription result
        return {
            "text": "This is a mock transcription of the parliamentary debate.",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Welcome to today's parliamentary session."
                },
                {
                    "id": 1,
                    "start": 5.0,
                    "end": 10.0,
                    "text": "We will be discussing the new climate bill."
                },
                {
                    "id": 2,
                    "start": 10.0,
                    "end": 15.0,
                    "text": "The opposition has raised several concerns."
                }
            ],
            "language": language
        }
    
    def search_transcription(self, transcription: Dict, query: str) -> List[Dict]:
        """
        Search a transcription for specific text.
        
        Args:
            transcription: Transcription dictionary
            query: Search query
            
        Returns:
            List of matching segments with timestamps
        """
        query = query.lower()
        matches = []
        
        for segment in transcription.get("segments", []):
            if query in segment.get("text", "").lower():
                matches.append(segment)
                
        return matches
    
    def get_transcription_file(self, video_path: str) -> Optional[Path]:
        """
        Get the path to a transcription file for a video if it exists.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the transcription file or None if not found
        """
        video_path = Path(video_path)
        transcription_file = self.output_dir / f"{video_path.stem}_transcription.json"
        
        if transcription_file.exists():
            return transcription_file
            
        return None
    
    def load_transcription(self, transcription_path: str) -> Dict:
        """
        Load a transcription from a file.
        
        Args:
            transcription_path: Path to the transcription file
            
        Returns:
            Transcription dictionary
        """
        with open(transcription_path, 'r') as f:
            return json.load(f)
