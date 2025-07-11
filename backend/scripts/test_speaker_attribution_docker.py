#!/usr/bin/env python3
"""
Script to test the improved speaker attribution in the Docker container.
This script runs the speaker attribution pipeline on a real video and
analyzes the member ID distribution in the recognition events.
"""

import os
import sys
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the app directory to the path for Docker environment
sys.path.append('/app')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_speaker_attribution_test(video_path: str, output_dir: str):
    """
    Run the speaker attribution pipeline on a real video.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to store output files
    """
    logger.info(f"Running speaker attribution test on {video_path}...")
    
    # Import necessary modules
    try:
        from backend.db.database import get_db
        from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
        from backend.services.integration.parliament_clips_integration import ParliamentClipsIntegrationService
    except ImportError as e:
        logger.error(f"Error importing modules: {e}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create services
        multimodal_service = MultimodalRecognitionService()
        clips_service = ParliamentClipsIntegrationService()
        
        # Generate a unique video ID
        video_id = int(time.time())
        
        # Process the video
        logger.info(f"Processing video with ID {video_id}...")
        result = multimodal_service.process_video_with_transcription(
            db=db,
            video_path=video_path,
            output_dir=output_dir,
            video_id=video_id,
            save_clips=True
        )
        
        if not result["success"]:
            logger.error(f"Failed to process video: {result.get('error')}")
            return False
        
        # Get recognition events
        recognition_events = result.get("recognition_events", [])
        logger.info(f"Generated {len(recognition_events)} recognition events")
        
        # Analyze member ID distribution
        member_ids = {}
        for event in recognition_events:
            member_id = event.get("member_id")
            if member_id:
                member_ids[member_id] = member_ids.get(member_id, 0) + 1
        
        logger.info("Member ID distribution in recognition events:")
        for member_id, count in sorted(member_ids.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"Member ID {member_id}: {count} events")
        
        # Check if we have a diverse set of member IDs
        if len(member_ids) > 1:
            logger.info("✅ Multiple member IDs detected - speaker attribution is working correctly")
        else:
            logger.warning("⚠️ Only one member ID detected - speaker attribution may still have issues")
            
        # Analyze confidence distribution
        confidence_values = [event.get("confidence", 0) for event in recognition_events if event.get("member_id")]
        if confidence_values:
            avg_confidence = sum(confidence_values) / len(confidence_values)
            min_confidence = min(confidence_values)
            max_confidence = max(confidence_values)
            logger.info(f"Confidence stats: avg={avg_confidence:.4f}, min={min_confidence:.4f}, max={max_confidence:.4f}")
            
        # Analyze confidence gap distribution
        gap_values = [event.get("confidence_gap", 0) for event in recognition_events if event.get("member_id")]
        if gap_values:
            avg_gap = sum(gap_values) / len(gap_values)
            min_gap = min(gap_values)
            max_gap = max(gap_values)
            logger.info(f"Confidence gap stats: avg={avg_gap:.4f}, min={min_gap:.4f}, max={max_gap:.4f}")
        
        # Save recognition events to parliament_clips
        clips_result = clips_service.save_recognition_events_to_parliament_clips(
            video_id=video_id,
            recognition_events=recognition_events,
            video_path=video_path
        )
        
        if clips_result["success"]:
            logger.info(f"✅ Successfully saved {clips_result.get('inserted', 0)} clips to parliament_clips")
        else:
            logger.error(f"Failed to save clips: {clips_result.get('error')}")
        
        # Save results to JSON file for analysis
        results_file = os.path.join(output_dir, f"speaker_attribution_results_{video_id}.json")
        with open(results_file, "w") as f:
            json.dump({
                "video_id": video_id,
                "timestamp": datetime.now().isoformat(),
                "recognition_events": recognition_events,
                "member_id_distribution": {str(k): v for k, v in member_ids.items()},
                "clips_saved": clips_result.get("inserted", 0)
            }, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error running speaker attribution test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to test improved speaker attribution."""
    logger.info("Starting improved speaker attribution test...")
    
    # Define test parameters
    video_path = "/app/data/media/713.mp4"  # Use actual Parliament TV video
    output_dir = "/app/data/test_output"
    
    # Check if video exists
    if not os.path.exists(video_path):
        logger.error(f"Test video not found: {video_path}")
        logger.info("Please provide a path to a real Parliament TV video:")
        video_path = input("Video path: ").strip()
        
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            sys.exit(1)
    
    # Run the test
    success = run_speaker_attribution_test(video_path, output_dir)
    
    if success:
        logger.info("✅ Speaker attribution test completed successfully")
    else:
        logger.error("❌ Speaker attribution test failed")
    
if __name__ == "__main__":
    main()
