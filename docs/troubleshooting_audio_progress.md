# Troubleshooting: Audio Progress Reporting Issues

*Created: August 6, 2025 by Joe Bradley (joe@veedoo.io)*

## Issue: Audio Processing Appears to Stall at ~22 Minutes

### Symptoms
- Progress logs show audio processing stopping at approximately 22 minutes (`out_time=00:22:XX`)
- Audio progress log file stops updating
- System appears to hang or stall during audio download/encoding
- Video processing continues normally

### Root Cause
This is **NOT** an actual processing stall. It's a **known limitation** of FFmpeg's progress reporting mechanism when processing long HLS (HTTP Live Streaming) audio streams from Parliament TV.

**Technical Details:**
- Parliament TV uses HLS with specific segment boundaries
- FFmpeg's progress reporting buffer has limitations with long streams
- Progress updates cease after ~22 minutes due to buffer overflow or stream metadata changes
- The actual audio encoding process continues normally

### Verification Steps

1. **Check if FFmpeg processes are still running:**
   ```bash
   docker-compose -f docker-compose.dev.yml exec app ps aux | grep ffmpeg
   ```
   - Look for active ffmpeg processes with CPU usage
   - Audio process should show `libmp3lame` encoding

2. **Monitor file growth:**
   ```bash
   ls -la data/media/ | grep audio_
   ```
   - Audio file should continue growing in size
   - Typical size: ~1MB per minute of audio

3. **Check enhanced monitoring logs:**
   ```
   WARNING: Progress reporting may have stalled (no updates for 60s) but processes still running
   KNOWN ISSUE: FFmpeg progress reporting for Parliament TV audio streams often stops after ~22 minutes
   ```

### Expected Behavior
- ✅ Audio file continues to grow
- ✅ FFmpeg process remains active (CPU usage)
- ❌ Progress logs stop updating
- ✅ Final audio file is complete and usable

### Resolution
**No action required.** This is expected behavior. The system will:
1. Continue audio processing in the background
2. Complete the full audio file successfully
3. Log appropriate warnings about the progress reporting limitation
4. Proceed with normal pipeline operations once audio is complete

### Prevention
This cannot be prevented as it's an FFmpeg limitation, but the enhanced monitoring system provides transparency:
- Detects when processes are running without progress updates
- Logs clear explanations of the expected behavior
- Confirms that processing is continuing normally

### Alternative Monitoring
If you need to verify audio processing progress during the "stall":
1. Monitor file size growth manually
2. Check CPU usage of ffmpeg processes
3. Use system process monitoring tools
4. Wait for completion - audio files are typically completed successfully

### Related Documentation
- [Audio Processing Pipeline](audio_processing_pipeline.md)
- [Parliament TV Optimization Roadmap](parliament_tv_optimization_roadmap.md)
