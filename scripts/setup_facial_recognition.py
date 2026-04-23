#!/usr/bin/env python3
"""
Setup Facial Recognition System

This script sets up the facial recognition system by:
1. Downloading sample MP photos
2. Creating MP profiles in the database
3. Generating face encodings
4. Updating the MP encodings database

Usage:
    python setup_facial_recognition.py

This will replace the fake data in mp_encodings.json with real MP profiles and encodings.
"""

import os
import sys
import subprocess
import logging
import json
from pathlib import Path
import requests
import shutil
import face_recognition
from datetime import datetime
import tempfile

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
logger = logging.getLogger("setup_facial_recognition")

# Constants
MP_PHOTOS_DIR = Path("/app/data/mp_photos")
MP_ENCODINGS_FILE = Path("/app/data/mp_encodings.json")

# Sample MP data with photo URLs
# These are public domain photos of UK politicians from Wikipedia
SAMPLE_MPS = [
    {
        "name": "Keir Starmer",
        "party": "Labour",
        "constituency": "Holborn and St Pancras",
        "parliament_id": "MP001",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Official_portrait_of_Keir_Starmer_crop_2.jpg/440px-Official_portrait_of_Keir_Starmer_crop_2.jpg"
    },
    {
        "name": "Rishi Sunak",
        "party": "Conservative",
        "constituency": "Richmond (Yorks)",
        "parliament_id": "MP002",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Official_portrait_of_Rishi_Sunak_crop_2.jpg/440px-Official_portrait_of_Rishi_Sunak_crop_2.jpg"
    },
    {
        "name": "Angela Rayner",
        "party": "Labour",
        "constituency": "Ashton-under-Lyne",
        "parliament_id": "MP003",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Official_portrait_of_Angela_Rayner_crop_2.jpg/440px-Official_portrait_of_Angela_Rayner_crop_2.jpg"
    },
    {
        "name": "Jeremy Hunt",
        "party": "Conservative",
        "constituency": "South West Surrey",
        "parliament_id": "MP004",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Official_portrait_of_Rt_Hon_Jeremy_Hunt_MP_crop_2.jpg/440px-Official_portrait_of_Rt_Hon_Jeremy_Hunt_MP_crop_2.jpg"
    },
    {
        "name": "Ed Davey",
        "party": "Liberal Democrats",
        "constituency": "Kingston and Surbiton",
        "parliament_id": "MP005",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Official_portrait_of_Sir_Edward_Davey_crop_2.jpg/440px-Official_portrait_of_Sir_Edward_Davey_crop_2.jpg"
    }
]

def ensure_directories():
    """Ensure required directories exist."""
    MP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

def download_photo(mp):
    """Download an MP photo from a URL."""
    try:
        # Create a safe filename from the MP name
        safe_name = mp["name"].lower().replace(" ", "_")
        filename = f"{safe_name}.jpg"
        
        # Destination path
        dest_path = MP_PHOTOS_DIR / filename
        
        # Download the photo with proper headers to avoid 403/400 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(mp["photo_url"], stream=True, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to download photo for {mp['name']}: HTTP {response.status_code}")
            return None
        
        # Save the photo
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded photo for {mp['name']} to {dest_path}")
        return dest_path
    except Exception as e:
        logger.exception(f"Error downloading photo for {mp['name']}: {str(e)}")
        return None

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

def create_mp_profile(mp, photo_path):
    """Create a new MP profile in the database."""
    try:
        # Generate face encoding
        face_encoding = generate_face_encoding(photo_path)
        
        if not face_encoding:
            logger.error(f"Failed to generate face encoding for {mp['name']}")
            return False
        
        # Create a database session
        db = SessionLocal()
        try:
            # Check if the speaker already exists
            existing_speaker = db.query(Speaker).filter(Speaker.name == mp["name"]).first()
            if existing_speaker:
                logger.info(f"MP profile for {mp['name']} already exists, updating...")
                
                # Update the existing speaker
                existing_speaker.party = mp.get("party")
                existing_speaker.constituency = mp.get("constituency")
                existing_speaker.parliament_id = mp.get("parliament_id")
                existing_speaker.photo_url = str(photo_path)
                existing_speaker.face_encoding = face_encoding
                existing_speaker.is_active = True
                
                db.commit()
                db.refresh(existing_speaker)
                
                logger.info(f"Updated MP profile for {mp['name']} with ID {existing_speaker.id}")
                return True
            
            # Create a new speaker
            speaker = Speaker(
                name=mp["name"],
                party=mp.get("party"),
                constituency=mp.get("constituency"),
                parliament_id=mp.get("parliament_id"),
                photo_url=str(photo_path),
                face_encoding=face_encoding,
                is_active=True
            )
            
            db.add(speaker)
            db.commit()
            db.refresh(speaker)
            
            logger.info(f"Created MP profile for {mp['name']} with ID {speaker.id}")
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
    logger.info("Setting up facial recognition system...")
    
    # Ensure required directories exist
    ensure_directories()
    
    # Download photos and create MP profiles
    success_count = 0
    
    for mp in SAMPLE_MPS:
        logger.info(f"Processing MP: {mp['name']}")
        
        # Download the photo
        photo_path = download_photo(mp)
        if not photo_path:
            logger.error(f"Failed to download photo for {mp['name']}, skipping...")
            continue
        
        # Create the MP profile
        if create_mp_profile(mp, photo_path):
            success_count += 1
    
    # Update the MP database
    if success_count > 0:
        logger.info(f"Successfully processed {success_count} MPs")
        
        if update_mp_database():
            logger.info("Facial recognition system setup completed successfully")
            
            # Display the contents of the MP encodings file
            try:
                with open(MP_ENCODINGS_FILE, "r") as f:
                    mp_data = json.load(f)
                    
                logger.info(f"MP encodings file now contains {len(mp_data.get('names', []))} MPs")
                
                # Print the names of the MPs
                if mp_data.get('names'):
                    logger.info(f"MPs in database: {', '.join(mp_data.get('names'))}")
            except Exception as e:
                logger.error(f"Error reading MP encodings file: {str(e)}")
        else:
            logger.error("Failed to update MP database")
    else:
        logger.error("Failed to process any MPs")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
