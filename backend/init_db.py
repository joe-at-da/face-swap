#!/usr/bin/env python3
"""
Database initialization script.
This script creates all the tables defined in the models.
"""

import os
import sys

# Add the parent directory to the path so we can import the backend package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy_utils import database_exists, create_database
from backend.db.base import Base
from backend.db.session import engine
from backend.core.config import settings

def init_db() -> None:
    """Initialize the database with all tables."""
    # Create database if it doesn't exist
    if not database_exists(settings.DATABASE_URL):
        create_database(settings.DATABASE_URL)
        print(f"Created database {settings.DATABASE_URL}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")

if __name__ == "__main__":
    print("Creating database tables...")
    init_db()
    print("Database initialization completed.")
