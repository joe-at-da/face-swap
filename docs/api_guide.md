# Parliament Video Clip Manager API Guide

This document provides a comprehensive guide to the Parliament Video Clip Manager API, including authentication, endpoints, request/response formats, and example usage.

## Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Parliament TV Captures](#parliament-tv-captures)
4. [Recognition](#recognition)
5. [Transcription](#transcription)
6. [Voice Profiles](#voice-profiles)
7. [Face Profiles](#face-profiles)
8. [MP Profiles](#mp-profiles)
9. [Files and Media](#files-and-media)
10. [Dashboard](#dashboard)
11. [Admin](#admin)
12. [Integration API](#integration-api)
13. [Parliament TV Debug](#parliament-tv-debug)

## Base URL

All API endpoints are prefixed with `/api/v1/`.

For local development with Docker:
```
http://localhost:8000/api/v1/
```

## Authentication

The API uses OAuth2 with JWT tokens for authentication.

### Login

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "username": "admin@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Get Current User

**Endpoint:** `GET /auth/me`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "email": "admin@example.com",
  "full_name": "Admin User",
  "role": "admin",
  "is_active": true,
  "id": 1
}
```

## User Management

### Register New User (Admin only)

**Endpoint:** `POST /auth/register`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password",
  "full_name": "New User",
  "role": "staff",
  "is_active": true
}
```

**Response:**
```json
{
  "email": "user@example.com",
  "full_name": "New User",
  "role": "staff",
  "is_active": true,
  "id": 2
}
```

### List Users (Admin only)

**Endpoint:** `GET /auth/users`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "email": "admin@example.com",
    "full_name": "Admin User",
    "role": "admin",
    "is_active": true,
    "id": 1
  },
  {
    "email": "user@example.com",
    "full_name": "New User",
    "role": "staff",
    "is_active": true,
    "id": 2
  }
]
```

## Parliament TV Captures

### Extract Parliament TV URL

**Endpoint:** `POST /parliament-tv/extract`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "url": "https://parliamentlive.tv/event/index/12345678-1234-1234-1234-123456789012"
}
```

**Response:**
```json
{
  "success": true,
  "video_url": "https://streaming-url.example.com/video.mp4",
  "audio_url": "https://streaming-url.example.com/audio.mp3",
  "title": "House of Commons - Debate on Example Bill",
  "event_date": "2023-05-15T14:30:00Z"
}
```

### Test Stream URL

**Endpoint:** `GET /parliament-tv/test-stream`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
```
video_url=https://streaming-url.example.com/video.mp4
audio_url=https://streaming-url.example.com/audio.mp3
```

**Response:**
```json
{
  "success": true,
  "message": "Stream URL is valid",
  "duration": 3.45
}
```

### Start Parliament TV Capture

**Endpoint:** `POST /parliament-tv`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "url": "https://parliamentlive.tv/event/index/12345678-1234-1234-1234-123456789012",
  "title": "House of Commons - Debate on Example Bill",
  "description": "Debate on the second reading of the Example Bill",
  "video_url": "https://streaming-url.example.com/video.mp4",
  "audio_url": "https://streaming-url.example.com/audio.mp3",
  "duration": 3600,
  "use_facial_recognition": true,
  "start_at": "00:15:30"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Capture started successfully",
  "capture_id": 123,
  "status": "active",
  "video_url": "https://streaming-url.example.com/video.mp4",
  "audio_url": "https://streaming-url.example.com/audio.mp3",
  "created_at": "2023-05-15T14:35:00Z"
}
```

### Get All Parliament TV Captures

**Endpoint:** `GET /parliament-tv/captures`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
```
status=active (optional, can be active, completed, failed, or draft)
```

**Response:**
```json
[
  {
    "id": 123,
    "title": "House of Commons - Debate on Example Bill",
    "description": "Debate on the second reading of the Example Bill",
    "status": "active",
    "video_url": "https://streaming-url.example.com/video.mp4",
    "audio_url": "https://streaming-url.example.com/audio.mp3",
    "video_path": "/app/data/temp/capture_0123.mp4",
    "audio_path": "/app/data/temp/capture_0123.mp3",
    "duration": 3600,
    "created_at": "2023-05-15T14:35:00Z",
    "created_by": {
      "id": 1,
      "email": "admin@example.com"
    },
    "metadata": {
      "parliament_tv_url": "https://parliamentlive.tv/event/index/12345678-1234-1234-1234-123456789012",
      "start_at": "00:15:30",
      "use_facial_recognition": true
    }
  }
]
```

### Get Parliament TV Capture by ID

**Endpoint:** `GET /parliament-tv/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 123,
  "title": "House of Commons - Debate on Example Bill",
  "description": "Debate on the second reading of the Example Bill",
  "status": "active",
  "video_url": "https://streaming-url.example.com/video.mp4",
  "audio_url": "https://streaming-url.example.com/audio.mp3",
  "video_path": "/app/data/temp/capture_0123.mp4",
  "audio_path": "/app/data/temp/capture_0123.mp3",
  "duration": 3600,
  "created_at": "2023-05-15T14:35:00Z",
  "created_by": {
    "id": 1,
    "email": "admin@example.com"
  },
  "metadata": {
    "parliament_tv_url": "https://parliamentlive.tv/event/index/12345678-1234-1234-1234-123456789012",
    "start_at": "00:15:30",
    "use_facial_recognition": true
  },
  "recognition_status": {
    "status": "not_started",
    "completion_percentage": 0
  },
  "transcription_status": {
    "status": "not_started"
  }
}
```

### Stop Parliament TV Capture

**Endpoint:** `POST /parliament-tv/{capture_id}/stop`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Capture stopped successfully",
  "capture_id": 123,
  "status": "completed"
}
```

### Delete Parliament TV Capture

**Endpoint:** `DELETE /parliament-tv/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Capture deleted successfully",
  "capture_id": 123
}
```

### Extract Audio for Capture

**Endpoint:** `POST /parliament-tv/{capture_id}/extract-audio`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Audio extraction started",
  "capture_id": 123,
  "status": "processing"
}
```

### Get Audio Extraction Status

**Endpoint:** `GET /parliament-tv/{capture_id}/audio-status`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "has_audio": true,
  "audio_path": "/app/data/temp/audio_extracts/capture_0123.mp3",
  "capture_id": 123
}
```

## Recognition

### Start Combined Recognition

**Endpoint:** `POST /recognition/combined-recognition`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "video_id": 123,
  "save_output": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Recognition process started",
  "video_id": 123,
  "status": "processing"
}
```

### Get Recognition Status

**Endpoint:** `GET /recognition/status/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "video_id": 123,
  "status": "processing",
  "completion_percentage": 45,
  "message": "Processing facial recognition",
  "step_name": "facial_recognition"
}
```

### Get Detailed Recognition Status

**Endpoint:** `GET /recognition/detailed-status/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "video_id": 123,
  "status": "processing",
  "completion_percentage": 45,
  "message": "Processing facial recognition",
  "step_name": "facial_recognition",
  "steps": [
    {
      "name": "video_processing",
      "status": "completed",
      "message": "Video processing completed",
      "completion_percentage": 100
    },
    {
      "name": "facial_recognition",
      "status": "processing",
      "message": "Processing facial recognition",
      "completion_percentage": 45
    },
    {
      "name": "voice_recognition",
      "status": "pending",
      "message": "Waiting for facial recognition to complete",
      "completion_percentage": 0
    }
  ]
}
```

### Get Recognition Results

**Endpoint:** `GET /recognition/results/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "speakers": [
    {
      "id": "speaker_1",
      "name": "John Smith",
      "profile_id": 42,
      "face_matches": [
        {
          "timestamp": 120.5,
          "confidence": 0.92,
          "image_path": "/app/data/temp/capture_0123_faces/face_120_5.jpg"
        }
      ],
      "voice_matches": [
        {
          "start_time": 118.2,
          "end_time": 125.7,
          "confidence": 0.88
        }
      ]
    },
    {
      "id": "speaker_2",
      "name": "Unknown Speaker",
      "profile_id": null,
      "face_matches": [
        {
          "timestamp": 145.3,
          "confidence": 0.85,
          "image_path": "/app/data/temp/capture_0123_faces/face_145_3.jpg"
        }
      ],
      "voice_matches": [
        {
          "start_time": 143.1,
          "end_time": 150.4,
          "confidence": 0.76
        }
      ]
    }
  ],
  "segments": [
    {
      "start_time": 118.2,
      "end_time": 125.7,
      "speaker_id": "speaker_1",
      "text": "I would like to address the concerns raised by the honorable member."
    },
    {
      "start_time": 143.1,
      "end_time": 150.4,
      "speaker_id": "speaker_2",
      "text": "Thank you for your response. I have a follow-up question."
    }
  ]
}
```

### Get Unidentified Speakers

**Endpoint:** `GET /recognition/speakers/{capture_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "unidentified_speakers": [
    {
      "id": "speaker_2",
      "name": "Unknown Speaker",
      "face_matches": [
        {
          "timestamp": 145.3,
          "confidence": 0.85,
          "image_path": "/app/data/temp/capture_0123_faces/face_145_3.jpg"
        }
      ],
      "voice_matches": [
        {
          "start_time": 143.1,
          "end_time": 150.4,
          "confidence": 0.76
        }
      ]
    }
  ]
}
```

## Transcription

### Transcribe Parliament TV Capture

**Endpoint:** `POST /parliament-tv/{capture_id}/transcribe`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
```
language=en (default: en)
model_size=medium (options: tiny, base, small, medium, large)
force=false (default: false, set to true to force re-transcription)
```

**Response:**
```json
{
  "success": true,
  "message": "Transcription started",
  "transcription_id": 42,
  "status": "processing",
  "capture_id": 123
}
```

### Get Parliament TV Transcription

**Endpoint:** `GET /parliament-tv/{capture_id}/transcription`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
```
language=en (default: en)
```

**Response:**
```json
{
  "success": true,
  "message": "Transcription available",
  "transcription_id": 42,
  "status": "ready",
  "capture_id": 123,
  "language": "en",
  "text": "Full transcription text...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "I would like to address the concerns raised by the honorable member."
    },
    {
      "start": 6.1,
      "end": 12.4,
      "text": "Thank you for your response. I have a follow-up question."
    }
  ],
  "file_exists": true,
  "file_path": "/app/data/temp/transcriptions/capture_0123_en.txt",
  "created_at": "2023-05-15T15:00:00Z",
  "updated_at": "2023-05-15T15:05:00Z"
}
```

## Voice Profiles

### Create Voice Profile

**Endpoint:** `POST /voice-profiles`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "John Smith",
  "description": "MP for Example Constituency",
  "mp_id": 123
}
```

