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
- Resource usage optimization
- Video compression improvements
- Cache configuration
- Performance monitoring
- Scale based on metrics

## Current Progress (as of April 30, 2025)

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
   - Storage management system

5. Social Media Integration
   - Twitter, Facebook, and Instagram platforms
   - Post scheduling and analytics
   - Multi-platform posting
   - Background task processing

6. Frontend Implementation
   - Next.js with TypeScript setup
   - Authentication system with JWT
   - Video clip management interface
   - Capture session interface
   - Social media dashboard
   - Admin interface for user and storage management
   - Responsive design with Tailwind CSS
   - Complete navigation system with all pages implemented
   - Placeholder pages for upcoming features

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

1. Transcription Feature (May 1, 2025)
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
   - System settings interface for application-wide configuration
   - System logs viewer for administrators
   - Custom branding tools for MPs
   - Advanced search with full-text capabilities for clips and transcriptions
   - Batch processing functionality for operations on multiple clips
   - Enhanced transcription features:
     - ✅ Basic transcription with Whisper integration
     - ✅ Transcription export to TXT format
     - ✅ Basic speaker diarization infrastructure
     - ✅ Speaker identification system:
       - ✅ Backend implementation complete with audio-based speaker separation
       - ✅ UI toggle for enabling speaker identification
       - ✅ Voice profile database structure established
       - ✅ Voice profile management interface for adding and managing speaker profiles
       - ✅ Audio sample upload and management for voice profiles
       - ✅ Integration with facial recognition for improved accuracy
     - 🏗️ Transcription editing interface
     - 🏗️ Additional export formats (SRT, JSON, DOCX)
     - 🏗️ Real-time transcription updates during streaming
     - 🏗️ Advanced search within transcriptions
     - 🏗️ Custom parliamentary vocabulary for improved accuracy
     - 🏗️ Multi-language support with automatic language detection
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
