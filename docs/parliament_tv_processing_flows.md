# Parliament TV Processing Flows

This document provides a comprehensive overview of the Parliament TV video processing workflows, comparing the different approaches and their use cases.

## Overview

The Parliament TV system supports multiple processing workflows designed for different use cases:

1. **Sequential Processing** - For analyzing complete Parliament sessions
2. **Non-Sequential Processing** - For targeted clip capture and analysis  
3. **Debug Processing** - For testing and debugging specific segments

## Processing Flow Comparison

| Aspect | Sequential Processing | Non-Sequential Processing | Debug Processing |
|--------|----------------------|---------------------------|------------------|
| **Input** | Long Parliament TV session | Specific duration segment | Existing segment files |
| **Segmentation** | Creates 30-min segments | Single file for duration | Uses pre-existing segments |
| **Recognition** | Per-segment (efficient) ✅ | Single file (efficient) ✅ | Per-segment (efficient) ✅ |
| **Database** | Multiple segment results | Single session results | Single segment results |
| **Use Case** | Full session analysis | Targeted clip analysis | Testing & debugging |
| **API Endpoint** | `/supabase-automation/process-parliament-tv` | `/parliament-tv` | `/parliament-tv/process-segment` |

## Sequential Processing Flow

**Purpose**: Analyze complete Parliament TV sessions efficiently by breaking them into manageable segments.

### Workflow:
1. **Download**: Downloads full video and audio streams from Parliament TV
2. **Segment Creation**: Splits content into 30-minute segments (`session_1.mp4`, `session_2.mp4`, etc.)
3. **Individual Processing**: Processes each segment for metadata storage
4. **Recognition per Segment**: Runs face recognition and transcription on each 30-minute segment
5. **Database Population**: Stores results for each segment in the database
6. **Automation**: Fully automated end-to-end processing

### Key Benefits:
- ✅ **Efficient Memory Usage**: Processes 30-minute segments (~600MB) instead of full sessions (7+GB)
- ✅ **Parallel Processing**: Can process multiple segments simultaneously
- ✅ **Fault Tolerance**: If one segment fails, others continue processing
- ✅ **Scalable**: Handles sessions of any length

### Example Usage:
```bash
curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "url": "https://parliamentlive.tv/Event/Index/session-id",
    "duration": 7200
  }'
```

## Non-Sequential Processing Flow

**Purpose**: Capture and analyze specific duration segments directly without full session processing.

### Workflow:
1. **Direct Capture**: Downloads only the specified duration from Parliament TV
2. **Single File Processing**: Creates one video file for the requested timeframe
3. **Recognition**: Runs face recognition and transcription on the single file
4. **Database Population**: Stores results for the captured segment
5. **Automation**: Fully automated for the specified duration

### Key Benefits:
- ✅ **Targeted Analysis**: Only processes the content you need
- ✅ **Faster Processing**: No segmentation overhead
- ✅ **Resource Efficient**: Downloads only required content
- ✅ **Immediate Results**: Direct processing without segmentation delays

### Example Usage:
```bash
curl -X POST "http://localhost:8000/api/v1/parliament-tv" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://parliamentlive.tv/Event/Index/session-id",
    "duration": 1800,
    "title": "PM Questions"
  }'
```

## Debug Processing Flow

**Purpose**: Test and debug recognition on specific segments using existing files.

### Workflow:
1. **File Detection**: Automatically finds existing segment files for the specified time range
2. **Efficient Processing**: Uses pre-existing segments instead of re-extracting
3. **Recognition**: Runs face recognition and transcription on the specific segment
4. **Database Population**: Stores results for the debug segment
5. **Fast Iteration**: Enables quick testing without full reprocessing

### Key Benefits:
- ✅ **Ultra-Fast**: Uses existing files, no re-extraction needed
- ✅ **Precise Testing**: Test specific time ranges efficiently
- ✅ **Development Friendly**: Perfect for debugging and development
- ✅ **Resource Minimal**: Minimal CPU/bandwidth usage

### Example Usage:
```bash
curl -X POST "http://localhost:8000/api/v1/parliament-tv/process-segment" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "session_id": 1202,
    "start_time": 5400,
    "end_time": 7200,
    "segment_label": "Test PM Questions segment"
  }'
```

