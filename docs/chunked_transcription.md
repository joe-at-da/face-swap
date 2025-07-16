# Chunked Transcription Documentation

## Overview

The Chunked Transcription feature enables the system to process long audio files (4+ hours) by breaking them into smaller, manageable chunks. This approach solves memory constraints and improves transcription accuracy for extended Parliament TV sessions.

## Features

- **Automatic Audio Chunking**: Splits long audio files into smaller segments based on configurable thresholds
- **Parallel Processing**: Processes audio chunks in parallel for faster transcription
- **Timestamp Preservation**: Maintains accurate timestamps across chunks
- **Seamless Integration**: Works with the existing transcription and multimodal recognition systems
- **JSON Format Compatibility**: Produces output compatible with Whisper format for downstream processing
- **Speaker Diarization**: Integrates with speaker identification for accurate speaker attribution

## Configuration

The chunked transcription system is controlled by the following environment variables:

- `LONG_AUDIO_THRESHOLD_SECONDS`: Audio duration threshold that triggers chunking (default: 3600 seconds / 1 hour)
- `AUDIO_CHUNK_SIZE_SECONDS`: Size of each audio chunk in seconds (default: 600 seconds / 10 minutes)
- `INCLUDE_CHUNK_MARKERS`: Whether to include chunk markers in the transcription output (default: true)

## Technical Implementation

### Chunking Process

1. **Audio Extraction**: The system extracts audio from the video source using the provided audio URL
2. **Length Detection**: If the audio exceeds the `LONG_AUDIO_THRESHOLD_SECONDS`, chunking is activated
3. **Chunk Creation**: Audio is split into chunks of `AUDIO_CHUNK_SIZE_SECONDS` using ffmpeg
4. **Parallel Transcription**: Each chunk is transcribed independently using Whisper
5. **Result Combination**: Chunk results are combined with proper timestamp adjustments
6. **JSON Formatting**: The combined result is formatted as a JSON object compatible with Whisper output format
7. **Database Storage**: The formatted transcription is stored in the database for the capture session

### Output Format

The chunked transcription system produces output in the following JSON format, which is compatible with the Whisper model output:

```json
{
  "text": "Full transcription text...",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 8.0,
      "text": "Segment text...",
      "tokens": [],
      "temperature": 0.0,
      "avg_logprob": -0.5,
      "compression_ratio": 1.0,
      "no_speech_prob": 0.1
    },
    // Additional segments...
  ],
  "language": "en"
}
```

### Integration with Multimodal Recognition

The chunked transcription system integrates with the multimodal recognition system, which:

1. Processes the transcription segments to identify speakers
2. Correlates speakers with facial recognition results
3. Creates speaker segments in the database
4. Exports the results to Supabase for frontend access

## Monitoring and Troubleshooting

### Monitoring Scripts

The following scripts are available for monitoring and troubleshooting chunked transcription:

- `monitor_end_to_end_processing_v2.sh`: Monitors the entire process from audio extraction to multimodal recognition
- `monitor_transcription.sh`: Monitors the transcription process specifically
- `extract_transcription_from_logs.py`: Extracts transcription content from Docker logs if needed

### Common Issues and Solutions

1. **Empty Transcription Results**:
   - Check if the audio extraction was successful
   - Verify that the audio URL is correct and accessible
   - Ensure the chunking process completed successfully

2. **Multimodal Recognition Failures**:
   - Verify that the transcription format matches the expected Whisper format
   - Check for empty segments in the transcription
   - Run the `fix_whisper_format.py` script to correct the format

3. **Missing Speaker Segments**:
   - Ensure the multimodal recognition system is properly processing the transcription
   - Check for errors in the speaker diarization process
   - Run the `update_multimodal_recognition.py` script to patch the system

## Recovery Tools

The following tools are available for recovering from transcription issues:

- `fix_whisper_format.py`: Fixes the transcription format to match the Whisper output format
- `update_multimodal_recognition.py`: Updates the multimodal recognition system to handle chunked transcription
- `direct_fix_transcription.py`: Directly updates the database with properly formatted transcription data

## Best Practices

1. **Testing New Integrations**:
   - Use the `test_chunked_transcription.py` script to test chunked transcription with different parameters
   - Verify that the output format is compatible with downstream systems

2. **Monitoring Long Transcriptions**:
   - Use the monitoring scripts to track the progress of long transcriptions
   - Check for errors in the Docker logs

3. **Format Validation**:
   - Always validate that the transcription format matches the expected Whisper format
   - Ensure that segments contain all required fields (id, seek, start, end, text)

## Future Enhancements

Planned enhancements for the chunked transcription feature include:

1. **Improved Chunk Boundary Detection**: Use silence detection to create more natural chunk boundaries
2. **Enhanced Error Recovery**: Automatically retry failed chunks
3. **Progress Tracking**: Provide real-time progress updates for each chunk
4. **Adaptive Chunk Sizing**: Dynamically adjust chunk size based on audio content
5. **Format Validation**: Add automatic validation of transcription format before multimodal processing
