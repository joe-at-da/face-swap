# Testing Guide

This guide covers the testing setup and procedures for the Parliament Video Clip Manager.

## Test Structure

Tests are organized in the `backend/tests` directory:

```
backend/tests/
├── api/
│   └── v1/
│       ├── test_auth.py       # Authentication tests
│       ├── test_capture.py    # Video capture endpoint tests
│       └── test_clips.py      # Video clip management tests
├── services/
│   ├── test_capture.py        # Video capture service tests
│   └── test_storage.py        # Storage management tests
└── conftest.py               # Test configuration and fixtures
```

## Test Setup

### Prerequisites

- Docker and Docker Compose installed
- Access to test database (automatically created by test fixtures)

### Configuration

Tests use a separate database URL defined in environment variables:
```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@db:5432/test_parliament_clips
```

The test configuration is handled by `conftest.py`, which:
- Creates a test database for each test session
- Sets up database migrations
- Provides fixtures for database sessions and API client
- Cleans up after tests complete

## Running Tests

### Run All Tests
```bash
docker-compose -f docker-compose.dev.yml run --rm app pytest
```

### Run Specific Test Files
```bash
docker-compose -f docker-compose.dev.yml run --rm app pytest backend/tests/api/v1/test_capture.py
```

### Run with Verbosity
```bash
docker-compose -f docker-compose.dev.yml run --rm app pytest -v
```

## Key Test Areas

### 1. Video Capture Tests
- Start/stop capture sessions
- Capture status monitoring
- Error handling for concurrent captures
- Stream URL validation

### 2. Video Clip Tests
- Clip creation from capture sessions
- Clip metadata management
- Storage cleanup
- Access control

### 3. Authentication Tests
- User login/logout
- JWT token validation
- Role-based access control
- Session management

## Database Migrations

Migrations are handled by Alembic and are located in `backend/alembic/versions/`.

### Key Migrations
1. `001_add_video_tables.py`
   - Creates `capture_sessions` table
   - Creates `video_clips` table
   - Sets up relationships and indexes

### Running Migrations
```bash
# Apply all migrations
docker-compose -f docker-compose.dev.yml run --rm app alembic upgrade head

# Create a new migration
docker-compose -f docker-compose.dev.yml run --rm app alembic revision -m "description"
```

### Test Data
Test fixtures provide sample data for:
- Users with different roles
- Capture sessions in various states
- Video clips with different metadata

## Best Practices

1. **Isolation**: Each test should be independent and clean up after itself
2. **Mocking**: Use mocks for external services (FFmpeg, storage)
3. **Fixtures**: Reuse fixtures for common setup
4. **Cleanup**: Always clean up test files and database records
5. **Coverage**: Aim for comprehensive test coverage of critical paths
