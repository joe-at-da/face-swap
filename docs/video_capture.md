# Video Capture Functionality

This document provides detailed information about the video capture functionality in the Parliament Video Clip Manager.

## Overview

The video capture functionality allows users to record streams from Parliament TV or other video sources. The system captures the video stream in real-time, saves it to a temporary storage location, and provides tools for managing capture sessions.

## Features

- **Live Stream Capture**: Capture live video streams from Parliament TV
- **Session Management**: Start, stop, and monitor capture sessions
- **Multiple Source Support**: Capture from various video sources (HLS, MP4, RTMP)
- **Error Handling**: Robust error handling for network and stream issues
- **Logging**: Detailed logging of capture events and errors

## Configuration

The video capture functionality is configured in the `backend/core/config.py` file:

```python
# Video Settings
PARLIAMENT_TV_URL: str = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
TEMP_STORAGE_PATH: str = "/app/data/temp"
MEDIA_STORAGE_PATH: str = "/app/data/media"
MAX_CLIP_DURATION_MINUTES: int = 30
CLEANUP_AGE_HOURS: int = 24
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `PARLIAMENT_TV_URL` | The default video source URL for captures |
| `TEMP_STORAGE_PATH` | Directory for storing temporary capture files |
| `MEDIA_STORAGE_PATH` | Directory for storing processed media files |
| `MAX_CLIP_DURATION_MINUTES` | Maximum duration for video clips |
| `CLEANUP_AGE_HOURS` | Age (in hours) after which temporary files are cleaned up |

## Parliament TV Stream URLs

For development and testing, the system uses a reliable test stream. In production, you'll need to use the actual Parliament TV stream URLs.

The actual Parliament TV stream URLs follow this format:
```
https://p7of6fc-a2-westeurope-fay.cdn.redbee.live/parliamentlive/vod/entities/[EVENT_ID]_[TOKEN]/mat/[STREAM_ID].m3u8
```

To obtain the actual stream URL for a specific Parliament TV event:
1. Open the event page in a browser (e.g., https://www.parliamentlive.tv/Event/Index/56fac7d5-b3be-4f69-94f3-e68ffc46c9c1)
2. Use browser developer tools to inspect network requests
3. Look for requests to `.m3u8` files, which are the HLS stream manifests

## API Endpoints

### Start Capture Session

```
POST /api/v1/capture
```

**Request Body:**
```json
{
  "title": "House of Commons Session",
  "description": "Prime Minister's Questions",
  "source_url": "https://example.com/stream.m3u8"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "active",
  "start_time": "2025-04-26T21:56:11.506582Z",
  "created_by_id": 1,
  "created_by": {
    "id": 1,
    "name": "Admin User",
    "email": "admin@parliament.uk"
  },
  "created_at": "2025-04-26T21:56:11.506582Z",
  "updated_at": null,
  "title": "House of Commons Session",
  "end_time": null,
  "file_path": null,
  "file_size": null,
  "duration": null
}
```

### Stop Capture Session

```
POST /api/v1/capture/{capture_id}/stop
```

**Response:**
```json
{
  "id": 1,
  "status": "completed",
  "start_time": "2025-04-26T21:56:11.506582Z",
  "end_time": "2025-04-26T22:30:45.123456Z",
  "file_path": "/app/data/temp/capture_20250426_215611.mp4",
  "file_size": 158176357,
  "duration": 2074
}
```

### Get Capture Session

```
GET /api/v1/capture/{capture_id}
```

### List Capture Sessions

```
GET /api/v1/capture
```

### Get Capture Logs

```
GET /api/v1/capture/{capture_id}/logs
```

## Implementation Details

The video capture functionality is implemented using the following components:

1. **StreamCapture Class**: Handles the actual video capture process using FFmpeg
2. **Capture Endpoints**: API endpoints for managing capture sessions
3. **Database Models**: Store capture session information and metadata

### StreamCapture Class

The `StreamCapture` class in `backend/services/video/capture.py` is responsible for the actual video capture process. It uses FFmpeg to capture the video stream and save it to a file.

Key methods:
- `start_capture()`: Starts capturing the video stream
- `stop_capture()`: Stops the capture process
- `is_capturing()`: Checks if a capture is currently in progress

### Error Handling

The system includes robust error handling for various scenarios:
- Network connectivity issues
- Stream format errors
- Storage space limitations
- Process management issues

## Troubleshooting

### Common Issues

1. **No video file is created**
   - Check if the source URL is accessible
   - Verify that FFmpeg is installed and working correctly
   - Check for errors in the application logs

2. **Capture process terminates unexpectedly**
   - Check for network connectivity issues
   - Verify that there is sufficient disk space
   - Check for errors in the application logs

3. **"A capture session is already running" error**
   - Only one capture session can be active at a time
   - Stop the current capture session before starting a new one

## Future Enhancements

1. **Multiple Simultaneous Captures**: Support for capturing from multiple sources simultaneously
2. **Scheduled Captures**: Ability to schedule capture sessions in advance
3. **Automatic Transcription**: Real-time transcription of captured content
4. **Enhanced Monitoring**: Better monitoring of capture sessions with real-time statistics
5. **Stream Health Metrics**: Monitoring of stream quality and health
