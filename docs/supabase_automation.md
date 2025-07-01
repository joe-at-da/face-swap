# Parliament TV Supabase Automation

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
SUPABASE_URL=your-supabase-url
SUPABASE_API_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_INTEGRATION_ENABLED=true
INTEGRATION_API_KEY=your-api-key-for-authentication
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
  "duration": 7200
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| url | string | Parliament TV URL to process |
| title | string | Title for the capture session |
| description | string | Description for the capture session (optional) |
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
