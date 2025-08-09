# Parliament Video Clip Manager - Technical Roadmap

## Project Overview
An application for UK Members of Parliament to capture, edit, and share video clips from Parliament TV feeds with automated transcription, branding, and multi-platform sharing capabilities.

## Technical Stack

### Backend
- Python 3.11+
- FastAPI for REST API
- PostgreSQL for main database
- Redis for caching and job queues
- Celery for background tasks

### Frontend
- Next.js with TypeScript
- Tailwind CSS for styling
- React Query for state management
- DaisyUI for UI components

### Video Processing
- OpenCV for video capture and processing
- FFmpeg for video encoding/decoding
- MoviePy for video editing
- face_recognition for face detection/recognition

### AI/ML Components
- Whisper for speech-to-text transcription
- BERT/GPT for text analysis and tagging
- TensorFlow for custom AI models

### Cloud Infrastructure
- Hetzner for hosting
- Docker for containerization

## Development Phases

### Phase 1: Core Infrastructure ✅
- ✅ Project structure setup
- ✅ Database models and migrations
- ✅ Environment configuration
- ✅ Authentication system with JWT
- ✅ Role-based access control
- ✅ Test infrastructure
- ✅ FastAPI server implementation
- ✅ Video capture system
- ✅ Basic CRUD operations

### Phase 2: Video Processing ✅
- ✅ Parliament TV feed integration
- ✅ Video capture and storage
- ✅ Basic clip editing
- ✅ Transcription integration with Whisper
- ✅ Chunked transcription for long recordings
- ✅ Storage management system
- ✅ Face recognition setup

### Phase 3: User Interface ✅
- ✅ Next.js frontend setup
- ✅ Authentication system with JWT integration
- ✅ Video management interface
- ✅ Clip editor component
- ✅ User dashboard
- ✅ Admin interface

### Phase 4: Advanced Features 🏗️
- ✅ Social media integration
- ✅ Analytics dashboard
- ✅ Complete navigation system
- ✅ Placeholder pages for upcoming features
- 🏗️ Custom branding tools
- 🏗️ Batch processing
- 🏗️ Advanced search

### Phase 5: Deployment & Infrastructure 🌐
1. **Initial Deployment** (Current Focus)
   - ✅ Local development setup
   - 🏗️ Single server deployment on Hetzner
     - AX41 Dedicated Server setup
     - Docker containerization
     - Service configuration
   - Basic monitoring

2. **Production Setup**
   - SSL/TLS configuration
   - Cloudflare Free CDN
   - Backup system
   - Monitoring tools

3. **Future Scaling** (Only when needed)
   - Storage expansion
   - Service separation
   - Load balancing
   - Performance optimization

### Phase 6: Optimization & Scale 📈
- ✅ Resource usage optimization for long transcriptions
- ✅ Chunked transcription format standardization
- ✅ Multimodal recognition integration with chunked transcription
- Video compression improvements
- Cache configuration
- Performance monitoring
- Scale based on metrics

### Phase 7: Advanced Transcription & Recognition 🔊
- Improved chunk boundary detection using silence detection
- Enhanced error recovery for failed transcription chunks
- Real-time progress tracking for chunked transcription
- Adaptive chunk sizing based on audio content
- Automatic format validation for transcription data
- ✅ Enhanced speaker diarization integration with member ID preservation
- ✅ Improved face-to-voice correlation with confidence-based normalization

## Current Progress (as of May 25, 2025)

### Completed ✅
1. Project Structure
   - Directory layout
   - Core configuration
   - Database models
   - Dependencies installed
   - Documentation structure

2. Database Setup
   - PostgreSQL configured
   - Initial migrations
   - Base models created
   - Test database management

3. Authentication System
   - JWT-based authentication
   - Role-based access control (ADMIN, MP, STAFF)
   - User management endpoints
   - Password hashing with bcrypt
   - Comprehensive test coverage

