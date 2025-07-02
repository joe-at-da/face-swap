#!/usr/bin/env python
"""
Script to run the MP face matching pipeline for all MPs.
This script:
1. Checks if the necessary tables exist in the database
2. Creates any missing tables
3. Ingests a test video if needed
4. Runs the face matching pipeline
5. Checks for generated clips
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database models
from backend.db.base import Base
from backend.db.session import SessionLocal, engine
from backend.db.models.video import Video
from backend.db.models.parliament_video import ParliamentVideo
from backend.db.models.parliament_member_clip import ParliamentMemberClip
from backend.db.models.recognition_process import RecognitionProcess

# Import services
from backend.services.integration.supabase_client import SupabaseService
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher
from backend.services.recognition.member_matching.parliament_clip import create_member_clip

def check_database_tables() -> bool:
    """
    Check if the necessary tables exist in the database.
    Create any missing tables.
    
    Returns:
        bool: True if all tables exist, False otherwise
    """
    try:
        # Create a database session
        db = SessionLocal()
        
        try:
            # Check if tables exist by querying them
            tables_to_check = [
                ("videos", Video),
                ("parliament_videos", ParliamentVideo),
                ("parliament_member_clips", ParliamentMemberClip),
                ("recognition_processes", RecognitionProcess)
            ]
            
            missing_tables = []
            
            for table_name, model in tables_to_check:
                try:
                    # Try to query the table
                    db.query(model).first()
                    logger.info(f"Table '{table_name}' exists")
                except Exception as e:
                    logger.warning(f"Table '{table_name}' does not exist: {str(e)}")
                    missing_tables.append((table_name, model))
            
            if missing_tables:
                logger.info(f"Creating {len(missing_tables)} missing tables...")
                
                # Create missing tables
                for table_name, model in missing_tables:
                    try:
                        # Create table
                        model.__table__.create(engine)
                        logger.info(f"Created table '{table_name}'")
                    except Exception as e:
                        # Check if the error is because the table already exists
                        if "already exists" in str(e):
                            logger.info(f"Table '{table_name}' already exists, skipping creation")
                        else:
                            logger.error(f"Failed to create table '{table_name}': {str(e)}")
                            return False
            
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error checking database tables: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def ingest_test_video(video_path: str) -> Optional[int]:
    """
    Ingest a test video if needed.
    
    Args:
        video_path: Path to the test video
        
    Returns:
        int: ID of the ingested video, or None if failed
    """
    try:
        # Create a database session
        db = SessionLocal()
        
        try:
            # Check if we already have videos in the database
            existing_video = db.query(Video).first()
            
            if existing_video:
                logger.info(f"Using existing video with ID {existing_video.id}")
                return existing_video.id
            
            # No videos found, ingest a new one
            logger.info(f"Ingesting test video from {video_path}")
            
            # Create a new video record
            video = Video(
                title="Test Parliament Video",
                description="Test video for MP face matching",
                source_url="https://example.com/test_video",
                file_path=video_path,
                video_path=video_path,
                status="completed",  # Mark as completed for testing
                duration=300.0,  # Assume 5 minutes for test
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(video)
            db.commit()
            db.refresh(video)
            
            # Create a parliament video record
            parliament_video = ParliamentVideo(
                video_id=video.id,
                parliament_id="test_parliament_id",
                session_date=datetime.utcnow().date(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(parliament_video)
            db.commit()
            
            logger.info(f"Ingested test video with ID {video.id}")
            
            # Create a recognition process record
            try:
                process = RecognitionProcess(
                    video_id=video.id,
                    process_type="face_recognition",
                    status="completed",
                    start_time=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            except Exception as e:
                logger.warning(f"Error creating recognition process with capture_session_id: {str(e)}")
                # Try without the capture_session_id field
                process = RecognitionProcess(
                    video_id=video.id,
                    process_type="face_recognition",
                    status="completed",
                    start_time=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            
            db.add(process)
            db.commit()
            
            logger.info(f"Created recognition process for video ID {video.id}")
            
            return video.id
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error ingesting test video: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def run_face_matching(video_id: int) -> bool:
    """
    Run the face matching pipeline for a video.
    
    Args:
        video_id: ID of the video to process
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a database session
        db = SessionLocal()
        
        try:
            # Initialize the member matcher
            matcher = ParliamentMemberMatcher(db)
            
            # Load parliament members
            success = matcher.load_parliament_members()
            
            if not success:
                logger.error("Failed to load parliament members")
                return False
            
            # Get the video
            video = db.query(Video).filter(Video.id == video_id).first()
            
            if not video:
                logger.error(f"Video with ID {video_id} not found")
                return False
            
            logger.info(f"Running face matching for video ID {video_id}")
            
            # For testing purposes, let's create some sample face matches
            # In a real scenario, we would extract faces from the video and match them
            
            # Sample face data with embeddings
            sample_faces = [
                {
                    "embedding": [0.1] * 128,  # 128-dimensional embedding
                    "frame_time": 10.0,
                    "confidence": 0.9
                },
                {
                    "embedding": [0.2] * 128,
                    "frame_time": 60.0,
                    "confidence": 0.85
                },
                {
                    "embedding": [0.3] * 128,
                    "frame_time": 120.0,
                    "confidence": 0.95
                }
            ]
            
            # Match each face to a member
            for i, face_data in enumerate(sample_faces):
                # Match face to member
                match_result = matcher._match_face_to_member(face_data)
                
                if match_result.get("matched", False):
                    # Get member ID
                    member_id = match_result.get("member_id")
                    confidence = match_result.get("confidence", 0.0)
                    
                    # Create a clip for this match
                    start_time = face_data.get("frame_time", 0.0) - 5.0  # 5 seconds before
                    end_time = face_data.get("frame_time", 0.0) + 25.0   # 25 seconds after
                    
                    # Create member clip
                    clip = create_member_clip(
                        db=db,
                        video_id=video_id,
                        member_id=int(member_id) if member_id.isdigit() else 1,  # Convert to int if possible
                        start_time=start_time,
                        end_time=end_time,
                        confidence=confidence,
                        transcript=f"Sample transcript for clip {i+1}",
                        metadata={
                            "frame_time": face_data.get("frame_time"),
                            "face_confidence": face_data.get("confidence")
                        }  # Will be stored in clip_metadata field
                    )
                    
                    if clip:
                        logger.info(f"Created clip for member {member_id} at time {start_time}-{end_time}")
                    else:
                        logger.warning(f"Failed to create clip for member {member_id}")
                else:
                    logger.warning(f"No match found for face at time {face_data.get('frame_time')}")
            
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error running face matching: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_generated_clips() -> List[Dict[str, Any]]:
    """
    Check for generated clips in the database.
    
    Returns:
        List[Dict[str, Any]]: List of generated clips
    """
    try:
        # Create a database session
        db = SessionLocal()
        
        try:
            # Query all clips
            clips = db.query(ParliamentMemberClip).all()
            
            if not clips:
                logger.warning("No clips found in the database")
                return []
            
            # Convert to dictionaries
            clip_data = []
            for clip in clips:
                clip_data.append({
                    "id": clip.id,
                    "member_id": clip.member_id,
                    "video_id": clip.video_id,
                    "start_time": clip.start_time,
                    "end_time": clip.end_time,
                    "duration": clip.duration,
                    "confidence": clip.confidence,
                    "transcript": clip.transcript[:50] + "..." if clip.transcript and len(clip.transcript) > 50 else clip.transcript
                })
            
            logger.info(f"Found {len(clips)} clips in the database")
            return clip_data
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error checking generated clips: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run the MP face matching pipeline")
    parser.add_argument("--video-path", default="/app/data/test_video.mp4", help="Path to test video file")
    args = parser.parse_args()
    
    logger.info("Starting MP face matching pipeline")
    
    # Step 1: Check database tables
    logger.info("Step 1: Checking database tables")
    tables_ok = check_database_tables()
    
    if not tables_ok:
        logger.error("Failed to check or create database tables")
        sys.exit(1)
    
    # Step 2: Ingest test video if needed
    logger.info("Step 2: Ingesting test video if needed")
    video_id = ingest_test_video(args.video_path)
    
    if not video_id:
        logger.error("Failed to ingest test video")
        sys.exit(1)
    
    # Step 3: Run face matching
    logger.info("Step 3: Running face matching")
    success = run_face_matching(video_id)
    
    if not success:
        logger.error("Failed to run face matching")
        sys.exit(1)
    
    # Step 4: Check generated clips
    logger.info("Step 4: Checking generated clips")
    clips = check_generated_clips()
    
    if not clips:
        logger.warning("No clips were generated")
    else:
        logger.info(f"Generated {len(clips)} clips:")
        for clip in clips:
            logger.info(f"  - Member {clip['member_id']}: {clip['start_time']:.1f}s - {clip['end_time']:.1f}s (confidence: {clip['confidence']:.2f})")
    
    logger.info("MP face matching pipeline completed successfully")

if __name__ == "__main__":
    main()
