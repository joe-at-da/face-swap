#!/usr/bin/env python3
"""
Chunked Transcription for Long Audio Files

This script transcribes long audio files by splitting them into smaller chunks,
processing each chunk separately, and then combining the results.
This helps avoid memory issues with the Whisper model when processing long recordings.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path to import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the audio chunker and centralized configuration
from scripts.audio_chunker import AudioChunker

# Import centralized configuration
try:
    from backend.core.recognition_config import AudioConfig
except ImportError:
    # Fallback values if config module is not available
    class AudioConfig:
        DEFAULT_CHUNK_SIZE = 30

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chunked_transcription")

# Use centralized configuration for chunk size
DEFAULT_CHUNK_SIZE = AudioConfig.DEFAULT_CHUNK_SIZE

class ChunkedTranscriber:
    """Class for transcribing long audio files in chunks."""
    
    def __init__(self, model_size: str = "tiny", chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize the chunked transcriber.
        
        Args:
            model_size: Size of the Whisper model to use (tiny, base, small, medium, large)
            chunk_size: Size of each chunk in seconds
        """
        self.model_size = model_size
        self.chunk_size = chunk_size
        self.chunker = AudioChunker(chunk_size=chunk_size)
        
        # Check if we're running in Docker or locally
        if os.path.exists("/app"):
            # Docker environment
            self.scripts_dir = Path("/app/scripts")
            self.temp_dir = Path("/app/data/temp")
        else:
            # Local environment
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.scripts_dir = base_dir / "scripts"
            self.temp_dir = base_dir / "data" / "temp"
        
        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using temp directory: {self.temp_dir}")
    
    def transcribe(self, audio_path: str, output_file: Optional[str] = None, include_markers: bool = False) -> Dict[str, Any]:
        """
        Transcribe a long audio file by splitting it into chunks.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            
        Returns:
            Dict with transcription results
        """
        logger.info(f"Starting chunked transcription for: {audio_path}")
        
        # Check if audio file exists
        if not os.path.exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Audio file not found. Please check the audio extraction process.",
                "transcript": "No audio file available for transcription."
            }
        
        # Get audio duration
        duration = self.chunker.get_audio_duration(audio_path)
        if duration <= 0:
            error_msg = f"Invalid audio duration: {duration} seconds"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Audio file has invalid duration. Please check the audio extraction process.",
                "transcript": "Invalid audio file cannot be transcribed."
            }
        
        # Determine if we need to chunk the audio
        needs_chunking = duration > self.chunk_size
        logger.info(f"Audio duration: {duration} seconds, needs chunking: {needs_chunking}")
        
        if needs_chunking:
            # Split the audio into chunks
            logger.info(f"Splitting audio into chunks of {self.chunk_size} seconds")
            chunk_paths = self.chunker.split_audio(audio_path)
            
            if not chunk_paths:
                error_msg = "Failed to split audio into chunks"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": "Failed to split audio into chunks. Please check the logs for details.",
                    "transcript": "Failed to process audio file."
                }
            
            # Process each chunk
            logger.info(f"Processing {len(chunk_paths)} audio chunks")
            chunk_results = []
            
            for i, chunk_path in enumerate(chunk_paths):
                logger.info(f"Processing chunk {i+1}/{len(chunk_paths)}: {chunk_path}")
                
                # Create a temporary output file for this chunk
                chunk_output = None
                if output_file:
                    chunk_output = f"{os.path.splitext(output_file)[0]}_chunk_{i:03d}.txt"
                
                # Transcribe this chunk
                result = self._transcribe_single_file(chunk_path, chunk_output)
                
                if result["success"]:
                    # Calculate the actual start time of this chunk
                    start_time = i * self.chunk_size
                    
                    # Add the chunk result with timing information
                    chunk_results.append({
                        "chunk_index": i,
                        "start_time": start_time,
                        "end_time": start_time + self.chunk_size,
                        "transcript": result["transcript"],
                        "output_file": result["output_file"]
                    })
                    logger.info(f"Successfully transcribed chunk {i+1}")
                else:
                    logger.error(f"Failed to transcribe chunk {i+1}: {result['error']}")
            
            # Combine the chunk results
            if not chunk_results:
                error_msg = "All chunks failed to transcribe"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": "Failed to transcribe any audio chunks. Please check the logs for details.",
                    "transcript": "Failed to transcribe audio file."
                }
            
            # Combine the transcripts
            combined_transcript = self._combine_chunk_transcripts(chunk_results, include_markers=include_markers)
            
            # Save the combined transcript if an output file was specified
            final_output_file = output_file
            if final_output_file:
                try:
                    os.makedirs(os.path.dirname(final_output_file), exist_ok=True)
                    with open(final_output_file, 'w') as f:
                        f.write(combined_transcript)
                    logger.info(f"Saved combined transcript to: {final_output_file}")
                except Exception as e:
                    logger.error(f"Error saving combined transcript: {str(e)}")
                    final_output_file = None
            
            return {
                "success": True,
                "output_file": final_output_file,
                "transcript": combined_transcript,
                "message": f"Successfully transcribed {len(chunk_results)} audio chunks",
                "chunks": chunk_results,
                "duration": duration
            }
        else:
            # For shorter audio files, transcribe directly
            logger.info("Audio file is short enough to transcribe directly")
            return self._transcribe_single_file(audio_path, output_file)
    
    def _transcribe_single_file(self, audio_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe a single audio file using the parliament_transcription.py script.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            
        Returns:
            Dict with transcription results
        """
        # Prepare the command
        script_path = self.scripts_dir / "parliament_transcription.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            error_msg = f"Transcription script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "transcript": ""
            }
        
        # Ensure the output directory exists if output_file is provided
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        cmd = [
            "python",
            str(script_path),
            audio_path,
            "--input-type", "audio",
            "--format", "txt",
            "--language", "en",
            "--model", self.model_size
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running transcription command: {' '.join(cmd)}")
        
        try:
            # Execute the command with a timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout per chunk
                logger.info(f"Transcription process stdout: {stdout}")
                if stderr:
                    logger.warning(f"Transcription process stderr: {stderr}")
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                logger.error("Transcription process timed out after 10 minutes")
                return {
                    "success": False,
                    "error": "Transcription process timed out after 10 minutes",
                    "output_file": None,
                    "transcript": ""
                }
            
            # Check if the process was successful
            if process.returncode != 0:
                error_msg = stderr.strip()
                logger.error(f"Transcription process returned error code {process.returncode}")
                logger.error(f"STDERR: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "transcript": ""
                }
            
            # Parse the output to get the output file path
            output_path = None
            for line in stdout.splitlines():
                if "Transcript saved to:" in line:
                    output_path = line.split("Transcript saved to:", 1)[1].strip()
                    logger.info(f"Found transcript path in output: {output_path}")
                    break
            
            # If no output path was found in stdout, check if output_file was provided
            if not output_path and output_file:
                output_path = output_file
            
            # Load the transcript file if it exists
            transcript = ""
            if output_path and os.path.exists(output_path):
                try:
                    with open(output_path, 'r') as f:
                        transcript = f.read()
                    logger.info(f"Successfully loaded transcript from {output_path}, length: {len(transcript)} characters")
                except Exception as e:
                    logger.error(f"Error loading transcript file: {str(e)}")
            
            return {
                "success": True,
                "output_file": output_path,
                "transcript": transcript,
                "message": "Transcription completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None,
                "transcript": ""
            }
    
    def _combine_chunk_transcripts(self, chunk_results: List[Dict[str, Any]], include_markers: bool = True) -> str:
        """
        Combine transcripts from multiple chunks into a single transcript.
        
        Args:
            chunk_results: List of chunk results with transcripts
            include_markers: Whether to include chunk markers in the output
            
        Returns:
            Combined transcript text
        """
        # Sort chunks by start time
        sorted_chunks = sorted(chunk_results, key=lambda x: x["chunk_index"])
        
        # Combine the transcripts
        combined_text = ""
        for chunk in sorted_chunks:
            if include_markers:
                # Add a header for each chunk
                start_time = self._format_time(chunk["start_time"])
                end_time = self._format_time(chunk["end_time"])
                combined_text += f"\n\n[CHUNK {chunk['chunk_index']+1} - {start_time} to {end_time}]\n\n"
            elif combined_text:  # Add spacing between chunks if not the first chunk
                combined_text += "\n\n"
                
            combined_text += chunk["transcript"]
        
        return combined_text.strip()
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds to HH:MM:SS.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Transcribe long audio files in chunks')
    parser.add_argument('audio_file', help='Path to the audio file to transcribe')
    parser.add_argument('--output', '-o', help='Path to save the output transcript')
    parser.add_argument('--model', '-m', default="tiny", help='Whisper model size (tiny, base, small, medium, large)')
    parser.add_argument('--chunk-size', type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f'Size of each chunk in seconds (default: {DEFAULT_CHUNK_SIZE})')
    args = parser.parse_args()
    
    try:
        transcriber = ChunkedTranscriber(model_size=args.model, chunk_size=args.chunk_size)
        result = transcriber.transcribe(args.audio_file, args.output)
        
        if result["success"]:
            print(f"Successfully transcribed audio file")
            print(f"Output file: {result['output_file']}")
            print(f"Transcript length: {len(result['transcript'])} characters")
            if "chunks" in result:
                print(f"Processed {len(result['chunks'])} chunks")
            return 0
        else:
            print(f"Failed to transcribe audio file: {result['error']}")
            return 1
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
