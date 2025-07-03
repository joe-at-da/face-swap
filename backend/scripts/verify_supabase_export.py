#!/usr/bin/env python
"""
Script to verify and validate Parliament Clips export to Supabase.
This script performs the following checks:
1. Verifies clips in local SQLite database
2. Checks member_id mapping between SQLite and Supabase
3. Validates that clips were successfully exported to Supabase
4. Provides detailed reporting on any issues found
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import required modules
from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
from backend.services.integration.supabase_client import SupabaseService
from backend.db.session import SessionLocal
from backend.db.models import Speaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("supabase_export_verification")
logger.setLevel(logging.INFO)


def load_clips_from_sqlite(video_id: int = None) -> List[Dict[str, Any]]:
    """
    Load clips directly from the SQLite database, optionally filtered by video ID.
    """
    # Initialize the ParliamentClipsIntegrationService to get the db_path
    clips_service = ParliamentClipsIntegrationService()
    db_path = clips_service.db_path
    
    try:
        # Connect to SQLite database
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query clips, optionally filtered by video ID
        if video_id is not None:
            cursor.execute("""
                SELECT * FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = ?
            """, (video_id,))
        else:
            cursor.execute("SELECT * FROM parliament_clips")
        
        clips = []
        for row in cursor.fetchall():
            # Convert row to dictionary
            clip = dict(row)
            
            # Parse metadata JSON if it exists
            if clip['metadata']:
                try:
                    clip['metadata'] = json.loads(clip['metadata'])
                except:
                    pass
                    
            clips.append(clip)
        
        if video_id is not None:
            logger.info(f"Found {len(clips)} clips in SQLite database for video ID {video_id}")
        else:
            logger.info(f"Found {len(clips)} total clips in SQLite database")
        
        return clips
    except Exception as e:
        logger.error(f"Error loading clips from SQLite: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def verify_speaker_matches() -> None:
    """
    Verify that all member_ids in the SQLite database have matching Speaker records.
    """
    # Load all clips from SQLite
    clips = load_clips_from_sqlite()
    
    if not clips:
        logger.error("No clips found in SQLite database")
        return
    
    # Extract unique member_ids
    member_ids = set()
    for clip in clips:
        member_id = clip.get("member_id")
        if member_id and member_id != "default_unknown":
            member_ids.add(member_id)
    
    logger.info(f"Found {len(member_ids)} unique member_ids in clips")
    
    # Check if each member_id has a matching Speaker record
    db = SessionLocal()
    try:
        # Get all speakers
        speakers = db.query(Speaker).all()
        logger.info(f"Found {len(speakers)} speakers in the database")
        
        # Create a set of parliament_ids from speakers
        speaker_parliament_ids = {speaker.parliament_id for speaker in speakers if speaker.parliament_id}
        
        # Check which member_ids have matching Speaker records
        matched_member_ids = member_ids.intersection(speaker_parliament_ids)
        unmatched_member_ids = member_ids - speaker_parliament_ids
        
        logger.info(f"Member IDs with matching Speaker records: {len(matched_member_ids)}/{len(member_ids)}")
        
        if unmatched_member_ids:
            logger.warning(f"Found {len(unmatched_member_ids)} member_ids without matching Speaker records:")
            for member_id in sorted(unmatched_member_ids):
                logger.warning(f"  - {member_id}")
        else:
            logger.info("All member_ids have matching Speaker records!")
            
        # Count clips by member_id
        member_id_counts = {}
        for clip in clips:
            member_id = clip.get("member_id", "None")
            if member_id not in member_id_counts:
                member_id_counts[member_id] = 0
            member_id_counts[member_id] += 1
        
        logger.info(f"Member ID distribution in clips: {member_id_counts}")
            
    except Exception as e:
        logger.error(f"Error verifying speaker matches: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


def check_supabase_clips(video_id: int = None) -> None:
    """
    Check if clips have been successfully exported to Supabase.
    """
    logger.info("Checking clips in Supabase...")
    
    # Initialize Supabase client
    supabase_client = SupabaseService(use_service_role=True)
    
    try:
        # Check for valid member IDs in parliament_members table
        member_response = supabase_client.client.table('parliament_members').select('id,member_id').limit(5).execute()
        valid_members = member_response.data if member_response.data else []
        logger.info(f"Found {len(valid_members)} valid members in parliament_members table")
        
        # Extract the integer member_ids (not the UUID primary keys)
        valid_member_ids = [member['member_id'] for member in valid_members if 'member_id' in member]
        logger.info(f"Valid integer member_ids: {valid_member_ids}")
        
        # Query clips from Supabase
        if video_id is not None:
            # If we have a specific video ID, try to find clips with that video ID in metadata
            clips_response = supabase_client.client.table('parliament_member_clips').select('*').execute()
            clips = clips_response.data if clips_response.data else []
            
            # Filter clips by video ID (if possible)
            filtered_clips = []
            for clip in clips:
                if clip.get('full_video_path') and str(video_id) in clip.get('full_video_path'):
                    filtered_clips.append(clip)
            
            logger.info(f"Found {len(filtered_clips)} clips in Supabase for video ID {video_id} (out of {len(clips)} total clips)")
            clips = filtered_clips
        else:
            # Otherwise, get all clips
            clips_response = supabase_client.client.table('parliament_member_clips').select('*').execute()
            clips = clips_response.data if clips_response.data else []
            logger.info(f"Found {len(clips)} total clips in Supabase")
        
        # Check member_id distribution in Supabase clips
        member_id_counts = {}
        for clip in clips:
            member_id = clip.get("member_id", "None")
            if member_id not in member_id_counts:
                member_id_counts[member_id] = 0
            member_id_counts[member_id] += 1
        
        logger.info(f"Member ID distribution in Supabase clips: {member_id_counts}")
        
        # Compare with local SQLite clips
        sqlite_clips = load_clips_from_sqlite(video_id)
        logger.info(f"Comparison - SQLite: {len(sqlite_clips)} clips, Supabase: {len(clips)} clips")
        
        # Check for any potential issues with member_id mapping
        if clips:
            sample_clip = clips[0]
            logger.info(f"Sample Supabase clip: {json.dumps(sample_clip, default=str)}")
            
    except Exception as e:
        logger.error(f"Error checking Supabase clips: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description='Verify Parliament Clips export to Supabase')
    parser.add_argument('video_id', type=int, nargs='?', help='Optional video ID to filter clips')
    parser.add_argument('--check-sqlite', action='store_true', help='Check clips in local SQLite database')
    parser.add_argument('--check-speakers', action='store_true', help='Check speaker matches')
    parser.add_argument('--check-supabase', action='store_true', help='Check clips in Supabase')
    parser.add_argument('--all', action='store_true', help='Run all checks')
    
    args = parser.parse_args()
    
    # If no specific checks are requested, run all checks
    if not (args.check_sqlite or args.check_speakers or args.check_supabase):
        args.all = True
    
    logger.info("Starting verification of Parliament Clips export...")
    
    if args.all or args.check_sqlite:
        logger.info("=== CHECKING SQLITE DATABASE ===")
        load_clips_from_sqlite(args.video_id)
    
    if args.all or args.check_speakers:
        logger.info("=== CHECKING SPEAKER MATCHES ===")
        verify_speaker_matches()
    
    if args.all or args.check_supabase:
        logger.info("=== CHECKING SUPABASE CLIPS ===")
        check_supabase_clips(args.video_id)
    
    logger.info("Verification complete!")


if __name__ == "__main__":
    main()