**Response:**
```json
{
  "id": 42,
  "name": "John Smith",
  "description": "MP for Example Constituency",
  "mp_id": 123,
  "created_at": "2023-05-15T15:10:00Z",
  "updated_at": "2023-05-15T15:10:00Z",
  "created_by": {
    "id": 1,
    "email": "admin@example.com"
  }
}
```

### Get Voice Profiles

**Endpoint:** `GET /voice-profiles`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "id": 42,
    "name": "John Smith",
    "description": "MP for Example Constituency",
    "mp_id": 123,
    "created_at": "2023-05-15T15:10:00Z",
    "updated_at": "2023-05-15T15:10:00Z",
    "created_by": {
      "id": 1,
      "email": "admin@example.com"
    }
  }
]
```

## Face Profiles

### Create Face Profile

**Endpoint:** `POST /face-profiles`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "John Smith",
  "description": "MP for Example Constituency",
  "mp_id": 123
}
```

**Response:**
```json
{
  "id": 42,
  "name": "John Smith",
  "description": "MP for Example Constituency",
  "mp_id": 123,
  "created_at": "2023-05-15T15:15:00Z",
  "updated_at": "2023-05-15T15:15:00Z",
  "created_by": {
    "id": 1,
    "email": "admin@example.com"
  }
}
```

