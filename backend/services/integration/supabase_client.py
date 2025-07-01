"""
Supabase client configuration and utilities for Parliament TV integration.
This module provides a configured Supabase client and helper functions
for working with Supabase storage, database, and queues.
"""

import os
import logging
from typing import Dict, Any, Optional, List

from supabase import create_client, Client
from backend.core.config import settings

logger = logging.getLogger(__name__)

def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Create and return a configured Supabase client.
    Uses SUPABASE_URL and SUPABASE_API_KEY from environment variables.
    
    Args:
        use_service_role: If True, use the service role key instead of the anon key
                         Service role has admin privileges and should be used for
                         server-side operations only.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY if use_service_role else settings.SUPABASE_API_KEY
    
    if not url or not key:
        raise ValueError(
            "Supabase URL and API key must be set in environment variables "
            "(SUPABASE_URL and SUPABASE_API_KEY or SUPABASE_SERVICE_ROLE_KEY)"
        )
    
    return create_client(url, key)


class SupabaseService:
    """Service for interacting with Supabase."""
    
    def __init__(self, use_service_role: bool = True):
        """
        Initialize the Supabase service.
        
        Args:
            use_service_role: If True, use the service role key for admin privileges
                             This is required for storage operations and should be
                             used for server-side operations only.
        """
        self.client = get_supabase_client(use_service_role=use_service_role)
        self.media_bucket = settings.SUPABASE_MEDIA_BUCKET
        self.export_bucket = settings.SUPABASE_EXPORT_BUCKET
        self.full_videos_bucket = settings.SUPABASE_FULL_VIDEOS_BUCKET
    
    # Database operations
    
    def insert_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert video data into Supabase 'videos' table.
        
        Args:
            video_data: Dictionary containing video metadata
            
        Returns:
            Response from Supabase
        """
        return self.client.table('videos').insert(video_data).execute()
    
    def insert_clip(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert clip data into Supabase 'clips' table.
        
        Args:
            clip_data: Dictionary containing clip metadata
            
        Returns:
            Response from Supabase
        """
        return self.client.table('clips').insert(clip_data).execute()
    
    def get_video_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video status from Supabase.
        
        Args:
            video_id: ID of the video to check
            
        Returns:
            Video data if found, None otherwise
        """
        response = self.client.table('videos').select('*').eq('video_id', video_id).execute()
        data = response.data
        
        if data and len(data) > 0:
            return data[0]
        return None
    
    # Storage operations
    
    def upload_file(self, bucket: str, path: str, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: Destination path in the bucket
            file_path: Local file path to upload
            
        Returns:
            Response from Supabase Storage
        """
        with open(file_path, 'rb') as f:
            return self.client.storage.from_(bucket).upload(path, f)
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """
        Get public URL for a file in Supabase Storage.
        
        Args:
            bucket: Storage bucket name
            path: Path to the file in the bucket
            
        Returns:
            Public URL for the file
        """
        return self.client.storage.from_(bucket).get_public_url(path)
        
    def upload_full_video(self, file_path: str, destination_path: str) -> Dict[str, Any]:
        """Upload a full video file to Supabase storage."""
        if not file_path:
            logger.warning("Video file path is None")
            return {"success": False, "error": "File path is None"}
            
        # Check if the file exists with the provided path
        if not os.path.exists(file_path):
            # Try alternative naming pattern
            # If the path is like /app/data/media/parliament_tv_467.mp4, try /app/data/media/467.mp4
            if 'parliament_tv_' in file_path:
                capture_id = file_path.split('parliament_tv_')[-1].split('.')[0]
                alternative_path = os.path.join(os.path.dirname(file_path), f"{capture_id}.mp4")
                if os.path.exists(alternative_path):
                    logger.info(f"Using alternative file path: {alternative_path}")
                    file_path = alternative_path
                else:
                    logger.warning(f"Video file not found at either path: {file_path} or {alternative_path}")
                    return {"success": False, "error": f"File not found: {file_path}"}
            else:
                logger.warning(f"Video file not found: {file_path}")
                return {"success": False, "error": f"File not found: {file_path}"}
            
        # Use the file's basename if no destination path is provided
        if destination_path is None:
            destination_path = os.path.basename(file_path)
            
        # Ensure we're using the service role key for admin access
        if not self.client.auth.get_session():
            # Re-initialize with service role if needed
            self.client = get_supabase_client(use_service_role=True)
            
        try:
            with open(file_path, 'rb') as f:
                # Use file_options to set cache control and upsert behavior
                response = self.client.storage.from_(self.full_videos_bucket).upload(
                    path=destination_path,
                    file=f,
                    file_options={"cache-control": "3600", "upsert": "true"}
                )
                
            # Get the public URL for the uploaded file
            public_url = self.client.storage.from_(self.full_videos_bucket).get_public_url(destination_path)
            
            return {
                "success": True,
                "path": destination_path,
                "public_url": public_url,
                "response": response
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    # Queue operations
    
    def add_to_video_processing_queue(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a job to the video_processing queue.
        
        Args:
            video_data: Video data to process
            
        Returns:
            Response from Supabase
        """
        return self.client.table('video_processing_queue').insert(video_data).execute()
    
    def add_to_clip_creation_queue(self, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add jobs to the clip_creation queue.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        return self.client.table('clip_creation_queue').insert(clip_data).execute()
