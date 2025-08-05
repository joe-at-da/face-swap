# Parliament TV Supabase Automation

*Updated: August 5, 2025 by Joe Bradley (joe@veedoo.io)*

This document describes the automated Parliament TV processing pipeline that handles the entire workflow from URL extraction to Supabase integration, including saving individual member clips with detailed metadata.

## Overview

The Parliament TV Supabase Automation feature provides a unified API endpoint that automates the entire workflow:

1. Extracting stream URLs from Parliament TV event pages
2. Capturing video using the original URL (maintaining separate audio and video streams)
3. Performing combined recognition (facial and voice)
4. Retrieving recognition results
5. Uploading the full combined video to Supabase storage using the service role key
6. Adding individual member clips to the Supabase `parliament_member_clips` table with detailed metadata

## Prerequisites

To use this feature, ensure the following environment variables are configured:

```
SUPABASE_URL="http://127.0.0.1:54321"
SUPABASE_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
SUPABASE_MEDIA_BUCKET="parliament-tv-media"
SUPABASE_EXPORT_BUCKET="parliament-tv-exports"
SUPABASE_FULL_VIDEOS_BUCKET="full_videos"
SUPABASE_WEBHOOK_SECRET="super-secret-jwt-token-with-at-least-32-characters-long"
SUPABASE_INTEGRATION_ENABLED=true
SUPABASE_STORAGE_URL="http://127.0.0.1:54321/storage/v1/s3"
INTEGRATION_API_KEY=8448700525
```

The `SUPABASE_SERVICE_ROLE_KEY` is used server-side only for privileged operations like uploading full videos.

## API Endpoint

### Process Parliament TV to Supabase

```
POST /api/v1/supabase-automation/process-parliament-tv
```

This endpoint initiates the full processing pipeline for a Parliament TV URL.

#### Request Body

```json
{
  "url": "https://parliamentlive.tv/event/index/123456789",
  "title": "Parliament Session Title",
  "description": "Description of the session",
  "duration": 7200,
  "debug": false
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| url | string | Parliament TV URL to process |
| title | string | Title for the capture session |
| description | string | Description for the capture session (optional) |
| debug | boolean | Enable debug/test mode with shorter durations for testing (default: false) |
| duration | integer | Duration to capture in seconds (default: 7200 = 2 hours) |

#### Authentication

This endpoint requires API key authentication. Include the API key in the request header:

```
X-API-Key: your-integration-api-key
```

#### Response

```json
{
  "status": "processing",
  "message": "Started Parliament TV processing pipeline",
  "url": "https://parliamentlive.tv/event/index/123456789",
  "title": "Parliament Session Title",
  "description": "Description of the session",
  "duration": 7200
}
```

## Processing Pipeline

The endpoint performs the following steps asynchronously in the background:

1. **URL Extraction**: Extracts separate audio and video stream URLs from the Parliament TV page
2. **Video Capture**: Captures both audio and video streams separately
3. **Combined Recognition**: Processes the video with both facial and voice recognition
4. **Results Export**: Formats and exports recognition results for Supabase
5. **Full Video Upload**: Uploads the combined audio-video file to Supabase storage
6. **Member Clips Processing**: Creates and saves individual member clips to Supabase

### Member Clips Processing

The system processes recognition results to create individual clips for each identified member:

1. Extracts speaker segments from both facial and voice recognition results
2. Merges segments by the same speaker if they are close together (less than 60 seconds apart)
3. Creates detailed clip metadata including:
   - Timestamps (start/end)
   - Duration
   - Transcript segments
   - Confidence scores
   - Speaker information
   - Session metadata
4. Saves clips to the Supabase `parliament_member_clips` table

## Supabase Tables

### parliament_member_clips

This table stores individual clips for each identified member with detailed metadata:

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Unique identifier for the clip |
| video_id | string | ID of the parent video |
| member_id | string | ID of the member in the clip |
| member_name | string | Name of the member |
| start_time | float | Start time in seconds |
| end_time | float | End time in seconds |
| start_timestamp | string | Formatted start time (HH:MM:SS) |
| end_timestamp | string | Formatted end time (HH:MM:SS) |
| duration | float | Duration in seconds |
| transcript | string | Transcript text for this clip |
| confidence | float | Confidence score (0-1) |
| recognition_method | string | Method used for recognition (facial/voice) |
| full_video_url | string | URL to the full video in Supabase storage |
| session_title | string | Title of the Parliament session |
| session_date | string | Date of the session (ISO format) |
| session_description | string | Description of the session |
| original_url | string | Original Parliament TV URL |
| created_at | string | Timestamp when the clip was created (ISO format) |
| status | string | Processing status |

## Usage Guide

The Supabase automation API is the primary entry point for Parliament TV processing. This section provides comprehensive examples of how to use the API in various scenarios.

### Basic Usage

The simplest way to call the API is using curl:

```bash
curl --location 'http://localhost:8000/api/v1/supabase-automation/process-parliament-tv' \
  --header 'X-API-Key: 8448700525' \
  --header 'Content-Type: application/json' \
  --data '{
    "url": "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7", 
    "title": "Test Capture", 
    "description": "Test description", 
    "duration": 60
  }'