4. Video Processing Pipeline
   - Enhanced video capture from Parliament TV with improved error handling
   - Support for multiple video stream formats (HLS, MP4, RTMP)
   - Better process management for video capture
   - Fixed database transaction issues in capture sessions
   - Video clip creation and editing
   - Transcription service integration
   - Storage management system with accurate real-time metrics
   - Multi-layered fallback mechanisms for storage breakdown calculations
   - Speaker attribution consistency across continuous speech segments
   - Speech group tracking for improved speaker identification
   - Enhanced speaker diarization with member ID preservation and normalization
   - Prioritization of high-confidence member IDs from facial recognition
   - Transparent data handling without synthetic fallbacks

5. Social Media Integration
   - Twitter, Facebook, and Instagram platforms
   - Post scheduling and analytics
   - Multi-platform posting
   - Background task processing
   - 🏗️ Speaker matching (in progress)
   - 🏗️ Voice profiles (in progress)
   - 🏗️ Facial profiles integration (in progress)

6. Frontend Implementation
   - Next.js with TypeScript setup
   - Authentication system with JWT
   - Video clip management interface
   - Capture session interface
   - Social media dashboard with robust error handling
   - Admin interface with real-time system metrics and logs
   - Storage management dashboard with accurate usage statistics
   - Responsive design with Tailwind CSS
   - Complete navigation system with all pages implemented
   - Placeholder pages for upcoming features
   - Consistent dark mode styling across all admin pages
   - Fixed navigation links and redirects
   - Improved error handling with null checks
   - **Note**: System logs page uses mock data (real API endpoint not yet available)

### In Progress 🏗️
1. Testing Infrastructure
   - ✅ Test database setup
   - ✅ Authentication tests
   - ✅ Video clip tests
   - 🏗️ Social media tests
   - 🏗️ Transcription tests
   - 🏗️ Storage management tests
   - 🏗️ Frontend component tests

2. Documentation & User Experience
   - ✅ Comprehensive README with troubleshooting guide
   - ✅ Structured ROADMAP with clear progress tracking
   - ✅ Navigation improvements with all links functional
   - 🏗️ User guides and training materials

3. Deployment Setup
   - 🏗️ Hetzner server configuration
   - ✅ Docker setup
   - ✅ Local development environment
   - 🏗️ Service deployment
   - 🏗️ Monitoring setup

4. Advanced Features
   - 🏗️ Custom branding tools
   - 🏗️ Batch processing
   - 🏗️ Advanced search capabilities

### Recent Achievements (May 2025)

1. Real Data Metrics Integration (May 25, 2025)
   - Implemented accurate storage breakdown metrics with multi-layered fallback mechanisms
   - Enhanced system logs with robust fallback options when Docker commands aren't available
   - Fixed Prometheus metrics endpoint to ensure proper scraping of system metrics
   - Updated admin dashboard to display real-time system data instead of placeholder values
   - Added resilient error handling to ensure the UI remains functional even when services are unavailable

2. Facial Recognition Improvements (May 24, 2025)
   - Fixed unidentified face image loading issues by implementing direct backend URL access
   - Added robust fallback mechanisms for different URL formats and capture ID patterns
   - Implemented intelligent face grouping to reduce duplicate faces in the UI
   - Enhanced UI for face display with improved dark mode support and full-image viewing
   - Optimized image loading with better error handling and placeholder fallbacks

2. Transcription Feature (May 1, 2025)
   - Implemented automatic transcription for Parliament TV videos using Whisper
   - Created backend API endpoints for managing transcriptions
   - Developed frontend interface for viewing and managing transcriptions
   - Added support for multiple output formats (TXT, SRT, JSON, DOCX)
   - Integrated with speaker identification for enhanced transcription accuracy
   - Added language selection support (English, Welsh, Irish, Scottish Gaelic)

2. Video Capture System (April 30, 2025)
   - Enhanced video capture functionality with improved error handling
   - Added support for multiple video stream formats (HLS, MP4)
   - Implemented better process management for video capture
   - Fixed database transaction issues in capture sessions
   - Created comprehensive documentation for video capture functionality
   - Identified and documented the Parliament TV stream URL format

