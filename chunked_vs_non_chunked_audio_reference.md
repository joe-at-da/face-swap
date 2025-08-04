# Chunked vs Non-Chunked Audio Processing Reference

This document provides a comprehensive reference of all code paths where the logic diverges between chunked and non-chunked audio processing in the Parliament Clips system.

## Table of Contents
1. [Initial Decision Point](#1-initial-decision-point)
2. [Configuration Settings](#2-configuration-settings)
3. [Chunked Audio Processing Path](#3-chunked-audio-processing-path)
4. [Non-Chunked Audio Processing Path](#4-non-chunked-audio-processing-path)
5. [Diarization Segment Processing](#5-diarization-segment-processing)
6. [Transcript Integration](#6-transcript-integration)
7. [Speech Group Assignment](#7-speech-group-assignment)
8. [Multimodal Integration](#8-multimodal-integration)

## 1. Initial Decision Point

The initial decision on whether to use chunked or non-chunked processing happens in the `transcribe_audio` method of `VoiceRecognitionService`.

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Key decision logic:** Lines 125-148

```python
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
```

## 2. Configuration Settings

**File:** [recognition_config.py](/Users/joebradley/Veedoo/Development/the-mp/backend/core/recognition_config.py)

**Key configuration settings:** Lines 34-53

```python
class AudioConfig:
    """Audio processing configuration parameters."""
    
    # Default chunk size in seconds
    # - Production: 1200 seconds (20 minutes)
    # - Debug: 60 seconds (1 minute)
    # - Test: 30 seconds (for rapid testing of chunking behavior)
    DEFAULT_CHUNK_SIZE = 30 if TEST_MODE else (60 if DEBUG_MODE else 1200)
    
    # Default audio duration fallback when unable to determine actual duration
    # - Production: 3600 seconds (1 hour)
    # - Debug: 30 seconds
    # - Test: 30 seconds (for rapid testing of chunking behavior)
    DEFAULT_AUDIO_DURATION = 30 if TEST_MODE or DEBUG_MODE else 90000
    
    # Maximum duration for non-chunked transcription in seconds
    # - Production: 600 seconds (10 minutes)
    # - Debug: 30 seconds
    # - Test: 15 seconds (to force chunking for most test files)
    MAX_NON_CHUNKED_DURATION = 15 if TEST_MODE else (30 if DEBUG_MODE else 9000)
```

## 3. Chunked Audio Processing Path

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Method:** `_transcribe_long_audio` (starts at line 150)

```python
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
```

**Chunked Transcription Fallback:** Lines 600-680

```python
# If no diarization data in main result, check each chunk for diarization data
if not diarization_segments and "chunks" in chunked_result:
    all_diarization_segments = []
    logger.info("Checking individual chunks for diarization data")
    for i, chunk in enumerate(chunked_result["chunks"]):
        if "diarization" in chunk and chunk["diarization"].get("segments"):
            chunk_diarization = chunk["diarization"].get("segments", [])
            logger.info(f"Found {len(chunk_diarization)} diarization segments in chunk {i}")
            
            # Adjust timestamps to be relative to the entire audio, not just the chunk
            chunk_start = chunk.get("start", 0)
            for segment in chunk_diarization:
                # Ensure start_time and end_time fields exist
                if "start_time" not in segment and "start" in segment:
                    segment["start_time"] = segment["start"]
                if "end_time" not in segment and "end" in segment:
                    segment["end_time"] = segment["end"]
                
                # Adjust timestamps to be relative to the entire audio
```

## 4. Non-Chunked Audio Processing Path

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Method:** `_transcribe_standard_audio` (starts at line 511)

```python
def _transcribe_standard_audio(self, audio_path: str, output_file: Optional[str] = None) -> Dict:
    """
    Transcribe a standard-length audio file (non-chunked approach).
    
    Args:
        audio_path: Path to the audio file
        output_file: Optional path to save the output transcript
        
    Returns:
        Dict with transcription results
    """
    logger.info(f"Using standard (non-chunked) transcription for audio file: {audio_path}")
```

## 5. Diarization Segment Processing

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Method:** `_process_diarization_segments` (starts at line 297)

```python
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
```

**Method:** `_convert_chunked_transcript_to_segments` (starts at line 552)

```python
def _convert_chunked_transcript_to_segments(self, chunked_result: Dict, diarization_file: Optional[str] = None) -> List[Dict]:
    """
    Convert chunked transcription results to diarization segments.
    
    Args:
        chunked_result: Results from chunked transcription
        diarization_file: Optional path to a separate diarization file
        
    Returns:
        List of diarization segments
    """
    logger.info("Converting chunked transcript to diarization segments")
    
    # First, try to get diarization segments from the result directly
    diarization_segments = []
```

## 6. Transcript Integration

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Chunked Transcript Integration:** Lines 673-710

```python
logger.info("Final fallback: extracting speaker segments from chunks")
all_speaker_segments = []  # Initialize list to collect all speaker segments across chunks
chunk_results = chunked_result.get("chunks", [])

if not chunk_results:
    # If no chunks are available, create a single segment from the transcript
    transcript = chunked_result.get("transcript", "")
    if transcript:
        logger.info("Creating a single segment from the full transcript")
        segment = {
            "speaker": "SPEAKER_0",
            "start_time": 0.0,
            "end_time": duration or 60.0,  # Use provided duration or default
            "transcript": transcript
        }
        all_speaker_segments.append(segment)
```

**Non-Chunked Transcript Integration:** Lines 520-540

```python
# Process diarization segments to ensure consistent speech group IDs
# This is critical to ensure one clip per speaker turn, not per chunk
processed_segments = self._process_diarization_segments(diarization_segments)

# Add transcript text to each segment
for segment in processed_segments:
    segment_start = segment.get("start_time", 0)
    segment_end = segment.get("end_time", 0)
    speaker = segment.get("speaker", "UNKNOWN")
    
    # Extract the relevant part of the transcript for this segment
    segment_transcript = ""
    for line in transcript_lines:
        line_start, line_end, line_text = self._parse_transcript_line(line)
        
        # Check if this line overlaps with the segment
        if (line_start <= segment_end and line_end >= segment_start):
            segment_transcript += line_text + " "
```

## 7. Speech Group Assignment

**File:** [voice_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/voice_recognition.py)

**Speech Group Logic:** Lines 320-380

```python
# Initialize variables for tracking speech groups
speech_group_counter = 0
current_speaker = None
last_end_time = 0
processed_segments = []

# Process each segment
for segment in sorted_segments:
    # Extract segment data
    speaker = segment.get('speaker', 'UNKNOWN')
    start_time = segment.get('start_time', segment.get('start', 0))
    end_time = segment.get('end_time', segment.get('end', 0))
    
    # Ensure we have numeric timestamps
    try:
        start_time = float(start_time)
        end_time = float(end_time)
    except (ValueError, TypeError):
        logger.error(f"Invalid timestamps in segment: {segment}")
        continue
    
    # Create a new speech group if:
    # 1. This is the first segment
    # 2. The speaker has changed
    # 3. There's a significant gap between this segment and the previous one
    create_new_group = False
    
    if current_speaker is None:
        # First segment
        create_new_group = True
    elif current_speaker != speaker:
        # Speaker has changed
        create_new_group = True
    elif start_time - last_end_time > AudioConfig.MAX_SILENCE_DURATION:
        # Significant gap between segments
        create_new_group = True
```

## 8. Multimodal Integration

**File:** [multimodal_recognition.py](/Users/joebradley/Veedoo/Development/the-mp/backend/services/recognition/multimodal_recognition.py)

**Integration with Diarization Segments:** 

This file contains the integration logic that combines audio and video recognition results, which can be affected by whether the audio was processed using chunked or non-chunked approaches.

---

This reference document provides clickable links to the key locations in the codebase where the logic diverges between chunked and non-chunked audio processing. You can use these references to examine the specific implementation details and understand how the different processing paths work.
