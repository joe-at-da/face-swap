# Parliament TV Transcription

This document provides an overview of the transcription functionality for Parliament TV streams in the MP application.

## Overview

The transcription system allows for automatic speech-to-text conversion of Parliament TV audio, with support for speaker identification and multiple output formats. The system uses OpenAI's Whisper model for high-quality speech recognition.

## Features

- **Audio Extraction**: Automatically extracts audio from Parliament TV streams
- **Speech Recognition**: Uses Whisper for accurate speech-to-text conversion
- **Speaker Identification**: Links transcribed segments to identified speakers
- **Multiple Languages**: Supports transcription in various languages
- **Background Processing**: Runs as asynchronous tasks to avoid blocking the main application
- **API Integration**: Full REST API for creating and retrieving transcriptions

## Architecture

### Components

1. **TranscriptionService**: Core service that handles the actual transcription using Whisper
2. **API Endpoints**: REST endpoints for creating and retrieving transcriptions
3. **Background Tasks**: Celery tasks for asynchronous processing
4. **Database Models**: Models for storing transcription data and metadata

### Flow

1. User requests a transcription for a Parliament TV capture
2. System checks if audio has been extracted, and extracts it if not
3. A transcription record is created in the database with status "processing"
4. A background task is started to perform the transcription
5. The Whisper model processes the audio and generates text with timestamps
6. Speaker identification data is added if available
7. The transcription is saved to the database and as a JSON file
8. The transcription status is updated to "ready"

## API Endpoints

### Start a Transcription

```
POST /api/v1/parliament-tv/{capture_id}/transcribe
```

Parameters:
- `language`: Language code (default: "en")
- `model_size`: Whisper model size (tiny, base, small, medium, large)
- `force`: Whether to force re-transcription if one exists

Example Response:
```json
{
  "success": true,
  "message": "Transcription started",
  "transcription_id": 123,
  "status": "processing",
  "capture_id": 456
}
```

### Get Transcription

```
GET /api/v1/parliament-tv/{capture_id}/transcription
```

Parameters:
- `language`: Language code (default: "en")

Example Response (when ready):
```json
{
  "success": true,
  "message": "Transcription available",
  "transcription_id": 123,
  "status": "ready",
  "capture_id": 456,
  "language": "en",
  "text": "Full transcription text...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.0,
      "text": "Welcome to today's parliamentary session.",
      "duration": 5.0,
      "speaker": "Speaker Name",
      "confidence": 0.95
    },
    ...
  ],
  "file_exists": true,
  "file_path": "/path/to/transcription.json",
  "created_at": "2025-05-07T21:00:00Z",
  "updated_at": "2025-05-07T21:05:00Z"
}
```

## Models

### ParliamentTranscription

- `id`: Unique identifier
- `capture_id`: ID of the Parliament TV capture
- `language`: Language code
- `text`: Full transcription text
- `segments`: Array of transcription segments with timestamps
- `status`: Status of the transcription (processing, ready, failed)
- `error_message`: Error message if transcription failed
- `output_file_path`: Path to the transcription file
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `created_by_id`: ID of the user who created the transcription

## Testing

A test script is provided to verify the transcription functionality:

```bash
python test_transcription.py /path/to/audio/file.mp3 --language en --model base
```

This script will:
1. Load the specified audio file
2. Transcribe it using the TranscriptionService
3. Display the results, including a sample of the transcription

## Example Output

The transcription output includes:

1. **Full Text**: Complete transcription of the audio
2. **Segments**: Individual segments with start/end times
3. **Speaker Information**: Speaker names if available
4. **Metadata**: Information about the transcription process

Example segment:
```json
{
  "id": 0,
  "start": 0.0,
  "end": 5.0,
  "text": "Welcome to today's parliamentary session.",
  "duration": 5.0,
  "speaker": "Speaker Name",
  "confidence": 0.95
}
```

## Performance

- **Processing Time**: Depends on audio length and model size
  - Tiny model: ~5% of audio duration
  - Base model: ~10% of audio duration
  - Small model: ~20% of audio duration
  - Medium/Large models: ~30-50% of audio duration
- **Accuracy**: Higher with larger models, but requires more processing time
- **Speaker Identification**: Improves with clearer audio and distinct voices

## Future Improvements

1. **Real-time Transcription**: Support for live transcription during streaming
2. **Improved Speaker Diarization**: Better speaker separation and identification
3. **Custom Vocabulary**: Support for parliamentary terminology and names
4. **Transcript Editing**: UI for manual correction of transcriptions
5. **Search Functionality**: Advanced search across transcriptions

## Troubleshooting

### Common Issues

1. **Missing Audio**: Ensure audio has been extracted before requesting transcription
2. **Processing Failures**: Check error messages in the transcription record
3. **Long Processing Times**: Consider using a smaller model for faster results
4. **Speaker Identification Issues**: Verify speaker data is available and correctly formatted

### Logs

Transcription logs are available in the application logs with the prefix:
- `backend.services.video.transcription`
- `backend.services.tasks.parliament_tv_tasks`