2. Authentication System
   - Fixed redirect loop issues in authentication flow
   - Improved error handling for API requests
   - Enhanced token management for better security

3. Docker Environment
   - Completed Docker Compose setup for development
   - Configured services for local testing
   - Added documentation for Docker usage
   - Improved Docker development workflow with file synchronization guidance
   - Added troubleshooting steps for common Docker development issues

4. Documentation & Navigation
   - Created comprehensive troubleshooting guide in README
   - Added detailed video capture documentation
   - Structured ROADMAP with clear progress indicators
   - Implemented all missing pages for complete navigation
   - Added placeholder content for upcoming features

### Next Steps 📋

#### 1. Testing & Quality Assurance
   - Implement frontend component tests using Jest and React Testing Library
   - Complete API integration tests for social media, transcription, and storage management
   - Set up Cypress or Playwright for end-to-end testing of critical user workflows
   - Conduct performance testing to ensure the application can handle expected traffic

#### 2. Deployment Preparation
   - Order and configure Hetzner AX41 server (€69/month)
   - Set up CI/CD pipeline with GitHub Actions for automated testing and deployment
   - Finalize production Docker Compose configuration
   - Configure HTTPS with Let's Encrypt
   - Implement automated backup system for database and media files

#### 3. Monitoring & Maintenance
   - Set up Prometheus and Grafana for performance metrics
   - Implement Sentry or similar for error tracking
   - Configure centralized logging
   - Set up alerting for critical issues

#### 4. Remaining Features
   - ✅ System settings interface for application-wide configuration
   - ✅ Unidentified face display and management in recognition results
   - ⚠️ System logs viewer for administrators (frontend implemented with mock data)
     - Implement real backend API endpoint for system logs
     - Connect frontend to real API data
     - Add filtering and search capabilities
   - Custom branding tools for MPs
   - Advanced search with full-text capabilities for clips and transcriptions
   - Batch processing functionality for operations on multiple clips
   - Enhanced transcription features:
     - Basic transcription with Whisper integration
     - Transcription export to TXT format
     - Basic speaker diarization infrastructure
     - Speaker identification system:
       - Backend implementation complete with audio-based speaker separation
       - UI toggle for enabling speaker identification
       - Voice profile database structure established
       - Voice profile management interface for adding and managing speaker profiles
       - Audio sample upload and management for voice profiles
       - Integration with facial recognition for improved accuracy

### Speaker Diarization

### Overview
Speaker diarization is the process of partitioning an audio stream into segments according to who is speaking. The Parliament TV application implements advanced speaker diarization to identify different speakers in audio transcriptions, making it easier to follow debates and committee meetings.

### Features Implemented

- [x] **Voice Profile Management System**
  - Create and manage voice profiles for known speakers (MPs, ministers, etc.)
  - Upload and process audio samples for each profile
  - Calculate voice embeddings for speaker recognition
  - Store confidence scores based on sample quantity and quality

- [x] **Speaker Identification in Audio Transcription**
  - Identify known speakers using voice profiles
  - Detect speaker changes using Bayesian Information Criterion (BIC) segmentation
  - Maintain speaker continuity across segments with similar voice characteristics
  - Number unknown speakers consistently (Speaker 1, Speaker 2, etc.)

- [x] **UI for Managing Voice Profiles**
  - Admin interface for creating and editing voice profiles
  - Upload interface for adding audio samples to profiles
  - Display sample count and confidence scores

- [x] **Multi-modal Recognition**
  - Integrate with facial recognition for improved accuracy when video is available
  - Combine voice and face recognition results for higher confidence
  - Preserve highest confidence member IDs from facial recognition within speech groups
  - Normalize speaker IDs across continuous speech segments for consistent attribution

### Technical Implementation

#### Voice Profile Management
The system maintains a database of voice profiles in `/app/data/voice_profiles/profiles.json`. Each profile contains:
- Basic information (name, role, party)
- Voice embeddings generated from audio samples
- Confidence scores based on sample quantity

