#!/usr/bin/env python3
"""
Ingest and process a Parliament TV video to generate MP clips.

This script ingests a test or real Parliament TV video into the system,
triggers the video processing pipeline, and monitors the process.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import the backend package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.db.session import SessionLocal
from backend.services.integration.supabase_client import SupabaseService
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher
from backend.services.recognition.member_matching.database import load_members_from_supabase
from backend.services.video.processor import VideoProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ingest_video(video_path: str, title: str = None, description: str = None):
    """
    Ingest a video file into the system.
    
    Args:
        video_path: Path to the video file
        title: Title for the video (optional)
        description: Description for the video (optional)
    
    Returns:
        Video ID if successful, None otherwise
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None
    
    # Use filename as title if not provided
    if not title:
        title = os.path.basename(video_path)
    
    # Use title as description if not provided
    if not description:
        description = f"Parliament TV video: {title}"
    
    try:
        # Create Supabase service
        supabase = SupabaseService(use_service_role=True)
        
        # Upload the video file to Supabase storage
        logger.info(f"Uploading video: {video_path}")
        upload_result = supabase.upload_full_video(video_path)
        
        if not upload_result.get("success"):
            logger.error(f"Failed to upload video: {upload_result.get('error')}")
            return None
        
        # Get video metadata
        video_processor = VideoProcessor()
        duration = video_processor.get_video_duration(video_path)
        
        # Create video entry in database
        video_data = {
            "title": title,
            "description": description,
            "source_url": upload_result.get("public_url"),
            "duration": int(duration),
            "status": "uploaded",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert video into database
        logger.info("Creating video entry in database")
        insert_result = supabase.insert_video(video_data)
        
        if not insert_result.data:
            logger.error(f"Failed to insert video: {insert_result}")
            return None
        
        video_id = insert_result.data[0].get("id")
        logger.info(f"Video ingested successfully with ID: {video_id}")
        
        # Add to video processing queue
        queue_data = {
            "video_id": video_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info("Adding video to processing queue")
        queue_result = supabase.add_to_video_processing_queue(queue_data)
        
        if queue_result.get("error"):
            logger.warning(f"Warning: Failed to add to processing queue: {queue_result.get('error')}")
        
        return video_id
    
    except Exception as e:
        logger.error(f"Error ingesting video: {str(e)}")
        return None

def trigger_processing(video_id: int, db: Session):
    """
    Trigger the video processing pipeline for a specific video.
    
    Args:
        video_id: ID of the video to process
        db: Database session
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load members from Supabase
        logger.info("Loading parliament members from Supabase")
        members = load_members_from_supabase(db)
        
        if not members:
            logger.error("Failed to load parliament members")
            return False
        
        # Initialize the matcher with the database session
        logger.info("Initializing ParliamentMemberMatcher")
        matcher = ParliamentMemberMatcher(members, db=db)
        
        # Load member embeddings
        logger.info("Loading member embeddings")
        matcher.load_embeddings()
        
        # Create a recognition process entry
        logger.info(f"Creating recognition process for video ID: {video_id}")
        with db.begin():
            db.execute(
                """
                INSERT INTO recognition_processes 
                (video_id, status, process_type, created_at, updated_at) 
                VALUES (:video_id, :status, :process_type, NOW(), NOW())
                """,
                {
                    "video_id": video_id,
                    "status": "processing",
                    "process_type": "facial"
                }
            )
        
        # In a real system, this would be handled by a background worker
        # For this script, we'll simulate the processing
        logger.info("Video processing started - in a real system, this would be handled by a background worker")
        logger.info("Check the database for clips after processing completes")
        
        return True
    
    except Exception as e:
        logger.error(f"Error triggering processing: {str(e)}")
        return False

def check_processing_status(video_id: int, db: Session):
    """
    Check the status of video processing.
    
    Args:
        video_id: ID of the video to check
        db: Database session
    
    Returns:
        Status of the processing
    """
    try:
        result = db.execute(
            """
            SELECT status, error_message 
            FROM recognition_processes 
            WHERE video_id = :video_id 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            {"video_id": video_id}
        ).fetchone()
        
        if not result:
            return "No recognition process found"
        
        status = result[0]
        error_message = result[1]
        
        if error_message:
            return f"{status} (Error: {error_message})"
        
        return status
    
    except Exception as e:
        logger.error(f"Error checking processing status: {str(e)}")
        return "Error checking status"

def check_member_clips(member_id: int, db: Session):
    """
    Check if clips exist for a specific parliament member.
    
    Args:
        member_id: ID of the parliament member
        db: Database session
    
    Returns:
        List of clips for the member
    """
    try:
        clips = db.execute(
            """
            SELECT id, video_id, start_time, end_time, duration, confidence, clip_url
            FROM parliament_member_clips
            WHERE member_id = :member_id
            ORDER BY created_at DESC
            """,
            {"member_id": member_id}
        ).fetchall()
        
        return clips
    
    except Exception as e:
        logger.error(f"Error checking member clips: {str(e)}")
        return []

def main():
    """Main function to ingest and process a video."""
    parser = argparse.ArgumentParser(description="Ingest and process a Parliament TV video")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--title", help="Title for the video")
    parser.add_argument("--description", help="Description for the video")
    parser.add_argument("--member-id", type=int, help="Check clips for this member ID after processing")
    args = parser.parse_args()
    
    # Ingest the video
    video_id = ingest_video(args.video_path, args.title, args.description)
    
    if not video_id:
        logger.error("Video ingestion failed")
        return False
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Trigger processing
        success = trigger_processing(video_id, db)
        
        if not success:
            logger.error("Failed to trigger video processing")
            return False
        
        # Check processing status
        logger.info("Checking processing status...")
        status = check_processing_status(video_id, db)
        logger.info(f"Processing status: {status}")
        
        # If a member ID was specified, check for clips
        if args.member_id:
            logger.info(f"Checking clips for member ID: {args.member_id}")
            clips = check_member_clips(args.member_id, db)
            
            if clips:
                logger.info(f"Found {len(clips)} clips for member ID: {args.member_id}")
                for i, clip in enumerate(clips):
                    logger.info(f"Clip {i+1}: ID={clip[0]}, Video ID={clip[1]}, Start={clip[2]}, End={clip[3]}, Duration={clip[4]}, Confidence={clip[5]}")
            else:
                logger.info(f"No clips found for member ID: {args.member_id}")
        
        logger.info("Video ingestion and processing setup completed successfully")
        logger.info("The actual processing will continue in the background")
        return True
    
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
