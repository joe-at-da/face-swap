# Parliament Video Clip Manager - Setup Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 14
- Redis (for caching and job queues)
- FFmpeg (for video processing)

## Initial Setup

### 1. Database Setup

```bash
# Install PostgreSQL 14 (macOS)
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Create postgres user and set password
/opt/homebrew/opt/postgresql@14/bin/createuser -s postgres
/opt/homebrew/opt/postgresql@14/bin/psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# Create database
/opt/homebrew/opt/postgresql@14/bin/createdb parliament_clips
```

### 2. Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Update the following variables in `.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Your secret key for JWT
- Other API keys as needed

### 4. Database Migrations

```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## Development Server

### Running the Server

You can run the development server in two ways:

1. Using the management script directly:
   ```bash
   # Normal mode
   ./scripts/manage_server.sh

   # Debug mode with increased logging
   ./scripts/manage_server.sh debug
   ```

2. Using VSCode tasks (recommended):
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Type "Tasks: Run Task"
   - Select either:
     - "Start Server" for normal mode
     - "Start Server (Debug)" for debug mode with increased logging

The management script will automatically:
- Kill any existing process running on port 8000
- Start a new server instance on port 8000
- Enable auto-reload for development

## Project Structure

```
the-mp/
├── alembic/              # Database migrations
├── backend/
│   ├── core/            # Core functionality
│   │   └── config.py    # Configuration settings
│   └── db/              # Database models and utilities
│       └── models.py    # SQLAlchemy models
├── docs/                # Documentation
├── requirements.txt     # Python dependencies
├── .env.example        # Example environment variables
└── README.md           # Project overview
```

## Database Models

The project uses SQLAlchemy with the following models:

1. `User`: Manages user accounts and authentication
2. `VideoClip`: Stores video clip metadata and processing information
3. `SocialPost`: Tracks social media sharing status and metadata

## Next Steps

After completing the setup:
1. Start implementing the FastAPI server
2. Set up video capture system
3. Implement user authentication
4. Add video processing capabilities

## Troubleshooting

### Common Issues

1. PostgreSQL Connection Issues
   - Ensure PostgreSQL service is running
   - Verify database credentials in `.env`
   - Check if postgres user exists

2. Migration Issues
   - Make sure database exists
   - Check if alembic.ini is properly configured
   - Verify models are properly imported in env.py
