# Parliament TV Recognition System Documentation

## Overview

The Parliament TV Recognition System is designed to process video and audio captures from Parliament TV streams. It performs two main functions:

1. **Speaker Identification**: Identifies speakers in video footage using facial recognition
2. **Transcription**: Transcribes audio content using the Whisper model

The system is designed to handle separate audio and video streams, which is common in Parliament TV captures where audio and video are provided as separate files.

## System Architecture

### Components

1. **Recognition Endpoint**: REST API endpoint that orchestrates the recognition process
2. **Facial Recognition Service**: Identifies speakers in video footage
3. **Voice Recognition Service**: Transcribes audio content
4. **Progress Tracking**: Monitors and reports on the status of recognition processes

### Data Flow

1. User initiates recognition process through UI or API
2. System checks for available audio and video files
3. If video is available, speaker identification is performed
4. If audio is available, transcription is performed
5. Results are combined and stored in the database
6. Progress is tracked and reported throughout the process

## API Endpoints

### Start Recognition Process

```
POST /api/v1/recognition/combined-recognition
```

**Request Body:**
```json
{
  "video_id": 258,
  "save_output": true
}
```

**Response:**
```json
{
  "success": true,
  "video_id": 258,
  "speaker_identification": { ... },
  "transcription": { ... },
  "combined_output_file": "/path/to/combined_results.json",
  "message": "Recognition completed with available data",
  "processing_details": {
    "video_available": true,
    "audio_available": true,
    "video_path": "/path/to/video.mp4",
    "audio_path": "/path/to/audio.mp3",
    "timestamp": "2025-05-08T10:00:00.000Z"
  }
}
```

### Check Recognition Status

```
GET /api/v1/recognition/recognition-status/{video_id}
```

**Response:**
```json
{
  "success": true,
  "status": {
    "video_id": 258,
    "status": "completed",
    "started_at": "2025-05-08T09:55:00.000Z",
    "completed_at": "2025-05-08T10:00:00.000Z",
    "progress": {
      "status": "completed",
      "completed_at": "2025-05-08T10:00:00.000Z",
      "steps": [
        {
          "name": "initialization",
          "status": "completed",
          "timestamp": "2025-05-08T09:55:00.000Z"
        },
        {
          "name": "speaker_identification",
          "status": "completed",
          "timestamp": "2025-05-08T09:57:00.000Z"
        },
        {
          "name": "transcription",
          "status": "completed",
          "timestamp": "2025-05-08T09:59:00.000Z"
        },
        {
          "name": "completion",
          "status": "completed",
          "timestamp": "2025-05-08T10:00:00.000Z"
        }
      ]
    },
    "has_results": true
  }
}
```

## Command-Line Tools

### Run Recognition Script

The `run_recognition.py` script provides a command-line interface for running and monitoring recognition processes with real-time feedback.

**Basic Usage:**
```bash
python /app/scripts/run_recognition.py --video-id 258
```

**Options:**
- `--video-id` or `-v`: ID of the capture to process (required)
- `--username` or `-u`: Username for authentication (default: test@example.com)
- `--password` or `-p`: Password for authentication (default: testpassword)
- `--no-save`: Do not save output files
- `--timeout` or `-t`: Timeout in seconds for monitoring (default: 600)
- `--monitor-only` or `-m`: Only monitor an existing recognition process
- `--results-only` or `-r`: Only display results of a completed recognition process

## Database Schema

The recognition results and progress are stored in the `CaptureSession` table with the following fields:

- `recognition_status`: Status of the recognition process (not_started, processing, completed, error)
- `recognition_started_at`: Timestamp when the recognition process started
- `recognition_completed_at`: Timestamp when the recognition process completed
- `recognition_progress`: JSON object containing detailed progress information
- `recognition_results`: JSON object containing the combined recognition results

## Error Handling

The system is designed to handle errors gracefully:

1. If speaker identification fails but transcription succeeds, the process continues and returns partial results
2. If transcription fails but speaker identification succeeds, the process continues and returns partial results
3. If both fail, the process returns an error
4. All errors are logged and stored in the database for debugging

## UI Integration

The recognition system is integrated with the Parliament TV UI, allowing users to:

1. View the status of recognition processes
2. Start new recognition processes
3. View recognition results, including speaker identification and transcription

## Best Practices

1. **Audio and Video Files**: Ensure that audio and video files are properly separated and stored
2. **Error Handling**: Check the status endpoint regularly to monitor progress and detect errors
3. **Resource Management**: Recognition processes can be resource-intensive, especially for long videos
4. **Timeout Management**: Set appropriate timeouts for monitoring recognition processes

## Troubleshooting

### Common Issues

1. **Missing Audio/Video Files**: Ensure that both audio and video files are available and accessible
2. **Transcription Failures**: Check that the audio file contains valid audio data
3. **Speaker Identification Failures**: Ensure that the video file contains valid video data
4. **Database Errors**: Check that the database schema is up to date

### Debugging

1. Check the application logs for detailed error messages
2. Use the `recognition-status` endpoint to check the progress and status of recognition processes
3. Use the `run_recognition.py` script with the `--monitor-only` option to monitor existing processes
