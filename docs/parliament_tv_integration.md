# Parliament TV Integration

This document provides a comprehensive guide to the Parliament TV capture feature, which allows users to capture Parliament TV streams with facial recognition to automatically stop when the speaker is no longer present.

**Last Updated:** May 1, 2025

## Overview

The Parliament TV capture feature consists of several components:

1. **Backend API**: Endpoints for extracting stream URLs, testing streams, and managing capture sessions
2. **Frontend Interface**: User interface for initiating and monitoring captures
3. **Capture Scripts**: Python scripts for extracting stream URLs, downloading streams, and processing with facial recognition

## Setup Requirements

- Python 3.8+
- FFmpeg (for video processing)
- yt-dlp (for extracting stream URLs)
  - Added to Dockerfile.backend for automatic installation
  - Can be manually installed with `pip install yt-dlp`
- OpenCV (for facial recognition)

## Backend API Endpoints

The following API endpoints are available for Parliament TV capture:

### `POST /api/v1/parliament-tv`

Start a new Parliament TV capture session.

**Request Body:**
```json
{
  "url": "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS",
  "title": "Capture Title",
  "description": "Optional description",
  "duration": 300,
  "enable_facial_recognition": true
}
```

**Response:**
```json
{
  "id": 123,
  "title": "Capture Title",
  "status": "active",
  "url": "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS",
  "duration": 300,
  "facial_recognition_enabled": true,
  "start_time": "2025-05-01T01:00:00Z",
  "created_by_id": 1,
  "created_by": {
    "id": 1,
    "name": "User Name",
    "email": "user@example.com"
  },
  "created_at": "2025-05-01T01:00:00Z",
  "updated_at": "2025-05-01T01:00:00Z"
}
```

### `GET /api/v1/parliament-tv/extract-url`

Extract the direct stream URL from a Parliament TV event page.

**Query Parameters:**
- `url`: Parliament TV event URL

**Response:**
```json
{
  "direct_stream": "https://direct-stream-url.m3u8",
  "time_marker": {
    "seconds": 3600,
    "formatted": "01:00:00"
  }
}
```

### `GET /api/v1/parliament-tv/test-url`

Test if a stream URL is valid by downloading a small segment.

**Query Parameters:**
- `url`: Stream URL to test

**Response:**
```json
{
  "url": "https://direct-stream-url.m3u8",
  "is_valid": true
}
```

### `GET /api/v1/parliament-tv`

Get all Parliament TV capture sessions with optional filtering by status.

**Query Parameters:**
- `status`: Optional filter by status (active, completed, failed, draft)

**Response:**
```json
[
  {
    "id": 123,
    "title": "Capture Title",
    "status": "completed",
    "url": "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS",
    "duration": 300,
    "facial_recognition_enabled": true,
    "start_time": "2025-05-01T01:00:00Z",
    "end_time": "2025-05-01T01:05:00Z",
    "file_path": "/path/to/capture.mp4",
    "file_size": 12345678,
    "created_by_id": 1,
    "created_by": {
      "id": 1,
      "name": "User Name",
      "email": "user@example.com"
    },
    "created_at": "2025-05-01T01:00:00Z",
    "updated_at": "2025-05-01T01:05:00Z"
  }
]
```

### `GET /api/v1/parliament-tv/{capture_id}`

Get a specific Parliament TV capture session by ID.

**Path Parameters:**
- `capture_id`: ID of the capture session

**Response:**
```json
{
  "id": 123,
  "title": "Capture Title",
  "status": "completed",
  "url": "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS",
  "duration": 300,
  "facial_recognition_enabled": true,
  "start_time": "2025-05-01T01:00:00Z",
  "end_time": "2025-05-01T01:05:00Z",
  "file_path": "/path/to/capture.mp4",
  "file_size": 12345678,
  "created_by_id": 1,
  "created_by": {
    "id": 1,
    "name": "User Name",
    "email": "user@example.com"
  },
  "created_at": "2025-05-01T01:00:00Z",
  "updated_at": "2025-05-01T01:05:00Z"
}
```

## Frontend Interface

The Parliament TV capture interface is available at `/parliament-tv/capture` and provides the following functionality:

