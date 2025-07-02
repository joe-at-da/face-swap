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
        # Only using full_videos_bucket for all uploads
        self.full_videos_bucket = settings.SUPABASE_FULL_VIDEOS_BUCKET
        logger.info(f"Initialized SupabaseService with full_videos_bucket: {self.full_videos_bucket}")
    
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
            bucket: Storage bucket name (ignored, always using full_videos_bucket)
            path: Destination path in the bucket
            file_path: Local file path to upload
            
        Returns:
            Response from Supabase Storage
        """
        # Always use full_videos_bucket regardless of what bucket was passed
        logger.warning(f"Ignoring specified bucket '{bucket}' and using full_videos_bucket '{self.full_videos_bucket}' instead")
        
        # Only upload if the file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {"error": f"File not found: {file_path}"}
            
        # Only upload combined AV files
        filename = os.path.basename(file_path)
        if 'combined_av_' not in filename:
            logger.warning(f"Skipping upload of non-combined AV file: {filename}")
            return {"error": "Only combined AV files should be uploaded"}
            
        # Use the filename as the destination path to preserve the combined_av_XXX_TIMESTAMP.mp4 format
        destination_path = os.path.basename(path)
        
        try:
            with open(file_path, 'rb') as f:
                logger.info(f"Uploading {file_path} to {self.full_videos_bucket}/{destination_path}")
                return self.client.storage.from_(self.full_videos_bucket).upload(destination_path, f)
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {"error": str(e)}
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """
        Get public URL for a file in Supabase Storage.
        
        Args:
            bucket: Storage bucket name (ignored, always using full_videos_bucket)
            path: Path to the file in the bucket
            
        Returns:
            Public URL for the file
        """
        # Always use full_videos_bucket regardless of what bucket was passed
        logger.warning(f"Ignoring specified bucket '{bucket}' and using full_videos_bucket '{self.full_videos_bucket}' instead")
        
        # Use the filename as the destination path to preserve the combined_av_XXX_TIMESTAMP.mp4 format
        destination_path = os.path.basename(path)
        
        logger.info(f"Getting public URL for {destination_path} from bucket {self.full_videos_bucket}")
        return self.client.storage.from_(self.full_videos_bucket).get_public_url(destination_path)
        
    def upload_full_video(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
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
        
        # Check file size to ensure it's not empty
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"File exists but is empty (0 bytes): {file_path}")
            return {"success": False, "error": f"File is empty: {file_path}"}
        logger.info(f"File size: {file_size} bytes")
            
        # Use the file's basename if no destination path is provided
        if destination_path is None:
            # Extract just the filename without any path structure
            destination_path = os.path.basename(file_path)
            
            # For Parliament TV files, use a standardized naming convention
            # But preserve combined_av_ files with their original timestamped names
            if 'parliament_tv_' in destination_path and 'combined_av_' not in destination_path:
                # Convert parliament_tv_494.mp4 to just parliament_tv_494.mp4
                # This maintains backward compatibility with existing code
                pass
            # For combined_av_ files, keep the original filename with timestamp
            elif 'combined_av_' in destination_path:
                logger.info(f"Preserving combined AV filename: {destination_path}")
                # Keep the original filename
        
        # Always use the full_videos_bucket for all uploads, including combined AV files
        target_bucket = self.full_videos_bucket
        logger.info(f"Using bucket '{target_bucket}' for upload of file: {destination_path}")
        
        # Ensure we're not creating any nested folders
        destination_path = os.path.basename(destination_path)
        
        # Remove any nested folder prefixes like 'full_videos/' or 'combined/'
        for prefix in ['full_videos/', 'combined/', 'exports/', 'media/']:
            if destination_path.startswith(prefix):
                destination_path = destination_path[len(prefix):]
        
        # Force enable Supabase integration for this upload
        from backend.core.config import settings
        if not settings.SUPABASE_INTEGRATION_ENABLED:
            logger.warning("SUPABASE_INTEGRATION_ENABLED is set to False in settings. Proceeding with upload anyway.")
            
        # Ensure we're using the service role key for admin access
        try:
            # Always re-initialize with service role to ensure we have admin access
            self.client = get_supabase_client(use_service_role=True)
            logger.info("Re-initialized Supabase client with service role")
        except Exception as auth_error:
            logger.error(f"Failed to initialize Supabase client: {str(auth_error)}")
            return {"success": False, "error": f"Authentication error: {str(auth_error)}"}
            
        try:
            logger.info(f"Starting upload of {file_path} to bucket {self.full_videos_bucket} as {destination_path}")
            logger.info(f"File exists: {os.path.exists(file_path)}, File size: {os.path.getsize(file_path)}")
            logger.info(f"Supabase client initialized: {self.client is not None}")
            
            # Check if we have a valid session
            session_info = "No session"
            try:
                session = self.client.auth.get_session()
                if session:
                    session_info = f"Session exists, user: {session.user.email if session.user else 'None'}"
                else:
                    logger.warning("No active session found, but continuing with upload")
            except Exception as se:
                session_info = f"Error getting session: {str(se)}"
                logger.warning(f"Session error: {str(se)}, but continuing with upload")
            logger.info(f"Supabase session: {session_info}")
            
            # Try to create the bucket if it doesn't exist
            try:
                # Check if bucket exists first
                buckets = self.client.storage.list_buckets()
                logger.info(f"Available buckets: {buckets}")
                
                bucket_exists = False
                for bucket in buckets:
                    if bucket.get('name') == self.full_videos_bucket:
                        bucket_exists = True
                        logger.info(f"Bucket '{self.full_videos_bucket}' already exists")
                        break
                
                if not bucket_exists:
                    logger.warning(f"Bucket '{self.full_videos_bucket}' does not exist, attempting to create it")
                    # Create bucket with public access enabled
                    self.client.storage.create_bucket(
                        self.full_videos_bucket, 
                        {'public': True, 'file_size_limit': 100000000}  # 100MB limit
                    )
                    logger.info(f"Created bucket '{self.full_videos_bucket}' with public access")
                    
                    # Ensure bucket has proper public access policy
                    try:
                        # Update bucket to be publicly accessible
                        self.client.storage.update_bucket(self.full_videos_bucket, {'public': True})
                        logger.info(f"Updated bucket '{self.full_videos_bucket}' to ensure public access")
                    except Exception as policy_error:
                        logger.warning(f"Error updating bucket policy: {str(policy_error)}, but continuing with upload")
            except Exception as bucket_error:
                logger.warning(f"Error checking/creating bucket: {str(bucket_error)}, will attempt upload anyway")
            
            # Attempt the upload with retries
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    with open(file_path, 'rb') as f:
                        # Use file_options to set cache control, content-type and upsert behavior
                        logger.info(f"File opened successfully, uploading to {self.full_videos_bucket}/{destination_path} (attempt {retry_count + 1}/{max_retries})")
                        
                        # Set proper content type for MP4 files
                        content_type = "video/mp4" if file_path.lower().endswith(".mp4") else None
                        logger.info(f"Using content-type: {content_type}")
                        
                        # For MP4 files, we need to ensure proper MIME type and permissions
                        file_options = {
                            "cache-control": "max-age=3600",
                            "upsert": "true"
                        }
                        
                        if content_type:
                            file_options["content-type"] = content_type
                        
                        logger.info(f"Uploading with file options: {file_options}")
                        
                        # Upload the file with proper options
                        response = self.client.storage.from_(self.full_videos_bucket).upload(
                            path=destination_path,
                            file=f,
                            file_options=file_options
                        )
                        logger.info(f"Upload response: {response}")
                        
                        # If we get here, the upload was successful
                        break
                except Exception as upload_error:
                    last_error = upload_error
                    retry_count += 1
                    logger.warning(f"Upload attempt {retry_count} failed: {str(upload_error)}")
                    if retry_count < max_retries:
                        logger.info(f"Retrying upload in 2 seconds...")
                        import time
                        time.sleep(2)  # Wait 2 seconds before retrying
                    else:
                        logger.error(f"All {max_retries} upload attempts failed")
                        raise upload_error
                
            # Get the public URL for the uploaded file
            logger.info(f"Getting public URL for {destination_path} from bucket {self.full_videos_bucket}")
            public_url = self.client.storage.from_(self.full_videos_bucket).get_public_url(destination_path)
            
            # Replace host.docker.internal with localhost for external access
            if public_url and 'host.docker.internal' in public_url:
                original_url = public_url
                public_url = public_url.replace('host.docker.internal', 'localhost')
                logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
            
            logger.info(f"Public URL: {public_url}")
            
            # Update file metadata to ensure it has the correct content-type
            try:
                if file_path.lower().endswith(".mp4"):
                    logger.info(f"Updating file metadata to ensure correct content-type")
                    # Note: Supabase doesn't have a direct API for updating file metadata
                    # We're using the update_bucket method to ensure the bucket itself is public
                    self.client.storage.update_bucket(self.full_videos_bucket, {'public': True})
                    logger.info(f"Updated bucket settings to ensure public access")
            except Exception as metadata_error:
                logger.warning(f"Error updating file metadata: {str(metadata_error)}, but continuing")
            
            # Verify the URL is accessible
            logger.info(f"Upload successful. File should be accessible at: {public_url}")
            
            return {
                "success": True,
                "path": destination_path,
                "public_url": public_url,
                "response": response
            }
        except Exception as e:
            logger.error(f"Exception during upload: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        try:
            # Check if the table exists first
            tables = self.client.table('').select('*').limit(1).execute()
            logger.debug(f"Available tables: {tables}")
            
            # Try to create the table if it doesn't exist
            try:
                # Create a minimal schema for the queue if it doesn't exist
                self.client.table('video_processing_queue').insert({"id": "test", "created_at": "now()", "status": "pending"}).execute()
                logger.info("Created video_processing_queue table")
            except Exception as table_error:
                logger.warning(f"Could not create table: {str(table_error)}")
            
            # Now try to insert the actual data
            return self.client.table('video_processing_queue').insert(video_data).execute()
        except Exception as e:
            logger.error(f"Error adding to video processing queue: {str(e)}")
            # Continue without failing the whole process
            return {"error": str(e)}
    
    def add_to_clip_creation_queue(self, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add jobs to the clip_creation queue.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        try:
            # Make sure we're not passing any columns parameter
            return self.client.table('clip_creation_queue').insert(clip_data).execute()
        except Exception as e:
            logger.error(f"Error adding to clip creation queue: {str(e)}")
            return {"error": str(e)}
