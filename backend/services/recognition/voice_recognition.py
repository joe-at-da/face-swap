"""
Voice Recognition Service for Parliament TV Audios

This service provides voice recognition capabilities for Parliament TV audio files,
integrating with the existing scripts for speaker identification based on voice.
"""

import os
import sys
import json
import time
import logging
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings
from backend.core.recognition_config import AudioConfig, DiarizationConfig, TimeoutConfig
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class VoiceRecognitionService:
    """Service for voice recognition in Parliament TV audio files."""
    
    def __init__(self):
        """Initialize the voice recognition service."""
        self.base_dir = Path(os.environ.get('DATA_DIR', '/app/data'))
        self.voice_profiles_dir = self.base_dir / "voice_profiles"
        self.scripts_dir = Path("/app/scripts")
        
        # Create directories if they don't exist
        self.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        
    def _transcribe_audio_file(self, audio_file_path: str, timeout_seconds: int = 600) -> Dict[str, Any]:
        """Transcribe an audio file using the enhanced_parliament_transcription.py script."""
        logger.info(f"Transcribing audio file: {audio_file_path}")
        
        # Prepare the command - use the enhanced version of the script for better memory management
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts", "enhanced_parliament_transcription.py")
        
        cmd = [
            sys.executable,
            script_path,
            audio_file_path,
            "--format", "json",
            "--max-memory", "70"  # Set maximum memory usage to 70% to prevent OOM issues
        ]
        
        # Run the command with timeout
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
            if result.returncode == 0:
                # Parse the JSON output
                output = json.loads(result.stdout)
                return {
                    "success": True,
                    "output": output
                }
            else:
                logger.error(f"Transcription failed with return code {result.returncode}: {result.stderr}")
                return {
                    "success": False,
                    "error": f"Transcription failed with return code {result.returncode}"
                }
        except subprocess.TimeoutExpired:
            logger.error("Transcription timed out")
            return {
                "success": False,
                "error": "Transcription timed out"
            }
        
    def transcribe_audio(self, audio_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Transcribe an audio file using the appropriate method based on its duration.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            
        Returns:
            Dict with transcription results
        """
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
        try:
            duration = self._get_audio_duration(audio_path)
            logger.info(f"Audio duration: {duration} seconds")
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
        except Exception as e:
            error_msg = f"Error getting audio duration: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Failed to get audio duration. Please check the audio file.",
                "transcript": "Audio file cannot be processed."
            }
        
        # Get threshold for long audio directly from centralized config
        long_audio_threshold = AudioConfig.MAX_NON_CHUNKED_DURATION
        
        # Only force chunked transcription in debug/test mode
        force_chunked = False
        
        # Also force chunked transcription in debug/test mode to ensure consistent behavior
        # Use the centralized config values instead of reading environment variables directly
        from backend.core.recognition_config import DEBUG_MODE, TEST_MODE
        
        if DEBUG_MODE or TEST_MODE:
            logger.info(f"Debug/test mode detected: DEBUG_MODE={DEBUG_MODE}, TEST_MODE={TEST_MODE}")
            force_chunked = True

        if force_chunked:
            logger.info("Forcing chunked transcription approach regardless of duration")
            return self._transcribe_long_audio(audio_path, output_file, duration)
        
        # Choose transcription method based on duration
        if duration > long_audio_threshold:
            logger.info(f"Long audio file detected ({duration} seconds). Using chunked transcription approach.")
            return self._transcribe_long_audio(audio_path, output_file, duration)
        
        # For regular-length audio files, use the standard approach
        return self._transcribe_standard_audio(audio_path, output_file)
    
    def _transcribe_long_audio(self, audio_path: str, output_file: Optional[str] = None, duration: float = 0) -> Dict:
        """
        Transcribe a long audio file using the chunked transcription approach.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            duration: Duration of the audio file in seconds
            
        Returns:
            Dict with transcription results formatted with segments
        """
        logger.info(f"Using chunked transcription for long audio file: {audio_path} ({duration} seconds)")
        
        # Import the chunked transcriber here to avoid circular imports
        sys.path.append(str(Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))  # Add project root
        
        # Try to use the custom chunked transcription first (with better resource management)
        try:
            from scripts.custom_chunked_transcription import ChunkedTranscriber
            logger.info("Using enhanced custom chunked transcription with improved resource management")
        except ImportError:
            # Fall back to standard chunked transcription if custom one is not available
            from scripts.chunked_transcription import ChunkedTranscriber
            logger.warning("Enhanced custom chunked transcription not found, using standard implementation")
        
        # Maximum number of retries
        max_retries = 3  # Increased from 2 to 3 for more resilience
        retry_count = 0
        last_error = None
        
        # Get model size from environment variable or use default
        # For hour-long videos, we want to balance quality and memory usage
        # Options: tiny, base, small, medium, large
        model_size = os.environ.get('LONG_AUDIO_MODEL_SIZE', 'tiny')  # Default to 'tiny' for faster processing
        logger.info(f"Using model size '{model_size}' for long audio transcription")
        
        # Set up environment variables to limit memory usage
        os.environ['OMP_NUM_THREADS'] = '1'  # Limit OpenMP threads
        os.environ['MKL_NUM_THREADS'] = '1'  # Limit MKL threads
        
        # Use chunk size directly from centralized config
        # This ensures we always respect the global DEBUG_MODE/TEST_MODE settings
        chunk_size = AudioConfig.DEFAULT_CHUNK_SIZE
        
        if AudioConfig.DEFAULT_CHUNK_SIZE == 30:
            logger.info("TEST_MODE active: Using 30-second chunks")
        elif AudioConfig.DEFAULT_CHUNK_SIZE == 60:
            logger.info("DEBUG_MODE active: Using 60-second chunks")
        else:
            logger.info("Production mode: Using 60-minute chunks")
            
        logger.info(f"Using audio chunk size of {chunk_size} seconds")
        
        # Import debug/test mode flags
        from backend.core.recognition_config import DEBUG_MODE, TEST_MODE
        
        # Only include chunk markers in debug/test mode
        include_markers = DEBUG_MODE or TEST_MODE
        logger.info(f"Including chunk markers in transcript: {include_markers}")
        
        # Try transcription with retries
        while retry_count <= max_retries:
            try:
                # Initialize the chunked transcriber with appropriate settings
                try:
                    transcriber = ChunkedTranscriber(model_size=model_size, chunk_size=chunk_size)
                    logger.info(f"Successfully initialized chunked transcriber with model_size={model_size}, chunk_size={chunk_size}")
                except Exception as e:
                    logger.error(f"Error initializing chunked transcriber: {str(e)}")
                    raise
                
                # Transcribe the audio file
                result = transcriber.transcribe(audio_path, output_file, include_markers=include_markers)
                
                # Log the result
                if result["success"]:
                    logger.info(f"Chunked transcription completed successfully on attempt {retry_count + 1}")
                    if "chunks" in result:
                        logger.info(f"Processed {len(result['chunks'])} chunks")
                    
                    # Verify we have actual transcript content and not just placeholder
                    transcript = result.get("transcript", "")
                    if isinstance(transcript, str) and len(transcript.strip()) > 50:
                        logger.info(f"Transcript length: {len(transcript)} characters")
                        # Check if transcript contains actual content and not just placeholder text
                        if "[Transcription failed" not in transcript and "[No speech detected" not in transcript:
                            # Convert the chunked transcript into segments format that multimodal recognition expects
                            segments = self._convert_chunked_transcript_to_segments(result)
                            
                            # Return the result with segments
                            return {
                                "success": True,
                                "output_file": result.get("output_file"),
                                "transcript": {
                                    "segments": segments,
                                    "text": transcript
                                },
                                "message": f"Successfully transcribed audio with {len(segments)} segments"
                            }
                        else:
                            logger.warning(f"Transcript contains placeholder text: {transcript[:100]}...")
                            last_error = "Transcript contains placeholder text"
                    else:
                        logger.warning("Transcript is too short or empty")
                        last_error = "Transcript is too short or empty"
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Chunked transcription failed on attempt {retry_count + 1}: {error_msg}")
                    last_error = error_msg
                
                # If we got here and haven't returned, the transcription wasn't successful
                # Try with a different model size if we're going to retry
                if retry_count == 0 and model_size != "small":
                    model_size = "small"  # Try with small model on first retry
                    logger.info(f"Retrying with model size '{model_size}'")
                elif retry_count == 1 and model_size != "base":
                    model_size = "base"  # Try with base model on second retry
                    logger.info(f"Retrying with model size '{model_size}'")
                elif retry_count == 2 and model_size != "tiny":
                    model_size = "tiny"  # Try with tiny model on third retry as last resort
                    logger.info(f"Retrying with tiny model as last resort")
                    
                # Force garbage collection between retries
                import gc
                logger.info("Forcing garbage collection between retry attempts")
                for _ in range(3):
                    gc.collect()
                
            except Exception as e:
                logger.error(f"Error in chunked transcription attempt {retry_count + 1}: {str(e)}")
                last_error = str(e)
            
            retry_count += 1
            if retry_count <= max_retries:
                logger.info(f"Retrying chunked transcription (attempt {retry_count + 1} of {max_retries + 1})")
        
        # If we get here, all retries failed
        logger.error(f"All chunked transcription attempts failed after {max_retries + 1} tries. Last error: {last_error}")
        return {
            "success": False,
            "error": f"Failed after {max_retries + 1} attempts. Last error: {last_error}",
            "output_file": None,
            "message": f"Transcription failed after multiple attempts. Please check the logs for details.",
            "transcript": f"[Transcription could not be completed after {max_retries + 1} attempts. Last error: {last_error}]"
        }
    
    def _process_diarization_segments(self, diarization_segments: List[Dict]) -> List[Dict]:
        """
        Process diarization segments to ensure consistent speech group IDs.
        This is critical to ensure one clip per speaker turn, not per chunk.
        
        Args:
            diarization_segments: List of diarization segments from chunked result
            
        Returns:
            Processed diarization segments with consistent speech group IDs
        """
        if not diarization_segments:
            return []
            
        # Sort segments by start time to ensure proper sequencing
        sorted_segments = sorted(diarization_segments, key=lambda x: x.get('start_time', x.get('start', 0)))
        
        # Log the first few segments for debugging
        logger.info(f"Processing {len(sorted_segments)} diarization segments")
        for i, segment in enumerate(sorted_segments[:3]):  # Log first 3 segments
            logger.info(f"Segment {i} before processing: speaker={segment.get('speaker')}, "
                       f"start={segment.get('start_time', segment.get('start', 0))}, "
                       f"end={segment.get('end_time', segment.get('end', 0))}")
        
        # Assign speech group IDs based on speaker changes, not chunk boundaries
        processed_segments = []
        current_speaker = None
        speech_group_counter = 0
        
        for segment in sorted_segments:
            # Ensure we have start_time and end_time fields
            if 'start_time' not in segment and 'start' in segment:
                segment['start_time'] = segment['start']
            if 'end_time' not in segment and 'end' in segment:
                segment['end_time'] = segment['end']
                
            speaker = segment.get('speaker', 'UNKNOWN')
            
            # If speaker changes, increment speech group counter
            if speaker != current_speaker:
                speech_group_counter += 1
                current_speaker = speaker
                logger.debug(f"Speaker change detected: {speaker}, new speech group: {speech_group_counter}")
            
            # Create a new segment with consistent speech group ID
            new_segment = segment.copy()
            new_segment['speech_group_id'] = f"speech_group_{speech_group_counter}"
            
            # Ensure all required fields are present
            if 'start' not in new_segment and 'start_time' in new_segment:
                new_segment['start'] = new_segment['start_time']
            if 'end' not in new_segment and 'end_time' in new_segment:
                new_segment['end'] = new_segment['end_time']
                
            processed_segments.append(new_segment)
        
        logger.info(f"Processed {len(processed_segments)} diarization segments into {speech_group_counter} speech groups")
        
        # Log a few processed segments for debugging
        for i, segment in enumerate(processed_segments[:3]):  # Log first 3 segments
            logger.info(f"Segment {i} after processing: speaker={segment.get('speaker')}, "
                       f"speech_group={segment.get('speech_group_id')}, "
                       f"start={segment.get('start_time', segment.get('start', 0))}, "
                       f"end={segment.get('end_time', segment.get('end', 0))}")
                       
        return processed_segments
        
    def _convert_chunked_transcript_to_segments(self, chunked_result: Dict) -> List[Dict]:
        """
        Convert a chunked transcript into segments format that multimodal recognition expects.
        Uses diarization-driven segmentation to ensure consistent output with non-chunked transcription.
        
        Args:
            chunked_result: Result from the chunked transcriber
            
        Returns:
            List of segments in the format expected by multimodal recognition
        """
        logger.info("Converting chunked transcript to diarization-driven segments")
        
        # Check if we have diarization data in the chunked result
        if "diarization" in chunked_result and chunked_result["diarization"].get("segments"):
            # Use the diarization segments directly - this is the preferred approach
            logger.info(f"Using {len(chunked_result['diarization']['segments'])} diarization segments from chunked result")
            diarization_segments = chunked_result["diarization"]["segments"]
            
            # Ensure all diarization segments have start_time and end_time fields
            for segment in diarization_segments:
                if "start_time" not in segment and "start" in segment:
                    segment["start_time"] = segment["start"]
                if "end_time" not in segment and "end" in segment:
                    segment["end_time"] = segment["end"]
            
            # Log the diarization segments for debugging
            logger.info(f"Diarization segments before processing: {len(diarization_segments)} segments")
            for i, segment in enumerate(diarization_segments[:5]):  # Log first 5 segments
                logger.info(f"Segment {i}: speaker={segment.get('speaker')}, start={segment.get('start_time')}, end={segment.get('end_time')}")
            
            # Process diarization segments to ensure consistent speech group IDs
            # This is critical to ensure one clip per speaker turn, not per chunk
            processed_segments = self._process_diarization_segments(diarization_segments)
            
            # Log the processed segments for debugging
            logger.info(f"Processed segments after speech group assignment: {len(processed_segments)} segments")
            for i, segment in enumerate(processed_segments[:5]):  # Log first 5 segments
                logger.info(f"Processed segment {i}: speaker={segment.get('speaker')}, speech_group={segment.get('speech_group_id')}")
                
            # Get the transcript directory using our simple transcript finder
            from backend.services.recognition.transcript_finder import find_transcript_directory
            
            # Get video path for context if available
            video_path = None
            if "video_path" in chunked_result:
                video_path = chunked_result["video_path"]
            
            # Find transcript directory
            transcript_dir = find_transcript_directory(video_path)
            logger.info(f"Using transcript directory: {transcript_dir}")
            
            # Use the transcript matcher to match transcripts to segments
            from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments
            logger.info(f"Using transcript matcher with directory: {transcript_dir}")
            processed_segments = match_transcripts_to_diarization_segments(processed_segments, transcript_dir)
            
            # Log transcript matching results
            placeholder_count = sum(1 for s in processed_segments if s.get('text', '').startswith("Speech segment from"))
            match_count = len(processed_segments) - placeholder_count
            match_percentage = (match_count / len(processed_segments) * 100) if processed_segments else 0
            logger.info(f"Transcript matching results: {match_count}/{len(processed_segments)} segments matched ({match_percentage:.1f}%)")
            
            # Convert diarization segments to the format expected by multimodal recognition
            segments = []
            for i, segment in enumerate(processed_segments):
                speaker = segment.get("speaker", f"SPEAKER_{i % 10}")  # Use speaker from diarization or fallback
                start_time = segment.get("start_time", 0)
                end_time = segment.get("end_time", 0)
                speech_group_id = segment.get("speech_group_id", f"speech_group_{i}")
                
                # Create segment with required fields
                whisper_segment = {
                    "id": f"{start_time}-{end_time}",
                    "seek": start_time,
                    "start": start_time,
                    "end": end_time,
                    "text": segment.get("text", ""),  # Use existing text if available
                    "tokens": [],
                    "temperature": 0.0,
                    "avg_logprob": -0.5,
                    "compression_ratio": 1.0,
                    "no_speech_prob": 0.1,
                    "speaker": speaker,
                    "start_time": start_time,  # Add explicit start_time for transcript matcher
                    "end_time": end_time,      # Add explicit end_time for transcript matcher
                    "diarization_segment": True,  # Flag to indicate this is a diarization segment
                    "speech_group_marker": speech_group_id,  # Preserve speech group ID for consistent grouping
                    "recognition_method": "diarization"  # Mark as diarization-based for parliament_clips_integration
                }
                segments.append(whisper_segment)
            
            logger.info(f"Converted {len(segments)} diarization segments to multimodal recognition format")
            return segments
        
        # If no diarization data, fall back to extracting segments from chunks
        # This approach uses speaker turn detection based on transcript content
        logger.info("No diarization data found, using fallback approach to extract speaker segments from chunks")
        
        all_speaker_segments = []  # Initialize list to collect all speaker segments across chunks
        chunk_results = chunked_result.get("chunks", [])
        
        if not chunk_results:
            # If no chunks are available, create a single segment from the transcript
            transcript = chunked_result.get("transcript", "")
            if transcript:
                all_speaker_segments.append({
                    "speaker": "SPEAKER_0",
                    "text": transcript,
                    "start": 0,
                    "end": chunked_result.get("duration", 0),
                    "start_time": 0,
                    "end_time": chunked_result.get("duration", 0)
                })
            logger.warning("No chunks available, created single segment from transcript")
        else:
            # Process each chunk to extract speaker segments
            logger.info(f"Processing {len(chunk_results)} chunks to extract speaker segments")
            
            for i, chunk in enumerate(chunk_results):
                # Extract chunk data
                transcript = chunk.get("text", "")
                start_time = chunk.get("start", 0)
                end_time = chunk.get("end", 0)
                
                logger.info(f"Processing chunk {i}: start={start_time}, end={end_time}, text_length={len(transcript)}")
                
                # Initialize speaker segments for this chunk
                speaker_segments = []
                
                # Try to detect natural speaker turns within the chunk
                # Look for patterns like "Speaker: " or long pauses
                import re
                
                # Try to find speaker patterns like "Speaker: " or "[Speaker]:"
                speaker_pattern = re.compile(r'([A-Za-z\s]+):\s')
                speaker_matches = list(speaker_pattern.finditer(transcript))
                
                # Try to find pause patterns like "..." or "[pause]" or "[silence]"
                pause_pattern = re.compile(r'\.\.\.|\[pause\]|\[silence\]')
                pause_matches = list(pause_pattern.finditer(transcript))
                
                # If we found speaker patterns, use them to segment
                if speaker_matches:
                    logger.info(f"Found {len(speaker_matches)} speaker patterns in chunk {i}")
                    
                    # Process each speaker segment
                    last_end = 0
                    for j, match in enumerate(speaker_matches):
                        # Extract the speaker name
                        speaker_name = match.group(1).strip()
                        speaker = f"SPEAKER_{speaker_name}"
                        
                        # Calculate segment start and end positions
                        segment_start = match.start()
                        segment_end = speaker_matches[j+1].start() if j < len(speaker_matches) - 1 else len(transcript)
                        
                        # Extract the text for this segment
                        segment_text = transcript[segment_start:segment_end].strip()
                        
                        # Skip empty segments
                        if not segment_text:
                            continue
                            
                        # Calculate timing based on position in text
                        text_fraction_start = segment_start / len(transcript)
                        text_fraction_end = segment_end / len(transcript)
                        
                        segment_start_time = start_time + (end_time - start_time) * text_fraction_start
                        segment_end_time = start_time + (end_time - start_time) * text_fraction_end
                        
                        # Create the segment
                        speaker_segments.append({
                            "speaker": speaker,
                            "text": segment_text,
                            "start": segment_start_time,
                            "end": segment_end_time,
                            "start_time": segment_start_time,
                            "end_time": segment_end_time
                        })
                        
                        last_end = segment_end
                
                # If we found pause patterns, use them as fallback segmentation
                elif pause_matches:
                    logger.info(f"Found {len(pause_matches)} pause patterns in chunk {i}")
                    
                    # Process each pause-separated segment
                    last_end = 0
                    for j, match in enumerate(pause_matches):
                        # Calculate segment end position
                        segment_end = match.start()
                        
                        # Skip if this would create an empty segment
                        if segment_end <= last_end:
                            continue
                            
                        # Extract the text for this segment
                        segment_text = transcript[last_end:segment_end].strip()
                        
                        # Skip empty segments
                        if not segment_text:
                            continue
                            
                        # Calculate timing based on position in text
                        text_fraction_start = last_end / len(transcript)
                        text_fraction_end = segment_end / len(transcript)
                        
                        segment_start_time = start_time + (end_time - start_time) * text_fraction_start
                        segment_end_time = start_time + (end_time - start_time) * text_fraction_end
                        
                        # Create the segment with a unique speaker ID
                        speaker_segments.append({
                            "speaker": f"SPEAKER_{(i + j) % 10}",
                            "text": segment_text,
                            "start": segment_start_time,
                            "end": segment_end_time,
                            "start_time": segment_start_time,
                            "end_time": segment_end_time
                        })
                        
                        last_end = segment_end + match.end() - match.start()  # Skip the pause marker
                    
                    # Add the final segment after the last pause
                    if last_end < len(transcript):
                        segment_text = transcript[last_end:].strip()
                        if segment_text:
                            # Calculate timing based on position in text
                            text_fraction_start = last_end / len(transcript)
                            text_fraction_end = 1.0
                            
                            segment_start_time = start_time + (end_time - start_time) * text_fraction_start
                            segment_end_time = end_time
                            
                            speaker_segments.append({
                                "speaker": f"SPEAKER_{(i + len(pause_matches)) % 10}",
                                "text": segment_text,
                                "start": segment_start_time,
                                "end": segment_end_time,
                                "start_time": segment_start_time,
                                "end_time": segment_end_time
                            })
                else:
                    # If no natural segmentation found, create at least 2-3 segments within the chunk
                    # to ensure we don't have just one segment per chunk
                    logger.info(f"No natural segmentation found, creating artificial segments for chunk {i}")
                    
                    # Try to split into 2-3 segments based on transcript length
                    num_segments = min(3, max(2, len(transcript) // 100))
                    segment_length = len(transcript) / num_segments
                    
                    for j in range(num_segments):
                        start_idx = int(j * segment_length)
                        end_idx = int((j + 1) * segment_length) if j < num_segments - 1 else len(transcript)
                        
                        segment_text = transcript[start_idx:end_idx].strip()
                        if not segment_text:
                            continue
                            
                        # Calculate timing based on position
                        segment_start_time = start_time + (end_time - start_time) * (start_idx / len(transcript))
                        segment_end_time = start_time + (end_time - start_time) * (end_idx / len(transcript))
                        
                        speaker_segments.append({
                            "speaker": f"SPEAKER_{(i + j) % 10}",
                            "text": segment_text,
                            "start": segment_start_time,
                            "end": segment_end_time,
                            "start_time": segment_start_time,
                            "end_time": segment_end_time
                        })
                
                # If we still have no segments, fall back to one segment for the chunk
                if not speaker_segments:
                    logger.warning(f"Failed to extract speaker turns from chunk {i}, falling back to one segment")
                    speaker_segments.append({
                        "speaker": f"SPEAKER_{i % 10}",
                        "text": transcript,
                        "start": start_time,
                        "end": end_time,
                        "start_time": start_time,
                        "end_time": end_time
                    })
                
                # Add all speaker segments from this chunk to the overall list
                all_speaker_segments.extend(speaker_segments)
        
        # Log the extracted segments
        logger.info(f"Extracted {len(all_speaker_segments)} speaker segments from {len(chunk_results)} chunks")
        for i, segment in enumerate(all_speaker_segments[:5]):  # Log first 5 segments
            logger.info(f"Extracted segment {i}: speaker={segment['speaker']}, start={segment['start_time']:.2f}, end={segment['end_time']:.2f}, text={segment['text'][:50]}...")
        
        # Process speaker segments to ensure consistent speech group IDs
        # This is critical to ensure one clip per speaker turn, not per chunk
        processed_segments = self._process_diarization_segments(all_speaker_segments)
        
        # Get the transcript directory using our simple transcript finder
        try:
            from backend.services.recognition.transcript_finder import find_transcript_directory
            
            # Get video path for context if available
            video_path = None
            if "video_path" in chunked_result:
                video_path = chunked_result["video_path"]
            
            # Find transcript directory
            transcript_dir = find_transcript_directory(video_path)
            logger.info(f"Using transcript directory: {transcript_dir}")
            
            # Use the transcript matcher to match transcripts to segments
            from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments
            logger.info(f"Using transcript matcher with directory: {transcript_dir} for fallback segments")
            processed_segments = match_transcripts_to_diarization_segments(processed_segments, transcript_dir)
            
            # Log transcript matching results
            placeholder_count = sum(1 for s in processed_segments if s.get('text', '').startswith("Speech segment from"))
            match_count = len(processed_segments) - placeholder_count
            match_percentage = (match_count / len(processed_segments) * 100) if processed_segments else 0
            logger.info(f"Transcript matching results for fallback segments: {match_count}/{len(processed_segments)} segments matched ({match_percentage:.1f}%)")
        except Exception as e:
            logger.error(f"Error in transcript matching: {str(e)}")
            logger.warning("Continuing with original segments due to transcript matching error")
        
        # Convert speaker segments to the format expected by multimodal recognition
        segments = []  # Initialize segments list to collect all processed segments
        for segment in processed_segments:
            segment_id = f"{segment['start']}-{segment['end']}"
            speech_group_id = segment.get('speech_group_id', 'speech_group_0')
            
            whisper_segment = {
                "id": segment_id,
                "seek": segment["start"],
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": -0.5,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.1,
                "speaker": segment["speaker"],
                "start_time": segment["start_time"],  # Add explicit start_time for transcript matcher
                "end_time": segment["end_time"],      # Add explicit end_time for transcript matcher
                "diarization_segment": True,  # Flag to indicate this is a diarization segment
                "speech_group_marker": speech_group_id,  # Use processed speech group ID
                "recognition_method": "diarization"  # Mark as diarization-based for parliament_clips_integration
            }
            segments.append(whisper_segment)  # Add each segment to the segments list
            # Get the transcript directory using our simple transcript finder
            from backend.services.recognition.transcript_finder import find_transcript_directory
            
            # Get video path for context if available
            video_path = None
            if "video_path" in chunked_result:
                video_path = chunked_result["video_path"]
            
            # Find transcript directory
            transcript_dir = find_transcript_directory(video_path)
            logger.info(f"Using transcript directory for single segment: {transcript_dir}")
                
            try:
                from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments
                logger.info(f"Using transcript matcher with directory: {transcript_dir} for single segment")
                segments = match_transcripts_to_diarization_segments(segments, transcript_dir)
            except Exception as e:
                logger.error(f"Error in single segment transcript matching: {str(e)}")
                logger.warning("Continuing with original segment due to transcript matching error")
            
            return segments
        
        # Process each chunk to extract speaker turns
        # This is a fallback when diarization data is not available
        logger.info(f"Using fallback approach: extracting speaker turns from {len(chunk_results)} chunks")
        
        # Extract speaker segments from all chunks first
        all_speaker_segments = []
        
        # Get the transcript directory using our simple transcript finder
        from backend.services.recognition.transcript_finder import find_transcript_directory
        
        # Get video path for context if available
        video_path = None
        if "video_path" in chunked_result:
            video_path = chunked_result["video_path"]
        
        # Find transcript directory
        transcript_dir = find_transcript_directory(video_path)
        logger.info(f"Using transcript directory: {transcript_dir}")
        for i, chunk in enumerate(chunk_results):
            chunk_start = chunk.get("start", 0)
            chunk_end = chunk.get("end", 0)
            chunk_transcript = chunk.get("text", "")
            
            # Try to extract speaker turns from the transcript
            # Look for patterns like "Speaker X: text" or "[Speaker X] text"
            speaker_segments = []
            
            # Check if the chunk has its own diarization data
            if "diarization" in chunk and chunk["diarization"].get("segments"):
                # Use the chunk's diarization segments
                chunk_diarization_segments = chunk["diarization"]["segments"]
                logger.info(f"Found {len(chunk_diarization_segments)} diarization segments in chunk {i}")
                
                for j, segment in enumerate(chunk_diarization_segments):
                    speaker = segment.get("speaker", f"SPEAKER_{j % 10}")
                    start_time = segment.get("start_time", segment.get("start", chunk_start))
                    end_time = segment.get("end_time", segment.get("end", chunk_end))
                    
                    # Adjust times to be relative to the entire audio, not just the chunk
                    if start_time < chunk_start:
                        start_time += chunk_start
                    if end_time < chunk_end:
                        end_time += chunk_start
                    
                    speaker_segments.append({
                        "speaker": speaker,
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": segment.get("text", ""),  # May be empty, will be filled by transcript matcher
                        "chunk_index": i
                    })
            else:
                # No diarization data in the chunk, treat the entire chunk as one segment
                speaker_segments.append({
                    "speaker": f"SPEAKER_{i % 10}",
                    "start_time": chunk_start,
                    "end_time": chunk_end,
                    "text": chunk_transcript,
                    "chunk_index": i
                })
                
            # Add all speaker segments from this chunk to the overall list
            all_speaker_segments.extend(speaker_segments)

            
            # If we still have no segments, fall back to one segment for the chunk
            if not speaker_segments:
                logger.warning(f"Failed to extract speaker turns from chunk {i}, falling back to one segment")
                speaker_segments.append({
                    "speaker": f"SPEAKER_{i % 10}",
                    "text": transcript,
                    "start": start_time,
                    "end": end_time,
                    "start_time": start_time,
                    "end_time": end_time
                })
            
            # Add all speaker segments from this chunk to the overall list
            all_speaker_segments.extend(speaker_segments)
        
        # Log the extracted segments
        logger.info(f"Extracted {len(all_speaker_segments)} speaker segments from {len(chunk_results)} chunks")
        for i, segment in enumerate(all_speaker_segments[:5]):  # Log first 5 segments
            logger.info(f"Extracted segment {i}: speaker={segment['speaker']}, start={segment['start_time']:.2f}, end={segment['end_time']:.2f}, text={segment['text'][:50]}...")
        
        # Process speaker segments to ensure consistent speech group IDs
        # This is critical to ensure one clip per speaker turn, not per chunk
        processed_segments = self._process_diarization_segments(all_speaker_segments)
        
        # If we have a transcript directory, use the transcript matcher to match transcripts to segments
        try:
            # Always import the transcript matcher
            from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments
            
            # The transcript matcher now has built-in fallback directory handling
            # so we can safely pass the transcript_dir even if it might be None or empty
            logger.info(f"Using transcript matcher with directory: {transcript_dir} for fallback segments")
            processed_segments = match_transcripts_to_diarization_segments(processed_segments, transcript_dir)
            
            # Log transcript matching results
            placeholder_count = sum(1 for s in processed_segments if s.get('text', '').startswith("Speech segment from"))
            match_count = len(processed_segments) - placeholder_count
            match_percentage = (match_count / len(processed_segments) * 100) if processed_segments else 0
            logger.info(f"Transcript matching results for fallback segments: {match_count}/{len(processed_segments)} segments matched ({match_percentage:.1f}%)")
        except Exception as e:
            logger.error(f"Error in transcript matching: {str(e)}")
            logger.warning("Continuing with original segments due to transcript matching error")
        
        # Convert speaker segments to the format expected by multimodal recognition
        segments = []  # Initialize segments list to collect all processed segments
        for segment in processed_segments:
            segment_id = f"{segment['start']}-{segment['end']}"
            speech_group_id = segment.get('speech_group_id', 'speech_group_0')
            
            whisper_segment = {
                "id": segment_id,
                "seek": segment["start"],
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": -0.5,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.1,
                "speaker": segment["speaker"],
                "start_time": segment["start_time"],  # Add explicit start_time for transcript matcher
                "end_time": segment["end_time"],      # Add explicit end_time for transcript matcher
                "diarization_segment": True,  # Flag to indicate this is a diarization segment
                "speech_group_marker": speech_group_id,  # Use processed speech group ID
                "recognition_method": "diarization"  # Mark as diarization-based for parliament_clips_integration
            }
            segments.append(whisper_segment)  # Add each segment to the segments list
        
        # Log detailed information about the segments for debugging
        logger.info(f"Converted chunked transcript to {len(segments)} segments with speech group markers")
        
        # Log distribution of speakers and speech groups
        speaker_counts = {}
        speech_group_counts = {}
        for segment in segments:
            speaker = segment.get('speaker', 'unknown')
            speech_group = segment.get('speech_group_marker', 'unknown')
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
            speech_group_counts[speech_group] = speech_group_counts.get(speech_group, 0) + 1
        
        logger.info(f"Speaker distribution in segments: {speaker_counts}")
        logger.info(f"Speech group distribution in segments: {speech_group_counts}")
        
        # Log the first few segments for debugging
        for i, segment in enumerate(segments[:5]):
            logger.info(f"Final segment {i}: speaker={segment.get('speaker')}, "
                       f"speech_group={segment.get('speech_group_marker')}, "
                       f"start={segment.get('start_time'):.2f}, end={segment.get('end_time'):.2f}, "
                       f"text={segment.get('text')[:50]}...")
        
        return segments
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            import subprocess
            import json
            
            # Use ffprobe to get duration
            cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            
            logger.info(f"Audio duration: {duration} seconds")
            return duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            # Return a default duration if we can't determine it
            return 0.0
    
    def _transcribe_standard_audio(self, audio_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Transcribe a standard-length audio file using the direct approach.
        
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
                "output_file": None
            }
        
        # Ensure the output directory exists
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        cmd = [
            "python",
            str(script_path),
            audio_path,
            "--input-type", "audio",
            "--format", "txt",  # Explicitly specify format
            "--language", "en"  # Explicitly specify English language
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running transcription command: {' '.join(cmd)}")
        
        try:
            # Create a unique environment for this process to avoid resource contention
            env = os.environ.copy()
            env["OMP_NUM_THREADS"] = "1"  # Limit OpenMP threads
            env["MKL_NUM_THREADS"] = "1"  # Limit MKL threads
            
            # Force garbage collection before starting a new process
            import gc
            logger.info("Forcing garbage collection before starting transcription process")
            for _ in range(3):
                gc.collect()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                # Use a new process group to ensure complete cleanup
                start_new_session=True
            )
            
            try:
                # Use centralized timeout configuration
                timeout_seconds = TimeoutConfig.MAX_TRANSCRIPTION_PROCESSING_TIME
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                logger.info(f"Transcription process stdout: {stdout}")
                if stderr:
                    logger.warning(f"Transcription process stderr: {stderr}")
            except subprocess.TimeoutExpired:
                # Ensure we kill the entire process group, not just the main process
                try:
                    # On Unix, negative pid kills process group
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(1)  # Give it a second to terminate gracefully
                    if psutil.pid_exists(process.pid):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # Force kill if still running
                except (AttributeError, ProcessLookupError, NameError):
                    # Fallback for non-Unix or if process already terminated
                    try:
                        process.terminate()
                        time.sleep(1)
                        if process.poll() is None:
                            process.kill()
                    except:
                        pass
                
                stdout, stderr = process.communicate()
                timeout_minutes = timeout_seconds // 60
                error_msg = f"Transcription process timed out after {timeout_minutes} minutes"
                logger.error(error_msg)
                
                # Force cleanup after timeout
                import gc
                logger.info("Forcing garbage collection after timeout")
                for _ in range(3):
                    gc.collect()
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": f"Transcription failed due to timeout. The audio file may be too large or complex.",
                    "transcript": f"[Transcription failed: Process timed out after {timeout_minutes} minutes]"
                }
            
            # Check if the process was successful
            if process.returncode != 0:
                # Check for specific error messages
                error_msg = stderr.strip()
                logger.error(f"Transcription process returned error code {process.returncode}")
                logger.error(f"STDERR: {error_msg}")
                logger.error(f"STDOUT: {stdout.strip()}")
                
                if "Loading Whisper model" in stderr:
                    error_msg = "Failed to load Whisper model. The model may be corrupted or unavailable."
                    logger.error(f"Transcription failed: {error_msg}")
                    # This is a critical error that needs to be fixed
                    return {
                        "success": False,
                        "error": error_msg,
                        "output_file": None,
                        "message": "Transcription failed due to Whisper model loading issues. Please check the model installation.",
                        "transcript": "[Transcription failed: Unable to load Whisper model]"
                    }
                
                logger.error(f"Transcription failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": "Transcription failed due to an error. Please check the logs for details.",
                    "transcript": "[Transcription failed: " + error_msg + "]"
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
                logger.info(f"Using provided output file path: {output_path}")
            
            # Load the transcript file if it exists
            transcript = ""
            if output_path and os.path.exists(output_path):
                try:
                    with open(output_path, 'r') as f:
                        transcript = f.read()
                    logger.info(f"Successfully loaded transcript from {output_path}, length: {len(transcript)} characters")
                except Exception as e:
                    logger.error(f"Error loading transcript file: {str(e)}")
            elif not output_path:
                logger.warning("No transcript output path found in command output")
            elif not os.path.exists(output_path):
                logger.warning(f"Transcript file not found at expected path: {output_path}")
            
            # If we have no transcript but the process completed successfully, this is suspicious
            if not transcript and process.returncode == 0:
                logger.warning("Process completed successfully but no transcript was generated")
                
                # Check if there are any .txt files in the output directory that might be our transcript
                if output_path:
                    output_dir = os.path.dirname(output_path)
                    txt_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and os.path.getsize(os.path.join(output_dir, f)) > 0]
                    
                    if txt_files:
                        # Use the most recently modified file
                        newest_file = max(txt_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
                        newest_path = os.path.join(output_dir, newest_file)
                        logger.info(f"Found potential transcript file: {newest_path}")
                        
                        try:
                            with open(newest_path, 'r') as f:
                                transcript = f.read()
                            logger.info(f"Loaded transcript from alternative file, length: {len(transcript)} characters")
                            output_path = newest_path
                        except Exception as e:
                            logger.error(f"Error loading alternative transcript file: {str(e)}")
                
                if not transcript:
                    return {
                        "success": False,
                        "error": "Transcription process completed but no transcript was generated",
                        "output_file": output_path,
                        "transcript": ""
                    }
            
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
                "transcript": "[Transcription failed due to an unexpected error]"
            }
    
    def _transcribe_audio_chunked(self, audio_file_path: str, chunk_duration_seconds: int = 300, timeout_seconds: int = 600) -> Dict[str, Any]:
        """Transcribe an audio file in chunks to avoid memory issues."""
        logger.info(f"Transcribing audio file in chunks: {audio_file_path}")
        
        # Create a directory for chunks
        audio_dir = os.path.dirname(audio_file_path)
        chunks_dir = os.path.join(audio_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        # Split the audio file into chunks
        chunk_files = self._split_audio_into_chunks(audio_file_path, chunks_dir, chunk_duration_seconds)
        if not chunk_files:
            return {"success": False, "error": "Failed to split audio into chunks"}
        
        # Transcribe each chunk with improved memory management
        transcripts = []
        
        for i, chunk_file in enumerate(chunk_files):
            logger.info(f"Transcribing chunk {i+1}/{len(chunk_files)}: {chunk_file}")
            
            # Force garbage collection before starting a new chunk
            import gc
            logger.info("Forcing garbage collection before starting new chunk")
            for _ in range(3):
                gc.collect()
            
            # Check memory usage before transcribing
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            memory_mb = memory_info.rss / (1024 * 1024)
            logger.info(f"Memory usage before chunk {i+1}: {memory_mb:.2f} MB ({memory_percent:.2f}%)")
            
            # If memory usage is high, wait a bit and force cleanup again
            if memory_percent > 70:
                logger.warning(f"High memory usage detected ({memory_percent:.2f}%). Waiting for cleanup...")
                time.sleep(5)  # Wait for 5 seconds
                for _ in range(5):  # More aggressive cleanup
                    gc.collect()
            
            # Transcribe the chunk with enhanced script
            result = self._transcribe_audio_file(chunk_file, timeout_seconds)
            
            if not result["success"]:
                logger.error(f"Failed to transcribe chunk {i+1}/{len(chunk_files)}: {result.get('error', 'Unknown error')}")
                continue
            
            # Extract transcript data
            if "output" in result and isinstance(result["output"], dict):
                transcript_data = result["output"]
                transcripts.append({
                    "chunk_index": i,
                    "chunk_file": chunk_file,
                    "transcript_file": transcript_data.get("output_file", ""),
                    "data": transcript_data
                })
            else:
                logger.error(f"Invalid transcript data format for chunk {i+1}/{len(chunk_files)}")
            
            # Force cleanup after processing each chunk
            logger.info("Forcing cleanup after chunk processing")
            for _ in range(3):
                gc.collect()
            
            # Add a small delay between chunks to allow system to stabilize
            time.sleep(2)
        
        # Check if we have any transcripts
        if not transcripts:
            return {"success": False, "error": "No chunks were successfully transcribed"}
        
        # Combine the transcripts
        combined_transcript = self._combine_chunked_transcripts(transcripts)
        
        # Final cleanup
        logger.info("Final cleanup after all chunks processed")
        for _ in range(5):
            gc.collect()
        
        return {
            "success": True,
            "output": combined_transcript
        }
    
    def _split_audio_into_chunks(self, audio_file_path: str, chunks_dir: str, chunk_duration_seconds: int = 300) -> List[str]:
        """Split an audio file into chunks of specified duration."""
        try:
            # Get audio file information
            audio_info = AudioSegment.from_file(audio_file_path)
            total_duration_ms = len(audio_info)
            chunk_duration_ms = chunk_duration_seconds * 1000
            
            # Calculate number of chunks
            num_chunks = math.ceil(total_duration_ms / chunk_duration_ms)
            logger.info(f"Splitting audio file into {num_chunks} chunks of {chunk_duration_seconds} seconds each")
            
            chunk_files = []
            
            for i in range(num_chunks):
                # Calculate chunk start and end times
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, total_duration_ms)
                
                # Extract chunk
                chunk = audio_info[start_ms:end_ms]
                
                # Generate chunk filename
                chunk_filename = os.path.join(
                    chunks_dir, 
                    f"chunk_{i+1:03d}_{start_ms//1000:06d}_{end_ms//1000:06d}.wav"
                )
                
                # Export chunk
                chunk.export(chunk_filename, format="wav")
                chunk_files.append(chunk_filename)
                
                logger.info(f"Created chunk {i+1}/{num_chunks}: {chunk_filename} ({(end_ms-start_ms)/1000:.2f} seconds)")
                
                # Clear memory after each chunk export
                del chunk
                gc.collect()
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"Error splitting audio into chunks: {str(e)}")
            return []
    
    def _combine_chunked_transcripts(self, transcripts: List[Dict]) -> Dict:
        """Combine transcripts from multiple chunks into a single result."""
        # Sort transcripts by chunk index
        transcripts.sort(key=lambda x: x["chunk_index"])
        
        combined_segments = []
        combined_text = ""
        transcript_files = []
        
        # Track the cumulative time offset for adjusting timestamps
        time_offset = 0
        
        for transcript in transcripts:
            chunk_data = transcript.get("data", {})
            chunk_segments = chunk_data.get("segments", [])
            
            # Add transcript file to the list if available
            if transcript.get("transcript_file"):
                transcript_files.append(transcript["transcript_file"])
            
            # Adjust timestamps and add segments
            for segment in chunk_segments:
                # Create a copy of the segment to avoid modifying the original
                adjusted_segment = segment.copy()
                
                # Adjust timestamps
                if "start" in adjusted_segment:
                    adjusted_segment["start"] += time_offset
                if "end" in adjusted_segment:
                    adjusted_segment["end"] += time_offset
                
                combined_segments.append(adjusted_segment)
            
            # Update time offset for the next chunk
            # Use the last segment's end time if available, otherwise estimate from chunk duration
            if chunk_segments and "end" in chunk_segments[-1]:
                chunk_duration = chunk_segments[-1]["end"]
            else:
                # Estimate from audio file duration if available
                audio_file = transcript.get("chunk_file", "")
                if audio_file and os.path.exists(audio_file):
                    try:
                        audio_info = AudioSegment.from_file(audio_file)
                        chunk_duration = len(audio_info) / 1000  # Convert ms to seconds
                    except Exception:
                        # Default to 5 minutes if we can't determine
                        chunk_duration = 300
                else:
                    # Default to 5 minutes if we can't determine
                    chunk_duration = 300
            
            time_offset += chunk_duration
            
            # Append text
            if "text" in chunk_data:
                if combined_text:
                    combined_text += " "
                combined_text += chunk_data["text"]
        
        return {
            "segments": combined_segments,
            "text": combined_text,
            "transcript_files": transcript_files
        }
    
    def identify_speakers_in_audio(self, audio_path: str, output_file: Optional[str] = None, model_size: str = "tiny") -> Dict:
        """
        Identify speakers in an audio file using voice recognition and diarization.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output with speaker identification
            model_size: Size of the model to use (tiny, base, small, medium, large)
            
        Returns:
            Dict with identification results
        """
        logger.info(f"Identifying speakers in audio: {audio_path} with model size: {model_size}")
        
        # Prepare the command
        script_path = self.scripts_dir / "speaker_diarization.py"
        
        # Check if the script exists
        if not os.path.exists(script_path):
            error_msg = f"Speaker diarization script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "results_file": None
            }
        
        # Build the command
        cmd = [
            "python",
            str(script_path),
            audio_path,
            "--model", model_size
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"Speaker identification failed: {stderr}")
                return {
                    "success": False,
                    "error": stderr,
                    "output_file": None,
                    "results_file": None
                }
            
            # Parse the output to get the output file path and results file path
            output_path = None
            results_path = None
            
            for line in stdout.splitlines():
                if "Results saved to:" in line:
                    results_path = line.split(":", 1)[1].strip()
                    logger.info(f"Found results path: {results_path}")
                elif "Processed audio saved to:" in line:
                    output_path = line.split(":", 1)[1].strip()
                    logger.info(f"Found output path: {output_path}")
            
            # Load the results file if it exists
            results = {}
            if results_path and os.path.exists(results_path):
                try:
                    with open(results_path, 'r') as f:
                        results = json.load(f)
                    logger.info(f"Loaded diarization results: {len(results.get('segments', []))} segments, {len(results.get('speakers', {}))} speakers")
                    
                    # Check if we have any speakers
                    if 'speakers' in results and len(results['speakers']) == 0:
                        logger.warning("No speakers detected in the audio")
                except Exception as e:
                    logger.error(f"Error loading results file: {str(e)}")
            else:
                logger.warning(f"Results file not found or path is None: {results_path}")
            
            # Enhance the results with additional information
            enhanced_results = results.copy() if results else {}
            
            # Add summary information if not already present
            if "summary" not in enhanced_results:
                total_speakers = len(enhanced_results.get("speakers", {}))
                total_segments = len(enhanced_results.get("segments", []))
                total_duration = enhanced_results.get("processing_info", {}).get("total_duration", 0)
                
                enhanced_results["summary"] = {
                    "total_speakers": total_speakers,
                    "total_segments": total_segments,
                    "total_duration": total_duration,
                    "speakers_identified": any(s.get("matched", False) for s in enhanced_results.get("speakers", {}).values()),
                    "processed_at": datetime.now().isoformat()
                }
            
            return {
                "success": True,
                "output_file": output_path,
                "results_file": results_path,
                "results": make_json_serializable(enhanced_results),
                "message": "Speaker identification completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in speaker identification: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def combine_transcription_with_speakers(self, transcription_path: Optional[str], speaker_results_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Combine transcription data with speaker identification results.
        
        Args:
            transcription_path: Path to the transcription file (can be None)
            speaker_results_path: Path to the speaker identification results
            output_file: Optional path to save the combined output
            
        Returns:
            Dict with combined results
        """
        logger.info(f"Combining transcription with speaker identification: {transcription_path} + {speaker_results_path}")
        
        # Initialize transcription with empty structure
        transcription = {
            "text": "",
            "segments": []
        }
        
        # Load the transcription if path is provided
        if transcription_path:
            try:
                with open(transcription_path, 'r') as f:
                    try:
                        # First try to load as JSON
                        transcription = json.load(f)
                    except json.JSONDecodeError:
                        # If that fails, try to handle as text format
                        f.seek(0)  # Reset file pointer to beginning
                        text_content = f.read()
                        
                        # Create a simple JSON structure from the text
                        transcription = {
                            "text": text_content,
                            "segments": [{
                                "start": 0,
                                "end": 0,  # We don't have timing info in plain text
                                "text": text_content
                            }]
                        }
                        logger.info("Loaded transcription as plain text format")
            except Exception as e:
                logger.error(f"Error loading transcription: {str(e)}")
                # Continue with empty transcription instead of failing
                logger.warning("Continuing with empty transcription structure")
        else:
            logger.warning("No transcription path provided, using empty transcription structure")
            
        # Load the speaker identification results if provided
        speaker_results = {"segments": []}
        if speaker_results_path:
            try:
                with open(speaker_results_path, 'r') as f:
                    speaker_results = json.load(f)
            except Exception as e:
                logger.error(f"Error loading speaker identification results: {str(e)}")
                # Continue with empty speaker results instead of failing
                logger.warning("Continuing with empty speaker results")
        else:
            logger.warning("No speaker results path provided, using empty speaker segments")
        
        # Combine the results
        try:
            # Create a mapping of time ranges to speakers
            speaker_segments = speaker_results.get("segments", [])
            time_to_speaker = {}
            
            for segment in speaker_segments:
                start_time = segment.get("start_time", 0)
                end_time = segment.get("end_time", 0)
                speaker = segment.get("speaker", "")
                speaker_name = segment.get("speaker_name", speaker)
                
                # Add to the mapping
                time_to_speaker[(start_time, end_time)] = {
                    "speaker": speaker,
                    "name": speaker_name
                }
            
            # Add speaker information to each segment in the transcription
            segments = transcription.get("segments", [])
            
            for segment in segments:
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                
                # Find the speaker for this segment
                speaker_found = False
                
                for (speaker_start, speaker_end), speaker_info in time_to_speaker.items():
                    # Check if there's an overlap
                    if max(start, speaker_start) <= min(end, speaker_end):
                        segment["speaker"] = speaker_info["speaker"]
                        segment["speaker_name"] = speaker_info["name"]
                        speaker_found = True
                        break
                
                if not speaker_found:
                    segment["speaker"] = "unknown"
                    segment["speaker_name"] = "Unknown"
            
            # Create the combined results
            combined_results = {
                "text": transcription.get("text", ""),
                "segments": segments,
                "speakers": speaker_results.get("speakers", {}),
                "language": transcription.get("language", "en"),
                "combined_at": datetime.now().isoformat()
            }
            
            # Save to output file if provided
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(combined_results, f, indent=2, default=str)
                logger.info(f"Combined results saved to: {output_file}")
            
            return {
                "success": True,
                "combined_results": combined_results,
                "output_file": output_file
            }
            
        except Exception as e:
            logger.error(f"Error combining transcription with speaker identification: {str(e)}")
            return {
                "success": False,
                "error": f"Error combining results: {str(e)}"
            }
    
    def combine_recognition_results(self, audio_path: str, video_path: str, transcription_path: Optional[str] = None, output_file: Optional[str] = None) -> Dict:
        """
        Combine audio-based speaker diarization with video-based facial recognition.
        
        Args:
            audio_path: Path to the audio file
            video_path: Path to the video file
            transcription_path: Optional path to the transcription file
            output_file: Optional path to save the combined output
            
        Returns:
            Dict with combined recognition results
        """
        logger.info(f"Combining audio and video recognition for: {audio_path} and {video_path}")
        
        try:
            # Step 1: Get audio-based speaker identification
            audio_results = self.identify_speakers_in_audio(audio_path)
            
            if not audio_results.get("success", False):
                logger.error(f"Failed to identify speakers in audio: {audio_results.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to identify speakers in audio: {audio_results.get('error', 'Unknown error')}"
                }
            
            # Step 2: Get video-based face recognition
            try:
                from backend.services.recognition.facial_recognition import FacialRecognitionService
                facial_service = FacialRecognitionService()
                video_results = facial_service.identify_speakers_in_video(video_path)
                
                if not video_results.get("success", False):
                    logger.warning(f"Failed to identify faces in video: {video_results.get('error', 'Unknown error')}")
                    logger.warning("Proceeding with audio-only results")
                    video_results = {"speakers": {}, "frames": []}
                
            except Exception as e:
                logger.warning(f"Error in facial recognition: {str(e)}")
                logger.warning("Proceeding with audio-only results")
                video_results = {"speakers": {}, "frames": []}
            
            # Step 3: Align and combine results
            combined_results = self._align_recognition_results(audio_results.get("results", {}), video_results)
            
            # Step 4: If transcription exists, add speaker information
            if transcription_path and os.path.exists(transcription_path):
                combined_transcription = self.combine_transcription_with_speakers(
                    transcription_path, 
                    audio_results.get("results_file", ""),
                    output_file=output_file
                )
                
                if combined_transcription.get("success", False):
                    combined_results["transcription"] = combined_transcription.get("combined_results", {})
                    logger.info("Successfully added transcription to combined results")
            
            # Save combined results if output file is provided
            if output_file:
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                with open(output_file, 'w') as f:
                    json.dump(combined_results, f, indent=2, default=str)
                logger.info(f"Combined recognition results saved to: {output_file}")
            
            return {
                "success": True,
                "combined_results": combined_results,
                "output_file": output_file
            }
            
        except Exception as e:
            logger.error(f"Error combining recognition results: {str(e)}")
            return {
                "success": False,
                "error": f"Error combining recognition results: {str(e)}"
            }
    
    def _align_recognition_results(self, audio_results: Dict, video_results: Dict) -> Dict:
        """
        Align and combine audio-based speaker diarization with video-based facial recognition.
        
        Args:
            audio_results: Results from audio-based speaker diarization
            video_results: Results from video-based facial recognition
            
        Returns:
            Dict with aligned and combined results
        """
        try:
            # Extract speakers from both results
            audio_speakers = audio_results.get("speakers", {})
            video_speakers = video_results.get("speakers", {})
            
            # Create a mapping of speaker IDs to names from video recognition
            video_id_to_name = {}
            for speaker_id, speaker_info in video_speakers.items():
                if speaker_info.get("name", "") != "Unknown":
                    video_id_to_name[speaker_id] = speaker_info.get("name")
            
            # Update audio speakers with video recognition information
            for speaker_id, speaker_info in audio_speakers.items():
                # If the speaker is already matched, skip
                if speaker_info.get("matched", False) and speaker_info.get("confidence", 0) > 0.7:
                    continue
                
                # Try to match with video speakers based on name
                speaker_name = speaker_info.get("name", "")
                for video_id, video_name in video_id_to_name.items():
                    if speaker_name == video_name:
                        # Update with video recognition info
                        speaker_info["matched_with_video"] = True
                        speaker_info["video_speaker_id"] = video_id
                        speaker_info["confidence"] = max(speaker_info.get("confidence", 0), 0.8)  # Boost confidence
                        break
            
            # Update audio segments with improved speaker information
            audio_segments = audio_results.get("segments", [])
            for segment in audio_segments:
                speaker_id = segment.get("speaker", "")
                if speaker_id in audio_speakers:
                    segment["speaker_name"] = audio_speakers[speaker_id].get("name", speaker_id)
                    segment["speaker_confidence"] = audio_speakers[speaker_id].get("confidence", 0.0)
                    segment["matched_with_video"] = audio_speakers[speaker_id].get("matched_with_video", False)
            
            # Create combined results
            combined_results = {
                "speakers": audio_speakers,
                "segments": audio_segments,
                "video_speakers": video_speakers,
                "video_frames": video_results.get("frames", []),
                "processing_info": {
                    "combined_at": datetime.now().isoformat(),
                    "audio_processing": audio_results.get("processing_info", {}),
                    "video_processing": video_results.get("processing_info", {})
                }
            }
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error aligning recognition results: {str(e)}")
            # Return a basic structure with the original results
            return {
                "audio_results": audio_results,
                "video_results": video_results,
                "error": str(e)
            }
