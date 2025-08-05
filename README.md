# Parliament Video Clip Manager

*Updated: August 5, 2025 by Joe Bradley (joe@veedoo.io)*

A powerful application for UK Members of Parliament to capture, edit, and share video clips from Parliament TV feeds. Features automated transcription, branding, and multi-platform sharing capabilities.

![Project Status](https://img.shields.io/badge/status-beta-blue) ![Version](https://img.shields.io/badge/version-0.9.0-green)

## Features

- 📹 Video capture from Parliament TV feeds
- 🎭 Facial recognition-powered Parliament TV capture
- ✂️ Easy clip editing and branding
- 🎯 Face recognition and tagging
- 🔊 Automated transcription and subtitling with chunked processing for long recordings
- 🚀 Multi-platform social media sharing
- 🤖 AI-driven content analysis
- 🔐 Role-based access control (ADMIN, MP, STAFF)
- 🔑 JWT-based authentication
- 🧪 Comprehensive test coverage

## Tech Stack

- **Backend**: FastAPI, PostgreSQL, Redis, Celery
- **Video Processing**: OpenCV, FFmpeg, MoviePy
- **AI/ML**: TensorFlow, PyTorch, Whisper (with chunked processing for long recordings)
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Authentication**: JWT, bcrypt
- **Testing**: pytest, TestClient

## Quick Start

1. **Prerequisites**
   - Python 3.11+
   - PostgreSQL 14
   - Redis
   - FFmpeg
   - Node.js 18+
   - npm 9+

2. **Backend Installation**
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/the-mp.git
   cd the-mp

   # Set up Python environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with your settings

   # Create databases
   createdb parliament_clips
   createdb parliament_clips_test  # for testing
   ```

3. **Frontend Installation**
   ```bash
   # Navigate to frontend directory
   cd frontend

   # Install dependencies
   npm install

   # Configure environment
   cp .env.example .env.local
   # Edit .env.local with your settings
   ```

## Documentation

- [Setup Guide](docs/setup_guide.md) - Detailed installation and configuration
- [Database Management](docs/database_management.md) - Database setup, rebuild, and SQL IDE connections
- [Authentication](docs/authentication.md) - Auth system and user roles
- [Video Capture](docs/video_capture.md) - Video capture functionality and configuration
- [Transcription](docs/transcription.md) - Transcription functionality and configuration
- [Chunked Transcription](docs/chunked_transcription.md) - Long audio transcription processing
- [API Guide](docs/api_guide.md) - Complete API documentation including endpoints and authentication
- [Technical Roadmap](ROADMAP.md) - Project roadmap and phases
- [Deployment Guide](docs/deployment.md) - Production deployment

### API Authentication

The application supports two authentication methods:

1. **JWT Authentication** - For user-facing web application and dashboard access
   - Used for most API endpoints
   - Requires login with username/password to obtain access token
   - Include token in `Authorization: Bearer {token}` header

2. **API Key Authentication** - For integration with external systems
   - Used for integration API endpoints and media file access
   - Requires API key configured in environment variable `INTEGRATION_API_KEY`
   - Include API key in `X-API-Key: {api_key}` header
   - All integration endpoints use the `/api/v1/` URL prefix
   - Media files can be accessed via `/api/v1/media/file` endpoint with API key

For detailed API documentation and examples, see the [API Guide](docs/api_guide.md) and Postman collections in the `docs` directory.

## Development

### Running the Application

#### Method 1: Docker Setup (Recommended)

```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop all services
docker-compose -f docker-compose.dev.yml down
```

Once both servers are running:
1. Open your browser and navigate to http://localhost:3000
2. Log in with your credentials
3. Explore the application features:
   - Dashboard: System statistics and quick actions
   - Video Clips: Browse, create, edit clips
   - Capture: Manage Parliament TV capture sessions
   - Parliament TV: Capture Parliament TV streams with facial recognition
   - Social Media: Create and schedule posts
   - Admin: Manage users and storage

### Troubleshooting Guide

#### Docker Environment Troubleshooting

1. **Restarting Services**
   ```bash
   # Restart a specific service
   docker-compose -f docker-compose.dev.yml restart frontend
   docker-compose -f docker-compose.dev.yml restart app
   
   # Restart all services
   docker-compose -f docker-compose.dev.yml restart
   ```

2. **Rebuilding Services**
   ```bash
   # Rebuild and restart a specific service
   docker-compose -f docker-compose.dev.yml up -d --build app
   docker-compose -f docker-compose.dev.yml up -d --build frontend
   ```

3. **Syncing New Files with Docker Containers**
   When adding new Python modules or files to the backend, ensure they are properly synced with Docker containers:
   
   ```bash
   # Option 1: Use volume mounts in docker-compose.dev.yml (recommended for development)
   # Add this to the app service in docker-compose.dev.yml:
   # volumes:
   #   - ./backend:/app/backend
   
   # Option 2: Copy new files into the container
   docker-compose -f docker-compose.dev.yml exec app mkdir -p /app/backend/path/to/new/directory
   docker-compose -f docker-compose.dev.yml exec app bash -c "cat > /app/backend/path/to/new/file.py" < local_file.py
   
   # Option 3: Rebuild the container (slower but ensures all files are included)
   docker-compose -f docker-compose.dev.yml up -d --build app
   ```

3. **Viewing Logs**
   ```bash
   # View logs for all services
   docker-compose -f docker-compose.dev.yml logs -f
   
   # View logs for a specific service
   docker-compose -f docker-compose.dev.yml logs -f frontend
   
   # View last 50 lines of logs
   docker-compose -f docker-compose.dev.yml logs --tail=50 frontend
   ```

4. **Running Commands Inside Containers**
   ```bash
   # Install a package in the frontend container
   docker-compose -f docker-compose.dev.yml exec frontend npm install @tailwindcss/postcss --save
   
   # Run tests in the app container
   docker-compose -f docker-compose.dev.yml run --rm app pytest backend/tests/api/v1/test_capture.py -v
   ```

5. **Authentication Issues**
   - If you encounter redirect loops between login and dashboard:
     - Check browser console for authentication errors
     - Ensure the `isAuthenticated` flag is properly set in sessionStorage
     - Clear browser storage (localStorage and sessionStorage) and try again
   - If API endpoints return 401 errors:
     - Verify your token is valid and not expired
     - Check that the token is properly set in API requests

#### Direct Run Troubleshooting

1. **Frontend Issues**
   - Make sure all dependencies are installed:
     ```bash
     cd frontend
     npm install
     ```
   - If you see Tailwind CSS errors, check that your PostCSS configuration is correct:
     ```javascript
     // frontend/postcss.config.js
     module.exports = {
       plugins: {
         tailwindcss: {},
         autoprefixer: {},
       },
     }
     ```
   - Ensure your Tailwind configuration has the correct color definitions:
     ```javascript
     // frontend/tailwind.config.js
     /** @type {import('tailwindcss').Config} */
     module.exports = {
       // ... other config
       theme: {
         extend: {
           colors: {
             primary: {
               DEFAULT: "#0076C0", // Parliament blue
               dark: "#005A8E",
               light: "#3D9AD1",
             },
             // ... other colors
           },
         },
       },
     }
     ```

2. **Backend Issues**
   - Restart the backend server:
     ```bash
     ./scripts/manage_server.sh
     ```
   - Run in debug mode for more verbose logging:
     ```bash
     ./scripts/manage_server.sh debug
     ```
   - Check database connection settings in `.env`

### What's Running in Docker

When you start the application with Docker Compose, the following services are available:

- **Backend API (FastAPI)** - http://localhost:8000
  - API Documentation: http://localhost:8000/docs
- **Frontend (Next.js)** - http://localhost:3000
- **PostgreSQL database** - (Internal to Docker network)
- **Redis** for caching and message queues - (Internal to Docker network)
- **Celery worker** for background tasks - (Internal to Docker network)
- **Prometheus** for metrics collection - http://localhost:9090
- **Grafana** for monitoring dashboards - http://localhost:3001

#### Method 2: Direct Run

If you prefer to run the services directly without Docker:

```bash
# Terminal 1: Start backend server
./scripts/manage_server.sh

# Debug mode with increased logging (optional)
# ./scripts/manage_server.sh debug

# Terminal 2: Start frontend development server
cd frontend
npm install  # Ensure all dependencies are installed
npm run dev
```

The Docker setup includes:
- Backend API (FastAPI)
- Frontend (Next.js)
- PostgreSQL database
- Redis for caching and queues
- Celery worker for background tasks
- Prometheus and Grafana for monitoring

### Building for Production

```bash
# Build backend Docker image
docker build -t parliament-clips-backend -f Dockerfile.backend .

# Build frontend
cd frontend
npm run build
```

### Testing
```bash
# Run all tests
pytest -v

# Run specific test modules
pytest tests/test_auth_endpoints.py -v

# Run with coverage
pytest --cov=backend tests/
```

## Development Status

The Parliament Video Clip Manager has reached beta status with all core features implemented. Both backend and frontend components are complete and ready for deployment.

### Current Status (May 25, 2025)

1. **Backend**
   - ✅ FastAPI server with all endpoints implemented
   - ✅ Authentication system with JWT and RBAC
   - ✅ Video processing pipeline
   - ✅ Improved video capture functionality
   - ✅ Parliament TV capture with facial recognition
   - ✅ Automatic transcription with Whisper integration
   - ⚠️ Social media integration (in progress - speaker matching, voice and facial profiles pending)
   - ✅ Storage management with real-time metrics
   - ✅ System logs with fallback mechanisms
   - ✅ Prometheus metrics integration

2. **Frontend**
   - ✅ Next.js with TypeScript implementation
   - ✅ Video clip management interface
   - ✅ Capture session interface
   - ✅ Parliament TV capture interface
   - ✅ Transcription interface for viewing and managing transcriptions
   - ⚠️ Social media dashboard (speaker matching, voice and facial profiles in progress)
   - ✅ Admin interface with real-time system metrics and logs
   - ✅ Storage management dashboard with accurate usage statistics
   - ✅ Authentication and authorization flows

### Project Roadmap

For detailed information about the project roadmap, including completed milestones, current work, and future plans, please see the [ROADMAP.md](ROADMAP.md) file.

### Recent Achievements

1. **Real Data Metrics Integration**
   - Implemented accurate storage breakdown metrics with multi-layered fallback mechanisms
   - Enhanced system logs with robust fallback options when Docker commands aren't available
   - Fixed Prometheus metrics endpoint to ensure proper scraping of system metrics
   - Updated admin dashboard to display real-time system data instead of placeholder values
   - Added resilient error handling to ensure the UI remains functional even when services are unavailable

2. **Video Capture System**
   - Enhanced video capture functionality with improved error handling
   - Added support for multiple video stream formats (HLS, MP4)
   - Implemented Parliament TV capture with facial recognition
   - Implemented better process management for video capture
   - Fixed database transaction issues in capture sessions
   - Added comprehensive documentation for video capture functionality

3. **Authentication System**
   - Resolved redirect loop issues between login and dashboard
   - Implemented proper token storage and validation
   - Added graceful handling of API errors

4. **Docker Environment**
   - Completed Docker Compose setup for all services
   - Configured monitoring with Prometheus and Grafana
   - Added development convenience commands
   - **Important Note**: When adding new files or modules to the backend, ensure they are properly synced with Docker containers. Use volume mounts in development or rebuild containers after adding new files.

4. **Documentation**
   - Comprehensive README with setup instructions
   - Added detailed [video capture documentation](docs/video_capture.md)
   - Added [Parliament TV integration guide](docs/parliament_tv_integration.md)
   - Added [Transcription feature documentation](docs/transcription.md)
   - Troubleshooting guide for common issues
   - API documentation with Swagger UI

See [ROADMAP.md](ROADMAP.md) for more detailed development plans.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.
