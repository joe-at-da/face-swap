import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app

# Set test environment
os.environ["ENV_FILE"] = "tests/.env.test"

# Use test database URL
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/parliament_clips_test"
POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

# Create test engine with NullPool to avoid connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling
)

# Create sessionmaker
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(TestingSessionLocal)

def clear_db():
    """Clear all data from the test database."""
    print("\n=== Starting clear_db() ===")
    
    try:
        # Close any existing sessions
        print("Closing existing sessions...")
        Session.remove()
        engine.dispose()
        
        # Create a fresh connection to postgres database
        print("Creating fresh connection...")
        postgres_engine = create_engine(POSTGRES_URL, isolation_level='AUTOCOMMIT')
        postgres_conn = postgres_engine.connect()
        
        try:
            print("Terminating all other connections...")
            postgres_conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity 
                WHERE datname = 'parliament_clips_test'
                AND pid <> pg_backend_pid()
            """))
            
            print("Dropping and recreating database...")
            postgres_conn.execute(text("DROP DATABASE IF EXISTS parliament_clips_test"))
            postgres_conn.execute(text("CREATE DATABASE parliament_clips_test"))
            
        finally:
            postgres_conn.close()
            postgres_engine.dispose()
        
        # Create a new engine for the test database and create schema
        print("Creating tables...")
        test_engine = create_engine(SQLALCHEMY_DATABASE_URL, isolation_level='AUTOCOMMIT')
        Base.metadata.create_all(bind=test_engine)
        test_engine.dispose()
        
        print("=== Finished clear_db() ===\n")
    except Exception as e:
        print(f"Error in clear_db: {e}")
        raise e

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up test database once for the entire test session."""
    print("\n=== Setting up test database ===")
    try:
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        print("\n=== Tearing down test database ===")
        Session.remove()
        engine.dispose()

@pytest.fixture(scope="function")
def db():
    """Get a SQLAlchemy session for each test."""
    print("\n=== Creating new db session ===")
    Session.remove()  # Remove any existing session
    session = Session()
    try:
        yield session
    finally:
        print("\n=== Closing db session ===")
        session.close()
        Session.remove()

@pytest.fixture(scope="function", autouse=True)
def clean_db(db):
    """Ensure database is clean before each test."""
    print("\n=== Starting clean_db fixture ===")
    clear_db()
    try:
        yield
    finally:
        db.close()
        Session.remove()
    print("=== Finished clean_db fixture ===")

def override_get_db():
    """Override the get_db dependency for testing."""
    try:
        session = Session()
        yield session
    finally:
        session.close()
        Session.remove()

@pytest.fixture(scope="function")
def test_client():
    """Create a FastAPI TestClient."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
