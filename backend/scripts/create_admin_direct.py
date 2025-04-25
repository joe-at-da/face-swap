#!/usr/bin/env python3
"""
Script to create a default admin user for the Parliament Video Clip Manager
using direct SQL queries to avoid ORM circular dependencies
"""
import sys
import os
from pathlib import Path
import uuid
from datetime import datetime

# Add the parent directory to the path so we can import the backend modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from backend.core.config import settings
from backend.core.security import get_password_hash

def create_admin_user(engine, email, password):
    """Create an admin user with the given email and password using direct SQL."""
    # We'll let the database generate the ID (auto-increment)
    hashed_password = get_password_hash(password)
    created_at = datetime.utcnow()
    
    # Check if user already exists
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        )
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"User with email {email} already exists.")
            return
        
        # Insert new admin user
        conn.execute(
            text("""
            INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES (:email, :hashed_password, :full_name, :role, :is_active, :created_at, :created_at)
            """),
            {
                "email": email,
                "hashed_password": hashed_password,
                "full_name": "Admin User",
                "role": "admin",
                "is_active": True,
                "created_at": created_at
            }
        )
        conn.commit()
        
        print(f"Admin user created successfully with email: {email}")

def main():
    # Default credentials
    default_email = "admin@parliament.uk"
    default_password = "admin123"
    
    # Allow overriding via command line arguments
    if len(sys.argv) > 1:
        default_email = sys.argv[1]
    if len(sys.argv) > 2:
        default_password = sys.argv[2]
    
    # Create database connection
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost/parliament_clips")
    engine = create_engine(db_url)
    
    create_admin_user(engine, default_email, default_password)

if __name__ == "__main__":
    main()
