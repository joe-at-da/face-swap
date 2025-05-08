#!/usr/bin/env python
"""
Script to check recognition status for a capture session.
"""

import sys
import json
from sqlalchemy import create_engine, text
from backend.core.config import settings

def check_recognition_status(capture_id):
    """Check the recognition status for a capture session."""
    print(f"Checking recognition status for capture ID: {capture_id}")
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    # Query the database
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'capture_sessions' 
            AND column_name IN ('recognition_status', 'recognition_progress', 'recognition_results')
        """))
        columns = [row[0] for row in result]
        print(f"Recognition columns found: {', '.join(columns)}")
        
        # Get capture session data
        query = text("""
            SELECT id, status, 
                   recognition_status, 
                   recognition_progress,
                   recognition_started_at,
                   recognition_completed_at
            FROM capture_sessions 
            WHERE id = :capture_id
        """)
        result = conn.execute(query, {"capture_id": capture_id})
        row = result.fetchone()
        
        if not row:
            print(f"No capture session found with ID: {capture_id}")
            return
        
        print(f"Capture ID: {row[0]}")
        print(f"Capture Status: {row[1]}")
        print(f"Recognition Status: {row[2]}")
        
        if row[3]:  # recognition_progress
            try:
                progress = json.loads(row[3])
                print("\nRecognition Progress:")
                print(f"  Status: {progress.get('status', 'unknown')}")
                
                if 'steps' in progress:
                    print("\n  Steps:")
                    for step in progress['steps']:
                        print(f"    - {step.get('name', 'unknown')}: {step.get('status', 'unknown')} ({step.get('timestamp', 'no timestamp')})")
                
                if 'completed_at' in progress:
                    print(f"\n  Completed at: {progress['completed_at']}")
                elif 'error_at' in progress:
                    print(f"\n  Error at: {progress['error_at']}")
                    print(f"  Error: {progress.get('error', 'unknown error')}")
            except json.JSONDecodeError:
                print(f"Invalid JSON in recognition_progress: {row[3]}")
        else:
            print("No recognition progress data available")
        
        print(f"\nRecognition Started At: {row[4]}")
        print(f"Recognition Completed At: {row[5]}")

if __name__ == "__main__":
    capture_id = 264
    if len(sys.argv) > 1:
        capture_id = int(sys.argv[1])
    
    check_recognition_status(capture_id)