## Technical Architecture

### File Organization
```
/app/data/media/
├── session_1.mp4              # 30-minute video segments
├── session_1.mp3              # 30-minute audio segments
├── session_2.mp4
├── session_2.mp3
├── ...
├── parliament_tv_session_full.mp4    # Full session (if needed)
└── audio_session_full.mp3             # Full audio (if needed)
```

### Recognition Pipeline
Each processing flow uses the same recognition pipeline:

1. **Face Detection**: YuNet face detector identifies faces in video frames
2. **Face Recognition**: Matches detected faces against MP database
3. **Transcription**: Whisper converts audio to text
4. **Speaker Attribution**: Links transcript segments to identified speakers
5. **Database Storage**: Stores results in `parliament_clips.db` (SQLite) and PostgreSQL

### Database Schema
```sql
-- SQLite (temporary processing)
CREATE TABLE parliament_clips (
    id INTEGER PRIMARY KEY,
    member_id INTEGER,
    transcript TEXT,
    start_timestamp REAL,
    end_timestamp REAL,
    speech_group_id INTEGER,
    -- ... other fields
);

-- PostgreSQL (final storage)
CREATE TABLE parliament_member_clips (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES speakers(member_id),
    transcript TEXT,
    video_path TEXT,
    start_time REAL,
    end_time REAL,
    -- ... other fields
);
```

## Performance Characteristics

### Sequential Processing
- **Memory Usage**: ~600MB per segment (vs 7+GB for full session)
- **Processing Time**: ~5-10 minutes per 30-minute segment
- **Scalability**: Linear scaling with session length
- **Fault Tolerance**: High (segment-level isolation)

### Non-Sequential Processing  
- **Memory Usage**: Proportional to requested duration
- **Processing Time**: ~3-8 minutes for typical 30-minute clips
- **Scalability**: Constant (independent of full session length)
- **Fault Tolerance**: Medium (single file processing)

### Debug Processing
- **Memory Usage**: ~600MB per segment
- **Processing Time**: ~2-5 minutes (no extraction overhead)
- **Scalability**: Excellent for development/testing
- **Fault Tolerance**: High (uses existing files)

## Best Practices

### When to Use Sequential Processing
- ✅ Analyzing complete Parliament sessions
- ✅ Building comprehensive MP activity databases  
- ✅ Long-term archival and analysis projects
- ✅ When you need complete session coverage

### When to Use Non-Sequential Processing
- ✅ Capturing specific events or speeches
- ✅ Real-time or near-real-time analysis
- ✅ When storage space is limited
- ✅ Targeted content analysis

### When to Use Debug Processing
- ✅ Development and testing
- ✅ Debugging recognition issues
- ✅ Re-processing specific segments
- ✅ Performance testing and optimization

## Troubleshooting

### Common Issues

1. **Memory Issues**: Use sequential processing for large sessions
2. **Recognition Failures**: Check segment file integrity and MP database
3. **Database Conflicts**: Ensure proper SQLite to PostgreSQL export
4. **Performance Issues**: Monitor segment processing times and adjust concurrency

### Monitoring

Check processing status:
```bash
# View processing logs
docker-compose -f docker-compose.dev.yml logs --tail=50 app

# Check database population
docker exec the-mp-app-1 python -c "
import sqlite3
conn = sqlite3.connect('/app/backend/parliament_clips.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM parliament_clips')
print(f'Total clips: {cursor.fetchone()[0]}')
conn.close()
"
```

## Future Enhancements

- [ ] **Parallel Segment Processing**: Process multiple segments simultaneously
- [ ] **Adaptive Segmentation**: Dynamic segment sizes based on content
- [ ] **Real-time Processing**: Live stream analysis capabilities
- [ ] **Enhanced Fault Recovery**: Automatic retry mechanisms
- [ ] **Performance Optimization**: GPU acceleration for recognition tasks

## API Reference

For detailed API documentation, see:
- [Parliament TV Integration Guide](parliament_tv_integration.md)
- [Supabase Automation Guide](supabase_automation.md)
- [Recognition Pipeline Documentation](recognition_pipeline.md)

---

*Last updated: 2025-01-07*
*Contact: Development Team*
