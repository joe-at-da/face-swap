#!/usr/bin/env python
"""
Script to verify that clips have been successfully exported to Supabase by checking
if Speaker records exist for all member_ids in the local SQLite database and
comparing clips between SQLite and Supabase.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

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

logger = logging.getLogger("export_verification")
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
    If no SQLite clips are found, check Supabase clips instead.
    """
    # Load all clips from SQLite
    clips = load_clips_from_sqlite()
    
    if not clips:
        logger.warning("No clips found in SQLite database, checking Supabase clips instead")
        try:
            # Initialize Supabase client
            supabase_service = SupabaseService(use_service_role=True)
            
            # Query clips from Supabase
            response = supabase_service.client.table("parliament_member_clips").select("*").execute()
            
            if hasattr(response, "data") and response.data:
                supabase_clips = response.data
                logger.info(f"Found {len(supabase_clips)} clips in Supabase")
                
                # Extract member_ids from Supabase clips
                member_ids = set()
                for clip in supabase_clips:
                    member_id = clip.get("member_id")
                    if member_id:
                        member_ids.add(member_id)
                
                logger.info(f"Found {len(member_ids)} unique member_ids in Supabase clips")
                
                # Continue with speaker verification using Supabase member_ids
                clips = supabase_clips
            else:
                logger.error("No clips found in Supabase")
                return
        except Exception as e:
            logger.error(f"Error fetching Supabase clips: {str(e)}")
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


