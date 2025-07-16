#!/usr/bin/env python3
"""
Update Speech Groups in Parliament Clips Database

This script updates existing records in the parliament_clips SQLite database
to assign speech group IDs to clips that don't have them yet.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the parent directory to sys.path to allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_path():
    """Get the path to the parliament_clips.db file."""
    # Define paths for data storage
    docker_db_path = "/app/backend/parliament_clips.db"  # Path in Docker container
    local_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                "backend/parliament_clips.db")  # Local path
    
    # Use the path that exists
    if os.path.exists(docker_db_path):
        db_path = docker_db_path
        logger.info(f"Using Docker database path: {db_path}")
    elif os.path.exists(local_db_path):
        db_path = local_db_path
        logger.info(f"Using local database path: {db_path}")
    else:
        logger.error("Parliament clips database doesn't exist.")
        raise FileNotFoundError("Parliament clips database not found")
    
    return db_path

def update_speech_groups(video_id=None):
    """
    Update speech group IDs for clips in the parliament_clips table.
    
    Args:
        video_id: Optional ID of the video to update. If None, update all videos.
    
    Returns:
        Dict with results of the operation
    """
    db_path = get_db_path()
    conn = None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the speech_group_id column exists
        cursor.execute("PRAGMA table_info(parliament_clips)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'speech_group_id' not in columns:
            logger.info("Adding speech_group_id column to parliament_clips table")
            cursor.execute("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
            conn.commit()
        
        # Get all videos that need updating
        if video_id:
            cursor.execute("SELECT DISTINCT full_video_path FROM parliament_clips WHERE full_video_path LIKE ? AND (speech_group_id IS NULL OR speech_group_id = '')",
                          (f"%{video_id}%",))
        else:
            cursor.execute("SELECT DISTINCT full_video_path FROM parliament_clips WHERE speech_group_id IS NULL OR speech_group_id = ''")
        
        video_paths = cursor.fetchall()
        logger.info(f"Found {len(video_paths)} videos that need speech group updates")
        
        total_updated = 0
        
        for (video_path,) in video_paths:
            # Extract video ID from path if possible
            try:
                path_video_id = int(os.path.basename(video_path).split('_')[0])
            except (ValueError, IndexError):
                path_video_id = hash(video_path) % 10000  # Use a hash if we can't extract an ID
            
            # Get all clips for this video, ordered by member_id and start_timestamp
            cursor.execute("""
                SELECT id, member_id, start_timestamp, end_timestamp 
                FROM parliament_clips 
                WHERE full_video_path = ? 
                ORDER BY member_id, CAST(start_timestamp AS REAL)
            """, (video_path,))
            
            clips = cursor.fetchall()
            logger.info(f"Found {len(clips)} clips for video path {video_path}")
            
            # Group clips by temporal proximity only (not by member_id)
            MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds max gap between segments
            
            current_block = []
            speech_blocks = []
            
            for clip in clips:
                clip_id, member_id, start_time_str, end_time_str = clip
                
                try:
                    start_time = float(start_time_str)
                    end_time = float(end_time_str) if end_time_str else start_time + 1
                except (ValueError, TypeError):
                    logger.warning(f"Invalid timestamp format for clip {clip_id}: {start_time_str}-{end_time_str}")
                    continue
                
                if not current_block:
                    # First clip
                    current_block = [clip]
                else:
                    # Check time proximity only
                    prev_clip = current_block[-1]
                    prev_end_time = float(prev_clip[3]) if prev_clip[3] else float(prev_clip[2]) + 1
                    
                    if start_time - prev_end_time <= MAX_CONTINUOUS_SPEECH_GAP:
                        # Continuous speech (regardless of member_id)
                        current_block.append(clip)
                    else:
                        # Gap too large, start a new block
                        speech_blocks.append(current_block)
                        current_block = [clip]
            
            # Add the last block
            if current_block:
                speech_blocks.append(current_block)
            
            logger.info(f"Grouped {len(clips)} clips into {len(speech_blocks)} speech blocks")
            
            # Update speech_group_id for each temporal speech block (based only on time proximity)
            block_updates = 0
            for block_idx, block in enumerate(speech_blocks):
                # Generate a unique speech group ID
                first_clip = block[0]
                first_start_time = float(first_clip[2])
                speech_group_id = f"speech_group_{path_video_id}_{block_idx}_{int(first_start_time)}"
                
                # Update all clips in this block
                for clip in block:
                    clip_id = clip[0]
                    cursor.execute(
                        "UPDATE parliament_clips SET speech_group_id = ? WHERE id = ?",
                        (speech_group_id, clip_id)
                    )
                    block_updates += 1
            
            conn.commit()
            logger.info(f"Updated {block_updates} clips with speech group IDs for video {video_path}")
            total_updated += block_updates
        
        # Verify updates
        cursor.execute("SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id IS NOT NULL")
        non_null_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM parliament_clips")
        total_count = cursor.fetchone()[0]
        
        if total_count > 0:
            coverage_percentage = (non_null_count / total_count) * 100
            logger.info(f"Total clips with speech_group_id: {non_null_count}/{total_count} ({coverage_percentage:.1f}%)")
        else:
            logger.info(f"No clips found in the database")
        
        return {
            "success": True,
            "total_updated": total_updated,
            "videos_processed": len(video_paths),
            "clips_with_speech_group": non_null_count,
            "total_clips": total_count
        }
        
    except Exception as e:
        logger.error(f"Error updating speech groups: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if conn:
            conn.close()

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update speech group IDs in parliament_clips database')
    parser.add_argument('--video-id', type=str, help='Optional video ID to update')
    
    args = parser.parse_args()
    
    result = update_speech_groups(args.video_id)
    
    if result["success"]:
        logger.info(f"Successfully updated {result['total_updated']} clips in {result['videos_processed']} videos")
        if result['total_clips'] > 0:
            coverage_percentage = (result['clips_with_speech_group'] / result['total_clips']) * 100
            logger.info(f"Speech group coverage: {result['clips_with_speech_group']}/{result['total_clips']} clips ({coverage_percentage:.1f}%)")
        else:
            logger.info("No clips found in the database")
    else:
        logger.error(f"Failed to update speech groups: {result['error']}")

if __name__ == "__main__":
    main()
