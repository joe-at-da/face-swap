#!/usr/bin/env python3
"""
Test Speech Group Segmentation

This script tests the speech group segmentation logic by clearing existing clips
and running a new integration test with the updated speech group assignment logic.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Add the parent directory to the path to import local modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import local modules
try:
    # Use relative imports
    from services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
    from services.recognition.multimodal_recognition import MultimodalRecognitionService
    from scripts.validate_transcript_integration import TranscriptValidator
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def run_test():
    """Run the speech group segmentation test."""
    logger.info("=== Starting Speech Group Segmentation Test ===")
    
    # Initialize services
    parliament_clips_service = ParliamentClipsIntegrationService()
    multimodal_recognition = MultimodalRecognitionService()
    validator = TranscriptValidator()
    
    # 1. Clear existing clips
    logger.info("Clearing existing clips...")
    clear_result = parliament_clips_service._clear_all_local_clips()
    if not clear_result.get("success", False):
        logger.error(f"Failed to clear clips: {clear_result.get('errors', [])}")
        return False
    
    logger.info(f"Successfully cleared {clear_result.get('sqlite_clips_removed', 0)} clips")
    
    # 2. Run integration with a test video
    # Use a fixed video ID for testing
    video_id = 1027
    
    # Find a test video file
    test_video_path = "/app/data/media/1027/1027.mp4"
    local_test_video_path = os.path.expanduser("~/Veedoo/Development/the-mp/data/media/1027/1027.mp4")
    
    if os.path.exists(test_video_path):
        video_path = test_video_path
    elif os.path.exists(local_test_video_path):
        video_path = local_test_video_path
    else:
        logger.error(f"Test video not found at {test_video_path} or {local_test_video_path}")
        return False
    
    logger.info(f"Using test video: {video_path}")
    
    # 3. Run the recognition process
    logger.info(f"Starting recognition for video ID {video_id}...")
    recognition_result = multimodal_recognition.start_combined_recognition(video_id)
    
    if not recognition_result.get("success", False):
        logger.error(f"Recognition failed: {recognition_result.get('error', 'Unknown error')}")
        return False
    
    logger.info("Recognition completed successfully")
    
    # 4. Validate the results
    logger.info("Validating speech group segmentation...")
    validation_result = validator.validate_video_clips(video_id)
    
    if not validation_result.get("success", False):
        logger.error(f"Validation failed: {validation_result.get('error', 'Unknown error')}")
        return False
    
    # 5. Analyze the results
    total_clips = validation_result.get("total_clips", 0)
    speech_group_count = validation_result.get("speech_group_count", 0)
    avg_clips_per_group = validation_result.get("avg_clips_per_group", 0)
    
    logger.info(f"Total clips: {total_clips}")
    logger.info(f"Speech group count: {speech_group_count}")
    logger.info(f"Average clips per group: {avg_clips_per_group:.2f}")
    
    # Check if segmentation is correct (one clip per speech group)
    segmentation_correct = avg_clips_per_group <= 1.1  # Allow slight variance
    
    if segmentation_correct:
        logger.info("✅ Speech group segmentation is correct (one clip per speech group)")
    else:
        logger.warning("❌ Speech group segmentation is incorrect (multiple clips per speech group)")
        
        # Print group sizes for debugging
        group_sizes = validation_result.get("group_sizes", {})
        logger.info("Speech group sizes:")
        for group_id, size in group_sizes.items():
            logger.info(f"  {group_id}: {size} clips")
    
    # Print full validation results
    logger.info("Full validation results:")
    print(json.dumps(validation_result, indent=2))
    
    return segmentation_correct

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