def check_supabase_clips(video_id: Optional[int] = None) -> None:
    """
    Check clips in Supabase database.
    """
    # Load clips from SQLite (for comparison if available)
    sqlite_clips = load_clips_from_sqlite(video_id)
    
    if not sqlite_clips:
        logger.warning("No clips found in SQLite database, proceeding with Supabase check only")
    
    # Initialize Supabase client
    try:
        supabase_service = SupabaseService(use_service_role=True)
        
        # Query clips from Supabase
        response = supabase_service.client.table("parliament_member_clips").select("*")
        if video_id is not None:
            response = response.eq("video_id", video_id)
        
        supabase_clips = response.execute()
        
        if hasattr(supabase_clips, "data"):
            supabase_clips_data = supabase_clips.data
            logger.info(f"Found {len(supabase_clips_data)} clips in Supabase")
            
            # Report clip counts
            if video_id is not None:
                if sqlite_clips:
                    logger.info(f"SQLite clips for video {video_id}: {len(sqlite_clips)}")
                logger.info(f"Supabase clips for video {video_id}: {len(supabase_clips_data)}")
            else:
                if sqlite_clips:
                    logger.info(f"Total SQLite clips: {len(sqlite_clips)}")
                logger.info(f"Total Supabase clips: {len(supabase_clips_data)}")
            
            # Check member_ids in Supabase clips
            supabase_member_ids = {clip.get("member_id") for clip in supabase_clips_data if clip.get("member_id")}
            logger.info(f"Found {len(supabase_member_ids)} unique member_ids in Supabase clips")
            
            # Verify member_ids against parliament_members table
            try:
                # Query all member_ids from parliament_members table
                members_response = supabase_service.client.table("parliament_members").select("id,member_id,name").execute()
                if hasattr(members_response, "data"):
                    members_data = members_response.data
                    logger.info(f"Found {len(members_data)} members in parliament_members table")
                    
                    # Create mapping from UUID to integer member_id
                    uuid_to_member_id = {}
                    member_id_to_name = {}
                    for member in members_data:
                        if member.get("id") and member.get("member_id"):
                            uuid_to_member_id[member.get("id")] = member.get("member_id")
                            member_id_to_name[member.get("member_id")] = member.get("name")
                    
                    logger.info(f"Created mapping for {len(uuid_to_member_id)} members from UUID to integer member_id")
                    
                    # Check if all clip member_ids are valid
                    valid_member_ids = set(member_id_to_name.keys())
                    invalid_member_ids = supabase_member_ids - valid_member_ids
                    
                    if invalid_member_ids:
                        logger.warning(f"Found {len(invalid_member_ids)} invalid member_ids in clips:")
                        for member_id in sorted(invalid_member_ids):
                            logger.warning(f"  - {member_id}")
                    else:
                        logger.info("All member_ids in clips are valid!")
                    
                    # Show distribution of clips by member name
                    member_clip_counts = {}
                    for clip in supabase_clips_data:
                        member_id = clip.get("member_id")
                        if member_id in member_id_to_name:
                            name = member_id_to_name[member_id]
                            if name not in member_clip_counts:
                                member_clip_counts[name] = 0
                            member_clip_counts[name] += 1
                    
                    logger.info("Clip distribution by member name:")
                    for name, count in sorted(member_clip_counts.items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"  - {name}: {count} clips")
                else:
                    logger.error("Failed to retrieve members from parliament_members table")
            except Exception as e:
                logger.error(f"Error verifying member_ids: {str(e)}")
                
            # If SQLite clips are available, compare them with Supabase
            if sqlite_clips:
                # Extract member_ids from SQLite clips for comparison
                sqlite_member_ids = {clip.get("member_id") for clip in sqlite_clips if clip.get("member_id") and clip.get("member_id") != "default_unknown"}
                
                # Compare member_ids between SQLite and Supabase
                common_member_ids = sqlite_member_ids.intersection(supabase_member_ids)
                missing_in_supabase = sqlite_member_ids - supabase_member_ids
                extra_in_supabase = supabase_member_ids - sqlite_member_ids
                
                logger.info(f"Common member_ids: {len(common_member_ids)}/{len(sqlite_member_ids)}")
                
                if missing_in_supabase:
                    logger.warning(f"Found {len(missing_in_supabase)} member_ids in SQLite but not in Supabase:")
                    for member_id in sorted(missing_in_supabase):
                        logger.warning(f"  - {member_id}")
                
                if extra_in_supabase:
                    logger.warning(f"Found {len(extra_in_supabase)} member_ids in Supabase but not in SQLite:")
                    for member_id in sorted(extra_in_supabase):
                        logger.warning(f"  - {member_id}")
            
            # Check for duplicate clips in Supabase
            clip_keys = {}
            duplicates = []
            for clip in supabase_clips_data:
                key = (clip.get("video_id"), clip.get("start_time"), clip.get("end_time"), clip.get("member_id"))
                if key in clip_keys:
                    duplicates.append(key)
                else:
                    clip_keys[key] = True
            
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate clips in Supabase")
                for key in duplicates:
                    logger.warning(f"  - Video: {key[0]}, Start: {key[1]}, End: {key[2]}, Member: {key[3]}")
            else:
                logger.info("No duplicate clips found in Supabase")
        else:
            logger.error("Failed to retrieve clips from Supabase")
    
    except Exception as e:
        logger.error(f"Error checking Supabase clips: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Verify clips export to Supabase")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    parser.add_argument("--check-speakers", action="store_true", help="Check speaker matches")
    parser.add_argument("--check-supabase", action="store_true", help="Check Supabase clips")
    parser.add_argument("--video-id", type=int, help="Filter by video ID")
    
    args = parser.parse_args()
    
    # If no specific check is requested, run all checks
    if not (args.all or args.check_speakers or args.check_supabase):
        args.all = True
    
    return args


def main():
    """
    Main entry point.
    """
    logger.info("Verifying clips export...")
    
    args = parse_args()
    
    if args.all or args.check_speakers:
        logger.info("=== CHECKING SPEAKER MATCHES ===")
        verify_speaker_matches()
    
    if args.all or args.check_supabase:
        logger.info("=== CHECKING SUPABASE CLIPS ===")
        check_supabase_clips(args.video_id)
    
    logger.info("Verification complete!")


if __name__ == "__main__":
    main()
