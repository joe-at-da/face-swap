# Parliament TV Speaker Recognition System

## Overview

The Parliament TV Speaker Recognition System is a comprehensive solution for automatically identifying speakers in Parliament TV broadcasts. The system uses a combination of facial recognition and local database matching to identify Members of Parliament (MPs) in video streams, create clips, and export the results to Supabase.

## System Architecture

The system follows a hybrid architecture with local processing and Supabase integration:

1. **Local Processing**:
   - Video capture from Parliament TV streams
   - Frame extraction and facial recognition
   - Speaker matching using local MP database
   - Timeline event generation
   - Local PostgreSQL database for intermediate storage

2. **Supabase Integration**:
   - Initial MP data synchronization
   - Final export of recognition results
   - Clip creation and storage
   - Media file storage

## Key Components

### 1. MultimodalRecognitionService

The core service that orchestrates the recognition process:
- Processes video with transcription
- Extracts frames at strategic intervals
- Identifies speakers using facial recognition
- Integrates with ParliamentMemberMatcher for improved speaker identification
- Creates timeline events for visualization

### 2. ParliamentMemberMatcher

Specialized service for matching detected faces to known MPs:
- Maintains a local database of MP photos and face embeddings
- Matches face embeddings to known MPs with confidence scores
- Creates SpeakerIdentification and SpeakerAppearance records
- Handles unidentified speakers with default placeholders

### 3. Supabase Export

Exports recognition results to Supabase:
- Formats clips for Supabase clip_creation queue
- Uploads media files to Supabase storage
- Includes MP associations with clips
- Deduplicates clips to avoid redundant entries

## Directory Structure

- `/app/data/mp_photos/`: MP photos used for facial recognition
- `/app/data/temp/recognition/`: Temporary files for recognition processing
- `/app/data/temp/audio_extracts/`: Extracted audio files
- `/app/data/temp/transcriptions/`: Transcription files
- `/app/data/media/`: Media files for export

## Running the Pipeline

### Prerequisites

- Docker environment set up with `docker-compose.dev.yml`
- Environment variables configured for Supabase integration
- MP photos downloaded to `/app/data/mp_photos/`

### Using the Test Script

1. Make sure the Docker container is running:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. Execute the test script inside the Docker container:
   ```bash
   docker exec -it the-mp-backend /bin/bash -c "cd /app && ./scripts/run_test_pipeline.sh"
   ```

3. Monitor the logs for progress:
   ```bash
   docker logs -f the-mp-backend
   ```

### Manual Pipeline Execution

1. Capture a Parliament TV stream:
   ```python
   from backend.services.parliament_tv import ParliamentTVService
   from backend.db.session import SessionLocal

   db = SessionLocal()
   parliament_tv = ParliamentTVService()
   result = parliament_tv.start_capture(
       url="https://parliamentlive.tv/event/index/1b5736b4-7c93-4827-a4f4-35e00425c3fe",
       title="Test Capture",
       description="Test capture from Parliament TV",
       duration=300,
       db=db
   )
   capture_id = result["capture_id"]
   ```

2. Start the recognition process:
   ```python
   from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService

   recognition_service = MultimodalRecognitionService()
   recognition_result = recognition_service.start_combined_recognition(capture_id)
   ```

3. Export to Supabase:
   ```python
   from backend.services.integration.supabase_integration import SupabaseIntegration
   from backend.services.utils import make_json_serializable

   supabase = SupabaseIntegration()
   recognition_data = recognition_service.get_recognition_results(db, capture_id)
   video_metadata = {
       "title": "Test Capture",
       "description": "Test capture from Parliament TV",
       "capture_date": "2025-07-01T12:00:00",
       "duration": 300
   }
   
   export_result = supabase.export_and_upload_recognition(
       video_path="/app/data/media/test_capture.mp4",
       recognition_results=make_json_serializable(recognition_data),
       video_metadata=make_json_serializable(video_metadata),
       db_session=db,
       video_id=capture_id,
       upload_media=True
   )
   ```

## Troubleshooting

### Common Issues

1. **MP Photos Not Found**:
   - Ensure MP photos are downloaded to `/app/data/mp_photos/`
   - Check file permissions and ownership

2. **Supabase Export Failures**:
   - Verify Supabase environment variables are set correctly
   - Check network connectivity to Supabase
   - Ensure media files exist at the expected paths

3. **Recognition Accuracy Issues**:
   - Adjust confidence thresholds in `identify_speaker_in_frame` method
   - Add more MP photos to improve matching accuracy
   - Check lighting and angle of extracted frames

## Next Steps

1. **Voice Recognition Integration**:
   - Add voice profile creation for MPs
   - Implement voice-based speaker identification
   - Combine face and voice recognition for improved accuracy

2. **Manual Review Interface**:
   - Create web UI for reviewing automatic matches
   - Allow manual correction of misidentified speakers
   - Implement feedback loop to improve recognition models

3. **Performance Optimization**:
   - Implement batch processing for large videos
   - Add parallel processing of video segments
   - Optimize memory usage for large-scale processing

## Documentation

For more detailed information, refer to:
- [MP Photo Management Guide](/docs/mp_photo_management.md)
- [Speaker Recognition Roadmap](/docs/speaker_recognition_roadmap.md)
- [Parliament TV Integration](/docs/parliament_tv_integration.md)