### Get Face Profiles

**Endpoint:** `GET /face-profiles`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "id": 42,
    "name": "John Smith",
    "description": "MP for Example Constituency",
    "mp_id": 123,
    "created_at": "2023-05-15T15:15:00Z",
    "updated_at": "2023-05-15T15:15:00Z",
    "created_by": {
      "id": 1,
      "email": "admin@example.com"
    }
  }
]
```

## MP Profiles

### Get MP Profiles

**Endpoint:** `GET /mp-profiles`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
[
  {
    "id": 123,
    "name": "John Smith",
    "constituency": "Example Constituency",
    "party": "Example Party",
    "photo_url": "/api/v1/mp-profiles/123/photo",
    "created_at": "2023-05-15T15:20:00Z",
    "updated_at": "2023-05-15T15:20:00Z"
  }
]
```

### Get MP Profile by ID

**Endpoint:** `GET /mp-profiles/{mp_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": 123,
  "name": "John Smith",
  "constituency": "Example Constituency",
  "party": "Example Party",
  "photo_url": "/api/v1/mp-profiles/123/photo",
  "created_at": "2023-05-15T15:20:00Z",
  "updated_at": "2023-05-15T15:20:00Z",
  "voice_profile": {
    "id": 42,
    "name": "John Smith"
  },
  "face_profile": {
    "id": 42,
    "name": "John Smith"
  }
}
```

