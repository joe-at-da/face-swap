# Supabase Integration Setup Guide

This guide explains how to set up and use the Supabase integration with the Parliament Video Clip Manager backend.

## Overview

The Parliament Video Clip Manager integrates with Supabase to enable:

1. Storing video, audio, and recognition data in Supabase Storage
2. Sending video processing jobs to Supabase queues
3. Sending clip creation jobs to Supabase queues
4. Receiving webhook notifications from Supabase
5. Future direct API integration for real-time data synchronization

## Prerequisites

1. A Supabase account and project
2. Supabase API keys (anon key and service role key)
3. Configured storage buckets in Supabase:
   - `parliament-tv-media` (for media files)
   - `parliament-tv-exports` (for exported data)
4. Configured database tables in Supabase:
   - `video_processing_queue`
   - `clip_creation_queue`

## Installation

The Supabase Python client is required for integration:

```bash
pip install supabase
```

This is already included in the project requirements.

## Configuration

Add the following environment variables to your `.env` file:

```
# Supabase Integration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_API_KEY=your-supabase-api-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_MEDIA_BUCKET=parliament-tv-media
SUPABASE_EXPORT_BUCKET=parliament-tv-exports
SUPABASE_WEBHOOK_SECRET=your-webhook-secret
SUPABASE_INTEGRATION_ENABLED=true
```

## Database Schema

### Video Processing Queue

Create this table in your Supabase project:

```sql
CREATE TABLE video_processing_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  video_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  capture_date TIMESTAMP WITH TIME ZONE,
  duration FLOAT,
  video_url TEXT,
  audio_url TEXT,
  thumbnail_url TEXT,
  status TEXT DEFAULT 'pending',
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Clip Creation Queue

Create this table in your Supabase project:

```sql
CREATE TABLE clip_creation_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  video_id TEXT NOT NULL,
  start_time FLOAT NOT NULL,
  end_time FLOAT NOT NULL,
  speaker_id TEXT,
  speaker_name TEXT,
  confidence FLOAT DEFAULT 0.0,
  transcript TEXT,
  face_image_url TEXT,
  metadata JSONB,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Usage

### Exporting Data to Supabase

Use the following API endpoint to export video recognition and transcription data to Supabase:

```
POST /api/v1/supabase/export/{video_id}
```

This endpoint requires API key authentication using the `X-API-Key` header.

Example request:
```bash
curl -X POST "http://localhost:8000/api/v1/supabase/export/123" \
  -H "X-API-Key: your-integration-api-key"
```

### Checking Supabase Integration Status

To check the status of Supabase integration for a specific video:

```
GET /api/v1/supabase/status/{video_id}
```

Example request:
```bash
curl "http://localhost:8000/api/v1/supabase/status/123" \
  -H "X-API-Key: your-integration-api-key"
```

### Webhook Endpoints

The following webhook endpoints are available for receiving notifications from Supabase:

1. Video processed webhook:
```
POST /api/v1/supabase/webhooks/video-processed
```

2. Clip created webhook:
```
POST /api/v1/supabase/webhooks/clip-created
```

Both endpoints require API key authentication using the `X-API-Key` header.

## Data Flow

1. Parliament TV video is captured and processed by the backend
2. Recognition and transcription are performed
3. Data is exported to Supabase format
4. Data is uploaded to Supabase Storage
5. Jobs are added to Supabase queues
6. Supabase processes the jobs and sends webhook notifications back to the backend

## Important Notes

- **Audio and Video Streams**: Parliament TV provides separate URLs for audio and video streams. The system handles them independently and does not attempt to derive audio URLs from video URLs.
- **API Key Security**: All Supabase integration endpoints are secured with API key authentication.
- **Webhooks**: Webhook endpoints can be configured in Supabase to notify the backend when processing is complete.

## Testing with Postman

Use the provided Postman collections to test the Supabase integration endpoints:

1. Import the `Parliament_Video_Clip_Manager.postman_collection.json` collection
2. Set up environment variables including `integration_api_key`
3. Use the Supabase Integration folder to test the endpoints

For more details, see the [Postman Guide](postman_guide.md).
