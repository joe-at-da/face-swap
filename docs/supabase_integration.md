# Supabase Integration Guide

## Overview

This document outlines the hybrid approach used in the Parliament TV application, which leverages both a local PostgreSQL database (managed by Alembic) and Supabase as a remote data store. This architecture provides the benefits of local development and testing while enabling cloud-based data sharing and access.

## Architecture

### Local-First Approach

The application follows a **local-first** approach:

1. All core operations use the local PostgreSQL database
2. Supabase is used primarily for:
   - Initial data sourcing (e.g., parliament member data)
   - Final data export (e.g., processed clips and recognition results)
   - Remote storage of media files

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Supabase      │────▶│   Local DB      │────▶│   Supabase      │
│   (Data Source) │     │   (Processing)  │     │   (Export)      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Local Database (PostgreSQL)

### Key Components

- **Database Models**: Defined in `/backend/db/models/`
- **Migrations**: Managed by Alembic in `/backend/alembic/`
- **Session Management**: Handled by SQLAlchemy in `/backend/db/session.py`

### Important Models

- `CaptureSession`: Video capture sessions
- `RecognitionProcess`: Recognition process metadata and results
- `SpeakerIdentification`: Links speakers to capture sessions
- `SpeakerAppearance`: Individual speaker appearances with timestamps
- `ParliamentTranscription`: Transcription data for videos

## Supabase Integration

### Configuration

Supabase integration can be enabled/disabled via environment variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_INTEGRATION_ENABLED=true
```

### Data Synchronization

#### Parliament Member Data

1. Parliament member data is initially fetched from Supabase
2. Data is cached locally at `/app/data/temp/parliament_members.json`
3. Local cache is used as fallback if Supabase is unavailable
4. Minimal test data is created if neither source is available

#### MP Photos

1. MP photos are downloaded from Supabase storage or external URLs
2. Photos are cached locally at `/app/data/mp_photos/{member_id}.jpg`
3. Face embeddings are extracted and stored locally
4. Local photos are used for all facial recognition operations

#### Final Export

After local processing is complete:
1. Recognition results are exported to Supabase tables
2. Media clips are uploaded to Supabase storage
3. Metadata is updated in Supabase for web frontend access

## Speaker Matching System

### Components

- **ParliamentMemberMatcher**: Core class for matching speakers to parliament members
- **MultimodalRecognitionService**: Integrates facial and voice recognition
- **FacialRecognitionService**: Handles face detection and recognition
- **TimelineService**: Creates timeline data from recognition results

### Speaker Matching Process

1. **Data Preparation**:
   - Load parliament member data (from cache or Supabase)
   - Ensure MP photos are downloaded and cached locally
   - Extract face embeddings from photos

2. **Matching Process**:
   - Extract faces from video frames
   - Compare face embeddings to known parliament members
   - Create `SpeakerIdentification` records in local database
   - Create `SpeakerAppearance` records linked to identifications
   - Generate timeline data for visualization

3. **Export Process**:
   - Export matched clips to Supabase (optional)
   - Update recognition results in Supabase (optional)

## Automation Endpoint

The `/supabase-automation/process-parliament-tv` endpoint provides a unified workflow:

1. Extract stream URLs from Parliament TV page
2. Create capture session in local database
3. Download video and audio streams
4. Process video with multimodal recognition
5. Match speakers using ParliamentMemberMatcher
6. Export results to Supabase (if enabled)

## Best Practices

1. **Always use Docker container paths** for file operations:
   - `/app/data/temp/` for temporary files
   - `/app/data/mp_photos/` for MP photos
   - `/app/data/media/` for media files

2. **Handle Supabase unavailability gracefully**:
   - Use local cache as fallback
   - Provide meaningful error messages
   - Continue with minimal functionality when possible

3. **Respect foreign key constraints**:
   - Create parent records before child records
   - Use raw SQL with `text()` for precise control when needed
   - Verify record existence before creating relationships

4. **Optimize network operations**:
   - Cache remote data locally
   - Batch uploads and downloads
   - Use conditional requests when appropriate

## Future Improvements

1. **Enhanced Synchronization**:
   - Bidirectional sync between local DB and Supabase
   - Conflict resolution for concurrent edits
   - Offline-first capabilities with sync on reconnection

2. **Advanced Speaker Recognition**:
   - Voice recognition integration
   - Multi-modal fusion (face + voice)
   - Speaker diarization improvements

3. **Manual Review Interface**:
   - Web UI for reviewing and correcting automatic matches
   - Feedback loop to improve recognition accuracy
   - Batch processing of corrections

## Troubleshooting

### Common Issues

1. **Foreign Key Constraint Violations**:
   - Ensure parent records exist before creating child records
   - Check that IDs match between related tables
   - Use raw SQL for precise control over insertion order

2. **Missing MP Photos**:
   - Verify MP photo directory exists: `/app/data/mp_photos/`
   - Check download URLs and network connectivity
   - Ensure proper error handling for missing photos

3. **Supabase Connection Issues**:
   - Verify environment variables are set correctly
   - Check network connectivity to Supabase
   - Use local fallbacks when Supabase is unavailable

### Logging

Comprehensive logging is implemented throughout the application:

- Recognition processes log to `/app/logs/recognition.log`
- API endpoints log to `/app/logs/api.log`
- Background tasks log to `/app/logs/tasks.log`

## References

- [Supabase Documentation](https://supabase.io/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
