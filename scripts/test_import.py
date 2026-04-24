#!/usr/bin/env python3

import sys
from pathlib import Path

# Add the project root directory to Python path (so we can import backend)
project_root = Path(__file__).parent.parent
print(f"Project root: {project_root}")
print(f"Project root exists: {project_root.exists()}")

if project_root.exists():
    sys.path.insert(0, str(project_root))
    print(f"Added to Python path: {project_root}")
    
    # Try to import
    try:
        import backend
        print("✅ Successfully imported backend")
        
        # Check services directory
        services_dir = project_root / "backend" / "services"
        print(f"Services directory: {services_dir}")
        print(f"Services exists: {services_dir.exists()}")
        
        if services_dir.exists():
            try:
                from backend.services.recognition.face_recognition import FaceRecognitionService
                print("✅ Successfully imported FaceRecognitionService")
            except ImportError as e:
                print(f"❌ Failed to import FaceRecognitionService: {e}")
        
    except ImportError as e:
        print(f"❌ Failed to import backend: {e}")
else:
    print("❌ Backend directory not found")

print(f"Current Python path:")
for i, p in enumerate(sys.path[:10]):
    print(f"  {i}: {p}")
