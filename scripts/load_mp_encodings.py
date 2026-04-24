#!/usr/bin/env python3
"""
Load MP Encodings from JSON to Database

This script loads MP encodings from the existing mp_encodings.json file
into the database to enable speaker identification.
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

def load_mp_encodings():
    """Load MP encodings from JSON file to database."""
    encodings_file = Path("data/mp_encodings.json")
    
    if not encodings_file.exists():
        print(f"MP encodings file not found: {encodings_file}")
        return False
    
    print(f"Loading MP encodings from: {encodings_file}")
    
    with open(encodings_file, 'r') as f:
        mp_data = json.load(f)
    
    print(f"Found {len(mp_data)} MP entries in JSON file")
    
    session = SessionLocal()
    loaded_count = 0
    
    try:
        for mp_id, encoding in mp_data.items():
            # Check if MP already exists
            existing = session.query(FaceProfile).filter_by(name=str(mp_id)).first()
            
            if not existing:
                # Create new MP profile
                mp_profile = FaceProfile(
                    name=str(mp_id),
                    role="MP",
                    party="Unknown",
                    face_encoding=json.dumps(encoding),
                    confidence_score=0.9
                )
                session.add(mp_profile)
                loaded_count += 1
                print(f"Added MP: {mp_id}")
            else:
                print(f"MP already exists: {mp_id}")
        
        session.commit()
        print(f"✅ Successfully loaded {loaded_count} MP profiles to database")
        
        # Verify
        total_profiles = session.query(FaceProfile).count()
        print(f"Total MP profiles in database: {total_profiles}")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error loading MP encodings: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = load_mp_encodings()
    if success:
        print("\n✅ MP encodings loaded successfully!")
    else:
        print("\n❌ Failed to load MP encodings")
