#!/usr/bin/env python
"""
Test script for uploading a video to Supabase storage.
This script verifies that the Supabase integration is working correctly.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.integration.supabase_client import SupabaseService
from backend.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_supabase_upload(video_path: str = None):
    """
    Test uploading a video to Supabase storage.
    
    Args:
        video_path: Path to the video file to upload. If None, uses a test video.
    """
    try:
        # Initialize Supabase service with service role key
        logger.info("Initializing Supabase service with service role key")
        supabase = SupabaseService(use_service_role=True)
        
        # Use a test video if no path is provided
        if not video_path:
            # Look for a video file in the media directory
            media_dir = Path("/app/data/media")
            if not media_dir.exists():
                logger.warning(f"Media directory {media_dir} does not exist, using a local path")
                media_dir = Path("./data/media")
                if not media_dir.exists():
                    logger.error(f"Media directory {media_dir} does not exist")
                    return False
            
            # Find the first MP4 file in the media directory
            video_files = list(media_dir.glob("*.mp4"))
            if not video_files:
                logger.error(f"No MP4 files found in {media_dir}")
                return False
            
            video_path = str(video_files[0])
            logger.info(f"Using video file: {video_path}")
        
        # Check if the file exists
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        # Upload the video to Supabase storage
        logger.info(f"Uploading video to Supabase storage: {video_path}")
        result = supabase.upload_full_video(video_path)
        
        # Check the result
        if result.get("success", False):
            logger.info(f"Upload successful: {result}")
            logger.info(f"Public URL: {result.get('public_url')}")
            return True
        else:
            logger.error(f"Upload failed: {result}")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing Supabase upload: {str(e)}")
        return False

if __name__ == "__main__":
    # Get video path from command line argument if provided
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run the test
    success = test_supabase_upload(video_path)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
