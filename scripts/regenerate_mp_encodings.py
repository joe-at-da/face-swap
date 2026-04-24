#!/usr/bin/env python3
"""
Regenerate MP Encodings from Photos

This script regenerates MP face encodings from the MP photos using
the face_recognition library to ensure compatibility with the demo.
"""

import os
import sys
import cv2
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import face_recognition

def regenerate_encodings():
    """Regenerate MP encodings from photos."""
    photos_dir = Path("data/mp_photos")
    output_file = Path("data/mp_encodings_new.json")
    
    if not photos_dir.exists():
        logger.error(f"Photos directory not found: {photos_dir}")
        return False
    
    # Load member info from processed_members.json
    member_info = {}
    processed_file = photos_dir / "processed_members.json"
    if processed_file.exists():
        with open(processed_file, 'r') as f:
            members = json.load(f)
            # processed_members.json is a dict with UUIDs as keys
            for uuid, info in members.items():
                member_info[uuid] = uuid  # Use UUID as name for now
        logger.info(f"Loaded {len(member_info)} member IDs from processed_members.json")
    
    # Get all JPG files
    photo_files = list(photos_dir.glob("*.jpg"))
    logger.info(f"Found {len(photo_files)} MP photos")
    
    mp_data = {
        "ids": [],
        "names": [],
        "encodings": []
    }
    
    success_count = 0
    for i, photo_path in enumerate(photo_files):
        try:
            # Load image
            image = face_recognition.load_image_file(str(photo_path))
            
            # Detect faces
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                logger.warning(f"No face found in {photo_path.name}")
                continue
            
            # Use the first face
            face_encodings = face_recognition.face_encodings(image, face_locations)
            if not face_encodings:
                logger.warning(f"No encoding generated for {photo_path.name}")
                continue
            
            encoding = face_encodings[0].tolist()
            
            # Get MP ID and name
            mp_id = photo_path.stem
            
            # Try to get name from member_info
            if mp_id in member_info:
                name = member_info[mp_id]
            else:
                name = mp_id
            
            mp_data["ids"].append(mp_id)
            mp_data["names"].append(name)
            mp_data["encodings"].append(encoding)
            
            success_count += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1} photos, {success_count} successful")
        
        except Exception as e:
            logger.error(f"Error processing {photo_path.name}: {e}")
            continue
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(mp_data, f, indent=2)
    
    logger.info(f"✅ Regenerated {success_count} MP encodings")
    logger.info(f"Saved to: {output_file}")
    
    return True

if __name__ == "__main__":
    success = regenerate_encodings()
    if success:
        print("\n✅ MP encodings regenerated successfully!")
    else:
        print("\n❌ Failed to regenerate MP encodings")
