# Parliament TV Debug Endpoint

## Overview

The Parliament TV Debug Endpoint is designed to help developers process and debug specific segments of already-downloaded Parliament TV videos without requiring re-downloading of the full audio/video files. This is particularly useful for debugging recognition issues in specific time windows, such as MP identification problems in a particular segment.

## Key Features

- **Segment-specific processing**: Process only a specific time window from already-downloaded files
- **Rapid iteration**: Debug and fix issues without waiting for full video re-download
- **Reuse existing files**: Work with local files that have already been downloaded
- **Custom labeling**: Add descriptive labels to segments for easier identification

## Technical Implementation

The debug endpoint extracts segments from local files using FFmpeg's precise cutting capabilities, then processes these segments through the standard recognition pipeline. This approach allows for targeted debugging of specific segments without the overhead of re-downloading or re-processing the entire video.

## API Reference

### Process Specific Segment

**Endpoint:** `POST /api/v1/parliament-tv/process-segment`

**Authentication:** Requires API key in `X-API-Key` header

**Request Body:**
```json
{
  "session_id": 1150,                   // ID of the existing capture session with downloaded files
  "start_time": 5400,                   // Start time of the segment in seconds (e.g., 5400 = 90 minutes)
  "end_time": 7200,                     // End time of the segment in seconds (e.g., 7200 = 120 minutes)
  "segment_label": "MP identification debug"  // Optional label for the segment
}
```

**Response:**
```json
{
  "success": true,
  "message": "Started processing segment 5400-7200s from session 1150",
  "session_id": 1150,
  "segment_info": {
    "start_time": 5400,
    "end_time": 7200,
    "label": "MP identification debug"
  }
}
```

## Usage Examples

### Example 1: Debug MP Identification in 90-120 Minute Segment

```bash
curl -X POST "http://localhost:8000/api/v1/parliament-tv/process-segment" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "session_id": 1150,
    "start_time": 5400,
    "end_time": 7200,
    "segment_label": "MP identification debug"
  }'
```

### Example 2: Process First 30 Minutes of a Session

```bash
curl -X POST "http://localhost:8000/api/v1/parliament-tv/process-segment" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "session_id": 1150,
    "start_time": 0,
    "end_time": 1800,
    "segment_label": "Opening statements"
  }'
```

## Error Handling

The endpoint performs several validations:

- **Invalid time range**: Returns 400 Bad Request if end_time <= start_time
- **Session not found**: Returns 404 Not Found if the session ID doesn't exist
- **Missing files**: Returns 404 Not Found if video or audio files don't exist for the session

## Implementation Details

1. **Segment Extraction**:
   - Uses FFmpeg to extract precise segments from local MP4 and MP3 files
   - Maintains audio/video synchronization by using the same time parameters

2. **Processing Pipeline**:
   - Uses the existing recognition pipeline for the extracted segment
   - Preserves all metadata from the original session

3. **Output**:
   - Creates segment files in a debug-specific directory
   - Adds debug prefix to segment IDs for easy identification

## Integration with Existing System

The debug endpoint leverages the `ParliamentTVSequentialProcessor` class to extract and process segments, ensuring consistency with the main processing pipeline while providing the flexibility needed for debugging specific segments.
