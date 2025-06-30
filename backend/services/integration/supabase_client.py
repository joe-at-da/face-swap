"""
Supabase client configuration and utilities for Parliament TV integration.
This module provides a configured Supabase client and helper functions
for working with Supabase storage, database, and queues.
"""

import os
from typing import Dict, Any, Optional

from supabase import create_client, Client
from backend.core.config import settings

def get_supabase_client() -> Client:
    """
    Create and return a configured Supabase client.
    Uses SUPABASE_URL and SUPABASE_API_KEY from environment variables.
    """
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_API_KEY
    
    if not url or not key:
        raise ValueError(
            "Supabase URL and API key must be set in environment variables "
            "(SUPABASE_URL and SUPABASE_API_KEY)"
        )
    
    return create_client(url, key)


class SupabaseService:
    """Service for interacting with Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
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
    
    def add_to_clip_creation_queue(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a job to the clip_creation queue.
        
        Args:
            clip_data: Clip data to process
            
        Returns:
            Response from Supabase
        """
        return self.client.table('clip_creation_queue').insert(clip_data).execute()
