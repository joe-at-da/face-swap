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

# Set up logging
logger = logging.getLogger(__name__)

def find_diarization_file(video_path: Path) -> Optional[Path]:
    """Find the diarization JSON file for a given video path.
    
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


def create_speech_blocks_from_diarization(clips: List[Tuple], diarization_data: Dict) -> Tuple[List[List[Tuple]], Dict]:
    """
    Create speech blocks based on diarization data.
    
    Args:
        clips: List of clips (id, member_id, start_timestamp, end_timestamp)
        diarization_data: Dict with diarization data
        
    Returns:
        Tuple containing:
            - List of speech blocks, where each block is a list of clips
            - Dictionary mapping clip IDs to speaker labels
    """
    # Extract diarization segments
    diarization_segments = diarization_data.get('segments', [])
    if not diarization_segments:
        logger.warning("No diarization segments found in diarization data")
        return []
    
    # Sort clips by start time for easier matching
    sorted_clips = sorted(clips, key=lambda c: float(c[2]) if c[2] else 0)
    
    # First, assign each clip to a speaker based on diarization data
    clip_speaker_map = {}
    for clip in sorted_clips:
        clip_id, member_id, start_timestamp, end_timestamp = clip
        clip_start = float(start_timestamp) if start_timestamp else 0
        clip_end = float(end_timestamp) if end_timestamp else clip_start + 1
        clip_duration = clip_end - clip_start
        
        # Find the diarization segment that contains this clip
        matching_segment = None
        for segment in diarization_segments:
            segment_start = segment.get('start_time', 0)
            segment_end = segment.get('end_time', 0)
            
            # Check if clip overlaps with this segment
            # A clip is considered part of a segment if it overlaps by at least 50%
            overlap_start = max(clip_start, segment_start)
            overlap_end = min(clip_end, segment_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            
            if overlap_duration > (clip_duration * 0.5):
                matching_segment = segment
                break
        
        if matching_segment:
            segment_speaker = matching_segment.get('speaker', '')
            clip_speaker_map[clip_id] = segment_speaker
            logger.debug(f"Clip {clip_id} ({clip_start}-{clip_end}) assigned to {segment_speaker}")
        else:
            # No matching segment found, assign to None
            clip_speaker_map[clip_id] = None
            logger.debug(f"Clip {clip_id} ({clip_start}-{clip_end}) could not be assigned to any speaker")
    
    # Group clips by speaker
    speaker_clips = {}
    for clip in sorted_clips:
        clip_id = clip[0]
        speaker = clip_speaker_map.get(clip_id)
        if speaker not in speaker_clips:
            speaker_clips[speaker] = []
        speaker_clips[speaker].append(clip)
    
    # Create speech blocks from speaker groups
    speech_blocks = []
    for speaker, speaker_group in speaker_clips.items():
        if speaker is None:
            # For clips without a speaker, use temporal proximity
            temp_blocks = []
            current_block = []
            for clip in sorted(speaker_group, key=lambda c: float(c[2]) if c[2] else 0):
                if not current_block:
                    current_block = [clip]
                else:
                    prev_clip = current_block[-1]
                    prev_end = float(prev_clip[3]) if prev_clip[3] else float(prev_clip[2]) + 1
                    clip_start = float(clip[2]) if clip[2] else 0
                    
                    # Use temporal proximity
                    MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds
                    if clip_start - prev_end <= MAX_CONTINUOUS_SPEECH_GAP:
                        current_block.append(clip)
                    else:
                        temp_blocks.append(current_block)
                        current_block = [clip]
            
            if current_block:
                temp_blocks.append(current_block)
            
            speech_blocks.extend(temp_blocks)
        else:
            # For clips with a speaker, keep them in one group
            # Sort clips within the speaker group by timestamp
            sorted_speaker_group = sorted(speaker_group, key=lambda c: float(c[2]) if c[2] else 0)
            if sorted_speaker_group:
                speech_blocks.append(sorted_speaker_group)
    
    # Sort speech blocks by the start time of their first clip
    speech_blocks.sort(key=lambda block: float(block[0][2]) if block[0][2] else 0)
    
    num_speakers = len(set(segment.get('speaker', '') for segment in diarization_segments))
    logger.info(f"Diarization data contains {num_speakers} distinct speakers")
    logger.info(f"Created {len(speech_blocks)} speech blocks based on speaker changes in diarization data")
    
    # Ensure we're not creating too many blocks
    if len(speech_blocks) > num_speakers and num_speakers > 0:
        logger.warning(f"Created more speech blocks ({len(speech_blocks)}) than speakers ({num_speakers}). This may indicate a problem with grouping.")
    
    # Debug info
    for i, block in enumerate(speech_blocks):
        first_clip = block[0]
        last_clip = block[-1]
        first_start = float(first_clip[2]) if first_clip[2] else 0
        last_end = float(last_clip[3]) if last_clip[3] else 0
        speaker = clip_speaker_map.get(first_clip[0])
        logger.debug(f"Speech block {i}: {len(block)} clips, {first_start}-{last_end}, speaker: {speaker}")
    
    return speech_blocks, clip_speaker_map


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


def update_speech_groups(video_id=None, debug=False):
    """
    Update speech group IDs for clips in the parliament_clips table.
    
    Args:
        video_id: Optional ID of the video to update. If None, update all videos.
        debug: Whether to enable debug logging
    
    Returns:
        Dict with results of the operation
    """
    # Set up logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"Updating speech groups for video_id={video_id}, debug={debug}")
    
    # Connect to the database
    conn = None
    try:
        # Try multiple possible paths for the database
        possible_db_paths = [
            "/app/backend/parliament_clips.db",  # Docker container path
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/parliament_clips.db"),  # Local dev path
            "./backend/parliament_clips.db"  # Relative path
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                logger.info(f"Found database at {db_path}")
                break
                
        if not db_path:
            logger.error(f"Database not found in any of the expected locations: {possible_db_paths}")
            return {"success": False, "error": f"Database not found in any of the expected locations: {possible_db_paths}"}
            
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
                # Try to extract numeric video ID from the path
                filename = os.path.basename(video_path)
                # First try with underscore pattern (e.g., 803_video.mp4)
                if '_' in filename:
                    path_video_id = int(filename.split('_')[0])
                # Then try with just the filename (e.g., 803.mp4)
                else:
                    path_video_id = int(filename.split('.')[0])
                logger.info(f"Extracted video ID: {path_video_id} from path: {video_path}")
            except (ValueError, IndexError):
                path_video_id = hash(video_path) % 10000  # Use a hash if we can't extract an ID
                logger.warning(f"Could not extract video ID from path: {video_path}, using hash: {path_video_id}")
            
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
                    speech_blocks, clip_speaker_map = create_speech_blocks_from_diarization(clips, diarization_data)
                    diarization_used += 1
                    logger.info(f"Using diarization data to create speech groups for {video_path}")
                    
                    # Validate that we have the expected number of speech blocks
                    num_speakers = len(set(segment.get('speaker', '') for segment in diarization_data.get('segments', [])))
                    if num_speakers > 0 and len(speech_blocks) != num_speakers:
                        logger.warning(f"Expected {num_speakers} speech blocks (one per speaker), but created {len(speech_blocks)}. This may indicate a problem with grouping.")
                    
                    # Debug: Print clip to speaker assignments if debug mode is enabled
                    if hasattr(args, 'debug') and args.debug:
                        logger.debug(f"Clip to speaker assignments for {video_path}:")
                        for clip_id, speaker in clip_speaker_map.items():
                            cursor.execute("SELECT start_timestamp, end_timestamp FROM parliament_clips WHERE id = ?", (clip_id,))
                            clip_info = cursor.fetchone()
                            if clip_info:
                                start_time, end_time = clip_info
                                logger.debug(f"  Clip {clip_id} ({start_time}-{end_time}): Speaker {speaker}")
                            else:
                                logger.debug(f"  Clip {clip_id}: Speaker {speaker}")
                    
            
            # If no diarization data or blocks couldn't be created, fall back to temporal proximity
            if not speech_blocks:
                logger.info(f"Falling back to temporal proximity for {video_path}")
                speech_blocks = create_speech_blocks_by_proximity(clips)
            
            logger.info(f"Grouped {len(clips)} clips into {len(speech_blocks)} speech blocks")
            
            # Verify that each speech block has at least one clip
            empty_blocks = [i for i, block in enumerate(speech_blocks) if not block]
            if empty_blocks:
                logger.warning(f"Found {len(empty_blocks)} empty speech blocks: {empty_blocks}")
                # Remove empty blocks
                speech_blocks = [block for block in speech_blocks if block]
            
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
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # If force flag is provided, clear existing speech group IDs for the specified video
    if args.force and args.video_id:
        # Try multiple possible paths for the database
        possible_db_paths = [
            "/app/backend/parliament_clips.db",  # Docker container path
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/parliament_clips.db"),  # Local dev path
            "./backend/parliament_clips.db"  # Relative path
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                break
                
        if not db_path:
            logger.error(f"Database not found in any of the expected locations")
            return
            
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
    
    result = update_speech_groups(args.video_id, args.debug)
    
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
