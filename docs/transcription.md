# Transcription Feature Documentation

## Overview

The Parliament Video Clip Manager includes a powerful automatic transcription feature that allows users to generate accurate text transcriptions of Parliament TV videos. This feature uses OpenAI's Whisper model to convert speech to text, with support for multiple languages and output formats.

## Features

- **Automatic Transcription**: Convert speech to text using state-of-the-art AI models
- **Multiple Languages**: Support for English, Welsh, Irish, and Scottish Gaelic
- **Multiple Output Formats**: Generate transcriptions in TXT, SRT, JSON, and DOCX formats
- **Speaker Identification Integration**: Link transcriptions with speaker identification results for enhanced attribution
- **Asynchronous Processing**: Transcriptions run in the background, allowing users to continue working
- **Status Tracking**: Monitor transcription progress with real-time status updates
- **Content Viewing**: View transcription content directly in the browser
- **Download Options**: Download transcription files for offline use

## User Interface

The transcription feature is accessible from the capture detail page. The interface is divided into three main tabs:

1. **Start Transcription**: Configure and initiate new transcriptions
2. **Transcriptions**: View a list of existing transcriptions with status information
3. **View Transcription**: Read transcription content directly in the browser

### Starting a Transcription

To start a new transcription:

1. Navigate to a capture detail page
2. Click on the "Transcription" link
3. In the "Start Transcription" tab, configure the following options:
   - **Language**: Select the primary language spoken in the video
   - **Output Format**: Choose the desired output format
   - **Model Size**: Select the model size based on accuracy vs. speed requirements
   - **Speaker Identification**: Optionally link with a completed speaker identification
4. Click "Start Transcription"

### Viewing Transcriptions

To view existing transcriptions:

1. Navigate to the "Transcriptions" tab
2. Browse the list of transcriptions with status indicators
3. For completed transcriptions:
   - Click "View Transcription" to read the content in the browser
   - Click "Download" to download the transcription file
   - Click "Delete" to remove the transcription

## Technical Implementation

### Backend Components

- **API Endpoints**: Located in `/backend/api/v1/endpoints/transcription.py`
- **Database Model**: Defined in `/backend/db/models/transcription.py`
- **Processing Service**: Implemented in `/backend/services/transcription.py`

### Frontend Components

- **Transcription Page**: Implemented in `/frontend/pages/capture/[id]/transcription.tsx`
- **API Integration**: Uses React Query for data fetching and state management

### Database Schema

The `ParliamentTranscription` model includes the following fields:

- `id`: Primary key
- `capture_session_id`: Foreign key to the CaptureSession
- `user_id`: Foreign key to the User who initiated the transcription
- `speaker_identification_id`: Optional foreign key to a SpeakerIdentification
- `status`: Current status (pending, processing, completed, failed)
- `language`: Language code (en, cy, ga, gd)
- `format`: Output format (txt, srt, json, docx)
- `model`: Whisper model size (tiny, base, small, medium, large)
- `output_file`: Path to the output file when completed
- `error_message`: Error information if the transcription failed
- `created_at`: Timestamp when the transcription was created
- `updated_at`: Timestamp when the transcription was last updated

## Integration with Speaker Identification

The transcription feature can be integrated with the speaker identification feature to enhance transcription accuracy and provide speaker attribution. When a speaker identification is selected during transcription setup, the system will:

1. Use the speaker identification results to attribute speech segments to identified speakers
2. Include speaker names in the transcription output
3. Format the output based on the selected format (e.g., include speaker names in SRT subtitles)

## Docker Development Environment

When working with the transcription feature in a Docker development environment, be aware of the following:

1. The feature depends on the `backend.services.utils` module, which must be present in the Docker container
2. If you make changes to the transcription code, ensure the changes are properly synced with the Docker container
3. Use volume mounts in your docker-compose.dev.yml file to automatically sync local files with the container

Example volume mount configuration in docker-compose.dev.yml:

```yaml
services:
  app:
    # other configuration...
    volumes:
      - ./backend:/app/backend
```

## Troubleshooting

### Common Issues

1. **Transcription Stuck in Processing**:
   - Check the backend logs for errors
   - Verify that the Celery worker is running
   - Ensure the video file is accessible

2. **Missing Transcription Output**:
   - Verify that the output directory exists and is writable
   - Check for permission issues on the output directory

3. **Docker Environment Issues**:
   - If you encounter "Module not found" errors, ensure all required modules are present in the Docker container
   - Use the Docker troubleshooting steps in the README.md to sync new files with the container

## Future Enhancements

Planned enhancements for the transcription feature include:

1. **Automatic Speaker Diarization**: Identify and separate speakers without requiring speaker identification
2. **Transcription Editing Interface**: Allow users to edit and correct transcriptions
3. **Additional Output Formats**: Support for more output formats (PDF, HTML, etc.)
4. **Enhanced Language Support**: Add support for more languages
5. **Real-time Transcription**: Implement streaming transcription for live feeds

## API Reference

### Endpoints

- `POST /api/v1/transcription/parliament-tv`: Start a new transcription
- `GET /api/v1/transcription/parliament-tv/capture/{capture_id}`: Get transcriptions for a capture
- `GET /api/v1/transcription/parliament-tv/{transcription_id}`: Get a specific transcription
- `DELETE /api/v1/transcription/parliament-tv/{transcription_id}`: Delete a transcription

For detailed API documentation, refer to the Swagger UI at `/api/v1/docs`.
