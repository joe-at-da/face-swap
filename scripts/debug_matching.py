#!/usr/bin/env python3
"""Debug face matching issue."""

import json
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import SessionLocal
from backend.db.models import FaceProfile

# Load detected faces
faces_data = json.load(open('/tmp/parliament_face_demo/data/detected_faces.json'))
print(f'Detected faces: {len(faces_data)}')

# Check embedding format
if faces_data:
    sample_embedding = faces_data[0]['embedding']
    print(f'Embedding type: {type(sample_embedding)}')
    print(f'Embedding length: {len(sample_embedding)}')
    print(f'Sample values: {sample_embedding[:5]}')
    
    # Load MP database
    session = SessionLocal()
    mp_profile = session.query(FaceProfile).first()
    
    if mp_profile:
        mp_encoding = json.loads(mp_profile.face_encoding)
        print(f'MP encoding type: {type(mp_encoding)}')
        print(f'MP encoding length: {len(mp_encoding)}')
        print(f'MP sample values: {mp_encoding[:5]}')
        
        # Calculate similarity
        detected_embedding = np.array(sample_embedding)
        mp_embedding = np.array(mp_encoding)
        
        similarity = np.dot(detected_embedding, mp_embedding) / (
            np.linalg.norm(detected_embedding) * np.linalg.norm(mp_embedding)
        )
        print(f'Cosine similarity: {similarity:.4f}')
    
    session.close()
