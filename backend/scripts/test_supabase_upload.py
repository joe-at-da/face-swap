#!/usr/bin/env python
"""
Test script for uploading a combined AV video to Supabase storage.
This script verifies that the fixed Supabase upload implementation is working correctly with
combined AV files, which are the primary use case for the application.

This version uses the new SupabaseUploader class which fixes issues with base_url and headers.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.integration.supabase_upload import SupabaseUploader
from backend.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_supabase_upload(video_path: str = None, method: str = 'auto', bucket: str = 'videos', chunk_size: int = 5 * 1024 * 1024):
    """
    Test uploading a combined AV video to Supabase storage using the fixed SupabaseUploader class.
    
    Args:
        video_path: Path to the combined AV file to upload. If None, uses the latest combined AV file.
        method: Upload method to use ('direct', 'chunked', or 'auto').
        bucket: Supabase storage bucket to upload to.
        chunk_size: Size of chunks for chunked upload in bytes (default: 5MB).
    """
    start_time = time.time()
    try:
        # Initialize SupabaseUploader with service role key
        logger.info("Initializing SupabaseUploader with service role key")
        uploader = SupabaseUploader()
        
        # Use the latest combined AV file if no path is provided
        if not video_path:
            # Look for combined AV files in the media directory
            media_dir = Path("/app/data/media")
            if not media_dir.exists():
                logger.warning(f"Media directory {media_dir} does not exist, using a local path")
                media_dir = Path("./data/media")
                if not media_dir.exists():
                    logger.error(f"Media directory {media_dir} does not exist")
                    return False
            
            # Find the latest combined AV file in the media directory
            combined_av_files = sorted(list(media_dir.glob("combined_av_*.mp4")), key=lambda x: x.stat().st_mtime, reverse=True)
            if not combined_av_files:
                logger.error(f"No combined AV files found in {media_dir}")
                return False
            
            video_path = str(combined_av_files[0])
            logger.info(f"Using latest combined AV file: {video_path}")
        
        # Check if the file exists
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        file_size = os.path.getsize(video_path)
        logger.info(f"File size: {file_size / (1024 * 1024):.2f} MB")
        
        # Get file name for destination path
        file_name = os.path.basename(video_path)
        destination_path = f"test/{file_name}"
        
        # Upload the video to Supabase storage using the specified method
        logger.info(f"Uploading video to Supabase storage: {video_path}")
        logger.info(f"Using method: {method}, bucket: {bucket}, chunk size: {chunk_size / (1024 * 1024):.2f} MB")
        
        if method == 'direct':
            result = uploader.upload_large_video(file_path=video_path, destination_path=destination_path, bucket=bucket)
        elif method == 'chunked':
            result = uploader.upload_chunked_video(file_path=video_path, destination_path=destination_path, chunk_size=chunk_size, bucket=bucket)
        else:  # auto or any other value
            result = uploader.upload_full_video(file_path=video_path, destination_path=destination_path, chunk_size=chunk_size, bucket=bucket)
        
        # Check the result
        if result.get("success", False):
            elapsed_time = time.time() - start_time
            logger.info(f"Upload successful in {elapsed_time:.2f} seconds")
            logger.info(f"Public URL: {result.get('public_url')}")
            return True
        else:
            logger.error(f"Upload failed: {result}")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing Supabase upload: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Test Supabase upload with fixed implementation for combined AV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
        Examples:
          # Upload the latest combined AV file using automatic method selection
          python backend/scripts/test_supabase_upload.py
          
          # Upload a specific combined AV file using direct upload
          python backend/scripts/test_supabase_upload.py -f data/media/combined_av_818_20250720_180733.mp4 -m direct
          
          # Upload to a different bucket with custom chunk size
          python backend/scripts/test_supabase_upload.py -b full_videos -c 10485760
        '''
    )
    parser.add_argument('--file', '-f', dest='video_path', 
                      help='Path to combined AV file to upload (defaults to latest combined_av_*.mp4)')
    parser.add_argument('--method', '-m', dest='method', choices=['auto', 'direct', 'chunked'], default='auto',
                      help='Upload method to use: auto (based on file size), direct (extended timeout), or chunked')
    parser.add_argument('--bucket', '-b', dest='bucket', default='videos',
                      help='Supabase storage bucket to upload to (default: videos)')
    parser.add_argument('--chunk-size', '-c', dest='chunk_size', type=int, default=5 * 1024 * 1024,
                      help='Size of chunks for chunked upload in bytes (default: 5MB)')
    
    args = parser.parse_args()
    
    # Run the test with the provided arguments
    success = test_supabase_upload(
        video_path=args.video_path,
        method=args.method,
        bucket=args.bucket,
        chunk_size=args.chunk_size
    )
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
