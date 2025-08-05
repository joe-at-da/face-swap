# Parliament TV Processing Optimization Roadmap

*Last Updated: August 6, 2025 - Audio processing optimization and progress reporting issue resolution*

## Overview

This document outlines a comprehensive plan to optimize the Parliament TV processing pipeline, with a focus on reducing processing time while maintaining output quality. The optimizations are divided into phases, with each phase building on the previous one.

## ✅ Completed Optimizations

### Audio Processing Optimization (Completed August 6, 2025)
- **IMPLEMENTED**: Stream copy approach for audio downloads
- **Key Improvements**:
- ✅ Direct MP3 encoding with `libmp3lame` codec
- ✅ Optimized quality settings (`-q:a 3`) for speed/quality balance
- ✅ Multi-threading support (`-threads auto`)
- ✅ Enhanced progress monitoring with stall detection
- ✅ Eliminated redundant audio downloads (single download per session)
- ✅ Identified and documented ffmpeg progress reporting limitation

**Critical Discovery**:
- The "22-minute audio stall" was a progress reporting artifact, not an actual processing issue
- FFmpeg continues processing audio normally but stops updating progress logs after ~22 minutes
- This is due to HLS stream characteristics and ffmpeg's progress buffer limitations
- Enhanced monitoring now detects and logs this expected behavior

## Phase 1: FFmpeg Optimizations (Immediate Wins)

### 1.1 Encoding Parameter Optimizations
- Replace `-preset fast` with `-preset ultrafast`
- Change video quality from `-crf 22` to `-crf 28`
- Add `-tune fastdecode` for faster decoding
- Implement in: `ParliamentTVCapture.synchronized_extract()`

### 1.2 Audio Encoding Optimizations ✅ COMPLETED
- ~~Replace MP3 encoding (`-c:a libmp3lame -q:a 2`) with AAC (`-c:a aac -b:a 128k`)~~
- **IMPLEMENTED**: Stream copy approach (`-c:a copy`) as primary method
- **IMPLEMENTED**: Optimized MP3 fallback (`-c:a libmp3lame -q:a 3 -threads auto`)
- **Status**: Audio processing speed issue resolved

### 1.3 Hardware Acceleration
- Add `-hwaccel auto` before input specification
- Optionally use hardware-specific encoders where available:
  - NVIDIA: `-c:v h264_nvenc`
  - Intel: `-c:v h264_qsv`
  - AMD: `-c:v h264_amf`
- Implement in: `ParliamentTVCapture.synchronized_extract()`

## Phase 2: Monitoring and Database Optimizations (Short-term)

### 2.1 Reduce Database Update Frequency
- Update database every 10 seconds instead of every second
- Add timestamp tracking to monitor_progress function
- Implement in: `ParliamentTVCapture.synchronized_extract()` monitor_progress function

### 2.2 Optimize Progress Monitoring
- Increase sleep interval from 1 second to 5 seconds
- Implement in: `ParliamentTVCapture.synchronized_extract()` monitor_progress function

## Phase 3: Speaker-Focused Processing (Medium-term)

### 3.1 Center Frame Face Detection
- Create new method `detect_faces_center_frame_only()` that only processes the center portion of frames
- Define configurable center region size (e.g., middle 50% of frame)
- Implement in: `FaceRecognitionService`

### 3.2 Optimize Frame Sampling Rate
- Reduce frame extraction rate to 0.5 fps (one frame every 2 seconds)
- Implement in: `MultimodalRecognitionService.extract_frames()`

### 3.3 Skip Non-Central Faces
- Modify face processing to only handle the largest face in the center frame
- Implement in: `MultimodalRecognitionService.process_video_frames()`

### 3.4 Focus Diarization on Main Speakers
- Limit speaker diarization to focus on 1-3 main speakers
- Increase clustering threshold to focus on clearer speaker differences
- Implement in: `VoiceRecognitionService.identify_speakers_in_audio()`

## Phase 4: Advanced Processing Strategies (Long-term)

### 4.1 Implement Early Stopping for Face Processing
- Stop processing frames once main speaker is confidently identified
- Set maximum frames to check per segment (e.g., 10 frames)
- Implement in: `MultimodalRecognitionService`

### 4.2 Parallel Processing
- Process audio and visual components in parallel using ThreadPoolExecutor
- Merge results after parallel processing completes
- Implement in: `MultimodalRecognitionService.process_video()`

### 4.3 Smart Caching for Speaker Identification
- Cache speaker identification results for repeated appearances
- Use embedding hash as cache key
- Implement in: `FaceRecognitionService`

### 4.4 Segment-Based Processing
- Process video in 10-minute segments
- Enable parallel processing of segments
- Implement in: `ParliamentTVCapture`

### 4.5 Adaptive Processing Based on Content
- Analyze video complexity to determine optimal processing strategy
- Use different strategies for static (parliament session) vs. dynamic content
- Implement in: `MultimodalRecognitionService`

## Phase 5: Two-Phase Processing Strategy (Future Enhancement)

### 5.1 Quick First Pass
- Implement initial low-quality, high-speed processing for immediate results
- Use ultrafast preset, higher CRF, and lower resolution

### 5.2 Optional Quality Pass
- Add background task for higher-quality processing if needed
- Store both quick and quality results with appropriate metadata

## Implementation Timeline

| Phase | Timeframe | Estimated Speed Improvement |
|-------|-----------|----------------------------|
| Phase 1 | Week 1 | 3-5x faster video processing |
| Phase 2 | Week 2 | 10-20% additional improvement |
| Phase 3 | Weeks 3-4 | 2-3x additional improvement |
| Phase 4 | Weeks 5-8 | 2-4x additional improvement |
| Phase 5 | Future | Depends on requirements |

## Monitoring and Validation

For each optimization:
1. Measure baseline processing time before implementation
2. Implement changes in development environment
3. Measure new processing time and calculate improvement
4. Validate output quality meets requirements
5. Document findings and roll out to production

## Success Metrics

- Primary: Total processing time reduction (target: 80% reduction)
- Secondary: CPU/memory usage reduction
- Quality control: Speaker identification accuracy maintained within 5% of baseline

## Conclusion

This roadmap provides a structured approach to dramatically improving the Parliament TV processing pipeline's performance. By focusing first on the most impactful changes (FFmpeg optimizations) and then progressively implementing more sophisticated optimizations, we can achieve significant speed improvements while maintaining the quality and accuracy of speaker identification.
