#!/usr/bin/env python
"""
Utility script to upload full videos to Supabase storage.

Usage:
    python upload_full_video_to_supabase.py <video_file_path> [destination_path]

Example:
    python upload_full_video_to_supabase.py /path/to/combined_av_396_20250628_173955.mp4
"""

import os
import sys
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings
from backend.services.integration.supabase_upload import SupabaseUploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_video_from_api(video_id: str, output_path: str) -> Optional[str]:
    """
    Download a video from the API and save it to the specified path.
    
    Args:
        video_id: ID of the video to download
        output_path: Path to save the downloaded video
        
    Returns:
        Path to the downloaded video if successful, None otherwise
    """
    try:
        # Construct the API URL
        base_url = "http://localhost:8000"  # Change this to your actual API URL
        api_url = f"{base_url}/media/file?path=combined_av_{video_id}.mp4"
        
        logger.info(f"Downloading video from {api_url}")
        
        # Make the request
        response = requests.get(api_url, stream=True)
        response.raise_for_status()
        
        # Save the file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Video downloaded successfully to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return None

def upload_video_to_supabase(file_path: str, destination_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Upload a video to Supabase storage.
    
    Args:
        file_path: Path to the video file
        destination_path: Path in the bucket where the file should be stored
        
    Returns:
        Response from Supabase Storage with upload details
    """
    try:
        logger.info(f"Uploading video {file_path} to Supabase")
        
        # Initialize Supabase uploader with service role key and extended timeout (1 hour)
        supabase = SupabaseUploader(use_service_role=True, timeout=3600)
        
        # Upload the video to the full_videos bucket
        result = supabase.upload_full_video(file_path=file_path, destination_path=destination_path, bucket="full_videos")
        
        if result["success"]:
            logger.info(f"Video uploaded successfully to {result['path']}")
            logger.info(f"Public URL: {result['public_url']}")
        else:
            logger.error(f"Failed to upload video: {result['error']}")
            
        return result
    except Exception as e:
        logger.error(f"Error uploading video to Supabase: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    """Main function to handle command line arguments and execute the upload."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <video_file_path_or_id> [destination_path]")
        sys.exit(1)
        
    # Check if Supabase integration is enabled
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        logger.error("Supabase integration is not enabled. Set SUPABASE_INTEGRATION_ENABLED=true in your .env file.")
        sys.exit(1)
        
    video_path_or_id = sys.argv[1]
    destination_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check if the input is a file path or a video ID
    if os.path.exists(video_path_or_id):
        # It's a file path
        file_path = video_path_or_id
    else:
        # Assume it's a video ID, try to download it
        logger.info(f"Video file not found, assuming {video_path_or_id} is a video ID")
        temp_path = os.path.join(settings.TEMP_STORAGE_PATH, f"combined_av_{video_path_or_id}.mp4")
        file_path = download_video_from_api(video_path_or_id, temp_path)
        
        if not file_path:
            logger.error("Failed to download video")
            sys.exit(1)
    
    # Upload the video to Supabase
    result = upload_video_to_supabase(file_path, destination_path)
    
    # Clean up temporary file if we downloaded it
    if video_path_or_id != file_path and os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Removed temporary file {file_path}")
    
    if result["success"]:
        logger.info("Upload completed successfully")
        sys.exit(0)
    else:
        logger.error("Upload failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
