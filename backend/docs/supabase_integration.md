# Supabase Integration Setup

This document provides instructions for setting up and using the Supabase integration with the Parliament TV video capture and recognition system.

## Environment Variables

The following environment variables need to be configured for Supabase integration:

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

## Docker Setup

For Docker development environment, these variables have been added to the Docker containers. If you need to update them, you can:

1. Modify the environment section in `docker-compose.dev.yml`
2. Or set them directly in the container using:
   ```bash
   docker-compose -f docker-compose.dev.yml exec app bash -c "export VARIABLE_NAME=value"
   ```
3. Restart the containers to apply changes:
   ```bash
   docker-compose -f docker-compose.dev.yml restart
   ```

## Automated Parliament TV Processing

The system includes an automated endpoint for processing Parliament TV streams:

### API Endpoint

```
POST /api/v1/supabase-automation/process-parliament-tv
```

### Authentication

The endpoint is secured with API key authentication. Include the API key in the `X-API-Key` header:

```
X-API-Key: 8448700525
```

### Request Body

```json
{
  "url": "https://parliamentlive.tv/event/index/97c409d6-cd51-4596-9921-96e0bfeb7677",
  "title": "Session Title",
  "description": "Session Description",
  "debug": false,
  "duration": 7200
}
```

- `url`: Parliament TV URL to process
- `title`: Title for the capture session
- `description`: Description for the capture session
- `duration`: Duration to capture in seconds (default: 2 hours)

### Example cURL Request

```bash
curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
  -H "X-API-Key: 8448700525" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://parliamentlive.tv/event/index/97c409d6-cd51-4596-9921-96e0bfeb7677", "title":"Test Capture", "description":"Test description", "duration":90}'
```

## Automated Cron Job Setup

The system includes scripts to set up automated cron jobs for Parliament TV processing:

1. Run the setup script:
   ```bash
   python backend/scripts/setup_parliament_tv_cron.py
   ```

2. This will create a cron job that periodically calls the Parliament TV processing endpoint.

3. The cron job uses the `backend/scripts/call_parliament_tv_endpoint.py` script, which is created automatically if it doesn't exist.

4. By default, the cron job runs every 4 hours. You can modify this by editing the setup script.

## Processing Pipeline

The automated Parliament TV processing pipeline includes:

1. Extracting separate audio and video stream URLs from Parliament TV
2. Capturing audio and video streams independently
3. Running combined facial and voice recognition
4. Exporting recognition and transcription data to Supabase
5. Uploading the full combined video to Supabase storage
6. Processing recognition results to identify speaking segments
7. Creating and uploading clips for each speaking segment

## Speaker Segmentation Logic

The system implements the following logic to identify speaking segments and create clips:

1. **Speaker Identification**: The system combines facial recognition and voice recognition results to identify speakers in the video.

2. **Segment Merging**: Segments from the same speaker that are less than 60 seconds apart are merged into a single clip. This handles cases where an MP briefly pauses during their speech.

3. **Clip Boundaries**: A new clip is created when:
   - A different MP starts speaking
   - The same MP resumes speaking after a pause of more than 60 seconds

4. **Transcript Extraction**: For each clip, the system extracts the relevant portion of the transcript based on the start and end timestamps.

5. **Confidence Scoring**: Each clip includes a confidence score derived from the recognition results, indicating the system's confidence in the speaker identification.

## Supabase Integration Components

### SupabaseService Class

The `SupabaseService` class in `backend/services/integration/supabase_client.py` provides the following functionality:

- Authentication with Supabase using service role key
- Uploading files to Supabase Storage buckets
- Inserting data into Supabase tables
- Getting public URLs for uploaded files

### Recognition Export

The `export_recognition_results` function in `backend/services/recognition/supabase_export.py` handles:

- Creating a combined audio-video file for Supabase
- Exporting recognition results to a JSON file
- Combining recognition and transcription data
- Creating speaker-attributed transcripts

### Parliament Member Clips Table

The `parliament_member_clips` table in Supabase stores the following information for each clip:

- **member_id**: ID of the MP speaking
- **transcript**: Text for the MP speaking
- **full_video_path**: Path to the full video with audio
- **start_timestamp**: When MP starts speaking (e.g., "00:10:53")
- **end_timestamp**: When MP stops speaking (e.g., "00:11:43")
- **duration_seconds**: Duration of the clip in seconds
- **session_date**: Date of the parliamentary session
- **session_type**: Type of parliamentary session
- **debate_topic**: Topic of debate
- **status**: Status of the clip (e.g., "pending_review", "approved", "rejected")

## Important Notes

- Audio and video streams are handled as completely separate URLs, respecting Parliament TV's architecture
- No derivation of audio URLs from video URLs; audio URLs are used as provided
- The system uses real Parliament TV URLs, not test streams
- Full video upload uses Supabase service role key for privileged storage access
- All file paths within the Docker container use the `/app/` prefix (e.g., `/app/data/temp/`)
- Transcription files are stored in `/app/data/temp/transcriptions/`
- Audio files are stored in `/app/data/temp/audio_extracts/`
- The system prefers to read transcription from files rather than database fields when available

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure the SUPABASE_SERVICE_ROLE_KEY is correctly set and has the necessary permissions.

2. **File Access Issues**: Verify that file paths use the Docker container paths (`/app/data/...`) rather than local paths.

3. **Transcription Parsing Errors**: The system expects Parliament TV transcriptions in the format `[HH:MM:SS - HH:MM:SS] Text`. If parsing fails, check the transcription format.

4. **Missing Clips**: If clips are not being created, check that the recognition results contain both facial and voice recognition data, and that the speaker segmentation logic is correctly identifying speaking segments.

### Logs and Debugging

Detailed logs are available in the Docker container logs. To view them:

```bash
docker-compose -f docker-compose.dev.yml logs --tail=100 app
```

For more detailed logging, you can temporarily increase the log level in `backend/core/config.py`.

## Future Enhancements

1. **Webhook Notifications**: Implement webhook notifications for completed processing.

2. **Batch Processing**: Add support for batch processing multiple Parliament TV URLs.

3. **Advanced Speaker Identification**: Enhance speaker identification with additional ML models.

4. **Automatic Clip Publishing**: Integrate with social media platforms for automatic clip publishing.