## Files and Media

### Upload File

**Endpoint:** `POST /files/upload`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form Data:**
```
file: (binary file data)
type: profile_image
```

**Response:**
```json
{
  "success": true,
  "file_id": "12345678-1234-1234-1234-123456789012",
  "file_path": "/app/data/uploads/12345678-1234-1234-1234-123456789012.jpg",
  "file_url": "/api/v1/files/12345678-1234-1234-1234-123456789012",
  "file_type": "image/jpeg",
  "file_size": 12345
}
```

### Get File

**Endpoint:** `GET /files/{file_id}`

**Response:** Binary file data

## Dashboard

### Get Dashboard Stats

**Endpoint:** `GET /dashboard/stats`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_captures": 10,
  "active_captures": 1,
  "completed_captures": 8,
  "failed_captures": 1,
  "total_transcriptions": 8,
  "total_recognitions": 7,
  "storage_usage": {
    "total_gb": 25.4,
    "used_gb": 12.7,
    "available_gb": 12.7,
    "usage_percentage": 50
  }
}
```

## Admin

### Get System Info

**Endpoint:** `GET /admin/system/info`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "system": {
    "os": "Linux",
    "version": "5.15.0-1031-aws",
    "hostname": "parliament-video-clip-manager",
    "uptime": 1234567
  },
  "application": {
    "version": "1.0.0",
    "api_version": "v1",
    "environment": "production",
    "start_time": "2023-05-15T00:00:00Z",
    "uptime": 123456
  },
  "resources": {
    "cpu_usage": 25.4,
    "memory_usage": 45.7,
    "disk_usage": 50.0
  }
}
```

### Get Storage Info

**Endpoint:** `GET /admin/storage/info`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "total_storage_gb": 25.4,
  "used_storage_gb": 12.7,
  "available_storage_gb": 12.7,
  "usage_percentage": 50,
  "directories": [
    {
      "path": "/app/data/temp",
      "size_gb": 5.2,
      "file_count": 123
    },
    {
      "path": "/app/data/uploads",
      "size_gb": 3.1,
      "file_count": 45
    },
    {
      "path": "/app/data/transcriptions",
      "size_gb": 2.3,
      "file_count": 67
    }
  ]
}
```

## Using the API with Postman

A Postman collection is available in the repository at `docs/Parliament_Video_Clip_Manager.postman_collection.json`. You can import this collection into Postman to easily test all the API endpoints.

### Importing the Collection

1. Open Postman
2. Click on "Import" in the top left
3. Select the `Parliament_Video_Clip_Manager.postman_collection.json` file
4. The collection will be imported with all the API endpoints pre-configured

### Authentication Setup

The collection includes a pre-request script that automatically handles authentication. To use it:

1. Create an environment in Postman with the following variables:
   - `base_url`: The base URL of your API (e.g., `http://localhost:8000/api/v1`)
   - `email`: Your login email
   - `password`: Your login password

