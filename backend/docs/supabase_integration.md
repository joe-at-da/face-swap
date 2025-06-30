# Supabase Integration Setup

This document provides instructions for setting up and using the Supabase integration with the Parliament TV video capture and recognition system.

## Environment Variables

The following environment variables need to be configured for Supabase integration:

```
SUPABASE_URL=your_supabase_url
SUPABASE_API_KEY=your_supabase_api_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_INTEGRATION_ENABLED=true
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

## Important Notes

- Audio and video streams are handled as completely separate URLs, respecting Parliament TV's architecture
- No derivation of audio URLs from video URLs; audio URLs are used as provided
- The system uses real Parliament TV URLs, not test streams
- Full video upload uses Supabase service role key for privileged storage access
