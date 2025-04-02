# Parliament Video Clip Manager

A powerful application for UK Members of Parliament to capture, edit, and share video clips from Parliament TV feeds. Features automated transcription, branding, and multi-platform sharing capabilities.

## Features

- 📹 Video capture from Parliament TV feeds
- ✂️ Easy clip editing and branding
- 🎯 Face recognition and tagging
- 🔊 Automated transcription and subtitling
- 🚀 Multi-platform social media sharing
- 🤖 AI-driven content analysis

## Tech Stack

- **Backend**: FastAPI, PostgreSQL, Redis, Celery
- **Video Processing**: OpenCV, FFmpeg, MoviePy
- **AI/ML**: TensorFlow, PyTorch, Whisper
- **Frontend**: Next.js, TypeScript, Tailwind CSS

## Quick Start

1. **Prerequisites**
   - Python 3.11+
   - PostgreSQL 14
   - Redis
   - FFmpeg

2. **Installation**
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
   ```

For detailed setup instructions, see our [Setup Guide](docs/setup_guide.md).

## Documentation

- [Setup Guide](docs/setup_guide.md) - Detailed installation and configuration instructions
- [Technical Roadmap](ROADMAP.md) - Project roadmap and development phases

## Development Status

Currently in Phase 1 of development. See [ROADMAP.md](ROADMAP.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.