2. The pre-request script will automatically:
   - Log in using your credentials
   - Store the access token
   - Add the token to all subsequent requests

### Testing the API

1. Select the environment you created
2. Navigate to the "Login" request in the "Authentication" folder and send it to verify your credentials
3. You can now send any request in the collection to test the API

## Error Handling

All API endpoints follow a consistent error handling pattern:

- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict (e.g., already exists)
- **500 Internal Server Error**: Server-side error

Error responses have the following format:

## Parliament TV Debug

### Process Specific Segment

Process a specific segment from already-downloaded Parliament TV files without re-downloading the entire video.

**Endpoint:** `POST /parliament-tv/process-segment`

**Authentication:** API Key required

**Headers:**
```
X-API-Key: {api_key}
```

**Request:**
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

For more detailed information, see the [Parliament TV Debug documentation](parliament_tv_debug.md).

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. The current limits are:

- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users

When rate limits are exceeded, the API will return a 429 Too Many Requests response with a Retry-After header indicating how long to wait before making another request.

## Integration API

The Integration API provides endpoints for external systems to access recognition results and media files. These endpoints use API key authentication instead of JWT tokens.

### Authentication

Integration API endpoints require an API key to be provided in the `X-API-Key` header:

```
X-API-Key: your_api_key_here
```

The API key can be configured in the application's environment variables as `INTEGRATION_API_KEY`.

### List Videos

**Endpoint:** `GET /integration/videos`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Query Parameters:**
```
limit=10 (default: 10)
offset=0 (default: 0)
status=completed (optional, filter by status)
```

**Response:**
```json
{
  "success": true,
  "total": 25,
  "offset": 0,
  "limit": 10,
  "videos": [
    {
      "video_id": 123,
      "title": "Parliament TV Capture - Example Session",
      "description": "House of Commons debate",
      "capture_date": "2023-05-15T14:35:00Z",
      "duration": 3600,
      "status": "completed",
      "has_results": true,
      "audio_url": "https://streaming-url.example.com/audio.mp3",
      "video_url": "https://streaming-url.example.com/video.mp4",
      "combined_av_url": "/api/v1/media/file?path=combined_av_123_20230515_143500.mp4"
    }
  ]
}
```

### Get Recognition Results

**Endpoint:** `GET /integration/recognition/{video_id}`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Response:**
```json
{
  "success": true,
  "video_id": 123,
  "title": "Parliament TV Capture - Example Session",
  "capture_date": "2023-05-15T14:35:00Z",
  "duration": 3600,
  "speakers": [
    {
      "id": "speaker_1",
      "name": "John Smith",
      "profile_id": 42,
      "segments": [
        {
          "start_time": 118.2,
          "end_time": 125.7,
          "text": "I would like to address the concerns raised by the honorable member."
        }
      ]
    }
  ],
  "combined_av_url": "/api/v1/media/file?path=combined_av_123_20230515_143500.mp4"
}
```

### Get Media File

**Endpoint:** `GET /media/file`

**Headers:**
```
X-API-Key: your_api_key_here
```

**Query Parameters:**
```
path=combined_av_123_20230515_143500.mp4
```

**Response:** Binary file data with appropriate content type headers

### Integration API Postman Collection

A Postman collection for the Integration API is available in the repository at `docs/integration_endpoints.postman_collection.json`. This collection includes all the Integration API endpoints with the correct authentication headers and URL formats.

To use the collection:

1. Import the collection into Postman
2. Set the following variables in your environment:
   - `base_url`: The base URL of your API (e.g., `http://localhost:8000`)
   - `integration_api_key`: Your API key for integration endpoints
   - `video_id`: ID of a video to retrieve recognition results for
   - `file_path`: Path to a media file to download

