# Parliament TV Sequential Processing

## Overview

The Parliament TV Sequential Processing system is designed to handle long videos from Parliament TV by processing them in 30-minute segments. This approach solves memory issues that occur when processing very long videos in a single pass, while maintaining the integrity of the recognition results.

## Key Features

- **Auto-detection of Parliament TV videos**: Automatically scrapes the latest live or archived video from Parliament TV Commons if no URL is provided.
- **Full stream download**: Downloads the entire audio and video streams without duration limits.
- **Sequential processing**: Processes videos in 30-minute segments by making repeated API calls for each time window.
- **Segment concatenation**: After all segments are processed, concatenates audio/video segments into final files.
- **Integration with existing pipeline**: Uses the existing recognition pipeline for each segment without altering the current logic.

## System Components

1. **ParliamentTVScraper**: Scrapes Parliament TV Commons for live or recent archived videos.
2. **ParliamentTVSequentialProcessor**: Handles sequential processing of videos in 30-minute segments.
3. **API Endpoints**: Provides endpoints for initiating sequential processing.

## Usage Modes

The system supports three different modes of operation:

### 1. Auto-Detection Mode

When no URL is provided, the system automatically scrapes Parliament TV Commons for the latest video and processes it sequentially.

**API Request:**
```json
POST /supabase-automation/process-parliament-tv
{
  "title": "Auto-detected Parliament TV",
  "description": "Automatically detected from Parliament TV Commons"
}
```

**Process Flow:**
1. Scrapes Parliament TV Commons for the latest video
2. Downloads the entire audio and video streams
3. Processes the video in 30-minute segments
4. Concatenates the segments into final files

### 2. Sequential Processing Mode

When a URL is provided but no duration is specified, the system uses the provided URL but processes it sequentially in 30-minute segments.

**API Request:**
```json
POST /supabase-automation/process-parliament-tv
{
  "url": "https://parliamentlive.tv/event/index/123456",
  "title": "Parliament TV Sequential Processing",
  "description": "Processed sequentially in 30-minute segments"
}
```

**Process Flow:**
1. Extracts stream URLs from the provided Parliament TV URL
2. Downloads the entire audio and video streams
3. Processes the video in 30-minute segments
4. Concatenates the segments into final files

### 3. Original Processing Mode

When both URL and duration are provided, the system uses the original processing logic with the specified duration.

**API Request:**
```json
POST /supabase-automation/process-parliament-tv
{
  "url": "https://parliamentlive.tv/event/index/123456",
  "title": "Parliament TV Processing",
  "description": "Processed with original logic",
  "duration": 7200
}
```

**Process Flow:**
1. Extracts stream URLs from the provided Parliament TV URL
2. Captures audio and video for the specified duration
3. Processes the video in a single pass
4. Exports results to Supabase

## Technical Implementation

### Sequential Processing Workflow

1. **Stream URL Extraction**:
   - Uses the `extract-url.py` script to extract direct stream URLs from Parliament TV URLs.

2. **Full Stream Download**:
   - Downloads the entire audio and video streams using `yt-dlp` or `ffmpeg`.

3. **Segment Processing**:
   - For each 30-minute segment:
     - Makes an API call to the existing processing pipeline with segment information
     - Specifies start and end times for the segment
     - Processes the segment independently

4. **Segment Concatenation**:
   - After all segments are processed, concatenates the segments using `ffmpeg`
   - Creates final audio and video files

### Live Stream Handling

For live streams, the system:
1. Captures in 30-minute segments until the stream ends
2. Detects when the stream has ended based on processing results
3. Concatenates all captured segments

### Database Integration

- Creates a capture session in the database for the entire video
- Links all segment processing results to the parent capture session
- Updates the capture session with concatenated file paths when processing is complete

## Error Handling

- Robust error handling for stream extraction, download, and processing failures
- Logging of all steps and errors for debugging
- Graceful degradation if any segment fails to process

## Dependencies

- `beautifulsoup4`: For scraping Parliament TV Commons
- `ffmpeg`: For media processing and concatenation
- `yt-dlp`: For downloading streams
- Existing recognition pipeline components

## Configuration

The system uses the existing configuration for:
- API keys
- Media storage paths
- Recognition settings
- Supabase integration

## Testing

To test the system:

1. **Auto-detection mode**:
   ```
   curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{"title": "Test Auto-detection", "description": "Testing auto-detection mode"}'
   ```

2. **Sequential processing mode**:
   ```
   curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{"url": "https://parliamentlive.tv/event/index/123456", "title": "Test Sequential", "description": "Testing sequential processing"}'
   ```

3. **Original processing mode**:
   ```
   curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key" \
     -d '{"url": "https://parliamentlive.tv/event/index/123456", "title": "Test Original", "description": "Testing original processing", "duration": 7200}'
   ```
