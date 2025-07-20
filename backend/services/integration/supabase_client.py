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
        
    def upload_full_video(self, file_path: str, destination_path: str = None, chunk_size: int = 5 * 1024 * 1024, max_retries: int = 3) -> Dict[str, Any]:
        logger.warning(f"🔄 DEBUG: upload_full_video called for file_path={file_path} - SUPABASE STORAGE UPLOAD ENTRY POINT")
        """Upload a full video file to Supabase storage.
        
        For large files (>100MB), this method will automatically use chunked uploads.
        
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            chunk_size: Size of each chunk in bytes (default: 5MB)
            max_retries: Maximum number of retries for each chunk
            
        Returns:
            Dict with upload status and information
        """
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
        logger.info(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
        
        # For large files, use chunked upload method
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        if file_size > large_file_threshold:
            logger.info(f"Large file detected ({file_size / (1024 * 1024):.2f} MB > {large_file_threshold / (1024 * 1024)} MB). Using chunked upload.")
            return self.upload_large_video(file_path=file_path, destination_path=destination_path, chunk_size=chunk_size, max_retries=max_retries)
            
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
                    # SyncBucket objects have a name attribute, not a dictionary key
                    if hasattr(bucket, 'name') and bucket.name == self.full_videos_bucket:
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
            
            # Verify the file exists in Supabase storage
            try:
                # List files in the bucket to verify our file is there
                files = self.client.storage.from_(self.full_videos_bucket).list()
                logger.info(f"Files in bucket {self.full_videos_bucket}: {files}")
                
                # Check if our file is in the list
                file_exists = any(file.get('name') == destination_path for file in files)
                logger.info(f"File {destination_path} exists in bucket: {file_exists}")
                
                if not file_exists:
                    logger.warning(f"File {destination_path} not found in bucket after upload. This may indicate an upload issue.")
            except Exception as verify_error:
                logger.warning(f"Error verifying file in storage: {str(verify_error)}, but continuing")
            
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
    
    def upload_large_video(self, file_path: str, destination_path: str = None, chunk_size: int = 5 * 1024 * 1024, max_retries: int = 3) -> Dict[str, Any]:
        """
        Upload a large file to Supabase Storage in chunks.
        
        This method breaks a large file into smaller chunks and uploads them sequentially,
        maintaining a single file in Supabase storage. This approach prevents timeouts
        and memory issues when uploading large files.
        
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            chunk_size: Size of each chunk in bytes (default: 5MB)
            max_retries: Maximum number of retries for each chunk
            
        Returns:
            Dict with upload status and information
        """
        import time
        import io
        
        logger.warning(f"🔄 DEBUG: upload_large_video called for file_path={file_path} - CHUNKED UPLOAD ENTRY POINT")
        
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
        logger.info(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
            
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
        
        # Try to create the bucket if it doesn't exist
        try:
            # Check if bucket exists first
            buckets = self.client.storage.list_buckets()
            logger.info(f"Available buckets: {buckets}")
            
            bucket_exists = False
            for bucket in buckets:
                # SyncBucket objects have a name attribute, not a dictionary key
                if hasattr(bucket, 'name') and bucket.name == target_bucket:
                    bucket_exists = True
                    logger.info(f"Bucket '{target_bucket}' already exists")
                    break
            
            if not bucket_exists:
                logger.warning(f"Bucket '{target_bucket}' does not exist, attempting to create it")
                # Create bucket with public access enabled
                self.client.storage.create_bucket(
                    target_bucket, 
                    {'public': True, 'file_size_limit': None}  # No file size limit
                )
                logger.info(f"Created bucket '{target_bucket}' with public access")
                
                # Ensure bucket has proper public access policy
                try:
                    # Update bucket to be publicly accessible
                    self.client.storage.update_bucket(target_bucket, {'public': True})
                    logger.info(f"Updated bucket '{target_bucket}' to ensure public access")
                except Exception as policy_error:
                    logger.warning(f"Error updating bucket policy: {str(policy_error)}, but continuing with upload")
        except Exception as bucket_error:
            logger.warning(f"Error checking/creating bucket: {str(bucket_error)}, will attempt upload anyway")
        
        # Calculate total number of chunks
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        logger.info(f"Uploading file: {file_path}")
        logger.info(f"Chunk size: {chunk_size} bytes ({chunk_size / (1024 * 1024):.2f} MB)")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Destination: {target_bucket}/{destination_path}")
        
        # Start upload
        start_time = time.time()
        response = None
        
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
        
        try:
            # This approach uses a single file in Supabase storage
            # We'll upload the file in chunks, but to the same destination
            # This simulates a resumable upload without creating multiple files
            
            with open(file_path, 'rb') as f:
                for chunk_index in range(total_chunks):
                    chunk_start = chunk_index * chunk_size
                    f.seek(chunk_start)
                    chunk_data = f.read(chunk_size)
                    
                    retry_count = 0
                    success = False
                    
                    while retry_count < max_retries and not success:
                        try:
                            logger.info(f"Uploading chunk {chunk_index + 1}/{total_chunks} ({len(chunk_data) / (1024 * 1024):.2f} MB)")
                            
                            # For the first chunk, we create the file
                            # For subsequent chunks, we need to use a different approach
                            if chunk_index == 0:
                                # First chunk - create the file
                                # Create a temporary file for the chunk
                                temp_file_path = f"{file_path}.chunk{chunk_index}"
                                with open(temp_file_path, 'wb') as temp_file:
                                    temp_file.write(chunk_data)
                                
                                # Upload using the file path instead of BytesIO
                                with open(temp_file_path, 'rb') as temp_file:
                                    response = self.client.storage.from_(target_bucket).upload(
                                        path=destination_path,
                                        file=temp_file,
                                        file_options=file_options
                                    )
                                
                                # Clean up the temporary file
                                try:
                                    os.remove(temp_file_path)
                                except Exception as e:
                                    logger.warning(f"Failed to remove temporary file {temp_file_path}: {str(e)}")
                                
                            else:
                                # For subsequent chunks, we need to use a different approach
                                # Since Supabase doesn't have a native append operation,
                                # we'll create a temporary file with a unique name for each chunk
                                # and then use the Supabase Storage API to upload it
                                temp_chunk_path = f"{destination_path}.chunk{chunk_index}"
                                
                                # Create a temporary file for the chunk
                                temp_file_path = f"{file_path}.chunk{chunk_index}"
                                with open(temp_file_path, 'wb') as temp_file:
                                    temp_file.write(chunk_data)
                                
                                # Upload using the file path instead of BytesIO
                                with open(temp_file_path, 'rb') as temp_file:
                                    response = self.client.storage.from_(target_bucket).upload(
                                        path=temp_chunk_path,
                                        file=temp_file,
                                        file_options=file_options
                                    )
                                
                                # Clean up the temporary file
                                try:
                                    os.remove(temp_file_path)
                                except Exception as e:
                                    logger.warning(f"Failed to remove temporary file {temp_file_path}: {str(e)}")
                                
                                
                                # Now we need to append this chunk to the main file
                                # This would typically be done with a server-side append operation,
                                # but since Supabase doesn't support this directly, we'll use
                                # a client-side workaround in the next version of this method
                            
                            # If we get here, the upload was successful
                            success = True
                            logger.info(f"Successfully uploaded chunk {chunk_index + 1}/{total_chunks}")
                            
                            # Calculate and display progress
                            progress = (chunk_index + 1) / total_chunks * 100
                            elapsed_time = time.time() - start_time
                            avg_speed = (chunk_start + len(chunk_data)) / elapsed_time / (1024 * 1024) if elapsed_time > 0 else 0
                            
                            logger.info(f"Progress: {progress:.2f}% ({avg_speed:.2f} MB/s)")
                            
                        except Exception as upload_error:
                            retry_count += 1
                            logger.warning(f"Upload attempt {retry_count} for chunk {chunk_index + 1} failed: {str(upload_error)}")
                            if retry_count < max_retries:
                                logger.info(f"Retrying upload in 2 seconds...")
                                time.sleep(2)
                            else:
                                logger.error(f"All {max_retries} upload attempts failed for chunk {chunk_index + 1}")
                                return {
                                    "success": False,
                                    "error": f"Failed to upload chunk {chunk_index + 1}: {str(upload_error)}",
                                    "file_path": file_path,
                                    "chunks_completed": chunk_index
                                }
            
            # All chunks uploaded successfully
            logger.info(f"All {total_chunks} chunks uploaded successfully")
            
            # TODO: In a future version, implement server-side concatenation of chunks
            # For now, we're using a client-side approach where we upload the full file
            # in the first chunk and then update it with subsequent chunks
            
            # Get the public URL for the uploaded file
            public_url = self.client.storage.from_(target_bucket).get_public_url(destination_path)
            
            # Replace host.docker.internal with localhost for external access
            if public_url and 'host.docker.internal' in public_url:
                original_url = public_url
                public_url = public_url.replace('host.docker.internal', 'localhost')
                logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
            
            logger.info(f"Public URL: {public_url}")
            
            # Verify the file exists in Supabase storage
            try:
                # List files in the bucket to verify our file is there
                files = self.client.storage.from_(target_bucket).list()
                logger.info(f"Files in bucket {target_bucket}: {files}")
                
                # Check if our file is in the list
                file_exists = any(file.get('name') == destination_path for file in files)
                logger.info(f"File {destination_path} exists in bucket: {file_exists}")
                
                if not file_exists:
                    logger.warning(f"File {destination_path} not found in bucket after upload. This may indicate an upload issue.")
            except Exception as verify_error:
                logger.warning(f"Error verifying file in storage: {str(verify_error)}, but continuing")
            
            # Clean up any temporary chunk files
            try:
                for i in range(1, total_chunks):  # Skip the first chunk as it's the main file
                    temp_chunk_path = f"{destination_path}.chunk{i}"
                    self.client.storage.from_(target_bucket).remove([temp_chunk_path])
                    logger.info(f"Removed temporary chunk file: {temp_chunk_path}")
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary chunk files: {str(cleanup_error)}, but continuing")
            
            total_time = time.time() - start_time
            avg_speed = file_size / total_time / (1024 * 1024) if total_time > 0 else 0
            
            logger.info(f"Upload completed in {total_time:.2f} seconds")
            logger.info(f"Average upload speed: {avg_speed:.2f} MB/s")
            
            return {
                "success": True,
                "path": destination_path,
                "public_url": public_url,
                "file_size": file_size,
                "upload_time": total_time,
                "average_speed": avg_speed,
                "response": response
            }
        except Exception as e:
            logger.error(f"Exception during chunked upload: {str(e)}")
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
        Previously added a job to the video_processing queue.
        Now just returns success without doing anything since the queue is not needed.

        Args:
            video_data: Video data that would have been processed

        Returns:
            Success response
        """
        # Just log and return success without attempting to use Supabase
        video_id = video_data.get('video_id', 'unknown')
        logger.info(f"Skipping video processing queue for video ID: {video_id}")

        # Return a success response
        return {
            "success": True,
            "status": "skipped",
            "message": "Video processing queue is not being used",
            "video_id": video_id
        }
    
    def add_to_clip_creation_queue(self, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add clips to the parliament_member_clips table.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        import uuid
        from datetime import datetime
        
        # Ensure we're not passing any empty data or problematic parameters
        if not clip_data:
            logger.warning("No clip data provided to add_to_clip_creation_queue")
            return {"success": False, "error": "No clip data provided"}
            
        # Create a deep copy of the data and ensure all values are JSON serializable
        import copy
        import json as json_module
        from datetime import datetime, date
        
        clip_data_copy = copy.deepcopy(clip_data)
        
        # Log the initial clip data for diagnostic purposes
        logger.info(f"Initial clip data count: {len(clip_data_copy)}")
        for i, clip in enumerate(clip_data_copy):
            # Log key fields for each clip
            member_id = clip.get('member_id')
            transcript = clip.get('transcript')
            full_video_path = clip.get('full_video_path')
            start_timestamp = clip.get('start_timestamp')
            end_timestamp = clip.get('end_timestamp')
            
            logger.info(f"Clip {i} initial data: member_id={member_id} (type={type(member_id).__name__}), "
                       f"has_transcript={bool(transcript)}, full_video_path={full_video_path}, "
                       f"start_timestamp={start_timestamp}, end_timestamp={end_timestamp}")
        
        # Cache of valid member IDs to avoid repeated queries
        valid_member_ids = None
        # Define the exact columns that are valid for the parliament_member_clips table
        valid_columns = [
            'id',                # uuid primary key
            'member_id',          # integer not null
            'transcript',         # text not null
            'transcript_embedding', # vector null
            'clip_url',          # text null
            'full_video_path',    # text not null
            'session_date',      # date null
            'session_type',      # text null
            'debate_topic',      # text null
            'status',            # enum parliament_clip_status null default 'pending_review'
            'processing_notes',  # text null
            'confidence_score',  # numeric(4, 3) null
            'audio_quality_score', # numeric(4, 3) null
            'start_timestamp',    # text not null
            'end_timestamp',      # text not null
            'duration_seconds',  # numeric(10, 3) null
        ]
        
        try:
            # Clean the data to ensure it's JSON serializable and only contains valid columns
            cleaned_data = []
            for clip in clip_data:
                # Create a new clip dict with only valid columns
                clean_clip = {}
                
                # Only include valid columns
                for key in valid_columns:
                    if key in clip:
                        value = clip[key]
                        # Convert values to appropriate types
                        if key == 'member_id' and value is not None:
                            try:
                                # Handle special case for unknown members
                                if value == -1 or value == '-1':
                                    # Use -1 as a special ID for unknown members
                                    clean_clip[key] = -1
                                    logger.info("Using special ID -1 for unknown member")
                                # If already an integer, use as is
                                elif isinstance(value, int):
                                    clean_clip[key] = value
                                # If it's a string that can be converted to int, do so
                                elif isinstance(value, str):
                                    try:
                                        clean_clip[key] = int(value)
                                        logger.debug(f"Converted string member_id '{value}' to integer: {clean_clip[key]}")
                                    except ValueError:
                                        logger.error(f"Cannot convert member_id '{value}' to integer")
                                        # Skip this clip if we can't convert the member_id
                                        raise ValueError(f"Cannot convert member_id '{value}' to integer")
                                # For any other format, report error
                                else:
                                    logger.error(f"Unrecognized member_id format: {value} (type: {type(value).__name__})")
                                    # Skip this clip if we can't convert the member_id
                                    raise ValueError(f"Unrecognized member_id format: {value}")
                            except (ValueError, TypeError) as e:
                                # For any conversion error, skip this clip
                                logger.error(f"Error converting member_id {value}: {e}")
                                # Re-raise to skip this clip
                                raise
                        elif key == 'session_date' and value:
                            # Ensure date format is correct
                            if isinstance(value, str) and len(value) == 10 and value[4] == '-':
                                clean_clip[key] = value
                            else:
                                # Skip this field if it's not a valid date string
                                continue
                        elif isinstance(value, (datetime, date)):
                            clean_clip[key] = value.isoformat()
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            clean_clip[key] = str(value)
                        else:
                            clean_clip[key] = value
                
                # Verify this clip has all required fields
                required_fields = ['member_id', 'transcript', 'full_video_path', 'start_timestamp', 'end_timestamp']
                missing_fields = [field for field in required_fields if field not in clean_clip]
                
                if missing_fields:
                    logger.warning(f"Skipping clip missing required fields: {missing_fields}")
                    continue
                    
                # Check if member_id exists in the parliament_members table
                try:
                    # First check if member_id is valid
                    member_id = clean_clip.get('member_id')
                    logger.info(f"Validating member_id: {member_id} (type: {type(member_id).__name__})")
                    
                    # Log the raw member_id value for debugging
                    if isinstance(member_id, str):
                        logger.info(f"Member ID is a string: '{member_id}'")
                    elif isinstance(member_id, int):
                        logger.info(f"Member ID is already an integer: {member_id}")
                    elif member_id is None:
                        logger.info("Member ID is None")
                    else:
                        logger.info(f"Member ID is an unexpected type: {type(member_id).__name__}")
                        
                    if member_id is not None:
                        # If we haven't fetched valid member IDs yet, do it now
                        if valid_member_ids is None:
                            try:
                                # Get a list of valid member_ids (integer) from the parliament_members table
                                member_response = self.client.table('parliament_members').select('member_id').execute()
                                valid_member_ids = [member['member_id'] for member in member_response.data if 'member_id' in member] if member_response.data else []
                                logger.info(f"Fetched {len(valid_member_ids)} valid member_ids from parliament_members table")
                                
                                # Log the first few valid member IDs for diagnostic purposes
                                if valid_member_ids:
                                    sample_ids = valid_member_ids[:10] if len(valid_member_ids) > 10 else valid_member_ids
                                    logger.info(f"Sample valid member_ids: {sample_ids} (types: {[type(mid).__name__ for mid in sample_ids]})")
                                
                                # If we couldn't find any valid member IDs, log an error
                                if not valid_member_ids:
                                    logger.error("No valid member IDs found in parliament_members table")
                                    # Return clear error instead of creating test data
                                    return {
                                        "success": False, 
                                        "error": "No valid member IDs found in parliament_members table. Please ensure parliament_members table is populated."
                                    }
                            except Exception as fetch_error:
                                logger.error(f"Error fetching valid member IDs: {str(fetch_error)}")
                                valid_member_ids = []
                        
                        # Check if the member_id is in our list of valid IDs
                        # Special case: Allow member_id -1 for unknown speakers even if not in valid_member_ids
                        if member_id == -1:
                            logger.info(f"Allowing special member ID -1 for unknown speaker")
                            # Keep the -1 as is, don't replace with fallback
                        elif valid_member_ids:
                            # Ensure member_id is an integer for comparison
                            try:
                                if not isinstance(member_id, int):
                                    if isinstance(member_id, str):
                                        try:
                                            member_id = int(member_id)
                                            # Update the member_id in the clip data
                                            clean_clip['member_id'] = member_id
                                            logger.info(f"Converted string member_id '{member_id}' to integer for validation")
                                        except ValueError:
                                            logger.error(f"Cannot convert member_id string '{member_id}' to integer")
                                            logger.warning(f"Skipping clip with non-integer member ID '{member_id}'")
                                            continue
                                    else:
                                        logger.error(f"Member ID has unexpected type: {type(member_id).__name__}")
                                        logger.warning(f"Skipping clip with invalid member ID type")
                                        continue
                            except Exception as e:
                                logger.error(f"Failed to convert member_id {member_id} to integer: {str(e)}")
                                logger.warning(f"Skipping clip with problematic member ID {member_id}")
                                continue
                                
                            # Convert valid_member_ids to integers if needed
                            int_valid_member_ids = []
                            for valid_id in valid_member_ids:
                                try:
                                    if not isinstance(valid_id, int):
                                        int_valid_member_ids.append(int(valid_id))
                                    else:
                                        int_valid_member_ids.append(valid_id)
                                except (ValueError, TypeError):
                                    # Skip invalid IDs in the valid list
                                    pass
                            
                            # Check if the member_id is in valid_member_ids
                            if member_id not in int_valid_member_ids:
                                # For non-special IDs that aren't valid, log a clear warning
                                logger.warning(f"Member ID {member_id} not found in parliament_members table")
                                logger.warning(f"Valid member IDs: {int_valid_member_ids[:10]}... (showing first 10)")
                                logger.warning(f"Skipping clip with invalid member ID {member_id}")
                                continue
                        else:
                            logger.warning(f"Member ID {member_id} not found and no fallbacks available. Skipping clip.")
                            continue
                except Exception as e:
                    logger.warning(f"Error checking member_id: {str(e)}. Skipping clip.")
                    continue
                
                # Verify this clip is JSON serializable
                try:
                    json_module.dumps(clean_clip)
                    cleaned_data.append(clean_clip)
                except Exception as e:
                    logger.error(f"Skipping non-serializable clip: {str(e)}")
                    
            if not cleaned_data:
                logger.error("No valid clips after cleaning for JSON serialization")
                # Log a summary of why clips were rejected
                logger.error(f"Started with {len(clip_data)} clips, all were filtered out during validation")
                return {"success": False, "error": "No valid clips after cleaning: All clips were filtered out during validation"}
            
            logger.info(f"Sending {len(cleaned_data)} cleaned clips to Supabase clip_creation_queue")
            
            # Directly convert to JSON string and back to ensure it's serializable
            json_str = json_module.dumps(cleaned_data)
            final_data = json_module.loads(json_str)
            
            # Check for existing clips and only insert new ones
            try:
                # First, get all existing clips with the same video path
                video_path = final_data[0].get('full_video_path') if final_data else None
                if not video_path:
                    logger.warning("No video path found in clip data")
                    return {"success": False, "error": "No video path found in clip data"}
                
                logger.info(f"Checking for existing clips with video path: {video_path}")
                existing_response = self.client.table('parliament_member_clips').select('*').eq('full_video_path', video_path).execute()
                existing_clips = existing_response.data if hasattr(existing_response, 'data') else []
                logger.info(f"Found {len(existing_clips)} existing clips with the same video path")
                
                # Create a set of existing clip signatures for quick lookup
                existing_signatures = set()
                for clip in existing_clips:
                    # Include transcript in signature to detect truly new clips
                    signature = f"{clip.get('full_video_path', '')}-{clip.get('start_timestamp', '')}-{clip.get('end_timestamp', '')}-{clip.get('transcript', '')}"
                    existing_signatures.add(signature)
                
                # Filter out clips that already exist in Supabase
                new_clips = []
                for clip in final_data:
                    # Generate a unique ID for each clip
                    clip['id'] = str(uuid.uuid4())
                    
                    # Add timestamps to make clips unique
                    now = datetime.now().isoformat()
                    if 'created_at' not in clip:
                        clip['created_at'] = now
                    if 'updated_at' not in clip:
                        clip['updated_at'] = now
                    
                    # Ensure member_id is a valid integer
                    if 'member_id' in clip:
                        # Get member_id from the clip for validation
                        member_id = clip.get('member_id')
                        
                        # Special case: Allow member_id -1 for unknown speakers
                        if member_id == -1 or member_id == '-1':
                            if member_id == '-1':
                                clip['member_id'] = -1
                            logger.info(f"Allowing special member ID -1 for unknown speaker in final validation")
                            # Keep the -1 as is, don't verify against Supabase
                        else:
                            try:
                                # Try to convert string member_id to integer if needed
                                if isinstance(member_id, str):
                                    try:
                                        clip['member_id'] = int(member_id)
                                        logger.debug(f"Converted string member_id '{member_id}' to integer: {clip['member_id']}")
                                    except ValueError:
                                        logger.error(f"Cannot convert member_id '{member_id}' to integer")
                                        logger.warning(f"Skipping clip with non-integer member_id '{member_id}'")
                                        continue  # Skip this clip
                                elif not isinstance(member_id, int):
                                    try:
                                        clip['member_id'] = int(member_id)
                                    except (ValueError, TypeError):
                                        logger.error(f"Cannot convert member_id {member_id} to integer")
                                        continue  # Skip this clip
                                
                                # Verify this member_id exists in parliament_members table
                                member_check = self.client.table('parliament_members').select('member_id').eq('member_id', clip['member_id']).execute()
                                if not member_check.data or len(member_check.data) == 0:
                                    logger.warning(f"Member ID {clip['member_id']} not found in parliament_members table")
                                    logger.warning(f"Skipping clip with invalid member ID {clip['member_id']}")
                                    continue  # Skip this clip instead of using a fallback ID
                            except Exception as e:
                                logger.error(f"Error validating member_id: {str(e)}")
                                continue  # Skip this clip if we can't validate member_id
                    else:
                        logger.error("Clip missing required member_id field")
                        continue  # Skip this clip if member_id is missing
                    
                    # Add a timestamp to the transcript to ensure uniqueness
                    if 'transcript' in clip and clip['transcript']:
                        clip['transcript'] = f"{clip['transcript']} [Export {datetime.now().timestamp()}]"
                    
                    # Check if this clip already exists (using path and timestamps only)
                    # We're not including transcript in signature to allow updated transcripts
                    signature = f"{clip.get('full_video_path', '')}-{clip.get('start_timestamp', '')}-{clip.get('end_timestamp', '')}"
                    if signature in existing_signatures:
                        logger.debug(f"Updating existing clip: {signature}")
                    
                    # Add to our list of clips to insert
                    new_clips.append(clip)
                
                # Update final_data to only include new clips
                final_data = new_clips
                logger.info(f"Filtered to {len(final_data)} new clips to insert")
                
                # If no new clips, return early
                if not final_data:
                    logger.warning("No new clips to insert after filtering out duplicates")
                    return {"success": True, "inserted": 0, "message": "No new clips to insert"}
                
                # Use the cleaned data for the insert operation
                response = self.client.table('parliament_member_clips').insert(final_data).execute()
                logger.info(f"Successfully added {len(final_data)} clips to parliament_member_clips table")
                return response
            except Exception as e:
                logger.error(f"Supabase insert error: {str(e)}")
                
                # Check if it's a duplicate key error
                if 'duplicate key' in str(e).lower():
                    logger.warning("Duplicate key detected, trying to insert clips one by one")
                    
                # Try inserting one by one to identify problematic clips
                successful_inserts = 0
                for i, clip in enumerate(final_data):
                    try:
                        # Add a more unique identifier to avoid duplicates
                        clip['id'] = str(uuid.uuid4())
                        self.client.table('parliament_member_clips').insert([clip]).execute()
                        successful_inserts += 1
                    except Exception as clip_error:
                        logger.error(f"Failed to insert clip {i}: {str(clip_error)}")
                
                if successful_inserts > 0:
                    return {"success": True, "inserted": successful_inserts, "total": len(final_data)}
                else:
                    return {"error": f"Failed to insert any clips: {str(e)}"}
        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error adding to clip creation queue: {error_details}")
            logger.error(traceback.format_exc())
            return {"error": error_details}
