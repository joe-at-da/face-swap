#!/usr/bin/env python3
"""
Test Facial Recognition

This script tests the facial recognition system by processing a video file
and identifying speakers using the facial recognition service.

Usage:
    python test_facial_recognition.py --video /path/to/video.mp4

Example:
    python test_facial_recognition.py --video /app/data/temp/parliament_video.mp4
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path

# Add the parent directory to the path so we can import from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.services.recognition.facial_recognition import FacialRecognitionService
except ImportError:
    print("Error: Could not import backend modules. Make sure you're running this script from the project root.")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_facial_recognition")

def test_facial_recognition(video_path):
    """
    Test facial recognition on a video file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dict with test results
    """
    try:
        logger.info(f"Testing facial recognition on video: {video_path}")
        
        # Initialize the facial recognition service
        facial_recognition_service = FacialRecognitionService()
        
        # Load the MP database
        load_result = facial_recognition_service.load_mp_database()
        if not load_result["success"]:
            logger.error(f"Failed to load MP database: {load_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": f"Failed to load MP database: {load_result.get('error', 'Unknown error')}"
            }
        
        logger.info("MP database loaded successfully")
        
        # Process the video to detect faces
        detect_result = facial_recognition_service.detect_faces_in_video(video_path)
        if not detect_result["success"]:
            logger.error(f"Failed to detect faces: {detect_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": f"Failed to detect faces: {detect_result.get('error', 'Unknown error')}"
            }
        
        logger.info("Face detection completed successfully")
        
        # Identify speakers in the video
        identify_result = facial_recognition_service.identify_speakers(video_path)
        if not identify_result["success"]:
            logger.error(f"Failed to identify speakers: {identify_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": f"Failed to identify speakers: {identify_result.get('error', 'Unknown error')}"
            }
        
        logger.info("Speaker identification completed successfully")
        
        # Return the results
        return {
            "success": True,
            "detect_result": detect_result,
            "identify_result": identify_result
        }
    
    except Exception as e:
        logger.exception(f"Error testing facial recognition: {str(e)}")
        return {
            "success": False,
            "error": f"Error testing facial recognition: {str(e)}"
        }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test facial recognition")
    parser.add_argument("--video", required=True, help="Path to the video file")
    
    args = parser.parse_args()
    
    # Test facial recognition
    result = test_facial_recognition(args.video)
    
    if result["success"]:
        logger.info("Facial recognition test completed successfully")
        
        # Print the results
        if "identify_result" in result and "results" in result["identify_result"]:
            speakers = result["identify_result"]["results"].get("speakers", [])
            logger.info(f"Identified {len(speakers)} speakers:")
            
            for i, speaker in enumerate(speakers):
                logger.info(f"  {i+1}. {speaker['name']} - Confidence: {speaker['confidence']:.2f}, Duration: {speaker['duration']:.2f}s")
        
        return 0
    else:
        logger.error(f"Facial recognition test failed: {result.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
