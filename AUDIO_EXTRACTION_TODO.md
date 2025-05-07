# Audio Extraction Issues - TODO

## Problem Summary
The audio extraction process is not correctly respecting the specified duration and time markers, while video extraction works correctly. This leads to audio files being extracted from the beginning of the stream instead of the specified time marker, and for longer than the specified duration.

## Root Causes Identified
1. **Time Marker Extraction Failure**:
   - Log evidence: `No valid time marker found after all attempts, starting from beginning of stream`
   - The audio extraction code is failing to extract time markers from metadata

2. **Metadata Access Issues**:
   - Log evidence: `Found SQLAlchemy MetaData object - creating fresh metadata dictionary`
   - The code is encountering SQLAlchemy MetaData objects instead of the actual metadata containing time markers

3. **Directory Permission Issues**:
   - Log evidence: `Test file operation failed: Failed to create test file in /app/data/temp/audio_extracts`
   - Permission problems when trying to create the audio output directory

4. **Missing Log Files**:
   - Log evidence: `FFmpeg log file does not exist: /app/data/temp/ffmpeg_log_247.txt`
   - FFmpeg process logs aren't being created in the expected location

## Required Fixes

### 1. Fix Metadata Extraction
- Improve handling of SQLAlchemy MetaData objects to extract the actual metadata
- Add more robust fallback mechanisms for time marker extraction
- Ensure the code can handle different metadata formats consistently

### 2. Fix FFmpeg Command Construction
- Verify that both `-ss` (start position) and `-t` (duration) parameters are included in the FFmpeg command
- Ensure parameters are in the correct order for HLS streams
- Add validation to confirm the command includes all required parameters before execution

### 3. Fix Directory Permission Issues
- Simplify the directory creation approach to be more reliable
- Use consistent paths for temporary files
- Ensure proper error handling when directory operations fail

### 4. Improve Error Handling
- Add better error handling around FFmpeg log file creation and reading
- Implement more graceful fallbacks when parts of the process fail
- Improve logging to provide clearer information about what's happening

## Files to Modify
- `/backend/services/parliament_tv.py`: Fix the `extract_audio` method
- Focus on the time marker extraction logic around line 1580-1750
- Fix the FFmpeg command construction around line 1750-1800

## Testing Plan
1. Test with capture ID 247 which has a known time marker of 44610 seconds (12:23:30)
2. Verify that both video and audio respect the same time marker and duration
3. Test with different duration values to ensure they're applied correctly