```

### Common Usage Scenarios

#### 1. Capture a Specific Parliament TV Event

Provide the URL of the specific Parliament TV event:

```json
{
  "url": "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7",
  "title": "Test Capture",
  "description": "Test description"
}
```

#### 2. Capture with Time Limit

Limit the capture to a specific duration (in seconds):

```json
{
  "url": "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7",
  "title": "Test Capture",
  "description": "Test description",
  "duration": 90
}
```

#### 3. Capture Most Recent Event (Automated Mode)

Omit the URL to automatically capture the most recent or live event:

```json
{
  "title": "Test Capture",
  "description": "Test description"
}
```

#### 4. Capture with Specific MP Focus

Specify an MP to focus on during facial recognition:

```json
{
  "url": "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7",
  "title": "Test Capture",
  "description": "Test description",
  "target_member_id": 123
}
```

#### 5. Scheduled Capture (for Cron Jobs)

This format is ideal for scheduled cron jobs:

```json
{
  "title": "Daily Parliament Capture",
  "description": "Automated daily capture",
  "duration": 3600,
  "prevent_duplicates": true
}
```

### Advanced Options

| Parameter | Type | Description |
|-----------|------|-------------|
| url | string | Parliament TV event URL (optional) |
| title | string | Capture title (required) |
| description | string | Capture description (optional) |
| duration | integer | Maximum capture duration in seconds (optional) |
| target_member_id | integer | Specific MP to focus on (optional) |
| prevent_duplicates | boolean | Skip if event was already captured (optional) |
| start_offset | integer | Start capture from specific offset in seconds (optional) |
| enable_facial_recognition | boolean | Enable/disable facial recognition (default: true) |

### Integration Notes

- The API is designed to be called from scripts, cron jobs, or other automated systems
- Authentication is handled via the X-API-Key header
- The process runs asynchronously; the API returns immediately with a job ID
- Results can be monitored via the status endpoint

## Implementation Details

### Audio and Video Stream Handling

The system respects the separation of audio and video streams from Parliament TV:

1. Parliament TV provides separate URLs for audio and video streams
2. The audio stream URL (ending with audio_eng=64000.m3u8) is used directly for audio extraction
3. The video stream URL (ending with video=3000000.m3u8) is used for video capture
4. No derivation or substitution of audio URLs from video URLs is performed

### Speaker Segmentation Logic

The system implements the following logic to segment clips by speaker:

1. **Speaker Identification**: The system combines facial recognition and voice recognition results to identify speakers in the video.

2. **Segment Merging**: Segments from the same speaker that are less than 60 seconds apart are merged into a single clip. This handles cases where an MP briefly pauses during their speech.

3. **Clip Boundaries**: A new clip is created when:
   - A different MP starts speaking
   - The same MP resumes speaking after a pause of more than 60 seconds

4. **Transcript Extraction**: For each clip, the system extracts the relevant portion of the transcript based on the start and end timestamps.

5. **Confidence Scoring**: Each clip includes a confidence score derived from the recognition results, indicating the system's confidence in the speaker identification.

6. **Face-Voice Matching**: When both facial and voice recognition identify the same MP, the confidence score is increased. In cases of conflict, the system uses the recognition method with the higher confidence score.

## Usage Examples

### Triggering the Pipeline via API

```bash
curl -X POST "http://your-server/api/v1/supabase-automation/process-parliament-tv" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-integration-api-key" \
  -d '{
    "url": "https://parliamentlive.tv/event/index/123456789",
    "title": "Parliament Session Title",
    "description": "Description of the session",
    "duration": 7200
  }'
```

### Setting Up a Cron Job for Automated Processing

You can set up a cron job to automatically process Parliament TV sessions at scheduled times:

```bash
# Run every day at 10:00 AM
0 10 * * * curl -X POST "http://your-server/api/v1/supabase-automation/process-parliament-tv" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-integration-api-key" \
  -d '{
    "url": "https://parliamentlive.tv/event/index/todaysession",
    "title": "Daily Parliament Session",
    "description": "Automated daily capture",
    "duration": 7200
  }'
```

## Error Handling

The system implements comprehensive error handling:

1. Validation of Parliament TV URLs and stream extraction
2. Verification of both audio and video streams before processing
3. Detailed logging of each processing step
4. Capture session status updates in the database
5. Error reporting for failed clip saving operations

## Troubleshooting

If you encounter issues with the automation pipeline:

1. Check the application logs for detailed error messages
2. Verify that both audio and video streams are successfully extracted from the Parliament TV URL
3. Ensure the Supabase service role key has appropriate permissions
4. Confirm that the `parliament_member_clips` table exists in your Supabase database
5. Check that the combined recognition process completes successfully before attempting to save clips

## Security Considerations

1. The API endpoint is protected with API key authentication
2. The Supabase service role key is used only server-side for privileged operations
3. No sensitive credentials are exposed to the client
4. Future versions will implement webhook signature verification for additional security
