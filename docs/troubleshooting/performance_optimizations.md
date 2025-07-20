# Parliament TV Pipeline Performance Optimizations

This document outlines performance optimizations for the Parliament TV processing pipeline based on log analysis and code review.

## Identified Bottlenecks

1. **Excessive Polling for Capture Completion**
   - Current implementation polls every few seconds to check if captures are complete
   - Creates unnecessary CPU load and database queries

2. **Redundant System Metrics Collection**
   - Frequent metrics collection (~every 15 seconds) adds overhead
   - Docker metrics fallback to process stats in container environments

3. **Sequential Processing**
   - Video/audio extraction must complete before recognition tasks begin
   - Recognition tasks (transcription, diarization, face detection) run sequentially

4. **Inefficient Diarization File Searching**
   - Current implementation checks many possible paths
   - No caching of previously found paths

5. **Speech Group ID Updates**
   - Updating speech group IDs requires multiple database operations
   - No batch processing for updates

## Recommended Optimizations

### 1. Event-Based Capture Completion
Replace polling with event-based notifications:

```python
# Instead of polling:
def check_active_captures():
    # Polls database every few seconds
    
# Use event-based approach:
def register_capture_completion_callback(capture_id, callback):
    # Register callback to be triggered when capture completes
```

### 2. Optimize Metrics Collection
- Reduce frequency of metrics collection to once per minute
- Only collect metrics that are actively being used for monitoring

### 3. Parallel Processing
- Implement a task queue system (e.g., Celery) to parallelize recognition tasks
- Start transcription and face recognition as soon as partial media is available:

```python
def process_parliament_video(video_url):
    # Start extraction
    extraction_task = start_extraction(video_url)
    
    # Start recognition tasks as soon as media starts becoming available
    # Don't wait for full extraction to complete
    transcription_task = start_transcription_when_ready(extraction_task)
    diarization_task = start_diarization_when_ready(extraction_task)
    face_recognition_task = start_face_recognition_when_ready(extraction_task)
    
    # Wait for all tasks to complete
    wait_for_completion([transcription_task, diarization_task, face_recognition_task])
```

### 4. Optimize Diarization File Search
- Implement a caching mechanism for diarization file paths
- Prioritize search paths based on historical success rates
- Add indexing for common diarization file locations

```python
# Cache for diarization file paths
DIARIZATION_PATH_CACHE = {}

def find_diarization_file(video_path):
    video_id = extract_video_id(video_path)
    
    # Check cache first
    if video_id in DIARIZATION_PATH_CACHE:
        path = DIARIZATION_PATH_CACHE[video_id]
        if path.exists():
            return path
    
    # Prioritized search based on historical success
    for search_pattern in PRIORITIZED_SEARCH_PATTERNS:
        # Search logic
        if found:
            DIARIZATION_PATH_CACHE[video_id] = found_path
            return found_path
```

### 5. Batch Processing for Speech Group Updates
- Implement batch updates for speech group IDs
- Use database transactions to reduce overhead

```python
def update_speech_groups_batch(clips, diarization_data):
    # Process all clips in memory
    updates = []
    for clip in clips:
        # Determine speech group ID
        updates.append((clip_id, speech_group_id))
    
    # Execute as a single database transaction
    with db.transaction():
        db.executemany("UPDATE clips SET speech_group_id = ? WHERE id = ?", updates)
```

### 6. Database Optimization
- Add appropriate indexes to the SQLite database
- Consider using prepared statements for repeated queries
- Optimize query patterns for speech group updates

### 7. Caching Recognition Results
- Cache intermediate recognition results
- Implement a mechanism to reuse diarization results for clips from the same video

## Implementation Priority

1. Parallel processing of recognition tasks (highest impact)
2. Batch processing for speech group updates
3. Optimize diarization file search with caching
4. Replace polling with event-based notifications
5. Database optimization and indexing
6. Reduce metrics collection frequency

## Monitoring Impact

After implementing these optimizations, monitor:
- Total processing time for Parliament TV videos
- CPU and memory usage during processing
- Database query counts and execution times
- Time spent in each processing stage

Document performance improvements to guide future optimization efforts.