1. Input a Parliament TV URL
2. Validate the URL to ensure it can be captured
3. Set a title and optional description for the capture
4. Configure the maximum duration and facial recognition options
5. Start the capture process

## Capture Process

The capture process consists of the following steps:

1. **URL Extraction**: The direct stream URL is extracted from the Parliament TV event page using yt-dlp
2. **Stream Download**: The stream is downloaded using FFmpeg
3. **Facial Recognition**: The video is processed with facial recognition to detect when the speaker is no longer present
4. **Output Generation**: The final video is saved to the media directory

## Scripts

### `extract_direct_stream.py`

Extracts the direct stream URL from a Parliament TV event page.

```
python extract_direct_stream.py <parliament_tv_url> [--output OUTPUT_PATH]
```

### `parliament_capture_direct.py`

Captures a Parliament TV stream with facial recognition.

```
python parliament_capture_direct.py <parliament_tv_url> [--duration SECONDS] [--output OUTPUT_PATH]
```

### `test_stream_url.sh`

Tests if a stream URL is valid by downloading a small segment.

```
./test_stream_url.sh <stream_url> [--play]
```

## Troubleshooting

### Common Issues

1. **Stream URL Extraction Fails**
   - Ensure the Parliament TV URL is valid
   - Check that yt-dlp is installed and up to date
     - In Docker: `docker-compose -f docker-compose.dev.yml exec app pip install yt-dlp`
     - Local environment: `pip install yt-dlp`
   - Try using a different time marker in the URL

2. **Stream Download Fails**
   - Ensure FFmpeg is installed
   - Check network connectivity
   - Verify the stream URL is valid using the test script

3. **Facial Recognition Issues**
   - Ensure OpenCV is installed
   - Check that the video contains a visible speaker
   - Adjust the facial recognition parameters if needed

4. **Video Playback Issues**
   - Check that the video file exists in the expected location
   - Verify that the streaming endpoint is working correctly
   - Use the debugging tools described below to diagnose issues

### Logs

Logs for the capture process are stored in the following locations:

- Backend API logs: `/var/log/the-mp/backend.log`
- Capture script logs: `parliament_capture_*.log` in the current directory

### Debugging Tools

#### Video Server for Debugging

A debugging video server is available to help diagnose video playback issues:

```bash
# Run inside Docker container
python /app/scripts/video_server.py

# Run on host machine (recommended)
python /Users/joebradley/Veedoo/Development/the-mp/scripts/host_video_server.py
```

This server provides a web interface at http://localhost:8765 that allows you to:

- Browse all available Parliament TV videos
- Play videos directly in your browser
- Download videos for offline viewing
- See detailed file information

The host version of the server copies videos from the Docker container to your local machine, making them accessible even if there are permission or networking issues with the Docker container.

#### Debug Information in Capture Detail Page

The capture detail page now includes a debug section that shows:

- Capture ID and status
- File path information
- Video source URL being used
- Direct download link for the video file

This information can help diagnose issues with video playback and file access.

## Integration with Other Features

The Parliament TV capture feature integrates with the following existing features:

1. **Capture Sessions**: Parliament TV captures are stored as capture sessions in the database
2. **Media Storage**: Captured videos are stored in the media directory
3. **User Authentication**: Only authenticated users with appropriate permissions can initiate captures

## Recent Changes

### Integration with Main Application

The Parliament TV capture functionality has been integrated into the main application:

1. **Unified Navigation**: Parliament TV captures are now accessible through the main Captures section
2. **Enhanced Video Player**: The video player now handles Parliament TV videos with improved error recovery
3. **Robust Streaming Endpoint**: The streaming endpoint has been updated to better find and serve video files

### Technical Improvements

1. **Improved File Path Handling**: The system now tries multiple approaches to find video files
2. **Automatic File Path Updates**: When a file is found through alternative methods, the database is updated
3. **Fallback Mechanisms**: If one video source fails, the player automatically tries alternative sources

## Future Enhancements

Planned enhancements for the Parliament TV capture feature include:

1. **Scheduled Captures**: Ability to schedule captures for future events
2. **Speaker Recognition**: Identify specific speakers in the video
3. **Automatic Transcription**: Generate transcripts of the captured content
4. **Clip Generation**: Create short clips from the captured content
5. **Unified Media Management**: Complete integration with the main media management system
