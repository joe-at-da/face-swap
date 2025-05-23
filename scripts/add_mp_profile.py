#!/usr/bin/env python3
"""
Add MP Profile Script

This script adds a new MP profile to the database and generates face encodings
from a provided photo. It's designed to help set up the facial recognition system
with real MP data rather than using fake data.

Usage:
    python add_mp_profile.py --name "MP Name" --photo /path/to/photo.jpg [--party "Party Name"] [--constituency "Constituency"]

Example:
    python add_mp_profile.py --name "John Smith" --photo /app/data/mp_photos/john_smith.jpg --party "Labour" --constituency "London"
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import face_recognition
import json
import shutil
from datetime import datetime
import requests
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.db.session import SessionLocal
    from backend.db.models import Speaker
    from backend.services.recognition.facial_recognition import FacialRecognitionService
except ImportError:
    print("Error: Could not import backend modules. Make sure you're running this script from the project root.")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("add_mp_profile")

# Constants
MP_PHOTOS_DIR = Path("/app/data/mp_photos")
MP_ENCODINGS_FILE = Path("/app/data/mp_encodings.json")

def ensure_directories():
    """Ensure required directories exist."""
    MP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

def copy_photo(photo_path, mp_name):
    """Copy the photo to the MP photos directory."""
    # Create a safe filename from the MP name
    safe_name = mp_name.lower().replace(" ", "_")
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    
    # Destination path
    dest_path = MP_PHOTOS_DIR / filename
    
    # Copy the photo
    shutil.copy(photo_path, dest_path)
    
    return dest_path

def generate_face_encoding(image_path):
    """Generate a face encoding from an image file."""
    try:
        # Load the image
        image = face_recognition.load_image_file(str(image_path))
        
        # Find all faces in the image
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            logger.error(f"No faces detected in {image_path}")
            return None
        
        # If multiple faces are detected, use the largest one
        if len(face_locations) > 1:
            logger.warning(f"Multiple faces detected in {image_path}, using the largest one")
            
            # Find the largest face by area
            largest_area = 0
            largest_face_idx = 0
            
            for i, (top, right, bottom, left) in enumerate(face_locations):
                area = (bottom - top) * (right - left)
                if area > largest_area:
                    largest_area = area
                    largest_face_idx = i
            
            # Get encoding for the largest face
            face_encodings = face_recognition.face_encodings(image, [face_locations[largest_face_idx]])
        else:
            # Get encoding for the single face
            face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if not face_encodings:
            logger.error(f"Failed to generate face encoding for {image_path}")
            return None
        
        # Return the first face encoding
        return face_encodings[0].tolist()
        
    except Exception as e:
        logger.error(f"Error generating face encoding: {str(e)}")
        return None

def create_mp_profile(name, photo_path, party=None, constituency=None, parliament_id=None):
    """Create a new MP profile in the database."""
    try:
        # Copy the photo to the MP photos directory
        dest_path = copy_photo(photo_path, name)
        
        # Generate face encoding
        face_encoding = generate_face_encoding(dest_path)
        
        if not face_encoding:
            logger.error(f"Failed to generate face encoding for {name}")
            return False
        
        # Create a database session
        db = SessionLocal()
        try:
            # Create a new speaker
            speaker = Speaker(
                name=name,
                party=party,
                constituency=constituency,
                parliament_id=parliament_id,
                photo_url=str(dest_path),
                face_encoding=face_encoding,
                is_active=True
            )
            
            db.add(speaker)
            db.commit()
            db.refresh(speaker)
            
            logger.info(f"Created MP profile for {name} with ID {speaker.id}")
            
            # Update the MP encodings file
            update_mp_database()
            
            return True
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error creating MP profile: {str(e)}")
        return False

def update_mp_database():
    """Update the MP database with the latest face encodings."""
    try:
        facial_recognition_service = FacialRecognitionService()
        result = facial_recognition_service.update_mp_database()
        
        if result.get("success"):
            logger.info("MP database updated successfully")
            return True
        else:
            logger.error(f"Failed to update MP database: {result.get('error')}")
            return False
    except Exception as e:
        logger.exception(f"Error updating MP database: {str(e)}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Add an MP profile to the database")
    parser.add_argument("--name", required=True, help="MP name")
    parser.add_argument("--photo", required=True, help="Path to MP photo")
    parser.add_argument("--party", help="Political party")
    parser.add_argument("--constituency", help="Constituency")
    parser.add_argument("--parliament-id", help="Parliament ID")
    
    args = parser.parse_args()
    
    # Ensure required directories exist
    ensure_directories()
    
    # Check if the photo exists
    if not os.path.exists(args.photo):
        logger.error(f"Photo not found: {args.photo}")
        return 1
    
    # Create the MP profile
    success = create_mp_profile(
        name=args.name,
        photo_path=args.photo,
        party=args.party,
        constituency=args.constituency,
        parliament_id=args.parliament_id
    )
    
    if success:
        logger.info(f"MP profile for {args.name} created successfully")
        return 0
    else:
        logger.error(f"Failed to create MP profile for {args.name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
