#!/usr/bin/env python3
"""
Chunked Transcription for Long Audio Files

This script provides functionality to transcribe long audio files by splitting them into
manageable chunks and processing each chunk separately.

Features:
1. Split long audio files into chunks
2. Transcribe each chunk separately
3. Combine the results into a single transcript
4. Handle timeouts and errors gracefully

Usage:
    python custom_chunked_transcription.py <audio_file> [--output OUTPUT_FILE] [--model MODEL] [--chunk-size CHUNK_SIZE]

Example:
    python custom_chunked_transcription.py /app/data/temp/long_audio.wav --model tiny --chunk-size 3600
"""

import os
import sys
import json
import time
import logging
import tempfile
import subprocess
import psutil
import signal
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chunked_transcription")

# Constants
DEFAULT_CHUNK_SIZE = 3600  # 60 minutes in seconds
TIMEOUT_SECONDS = 1200  # 20 minute timeout per chunk (increased from 10 minutes)
MAX_MEMORY_PERCENT = 80  # Maximum memory usage percentage before forcing cleanup
USE_TINY_MODEL_FALLBACK = True  # Fallback to tiny model if base model fails

class ChunkedTranscriber:
    """
    Class for transcribing long audio files by splitting them into chunks.
    """
    
    def __init__(self, model_size: str = "tiny", chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize the chunked transcriber.
        
        Args:
            model_size: Size of the Whisper model to use (tiny, base, small, medium, large)
            chunk_size: Size of each chunk in seconds
        """
        self.model_size = model_size
        self.chunk_size = chunk_size
        
        # Set up paths
        if os.path.exists("/app"):
            # Docker environment
            self.temp_dir = Path("/app/data/temp")
            self.scripts_dir = Path("/app/scripts")
        else:
            # Local environment
            self.temp_dir = Path(os.path.expanduser("~/temp"))
            self.scripts_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create chunks directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.chunks_dir = self.temp_dir / "chunks" / f"{int(time.time())}_{timestamp}"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized chunked transcriber with model_size={model_size}, chunk_size={chunk_size}")
        logger.info(f"Using chunks directory: {self.chunks_dir}")
    
    def _force_garbage_collection(self):
        """
        Force garbage collection to free up memory between chunk processing.
        """
        import gc
        logger.info("Forcing garbage collection to free up memory")
        # Run garbage collection multiple times to ensure maximum cleanup
        for _ in range(3):
            gc.collect()
        
        # Log current memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        logger.info(f"Current memory usage: {memory_info.rss / (1024 * 1024):.2f} MB ({memory_percent:.2f}%)")
        
        # If memory usage is too high, try more aggressive cleanup
        if memory_percent > MAX_MEMORY_PERCENT:
            logger.warning(f"Memory usage is high ({memory_percent:.2f}%). Attempting more aggressive cleanup.")
            # Try to release any cached memory back to the OS
            if hasattr(gc, 'collect'):
                gc.collect()
            if hasattr(os, 'sync'):
                os.sync()
            # On Linux, we can try to release memory back to the OS
            try:
                with open('/proc/sys/vm/drop_caches', 'w') as f:
                    f.write('3')
            except (IOError, PermissionError):
                pass
    
    def transcribe(self, audio_path: str, output_file: Optional[str] = None, include_markers: bool = True) -> Dict[str, Any]:
        """
        Transcribe a long audio file by splitting it into chunks.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            include_markers: Whether to include chunk markers in the output
            
        Returns:
            Dict with transcription results
        """
        if not os.path.exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "transcript": ""
            }
        
        # Get the duration of the audio file
        duration = self._get_audio_duration(audio_path)
        if duration <= 0:
            error_msg = f"Failed to get duration of audio file: {audio_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "transcript": ""
            }
        
        logger.info(f"Audio file duration: {duration} seconds")
        
        # Check if the audio file is long enough to require chunking
        if duration > self.chunk_size:
            logger.info(f"Audio file is longer than {self.chunk_size} seconds, splitting into chunks")
            
            # Split the audio file into chunks
            chunks = self._split_audio(audio_path, duration)
            if not chunks:
                error_msg = "Failed to split audio file into chunks"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "transcript": ""
                }
            
            # Save chunk metadata
            metadata_file = self.chunks_dir / "chunks_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    "audio_path": audio_path,
                    "duration": duration,
                    "chunk_size": self.chunk_size,
                    "num_chunks": len(chunks),
                    "chunks": chunks
                }, f, indent=2)
            logger.info(f"Saved chunk metadata to {metadata_file}")
            
            # Transcribe each chunk
            chunk_results = []
            for i, chunk_path in enumerate(chunks):
                logger.info(f"Transcribing chunk {i+1}/{len(chunks)}: {chunk_path}")
                
                # Create output file for this chunk
                chunk_output = None
                if output_file:
                    chunk_output = str(self.chunks_dir / f"transcript_chunk_{i:03d}.txt")
                
                # Create metadata file for this chunk
                meta_output = str(self.chunks_dir / f"transcript_chunk_{i:03d}_20250801_084934.meta.json")
                
                # Clean up any previous resources before processing this chunk
                self._force_garbage_collection()
                
                # Transcribe the chunk in an isolated process with fallback to smaller model if needed
                result = self._transcribe_with_fallback(chunk_path, chunk_output)
                
                # Add chunk metadata to the result
                result["chunk_index"] = i
                result["chunk_path"] = chunk_path
                result["start_time"] = i * self.chunk_size
                result["end_time"] = min((i + 1) * self.chunk_size, duration)
                
                # Save chunk metadata for debugging and recovery
                try:
                    with open(meta_output, 'w') as f:
                        json.dump({
                            "chunk_index": i,
                            "chunk_path": chunk_path,
                            "output_path": chunk_output,
                            "start_time": i * self.chunk_size,
                            "end_time": min((i + 1) * self.chunk_size, duration),
                            "success": result["success"],
                            "timestamp": datetime.now().isoformat()
                        }, f, indent=2)
                except Exception as e:
                    logger.error(f"Error saving chunk metadata: {str(e)}")
                
                chunk_results.append(result)
                
                # Log the result
                if result["success"]:
                    logger.info(f"Successfully transcribed chunk {i+1}/{len(chunks)}")
                else:
                    logger.warning(f"Failed to transcribe chunk {i+1}/{len(chunks)}: {result.get('error', 'Unknown error')}")
                    
                # Force cleanup after processing each chunk
                self._force_garbage_collection()
            
            # Combine the transcripts
            combined_transcript = self._combine_chunk_transcripts(chunk_results, include_markers)
            
            # Save the combined transcript if output file is provided
            if output_file:
                try:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w') as f:
                        f.write(combined_transcript)
                    logger.info(f"Saved combined transcript to {output_file}")
                except Exception as e:
                    logger.error(f"Error saving combined transcript: {str(e)}")
            
            # Count successful chunks
            successful_chunks = sum(1 for chunk in chunk_results if chunk["success"])
            
            return {
                "success": successful_chunks > 0,  # Consider partial success if at least one chunk was transcribed
                "output_file": output_file,
                "transcript": combined_transcript,
                "message": f"Successfully transcribed {successful_chunks}/{len(chunk_results)} audio chunks",
                "chunks": chunk_results,
                "duration": duration
            }
        else:
            # For shorter audio files, transcribe directly
            logger.info("Audio file is short enough to transcribe directly")
            return self._transcribe_single_file(audio_path, output_file)
    
    def _monitor_process_memory(self, process_pid, stop_event):
        """
        Monitor memory usage of a process and kill it if it exceeds the threshold.
        
        Args:
            process_pid: PID of the process to monitor
            stop_event: Event to signal when monitoring should stop
        """
        logger.info(f"Starting memory monitor for process {process_pid}")
        try:
            process = psutil.Process(process_pid)
            while not stop_event.is_set():
                try:
                    # Check if process still exists
                    if not psutil.pid_exists(process_pid):
                        logger.info(f"Process {process_pid} no longer exists, stopping monitor")
                        break
                    
                    # Get memory usage
                    memory_percent = process.memory_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    
                    logger.info(f"Process {process_pid} memory usage: {memory_mb:.2f} MB ({memory_percent:.2f}%)")
                    
                    # Kill process if memory usage is too high
                    if memory_percent > MAX_MEMORY_PERCENT:
                        logger.warning(f"Process {process_pid} memory usage too high ({memory_percent:.2f}%), killing process")
                        try:
                            # Try to kill the process group first
                            os.killpg(os.getpgid(process_pid), signal.SIGTERM)
                        except (AttributeError, ProcessLookupError):
                            # Fallback to killing just the process
                            process.kill()
                        break
                    
                    # Sleep for a bit before checking again
                    time.sleep(5)
                except psutil.NoSuchProcess:
                    logger.info(f"Process {process_pid} no longer exists, stopping monitor")
                    break
                except Exception as e:
                    logger.error(f"Error monitoring process {process_pid}: {str(e)}")
                    break
        except Exception as e:
            logger.error(f"Error setting up memory monitor for process {process_pid}: {str(e)}")
    
    def _transcribe_with_fallback(self, audio_path: str, output_file: Optional[str] = None, model_size: str = None) -> Dict[str, Any]:
        """
        Attempt transcription with the specified model, falling back to a smaller model if it fails.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            model_size: Model size to use (if None, use self.model_size)
            
        Returns:
            Dict with transcription results
        """
        model_to_use = model_size or self.model_size
        
        # First attempt with specified model
        logger.info(f"Attempting transcription with {model_to_use} model")
        result = self._transcribe_single_file(audio_path, output_file, model_to_use)
        
        # If failed and we're not already using the smallest model, try with tiny model
        if not result["success"] and USE_TINY_MODEL_FALLBACK and model_to_use != "tiny":
            logger.warning(f"Transcription with {model_to_use} model failed, falling back to tiny model")
            result = self._transcribe_single_file(audio_path, output_file, "tiny")
        
        return result
    
    def _transcribe_single_file(self, audio_path: str, output_file: Optional[str] = None, model_size: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe a single audio file using the parliament_transcription.py script.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            model_size: Model size to use (if None, use self.model_size)
            
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
        
        # Create a unique environment for this process to avoid resource contention
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([env.get("PYTHONPATH", ""), str(self.scripts_dir.parent)])
        
        # Set environment variables to limit memory usage
        env["OMP_NUM_THREADS"] = "1"  # Limit OpenMP threads
        env["MKL_NUM_THREADS"] = "1"  # Limit MKL threads
        
        # Force garbage collection before starting a new process
        self._force_garbage_collection()
        
        # Use provided model_size or fall back to self.model_size
        model_to_use = model_size or self.model_size
        
        cmd = [
            "python",
            "-u",  # Unbuffered output
            str(script_path),
            audio_path,
            "--input-type", "audio",
            "--format", "txt",
            "--language", "en",
            "--model", model_to_use
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running transcription command: {' '.join(cmd)}")
        
        try:
            # Run in a separate process with isolated resources
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                # Use a new process group to ensure complete cleanup
                start_new_session=True
            )
            
            # Start memory monitoring in a separate thread
            stop_monitor = threading.Event()
            monitor_thread = threading.Thread(
                target=self._monitor_process_memory,
                args=(process.pid, stop_monitor)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            try:
                stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)  # Increased timeout per chunk
                # Stop the memory monitor
                stop_monitor.set()
                monitor_thread.join(timeout=1.0)
                
                logger.info(f"Transcription process stdout: {stdout}")
                if stderr:
                    logger.warning(f"Transcription process stderr: {stderr}")
            except subprocess.TimeoutExpired:
                # Stop the memory monitor
                stop_monitor.set()
                monitor_thread.join(timeout=1.0)
                
                # Ensure we kill the entire process group, not just the main process
                try:
                    # On Unix, negative pid kills process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(1)  # Give it a second to terminate gracefully
                    if psutil.pid_exists(process.pid):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Force kill if still running
                except (AttributeError, ProcessLookupError):
                    # Fallback for non-Unix or if process already terminated
                    try:
                        process.terminate()
                        time.sleep(1)
                        if process.poll() is None:
                            process.kill()
                    except:
                        pass
                
                stdout, stderr = process.communicate()
                logger.error(f"Transcription process timed out after {TIMEOUT_SECONDS // 60} minutes")
                
                # Force cleanup after timeout
                self._force_garbage_collection()
                
                return {
                    "success": False,
                    "error": f"Transcription process timed out after {TIMEOUT_SECONDS // 60} minutes",
                    "output_file": None,
                    "transcript": ""
                }
            finally:
                # Ensure process resources are released
                try:
                    process.stdout.close()
                    process.stderr.close()
                except:
                    pass
            
            # Check if the process was successful
            if process.returncode != 0:
                error_msg = stderr.strip()
                logger.error(f"Transcription process returned error code {process.returncode}")
                logger.error(f"STDERR: {error_msg}")
                
                # Force cleanup after error
                self._force_garbage_collection()
                
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
            
            # Force cleanup after successful processing
            self._force_garbage_collection()
            
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
                
            combined_text += chunk.get("transcript", "")
        
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
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            # Use ffprobe to get the duration
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return 0
            
            duration = float(result.stdout.strip())
            return duration
            
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return 0
    
    def _split_audio(self, audio_path: str, duration: float) -> List[str]:
        """
        Split an audio file into chunks.
        
        Args:
            audio_path: Path to the audio file
            duration: Duration of the audio file in seconds
            
        Returns:
            List of paths to the chunk files
        """
        try:
            # Calculate number of chunks
            num_chunks = int(duration / self.chunk_size) + (1 if duration % self.chunk_size > 0 else 0)
            logger.info(f"Splitting audio into {num_chunks} chunks of {self.chunk_size} seconds each")
            
            chunk_paths = []
            for i in range(num_chunks):
                # Calculate start time and duration for this chunk
                start_time = i * self.chunk_size
                chunk_duration = min(self.chunk_size, duration - start_time)
                
                # Create output path for this chunk
                chunk_path = str(self.chunks_dir / f"chunk_{i:03d}.wav")
                
                # Use ffmpeg to extract the chunk
                cmd = [
                    "ffmpeg",
                    "-y",  # Overwrite output files
                    "-ss", str(start_time),
                    "-i", audio_path,
                    "-t", str(chunk_duration),
                    "-ac", "1",  # Convert to mono
                    "-ar", "16000",  # 16kHz sample rate
                    "-vn",  # No video
                    chunk_path
                ]
                
                logger.info(f"Extracting chunk {i+1}/{num_chunks} with command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                if result.returncode != 0:
                    logger.error(f"ffmpeg failed: {result.stderr}")
                    continue
                
                # Check if the chunk file was created
                if os.path.exists(chunk_path):
                    chunk_paths.append(chunk_path)
                    logger.info(f"Created chunk file: {chunk_path}")
                else:
                    logger.error(f"Failed to create chunk file: {chunk_path}")
            
            return chunk_paths
            
        except Exception as e:
            logger.error(f"Error splitting audio: {str(e)}")
            return []

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
