# Parliament Video Clip Manager

A powerful application for UK Members of Parliament to capture, edit, and share video clips from Parliament TV feeds. Features automated transcription, branding, and multi-platform sharing capabilities.

![Project Status](https://img.shields.io/badge/status-beta-blue) ![Version](https://img.shields.io/badge/version-0.9.0-green)

## Features

- 📹 Video capture from Parliament TV feeds
- ✂️ Easy clip editing and branding
- 🎯 Face recognition and tagging
- 🔊 Automated transcription and subtitling
- 🚀 Multi-platform social media sharing
- 🤖 AI-driven content analysis
- 🔐 Role-based access control (ADMIN, MP, STAFF)
- 🔑 JWT-based authentication
- 🧪 Comprehensive test coverage

## Tech Stack

- **Backend**: FastAPI, PostgreSQL, Redis, Celery
- **Video Processing**: OpenCV, FFmpeg, MoviePy
- **AI/ML**: TensorFlow, PyTorch, Whisper
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
- [Authentication](docs/authentication.md) - Auth system and user roles
- [Technical Roadmap](ROADMAP.md) - Project roadmap and phases
- [Deployment Guide](docs/deployment.md) - Production deployment

## Development

### Running the Application

```bash
# Start backend server
./scripts/manage_server.sh

# Debug mode with increased logging
./scripts/manage_server.sh debug

# Start frontend development server (in a separate terminal)
cd frontend
npm run dev
```

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

Currently in Beta phase with all core features implemented. Both backend and frontend components are complete and ready for deployment. See [ROADMAP.md](ROADMAP.md) for detailed progress and next steps.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.
