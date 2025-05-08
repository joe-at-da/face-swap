#!/usr/bin/env python3
"""
Script to check database configuration for capture sessions
and verify that all required fields are properly set.
"""

import os
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Add the current directory to the path so we can import the backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary models and settings
from backend.core.config import settings
from backend.db.models.capture import CaptureSession

def check_capture(capture_id=None):
    """Check the database configuration for a specific capture or the latest one."""
    # Create SQLAlchemy engine and session
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get the capture session
        if capture_id:
            capture = session.query(CaptureSession).filter(CaptureSession.id == capture_id).first()
            if not capture:
                print(f"❌ Capture with ID {capture_id} not found")
                return
        else:
            # Get the latest capture
            capture = session.query(CaptureSession).order_by(CaptureSession.id.desc()).first()
            if not capture:
                print("❌ No captures found in the database")
                return
        
        print(f"✅ Found capture with ID: {capture.id}")
        
        # Check essential fields
        print("\n=== Basic Information ===")
        print(f"Title: {capture.title}")
        print(f"Status: {capture.status}")
        print(f"Created at: {capture.created_at}")
        
        # Check file paths
        print("\n=== File Paths ===")
        file_path = capture.file_path
        video_path = capture.video_path
        audio_path = capture.audio_path
        audio_file_path = capture.audio_file_path
        
        print(f"file_path: {file_path} {'✅ Exists' if file_path and os.path.exists(file_path) else '❌ Missing'}")
        print(f"video_path: {video_path} {'✅ Exists' if video_path and os.path.exists(video_path) else '❌ Missing'}")
        print(f"audio_path: {audio_path} {'✅ Exists' if audio_path and os.path.exists(audio_path) else '❌ Missing'}")
        print(f"audio_file_path: {audio_file_path} {'✅ Exists' if audio_file_path and os.path.exists(audio_file_path) else '❌ Missing'}")
        
        # Check recognition fields
        print("\n=== Recognition Status ===")
        print(f"recognition_status: {capture.recognition_status}")
        print(f"recognition_started_at: {capture.recognition_started_at}")
        print(f"recognition_completed_at: {capture.recognition_completed_at}")
        
        if capture.recognition_progress:
            try:
                progress = json.loads(capture.recognition_progress)
                print(f"recognition_progress: {json.dumps(progress, indent=2)}")
            except:
                print(f"recognition_progress: {capture.recognition_progress} (not valid JSON)")
        else:
            print("recognition_progress: None")
        
        # Check transcription fields
        print("\n=== Transcription Status ===")
        print(f"transcription_status: {capture.transcription_status}")
        print(f"transcription_path: {capture.transcription_path} {'✅ Exists' if capture.transcription_path and os.path.exists(capture.transcription_path) else '❌ Missing' if capture.transcription_path else 'None'}")
        print(f"transcription_completed_at: {capture.transcription_completed_at}")
        
        # Provide recommendations
        print("\n=== Recommendations ===")
        if not video_path:
            print("❌ video_path is missing. Run the following to fix:")
            print(f"  docker-compose -f docker-compose.dev.yml exec app python -c \"from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; from backend.core.config import settings; from backend.db.models.capture import CaptureSession; engine = create_engine(settings.DATABASE_URL); Session = sessionmaker(bind=engine); session = Session(); capture = session.query(CaptureSession).filter(CaptureSession.id == {capture.id}).first(); capture.video_path = '{file_path if file_path else f'/app/data/temp/capture_{capture.id:04d}.mp4'}'; session.commit(); print('Video path updated successfully'); session.close()\"")
        
        if not audio_path and not audio_file_path:
            print("❌ Both audio_path and audio_file_path are missing. Audio transcription may fail.")
            print("  Check if an audio file exists and update the database with its path.")
        
        if capture.recognition_status == "processing" and not capture.recognition_completed_at:
            print("⚠️ Recognition is still processing. If it's been stuck for a long time, you may need to reset it:")
            print(f"  docker-compose -f docker-compose.dev.yml exec app python -c \"from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; from backend.core.config import settings; from backend.db.models.capture import CaptureSession; engine = create_engine(settings.DATABASE_URL); Session = sessionmaker(bind=engine); session = Session(); capture = session.query(CaptureSession).filter(CaptureSession.id == {capture.id}).first(); capture.recognition_status = None; capture.recognition_progress = None; session.commit(); print('Recognition status reset successfully'); session.close()\"")
        
        if capture.transcription_status == "processing" and not capture.transcription_completed_at:
            print("⚠️ Transcription is still processing. If it's been stuck for a long time, you may need to reset it:")
            print(f"  docker-compose -f docker-compose.dev.yml exec app python -c \"from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker; from backend.core.config import settings; from backend.db.models.capture import CaptureSession; engine = create_engine(settings.DATABASE_URL); Session = sessionmaker(bind=engine); session = Session(); capture = session.query(CaptureSession).filter(CaptureSession.id == {capture.id}).first(); capture.transcription_status = None; session.commit(); print('Transcription status reset successfully'); session.close()\"")
        
    finally:
        session.close()

if __name__ == "__main__":
    # Get capture ID from command line if provided
    capture_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    check_capture(capture_id)