Audio samples are stored in `/app/data/voice_profiles/samples/[profile_id]/` and processed to extract MFCC features.

#### Speaker Diarization Algorithm
The diarization process uses multiple techniques:

1. **BIC Segmentation**: Detects speaker changes by comparing adjacent audio windows using Bayesian Information Criterion
2. **Voice Embedding Matching**: Compares voice characteristics with known profiles
3. **Speaker Continuity Logic**: Ensures segments with similar voice characteristics are assigned to the same speaker
4. **Facial Recognition Integration**: When video is available, uses face detection to confirm or improve voice matching
5. **Member ID Normalization**: Preserves numeric member IDs from facial recognition and applies the highest confidence ID to all segments in a speech group
6. **Transparent Data Handling**: Shows real data or clear error messages instead of fallbacks to maintain data integrity

#### Configuration Parameters
- `min_segment_duration`: Minimum duration between speaker changes (default: 1.0 seconds)
- `bic_lambda`: BIC penalty parameter for change detection sensitivity (default: 1.0)
- Voice similarity threshold: Threshold for considering segments from the same speaker (default: 0.8)

### Usage

1. **Creating Voice Profiles**:
   - Navigate to Admin > Voice Profiles
   - Click "Create New Profile" and enter speaker details
   - Upload at least 3-5 high-quality audio samples for each profile

2. **Transcribing with Speaker Identification**:
   - When starting a transcription, enable the "Speaker Identification" toggle
   - The system will attempt to identify speakers and mark segments accordingly
   - Known speakers will be labeled with their names
   - Unknown speakers will be labeled as "Speaker 1", "Speaker 2", etc.

### Future Improvements

#### Audio-Visual Integration (Current Priority)
- [ ] Connect facial recognition timestamps with voice recognition segments
- [ ] Implement unified timeline view showing both face detections and speaker segments
- [ ] Create correlation algorithm to match faces with voice segments based on timing
- [ ] Add confidence scoring for multi-modal matches (face+voice)
- [ ] Develop UI to display synchronized face and voice recognition results

#### Voice Recognition Enhancements
- [ ] Implement hierarchical clustering for improved speaker grouping
- [ ] Add adaptive threshold adjustment based on audio quality
- [ ] Implement speaker adaptation for improved recognition of specific speakers
- [ ] Add batch processing for voice profile training

#### Facial Recognition Enhancements
- [ ] Improve face clustering algorithm to better group similar faces
- [ ] Add face quality assessment to select the best representative image
- [ ] Implement face verification to confirm matches across different timestamps
- [ ] Add batch processing for face profile training

     - Transcription editing interface
     - Additional export formats (SRT, JSON, DOCX)
     - Real-time transcription updates during streaming
     - Advanced search within transcriptions
     - Custom parliamentary vocabulary for improved accuracy
     - Multi-language support with automatic language detection
     - Transcript comparison and version history
     - 🏗️ Transcript comparison and version history

#### 5. Documentation & Training
   - ✅ Comprehensive README with troubleshooting guide
   - ✅ Structured ROADMAP with clear progress tracking
   - ✅ Detailed video capture documentation
   - Create comprehensive user guides
   - Document administrative procedures
   - Complete OpenAPI/Swagger documentation
   - Prepare training materials for staff

## Technical Considerations

### Security
- OAuth2 authentication
- Role-based access control
- End-to-end encryption
- Regular security audits

### Scalability
- Microservices architecture
- Load balancing
- Auto-scaling
- CDN integration

### Monitoring
- Error tracking
- Performance monitoring
- Usage analytics
- System health checks

### Compliance
- GDPR compliance
- Data retention policies
- Privacy controls
- Audit trails

## Future Enhancements
- Mobile application
- Browser extension
- API for third-party integration
- Advanced analytics dashboard
- Machine learning improvements
- Additional social media platforms
- Custom branding templates
- Automated content moderation

For detailed deployment information, see [Deployment Guide](docs/deployment.md)

For a comprehensive overview of what's working with real data versus mock implementations, see [Implementation Status Report](docs/implementation_status.md)
