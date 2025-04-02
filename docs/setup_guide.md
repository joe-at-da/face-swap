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

### User
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STAFF)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
```

### VideoClip
```python
class VideoClip(Base):
    __tablename__ = "video_clips"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    source_url = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    status = Column(Enum(ClipStatus), nullable=False, default=ClipStatus.DRAFT)
    s3_key = Column(String)
    transcription = Column(String)
    faces_detected = Column(JSON)
    clip_metadata = Column(JSON, default={})
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### SocialPost
```python
class SocialPost(Base):
    __tablename__ = "social_posts"
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("video_clips.id"), nullable=False)
    platform = Column(Enum(SocialPlatform), nullable=False)
    status = Column(Enum(PostStatus), nullable=False, default=PostStatus.PENDING)
    post_id = Column(String)
    posted_at = Column(DateTime)
    post_url = Column(String)
    engagement_metrics = Column(JSON, default={})
    post_metadata = Column(JSON, default={})
```

## Testing

### Setting Up Test Environment

1. Create test database:
```bash
/opt/homebrew/opt/postgresql@14/bin/createdb parliament_clips_test
```

2. Configure test settings in `.env`:
```env
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/parliament_clips_test
```

### Running Tests

1. Run all tests:
```bash
pytest -v
```

2. Run specific test files:
```bash
# Auth tests
pytest tests/test_auth_endpoints.py -v

# Other test modules
pytest tests/test_clips.py -v
pytest tests/test_social.py -v
```

3. Run with coverage:
```bash
pytest --cov=backend tests/
```

### Test Database Management

The test suite includes automatic database management:
- Cleans up test database before each test
- Creates fresh tables for each test
- Handles test user creation and cleanup
- Manages database connections properly

### Writing Tests

1. Use provided fixtures:
```python
def test_example(test_client, db, clean_db):
    # test_client: FastAPI TestClient
    # db: SQLAlchemy Session
    # clean_db: Ensures fresh database
    ...
```

2. Create test users:
```python
# Create admin user
admin = create_test_admin(db)

# Create MP user
mp = create_test_mp(db)
```

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

## Additional Documentation

- [Authentication System](authentication.md) - Detailed auth system documentation
- [Deployment Guide](deployment.md) - Production deployment instructions
