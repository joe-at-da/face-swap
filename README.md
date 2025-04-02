# Parliament Video Clip Manager

A comprehensive video clip management system for UK Members of Parliament to capture, edit, and share video clips from Parliament TV feeds.

## Features

- Video capture from Parliament TV feeds
- Video editing and clip creation
- Automated transcription and subtitling
- Face recognition and speaker detection
- Social media integration
- AI-powered content analysis
- Custom branding and watermarking
- Multi-platform publishing

## Project Structure

```
parliament-clips/
├── backend/               # FastAPI backend
│   ├── api/              # API endpoints
│   ├── core/             # Core functionality
│   ├── db/               # Database models
│   ├── services/         # Business logic
│   └── workers/          # Celery tasks
├── frontend/             # Next.js frontend
│   ├── components/       # React components
│   ├── pages/           # Next.js pages
│   └── public/          # Static assets
├── scripts/             # Utility scripts
└── tests/              # Test suites
```

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/your-org/parliament-clips.git
cd parliament-clips
```

2. Set up Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the development servers:

Backend:
```bash
cd backend
uvicorn main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Development

- Follow the [ROADMAP.md](ROADMAP.md) for development priorities
- Use feature branches and pull requests
- Write tests for new features
- Follow the project's coding standards

## Testing

```bash
pytest tests/
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
