#!/usr/bin/env python3
"""
Validate Diarization Segmentation

This script validates the diarization-driven segmentation fix by directly analyzing
the parliament_clips database to check if clips are properly segmented by speaker turns.
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_segmentation():
    """Validate the diarization segmentation by analyzing the database."""
    logger.info("=== Starting Diarization Segmentation Validation ===")
    
    # Determine database path
    if os.path.exists("/app/backend/parliament_clips.db"):
        db_path = "/app/backend/parliament_clips.db"
    else:
        # Local development path
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = base_dir / "parliament_clips.db"
    
    logger.info(f"Using database at: {db_path}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all video IDs in the database
    cursor.execute(
        "SELECT DISTINCT full_video_path FROM parliament_clips"
    )
    video_paths = cursor.fetchall()
    
    if not video_paths:
        logger.error("No videos found in the database")
        return False
    
    logger.info(f"Found {len(video_paths)} videos in the database")
    
    # Analyze each video
    for video_path in video_paths:
        video_path = video_path[0]
        video_id = os.path.basename(video_path).split('.')[0] if video_path else "unknown"
        
        logger.info(f"\n=== Analyzing video: {video_id} ({video_path}) ===")
        
        # Get all clips for this video
        cursor.execute(
            "SELECT id, full_video_path, start_timestamp, end_timestamp, transcript, member_id, speech_group_id FROM parliament_clips WHERE full_video_path = ?",
            (video_path,)
        )
        clips = cursor.fetchall()
        
        if not clips:
            logger.warning(f"No clips found for video {video_id}")
            continue
        
        logger.info(f"Found {len(clips)} clips for video {video_id}")
        
        # Get unique speech group IDs
        cursor.execute(
            "SELECT DISTINCT speech_group_id FROM parliament_clips WHERE full_video_path = ?",
            (video_path,)
        )
        speech_groups = cursor.fetchall()
        speech_groups = [sg[0] for sg in speech_groups]
        
        logger.info(f"Found {len(speech_groups)} unique speech groups")
        
        # Count clips per speech group
        clips_per_group = defaultdict(int)
        for clip in clips:
            speech_group_id = clip[6]  # Index 6 is speech_group_id
            clips_per_group[speech_group_id] += 1
        
        # Check if we have multiple clips per speech group (incorrect segmentation)
        multiple_clips_groups = [sg for sg, count in clips_per_group.items() if count > 1]
        if multiple_clips_groups:
            logger.error(f"Found {len(multiple_clips_groups)} speech groups with multiple clips:")
            for sg in multiple_clips_groups[:5]:  # Show first 5
                logger.error(f"  - Speech group {sg}: {clips_per_group[sg]} clips")
            logger.error("This indicates incorrect segmentation - should be one clip per speech group")
        else:
            logger.info("All speech groups have exactly one clip - correct segmentation!")
        
        # Check for placeholder transcripts
        placeholder_count = 0
        for clip in clips:
            transcript = clip[4]  # Index 4 is transcript
            if not transcript or "Speech segment from" in transcript:
                placeholder_count += 1
        
        if placeholder_count > 0:
            placeholder_percent = (placeholder_count / len(clips)) * 100
            logger.warning(f"Found {placeholder_count} clips ({placeholder_percent:.1f}%) with placeholder transcripts")
        else:
            logger.info("No placeholder transcripts found - all clips have proper transcripts!")
        
        # Check for proper speech group IDs
        diarization_groups = [sg for sg in speech_groups if "diarization" in sg.lower()]
        if diarization_groups:
            logger.info(f"Found {len(diarization_groups)} speech groups with diarization-based IDs")
        else:
            logger.warning("No diarization-based speech group IDs found")
        
        # Check for proper member IDs
        unique_member_ids = set()
        for clip in clips:
            member_id = clip[5]  # Index 5 is member_id
            if member_id:
                unique_member_ids.add(member_id)
        
        logger.info(f"Found {len(unique_member_ids)} unique member IDs")
        
        # Check for proper start/end timestamps
        start_times = [float(clip[2]) for clip in clips if clip[2]]
        end_times = [float(clip[3]) for clip in clips if clip[3]]
        
        if start_times and end_times:
            min_start = min(start_times)
            max_end = max(end_times)
            total_duration = max_end - min_start
            
            logger.info(f"Clip time range: {min_start:.2f}s to {max_end:.2f}s (duration: {total_duration:.2f}s)")
            
            # Check for large gaps in timestamps
            sorted_clips = sorted(clips, key=lambda x: float(x[2]) if x[2] else 0)
            large_gaps = []
            
            for i in range(1, len(sorted_clips)):
                prev_end = float(sorted_clips[i-1][3]) if sorted_clips[i-1][3] else 0
                curr_start = float(sorted_clips[i][2]) if sorted_clips[i][2] else 0
                gap = curr_start - prev_end
                
                if gap > 5.0:  # Gap larger than 5 seconds
                    large_gaps.append((i-1, i, gap))
            
            if large_gaps:
                logger.warning(f"Found {len(large_gaps)} large gaps between clips:")
                for prev_idx, curr_idx, gap in large_gaps[:5]:  # Show first 5
                    logger.warning(f"  - Gap of {gap:.2f}s between clips {prev_idx} and {curr_idx}")
            else:
                logger.info("No large gaps between clips - continuous segmentation!")
    
    conn.close()
    logger.info("=== Diarization Segmentation Validation Complete ===")
    return True

if __name__ == "__main__":
    success = validate_segmentation()
    sys.exit(0 if success else 1)
