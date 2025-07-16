#!/usr/bin/env python3
"""
Update Speech Groups in Parliament Clips Database

This script updates existing records in the parliament_clips SQLite database
to assign speech group IDs to clips that don't have them yet.

It uses speaker diarization data when available to create more accurate speech groups.
When diarization data is not available, it falls back to using temporal proximity.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

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

def find_diarization_file(video_path: str) -> Optional[Path]:
    """
    Find the diarization JSON file for a given video path.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Path to the diarization file if found, None otherwise
    """
    # Extract video ID from path if possible
    try:
        # Handle different filename patterns
        video_basename = os.path.basename(video_path)
        # Try to extract video ID from various filename patterns
        if '_' in video_basename:
            video_id = video_basename.split('_')[0]
        else:
            video_id = os.path.splitext(video_basename)[0]
        
        logger.info(f"Extracted video ID: {video_id} from path: {video_path}")
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not extract video ID from path: {video_path}, error: {e}")
        video_id = None
    
    # Common locations for diarization files
    possible_paths = []
    
    # If we have a video ID, check ID-based paths
    if video_id:
        # Docker paths
        possible_paths.extend([
            Path(f"/app/data/media/{video_id}.diarization.json"),
            Path(f"/app/data/temp/{video_id}.diarization.json"),
        ])
        
        # Local paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths.extend([
            Path(os.path.join(base_dir, f"data/media/{video_id}.diarization.json")),
            Path(os.path.join(base_dir, f"data/temp/{video_id}.diarization.json")),
        ])
        
        # Audio-derived paths
        possible_paths.extend([
            Path(f"/app/data/temp/audio_extracts/{video_id}.audio_diarization.json"),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/{video_id}.audio_diarization.json"))
        ])
    
    # Derived from video path (regardless of whether we have a video ID)
    video_path_without_ext = os.path.splitext(video_path)[0]
    possible_paths.extend([
        Path(video_path_without_ext + ".diarization.json"),
    ])
    
    # Check if any of the possible paths exist
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found diarization file: {path}")
            return path
    
    logger.info(f"No diarization file found for video {video_path}")
    logger.debug(f"Checked paths: {possible_paths}")
    return None


def load_diarization_data(diarization_file: Path) -> Optional[Dict]:
    """
    Load speaker diarization data from a JSON file.
    
    Args:
        diarization_file: Path to the diarization JSON file
        
    Returns:
        Dict with diarization data if successful, None otherwise
    """
    try:
        with open(diarization_file, 'r') as f:
            data = json.load(f)
        
        # Validate that this is a diarization file
        if 'segments' in data and isinstance(data['segments'], list):
            logger.info(f"Successfully loaded diarization data with {len(data['segments'])} segments")
            return data
        else:
            logger.warning(f"File {diarization_file} does not appear to be a valid diarization file")
            return None
    except Exception as e:
        logger.error(f"Error loading diarization file {diarization_file}: {e}")
        return None


def create_speech_blocks_from_diarization(clips: List[Tuple], diarization_data: Dict) -> List[List[Tuple]]:
    """
    Create speech blocks based on diarization data.
    
    Args:
        clips: List of clips (id, member_id, start_timestamp, end_timestamp)
        diarization_data: Dict with diarization data
        
    Returns:
        List of speech blocks, where each block is a list of clips
    """
    # Extract diarization segments
    diarization_segments = diarization_data.get('segments', [])
    if not diarization_segments:
        logger.warning("No diarization segments found in diarization data")
        return []
    
    # Sort clips by start time
    sorted_clips = sorted(clips, key=lambda c: float(c[2]) if c[2] else 0)
    
    # Group all clips into a single speech block per video
    # This ensures all clips from the same video are grouped together
    # regardless of speaker changes in the diarization data
    speech_blocks = [sorted_clips] if sorted_clips else []
    
    logger.info(f"Created {len(speech_blocks)} speech blocks based on diarization data")
    logger.info(f"All clips from the same video are grouped into a single speech block")
    return speech_blocks


def create_speech_blocks_by_proximity(clips: List[Tuple]) -> List[List[Tuple]]:
    """
    Create speech blocks based on temporal proximity only.
    
    Args:
        clips: List of clips (id, member_id, start_timestamp, end_timestamp)
        
    Returns:
        List of speech blocks, where each block is a list of clips
    """
    MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds max gap between segments
    
    # Sort clips by start time
    sorted_clips = sorted(clips, key=lambda c: float(c[2]) if c[2] else 0)
    
    current_block = []
    speech_blocks = []
    
    for clip in sorted_clips:
        clip_id, member_id, start_timestamp, end_timestamp = clip
        
        # Convert timestamps to float for comparison
        start_time = float(start_timestamp) if start_timestamp else 0
        
        if not current_block:
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
    
    logger.info(f"Created {len(speech_blocks)} speech blocks based on temporal proximity")
    return speech_blocks


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
        diarization_used = 0
        
        for (video_path,) in video_paths:
            # Extract video ID from path if possible
            try:
                path_video_id = int(os.path.basename(video_path).split('_')[0])
            except (ValueError, IndexError):
                path_video_id = hash(video_path) % 10000  # Use a hash if we can't extract an ID
            
            # Get all clips for this video, ordered by start_timestamp
            cursor.execute("""
                SELECT id, member_id, start_timestamp, end_timestamp 
                FROM parliament_clips 
                WHERE full_video_path = ? 
                ORDER BY CAST(start_timestamp AS REAL)
            """, (video_path,))
            
            clips = cursor.fetchall()
            logger.info(f"Found {len(clips)} clips for video path {video_path}")
            
            # Try to find and load diarization data
            diarization_file = find_diarization_file(video_path)
            speech_blocks = []
            
            if diarization_file:
                diarization_data = load_diarization_data(diarization_file)
                if diarization_data:
                    # Create speech blocks based on diarization data
                    speech_blocks = create_speech_blocks_from_diarization(clips, diarization_data)
                    diarization_used += 1
                    logger.info(f"Using diarization data to create speech groups for {video_path}")
            
            # If no diarization data or blocks couldn't be created, fall back to temporal proximity
            if not speech_blocks:
                logger.info(f"Falling back to temporal proximity for {video_path}")
                speech_blocks = create_speech_blocks_by_proximity(clips)
            
            logger.info(f"Grouped {len(clips)} clips into {len(speech_blocks)} speech blocks")
            
            # Update speech_group_id for each speech block
            block_updates = 0
            for block_idx, block in enumerate(speech_blocks):
                if not block:  # Skip empty blocks
                    continue
                    
                # Generate a unique speech group ID
                first_clip = block[0]
                first_start_time = float(first_clip[2]) if first_clip[2] else 0
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
            "diarization_used": diarization_used,
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
    parser.add_argument('--force', action='store_true', help='Force update of speech groups even if already assigned')
    
    args = parser.parse_args()
    
    # If force flag is provided, clear existing speech group IDs for the specified video
    if args.force and args.video_id:
        db_path = get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Clear speech group IDs for the specified video
            cursor.execute(
                "UPDATE parliament_clips SET speech_group_id = NULL WHERE full_video_path LIKE ?",
                (f"%{args.video_id}%",)
            )
            conn.commit()
            affected_rows = cursor.rowcount
            logger.info(f"Cleared speech group IDs for {affected_rows} clips with video ID {args.video_id}")
            conn.close()
        except Exception as e:
            logger.error(f"Error clearing speech group IDs: {e}")
    
    result = update_speech_groups(args.video_id)
    
    if result["success"]:
        logger.info(f"Successfully updated {result['total_updated']} clips in {result['videos_processed']} videos")
        logger.info(f"Used diarization data for {result['diarization_used']} videos")
        
        if result['total_clips'] > 0:
            coverage_percentage = (result['clips_with_speech_group'] / result['total_clips']) * 100
            logger.info(f"Speech group coverage: {result['clips_with_speech_group']}/{result['total_clips']} clips ({coverage_percentage:.1f}%)")
        else:
            logger.info("No clips found in the database")
    else:
        logger.error(f"Failed to update speech groups: {result['error']}")

if __name__ == "__main__":
    main()
