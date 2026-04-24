#!/usr/bin/env python3
"""
Load Proper MP Database

This script loads the proper MP database with 1318 MPs from the mp_encodings.json file.
"""

import os
import sys
import json
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import SessionLocal
from backend.db.models import FaceProfile

def load_proper_mp_database():
    """Load proper MP database with 1318 MPs."""
    encodings_file = Path("data/mp_encodings.json")
    
    if not encodings_file.exists():
        print(f"MP encodings file not found: {encodings_file}")
        return False
    
    print(f"Loading proper MP database from: {encodings_file}")
    
    with open(encodings_file, 'r') as f:
        data = json.load(f)
    
    ids = data['ids']
    names = data['names']
    encodings = data['encodings']
    
    print(f"Found {len(ids)} MPs in JSON file")
    
    session = SessionLocal()
    
    try:
        # Clear existing profiles
        session.query(FaceProfile).delete()
        session.commit()
        print("Cleared existing database")
        
        # Load all MPs
        for i in range(len(ids)):
            mp_id = ids[i]
            name = names[i]
            encoding = encodings[i]
            
            # Create MP profile
            mp_profile = FaceProfile(
                name=name,
                role="MP",
                party="Unknown",
                face_encoding=json.dumps(encoding),
                confidence_score=0.9
            )
            session.add(mp_profile)
            
            if (i + 1) % 100 == 0:
                print(f"Loaded {i + 1} MPs...")
        
        session.commit()
        print(f"✅ Successfully loaded {len(ids)} MP profiles to database")
        
        # Verify
        total_profiles = session.query(FaceProfile).count()
        print(f"Total MP profiles in database: {total_profiles}")
        
        # Show sample MPs
        sample_profiles = session.query(FaceProfile).limit(5).all()
        print("Sample MPs:")
        for profile in sample_profiles:
            print(f"  - {profile.name}")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error loading MP database: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = load_proper_mp_database()
    if success:
        print("\n✅ Proper MP database loaded successfully!")
    else:
        print("\n❌ Failed to load proper MP database")
