# Audio Processing Pipeline

*Created: August 5, 2025 by Joe Bradley (joe@veedoo.io)*

## Overview

This document describes the audio processing pipeline used in the Parliament TV integration system, explaining the current implementation, its importance for the overall system, and areas for future optimization.

## Audio Processing Flow

The current audio pipeline follows these steps:

1. **HLS Audio Stream Download**:
   - Downloads audio from Parliament TV HLS stream
   - Uses FFmpeg with protocol whitelist for HTTP/HTTPS streaming
   - Converts to MP3 using libmp3lame encoder at quality level 2
   - Command structure:
     ```
     ffmpeg -y -protocol_whitelist file,http,https,tcp,tls,crypto -http_persistent 1 
            -allowed_extensions ALL -i [AUDIO_URL] -c:a libmp3lame -q:a 2 -vn 
            -hide_banner -progress [LOG_FILE] [OUTPUT_PATH]
     ```

2. **Audio Extraction for Segments**:
   - For each segment, extracts a portion of the audio file
   - Uses FFmpeg seeking to extract specific time ranges
   - Maintains the same encoding quality
   - Used for processing videos in manageable chunks (typically 30 minutes)

3. **Combined AV Processing**:
   - Combines the extracted audio with the corresponding video segment
   - Ensures synchronization between audio and video
   - Creates the final media files used for transcription and recognition

## Performance Considerations

### Current Bottlenecks

The audio processing can be time-consuming due to several factors:

1. **Network Bandwidth**:
   - Downloading HLS streams is dependent on network conditions
   - Parliament TV streams can be large and high-quality

2. **Encoding Process**:
   - Using libmp3lame with quality level 2 prioritizes audio quality over speed
   - Higher quality settings are more CPU-intensive

3. **Sequential Processing**:
   - While video and audio downloads happen in parallel, segment processing is sequential
   - No multi-threading for audio encoding tasks

### Importance of Audio Quality

The audio quality directly impacts several critical aspects of the system:

1. **Transcription Accuracy**: 
   - Better audio quality leads to more accurate transcription
   - Accurate transcription is essential for correctly attributing speech to MPs

2. **Speaker Turn Detection**:
   - The system relies on audio cues to detect when one MP stops speaking and another begins
   - Clean audio improves the accuracy of speaker boundaries

3. **Speech Group ID Assignment**:
   - Speech groups are created based on audio segments that appear to be from the same speaker
   - Better audio quality improves the consistency of these groupings

4. **Face-Voice Alignment**:
   - Matching the correct face to the correct speech segment requires precise audio timing
   - Audio quality affects the precision of this alignment

## Current Challenges

Currently, only about 25% of the processed data has good alignment between:
- MP speaking (identified correctly)
- What they say (accurate transcription)
- Their face (correct recognition)
- Speech group ID assignment (proper grouping)

This is likely due to:
- Imperfect speaker turn detection
- Transcription errors in noisy or overlapping speech
- Timing misalignments between audio and video
- Variations in audio quality from the source

## Future Optimizations

TODO: Profile and optimize the audio processing pipeline:

1. **Performance Improvements**:
   - Investigate faster encoders while maintaining sufficient quality for transcription
   - Implement parallel processing for audio segments
   - Optimize FFmpeg parameters for better performance
   - Consider pre-filtering audio to remove noise before encoding

2. **Quality Improvements**:
   - Benchmark different quality settings vs. transcription accuracy
   - Implement adaptive quality based on audio characteristics
   - Add noise reduction for parliamentary background noise

3. **Pipeline Improvements**:
   - Investigate improved speaker turn detection algorithms
   - Enhance alignment between speech groups, transcription, and facial recognition
   - Implement more sophisticated diarization techniques

4. **Monitoring and Metrics**:
   - Add instrumentation to measure processing time at each stage
   - Track quality metrics to identify problematic audio sources
   - Implement automatic quality assessment

## Conclusion

The audio processing pipeline is a critical component of the Parliament TV integration system. While the current implementation prioritizes quality for accurate transcription and speaker recognition, there are opportunities for optimization to improve both performance and accuracy. Future work should focus on finding the optimal balance between processing speed and audio quality to enhance the overall system effectiveness.
