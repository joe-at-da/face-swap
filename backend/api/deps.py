from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.core.config import get_settings

settings = get_settings()

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Add more dependencies as needed (e.g., get_current_user)
