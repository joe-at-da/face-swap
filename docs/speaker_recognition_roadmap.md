# Speaker Recognition System Roadmap

## Current Status (July 2025)

### Completed Features

1. **Core Speaker Matching**
   - ✅ Local database models for `SpeakerIdentification` and `SpeakerAppearance`
   - ✅ Face embedding extraction and comparison
   - ✅ MP photo caching at `/app/data/mp_photos/`
   - ✅ Default unidentified speaker handling
   - ✅ Foreign key constraint handling

2. **Parliament Member Data Management**
   - ✅ Supabase data fetching with local caching
   - ✅ Fallback to cached data when Supabase is unavailable
   - ✅ Minimal test data generation for development

3. **Integration**
   - ✅ Integration with `MultimodalRecognitionService`
   - ✅ Support for the `/supabase-automation/process-parliament-tv` endpoint
   - ✅ Docker container path compliance

### Completed Recently

1. **Multimodal Recognition Integration**
   - ✅ Full integration of ParliamentMemberMatcher into MultimodalRecognitionService
   - ✅ Proper handling of speaker appearances in recognition results
   - ✅ Enhanced clip formatting for Supabase export with MP associations
   - ✅ End-to-end test script for validating the full pipeline
   - ✅ Comprehensive MP photo management documentation

2. **Speaker Attribution Consistency**
   - ✅ Implemented speaker normalization across continuous speech segments
   - ✅ Added speech group tracking for related segments
   - ✅ Enhanced confidence-based speaker selection for continuous speech
   - ✅ Database integration for persistent speech group IDs
   - ✅ Improved reliability of speaker identification in exported data

### In Progress

1. **Multimodal Recognition Enhancements**
   - 🔄 Improved face detection in video frames
   - 🔄 Better handling of multiple faces in a single frame
   - 🔄 Confidence threshold tuning

2. **Performance Optimization**
   - 🔄 Batch processing for large videos
   - 🔄 Parallel processing of video segments
   - 🔄 Memory usage optimization

## Short-Term Goals (Next 2-4 Weeks)

1. **Voice Recognition Integration**
   - Add voice profile creation for MPs
   - Implement voice-based speaker identification
   - Combine face and voice recognition results for improved accuracy

2. **Manual Review Interface**
   - Create web UI for reviewing automatic matches
   - Allow manual correction of misidentified speakers
   - Implement feedback loop to improve recognition models

3. **Export Enhancement**
   - Improve Supabase export reliability
   - Add selective export options (e.g., only export high-confidence matches)
   - Implement background export tasks

## Medium-Term Goals (2-3 Months)

1. **Advanced Recognition Features**
   - Speaker diarization for overlapping speakers
   - Emotion and sentiment analysis
   - Gesture and posture recognition

2. **Training Interface**
   - Tools for adding new MPs to the system
   - Interface for improving existing MP profiles
   - Batch training from verified footage

3. **Analytics and Reporting**
   - Speaking time analysis by MP
   - Topic detection and analysis
   - Interaction patterns between MPs

## Long-Term Vision (6+ Months)

1. **AI-Powered Analysis**
   - Automatic highlight generation
   - Important moment detection
   - Contextual understanding of debates

2. **Multi-Source Integration**
   - Integration with additional video sources beyond Parliament TV
   - Support for different chamber layouts and camera angles
   - Cross-referencing with official records

3. **Public API**
   - Secure API for third-party applications
   - Subscription-based access to recognition results
   - Developer tools and documentation

## Technical Debt and Improvements

1. **Code Quality**
   - Refactor duplicate code in recognition services
   - Improve error handling and logging
   - Add comprehensive unit and integration tests

2. **Database Optimization**
   - Optimize database schema for performance
   - Implement proper indexing
   - Add database maintenance tools

3. **Documentation**
   - Complete API documentation
   - Add developer guides
   - Create user manuals for non-technical users

## Implementation Notes

### Speaker Recognition Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Video Input   │────▶│   Face/Voice    │────▶│   Speaker       │
│                 │     │   Detection     │     │   Matching      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Export to     │◀────│   Timeline      │◀────│   Database      │
│   Supabase      │     │   Generation    │     │   Storage       │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Components

1. **ParliamentMemberMatcher**
   - Core class for matching speakers to parliament members
   - Handles face embedding comparison
   - Manages MP photo caching

2. **MultimodalRecognitionService**
   - Integrates facial and voice recognition
   - Processes video segments
   - Creates timeline data

3. **Database Models**
   - `SpeakerIdentification`: Links speakers to capture sessions
   - `SpeakerAppearance`: Individual speaker appearances with timestamps
   - `RecognitionProcess`: Tracks recognition status and results

## Resources and Dependencies

1. **Required Libraries**
   - OpenCV for face detection
   - face_recognition for face embedding extraction
   - SQLAlchemy for database operations
   - Supabase Python client for Supabase integration

2. **Infrastructure**
   - Docker containers for consistent environment
   - PostgreSQL database for local storage
   - Supabase for remote storage and sharing

3. **Development Tools**
   - FastAPI for API endpoints
   - Alembic for database migrations
   - pytest for testing

## Conclusion

The speaker recognition system is evolving from a basic facial recognition system to a comprehensive multimodal speaker identification platform. By focusing on local processing with optional Supabase integration, we maintain development flexibility while enabling cloud-based sharing and access.

The immediate focus is on improving the integration between our enhanced `ParliamentMemberMatcher` and the `MultimodalRecognitionService`, ensuring that all speaker identifications use our robust local database approach while maintaining compatibility with the Supabase export functionality.
