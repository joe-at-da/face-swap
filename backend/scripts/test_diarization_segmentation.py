#!/usr/bin/env python3
"""
Test Diarization Segmentation

This script tests the diarization-driven segmentation logic by clearing existing clips
and running a new integration test with the updated segmentation logic.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import local modules
try:
    from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
    from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def run_test():
    """Run the diarization segmentation test."""
    logger.info("=== Starting Diarization Segmentation Test ===")
    
    # Initialize services
    parliament_clips_service = ParliamentClipsIntegrationService()
    multimodal_recognition = MultimodalRecognitionService()
    
    # 1. Clear existing clips
    logger.info("Clearing existing clips...")
    clear_result = parliament_clips_service._clear_all_local_clips()
    if not clear_result.get("success", False):
        logger.error(f"Failed to clear clips: {clear_result.get('errors', [])}")
        return False
    
    logger.info(f"Successfully cleared {clear_result.get('sqlite_clips_removed', 0)} clips")
    
    # 2. Run integration with a test video
    # Use video ID 1048 which is available in the Docker container
    video_id = 1048
    
    # Find the test video file
    test_video_path = f"/app/data/media/{video_id}.mp4"
    
    if not os.path.exists(test_video_path):
        logger.error(f"Test video not found at {test_video_path}")
        return False
    
    logger.info(f"Using test video: {test_video_path}")
    
    # 3. Run the recognition process
    logger.info(f"Starting recognition for video ID {video_id}...")
    recognition_result = multimodal_recognition.start_combined_recognition(video_id)
    
    if not recognition_result.get("success", False):
        logger.error(f"Recognition failed: {recognition_result.get('error', 'Unknown error')}")
        return False
    
    logger.info("Recognition completed successfully")
    
    # 4. Analyze the results
    logger.info("Analyzing speech group segmentation...")
    
    # Connect to the SQLite database
    import sqlite3
    db_path = parliament_clips_service.db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query to get all clips for this video using full_video_path
    video_path_pattern = f"%{video_id}.mp4"
    cursor.execute(
        "SELECT id, full_video_path, start_timestamp, end_timestamp, transcript, member_id, speech_group_id FROM parliament_clips WHERE full_video_path LIKE ?",
        (video_path_pattern,)
    )
    clips = cursor.fetchall()
    
    # Query to get unique speech group IDs
    cursor.execute(
        "SELECT DISTINCT speech_group_id FROM parliament_clips WHERE full_video_path LIKE ?",
        (video_path_pattern,)
    )
    speech_groups = cursor.fetchall()
    
    # Count clips per speech group
    clips_per_group = {}
    for clip in clips:
        speech_group_id = clip[6]  # Index 6 is speech_group_id
        if speech_group_id not in clips_per_group:
            clips_per_group[speech_group_id] = 0
        clips_per_group[speech_group_id] += 1
    
    # Calculate statistics
    total_clips = len(clips)
    speech_group_count = len(speech_groups)
    avg_clips_per_group = total_clips / speech_group_count if speech_group_count > 0 else 0
    
    logger.info(f"Total clips: {total_clips}")
    logger.info(f"Speech group count: {speech_group_count}")
    logger.info(f"Average clips per group: {avg_clips_per_group:.2f}")
    
    # Check if segmentation is correct (one clip per speech group)
    segmentation_correct = avg_clips_per_group <= 1.1  # Allow slight variance
    
    if segmentation_correct:
        logger.info("✅ Segmentation is correct: One clip per speech group")
    else:
        logger.error("❌ Segmentation is incorrect: Multiple clips per speech group")
        
        # Print details of speech groups with multiple clips
        for group_id, count in clips_per_group.items():
            if count > 1:
                logger.error(f"Speech group {group_id} has {count} clips")
                
                # Get clips for this speech group
                cursor.execute(
                    "SELECT id, start_time, end_time, transcript FROM parliament_clips WHERE speech_group_id = ?",
                    (group_id,)
                )
                group_clips = cursor.fetchall()
                
                for clip in group_clips:
                    clip_id, start_time, end_time, transcript = clip
                    logger.error(f"  Clip {clip_id}: {start_time}-{end_time}, Transcript: {transcript[:50]}...")
    
    # Check for placeholder transcripts
    cursor.execute(
        "SELECT COUNT(*) FROM parliament_clips WHERE full_video_path LIKE ? AND transcript LIKE 'Speech segment from%'",
        (video_path_pattern,)
    )
    placeholder_count = cursor.fetchone()[0]
    placeholder_percentage = (placeholder_count / total_clips) * 100 if total_clips > 0 else 0
    
    logger.info(f"Placeholder transcripts: {placeholder_count}/{total_clips} ({placeholder_percentage:.2f}%)")
    
    if placeholder_percentage > 50:
        logger.warning("⚠️ High percentage of placeholder transcripts")
    
    # Close the database connection
    conn.close()
    
    return segmentation_correct

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
