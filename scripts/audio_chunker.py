#!/usr/bin/env python3
"""
Audio Chunker for Long Audio Files

This script splits long audio files into smaller chunks for more efficient processing
with the Whisper transcription model, helping to avoid memory issues.
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audio_chunker")

# Default chunk size in seconds (10 minutes)
DEFAULT_CHUNK_SIZE = 600

class AudioChunker:
    """Class for splitting long audio files into smaller chunks."""
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize the audio chunker.
        
        Args:
            chunk_size: Size of each chunk in seconds
        """
        self.chunk_size = chunk_size
        
        # Check if we're running in Docker or locally
        if os.path.exists("/app"):
            # Docker environment
            self.temp_dir = Path("/app/data/temp/chunks")
        else:
            # Local environment
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.temp_dir = base_dir / "data" / "temp" / "chunks"
        
        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using temp directory: {self.temp_dir}")
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            audio_info = json.loads(result.stdout)
            duration = float(audio_info.get('format', {}).get('duration', 0))
            logger.info(f"Audio duration: {duration} seconds")
            return duration
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to get audio duration: {str(e)}")
            return 0
    
    def split_audio(self, audio_path: str) -> List[str]:
        """
        Split an audio file into smaller chunks.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            List of paths to the audio chunks
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return []
        
        # Get audio duration
        duration = self.get_audio_duration(audio_path)
        if duration <= 0:
            logger.error(f"Invalid audio duration: {duration}")
            return []
        
        # If the audio is shorter than the chunk size, return the original file
        if duration <= self.chunk_size:
            logger.info(f"Audio file is shorter than chunk size, no need to split")
            return [audio_path]
        
        # Calculate number of chunks
        num_chunks = int(duration / self.chunk_size) + 1
        logger.info(f"Splitting audio into {num_chunks} chunks of {self.chunk_size} seconds each")
        
        # Create a timestamp for the chunk directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_name = Path(audio_path).stem
        chunk_dir = self.temp_dir / f"{audio_name}_{timestamp}"
        chunk_dir.mkdir(exist_ok=True)
        
        # Split the audio into chunks
        chunk_paths = []
        for i in range(num_chunks):
            start_time = i * self.chunk_size
            chunk_path = chunk_dir / f"chunk_{i:03d}.wav"
            
            # Use ffmpeg to extract the chunk
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(self.chunk_size),
                "-c:a", "pcm_s16le",  # Use WAV format for best compatibility
                "-ar", "16000",  # 16kHz sample rate for Whisper
                str(chunk_path)
            ]
            
            try:
                logger.info(f"Extracting chunk {i+1}/{num_chunks}: {start_time}s to {start_time + self.chunk_size}s")
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Verify the chunk was created successfully
                if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
                    chunk_paths.append(str(chunk_path))
                    logger.info(f"Created chunk: {chunk_path}")
                else:
                    logger.warning(f"Failed to create chunk: {chunk_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error creating chunk {i+1}: {str(e)}")
        
        logger.info(f"Created {len(chunk_paths)} chunks from {audio_path}")
        
        # Create a metadata file with information about the chunks
        metadata = {
            "original_file": audio_path,
            "original_duration": duration,
            "chunk_size": self.chunk_size,
            "num_chunks": num_chunks,
            "chunks": [
                {
                    "index": i,
                    "path": path,
                    "start_time": i * self.chunk_size,
                    "end_time": min((i + 1) * self.chunk_size, duration)
                }
                for i, path in enumerate(chunk_paths)
            ],
            "created_at": datetime.now().isoformat()
        }
        
        metadata_path = chunk_dir / "chunks_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved chunk metadata to: {metadata_path}")
        
        return chunk_paths

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Split long audio files into smaller chunks')
    parser.add_argument('audio_file', help='Path to the audio file to split')
    parser.add_argument('--chunk-size', type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f'Size of each chunk in seconds (default: {DEFAULT_CHUNK_SIZE})')
    args = parser.parse_args()
    
    try:
        chunker = AudioChunker(chunk_size=args.chunk_size)
        chunk_paths = chunker.split_audio(args.audio_file)
        
        if chunk_paths:
            print(f"Successfully split audio into {len(chunk_paths)} chunks:")
            for i, path in enumerate(chunk_paths):
                print(f"  Chunk {i+1}: {path}")
            return 0
        else:
            print("Failed to split audio file.")
            return 1
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
