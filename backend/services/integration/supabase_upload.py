"""
Supabase upload service for handling large video uploads to Supabase Storage.
This implementation fixes issues with the base_url and headers in the original implementation.
"""

import os
import sys
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

# Add the project root to the path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseUploader:
    """Service for uploading videos to Supabase Storage."""
    
    def __init__(self, use_service_role: bool = True, timeout: int = 600):
        """
        Initialize the Supabase uploader.
        
        Args:
            use_service_role: If True, use the service role key instead of the anon key
                             Service role has admin privileges and should be used for
                             server-side operations only.
            timeout: Timeout in seconds for direct uploads (default: 600 seconds = 10 minutes)
        """
        # Store the URL and API key directly for direct API access
        self.supabase_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_SERVICE_ROLE_KEY if use_service_role else settings.SUPABASE_API_KEY
        
        if not self.supabase_url or not self.api_key:
            raise ValueError(
                "Supabase URL and API key must be set in environment variables "
                "(SUPABASE_URL and SUPABASE_API_KEY or SUPABASE_SERVICE_ROLE_KEY)"
            )
        
        # Initialize the Supabase client
        self.client = create_client(self.supabase_url, self.api_key)
        self.full_videos_bucket = "full_videos"
        self.clips_bucket = "clips"
        self.timeout = timeout
        logger.info(f"Initialized SupabaseUploader with timeout: {self.timeout} seconds")
        
    def upload_full_video(self, file_path: str, destination_path: str = None, chunk_size: int = 5 * 1024 * 1024, bucket: str = "videos", max_retries: int = 3) -> Dict[str, Any]:
        """Upload a full video file to Supabase storage.
        
        For large files (>100MB), this method will automatically use direct upload with extended timeout.
        For extremely large files (>50GB), it will use chunked upload as a fallback.
        
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            chunk_size: Size of each chunk in bytes (default: 5MB)
            max_retries: Maximum number of retries for each chunk
            
        Returns:
            Dict with upload status and information
        """
        logger.info(f"Starting upload for file: {file_path}")
            
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
        
        # Tiered approach based on file size
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        extremely_large_threshold = 50 * 1024 * 1024 * 1024  # 50GB
        
        if file_size > extremely_large_threshold:
            logger.info(f"Extremely large file detected ({file_size / (1024 * 1024 * 1024):.2f} GB > 50 GB). Using chunked upload.")
            return self.upload_chunked_video(file_path=file_path, destination_path=destination_path, chunk_size=chunk_size, bucket=bucket, max_retries=max_retries)
        elif file_size > large_file_threshold:
            logger.info(f"Large file detected ({file_size / (1024 * 1024):.2f} MB > {large_file_threshold / (1024 * 1024)} MB). Using direct upload with extended timeout.")
            return self.upload_large_video(file_path=file_path, destination_path=destination_path, bucket=bucket, max_retries=max_retries)
            
        # For smaller files, use standard upload
        logger.info(f"Standard file size detected ({file_size / (1024 * 1024):.2f} MB). Using standard upload.")
        
        # Use the file's basename if no destination path is provided
        if destination_path is None:
            destination_path = os.path.basename(file_path)
            
        # Use the provided bucket parameter
        target_bucket = bucket
        logger.info(f"Using bucket '{target_bucket}' for upload: {destination_path}")
        
        # Ensure we're not creating any nested folders
        destination_path = os.path.basename(destination_path)
        
        # Remove any nested folder prefixes
        for prefix in ['full_videos/', 'combined/', 'exports/', 'media/']:
            if destination_path.startswith(prefix):
                destination_path = destination_path[len(prefix):]
        
        # Try to create the bucket if it doesn't exist
        self._ensure_bucket_exists(target_bucket)
        
        # Start upload
        start_time = time.time()
        response = None
        
        # Set proper content type for MP4 files
        content_type = "video/mp4" if file_path.lower().endswith(".mp4") else None
        
        # For MP4 files, we need to ensure proper MIME type and permissions
        file_options = {
            "cache-control": "max-age=3600",
            "upsert": "true"
        }
        
        if content_type:
            file_options["content-type"] = content_type
            logger.info(f"Using content-type: {content_type}")
        
        # Try upload with retries
        retry_count = 0
        success = False
        error = None
        
        while retry_count < max_retries and not success:
            try:
                logger.info(f"Upload attempt {retry_count + 1}/{max_retries}")
                
                # Open the file and upload it
                with open(file_path, 'rb') as upload_file:
                    response = self.client.storage.from_(target_bucket).upload(
                        path=destination_path,
                        file=upload_file,
                        file_options=file_options
                    )
                    success = True
                    logger.info(f"Upload successful: {response}")
                
            except Exception as upload_error:
                retry_count += 1
                error = str(upload_error)
                logger.warning(f"Upload attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Retrying upload in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} upload attempts failed")
        
        if not success:
            return {
                "success": False,
                "error": error or "Unknown error during upload",
                "file_path": file_path
            }
        
        # Get the public URL for the uploaded file
        public_url = self.client.storage.from_(target_bucket).get_public_url(destination_path)
        
        # Replace host.docker.internal with localhost for external access
        if public_url and 'host.docker.internal' in public_url:
            original_url = public_url
            public_url = public_url.replace('host.docker.internal', 'localhost')
            logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
        
        # Calculate upload statistics
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
        
    def upload_large_video(self, file_path: str, destination_path: str = None, bucket: str = "videos", max_retries: int = 3) -> Dict[str, Any]:
        """Upload a large video file to Supabase storage using direct upload with extended timeout.
        
        This method uses a direct upload approach with increased timeout settings:
        1. Uploads the entire file at once with a 10-minute timeout (instead of default 60 seconds)
        2. Provides progress reporting and proper error handling
        3. Handles retries with exponential backoff
        
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            max_retries: Maximum number of retries for upload
            
        Returns:
            Dict with upload status and information
        """
        logger.info(f"Starting large file upload for: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        logger.info(f"Large file size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
        
        # Use the file's basename if no destination path is provided
        if destination_path is None:
            destination_path = os.path.basename(file_path)
            
        # Use the provided bucket parameter
        target_bucket = bucket
        logger.info(f"Using bucket '{target_bucket}' for direct upload: {destination_path}")
        
        # Ensure we're not creating any nested folders
        destination_path = os.path.basename(destination_path)
        
        # Remove any nested folder prefixes
        for prefix in ['full_videos/', 'combined/', 'exports/', 'media/']:
            if destination_path.startswith(prefix):
                destination_path = destination_path[len(prefix):]
        
        # Try to create the bucket if it doesn't exist
        self._ensure_bucket_exists(target_bucket)
        
        # Start upload
        start_time = time.time()
        response = None
        
        # Set proper content type for MP4 files
        content_type = "video/mp4" if file_path.lower().endswith(".mp4") else None
        
        # For MP4 files, we need to ensure proper MIME type and permissions
        file_options = {
            "cache-control": "max-age=3600",
            "upsert": "true"
        }
        
        if content_type:
            file_options["content-type"] = content_type
            logger.info(f"Using content-type: {content_type}")
        
        # Try upload with retries
        retry_count = 0
        success = False
        error = None
        # Use the instance timeout parameter set during initialization
        timeout = self.timeout
        
        while retry_count < max_retries and not success:
            try:
                logger.info(f"Upload attempt {retry_count + 1}/{max_retries}")
                
                # Open the file and upload it directly with increased timeout
                with open(file_path, 'rb') as upload_file:
                    # Get the underlying URL for direct upload
                    url = f"{self.supabase_url}/storage/v1/object/{target_bucket}/{destination_path}"
                    
                    # Create headers with the auth token
                    headers = {
                        'Authorization': f'Bearer {self.api_key}',
                        'apiKey': self.api_key
                    }
                    
                    # Create a custom session with increased timeout
                    session = requests.Session()
                    session.headers.update(headers)
                    
                    # Upload the file with progress reporting
                    file_size_mb = file_size / (1024 * 1024)
                    logger.info(f"Starting upload of {file_size_mb:.2f} MB file with {timeout} seconds timeout")
                    
                    # Use the session to upload the file with increased timeout
                    response = session.post(
                        url,
                        files={"file": upload_file},
                        data=file_options,
                        timeout=timeout
                    )
                    
                    # Check if the upload was successful
                    if response.status_code == 200:
                        success = True
                        logger.info(f"Upload successful with status code {response.status_code}")
                    else:
                        raise Exception(f"Upload failed with status code {response.status_code}: {response.text}")
                
            except Exception as upload_error:
                retry_count += 1
                error = str(upload_error)
                logger.warning(f"Upload attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Retrying upload in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} upload attempts failed")
        
        if not success:
            return {
                "success": False,
                "error": error or "Unknown error during upload",
                "file_path": file_path
            }
        
        # Get the public URL for the uploaded file
        public_url = self.client.storage.from_(target_bucket).get_public_url(destination_path)
        
        # Replace host.docker.internal with localhost for external access
        if public_url and 'host.docker.internal' in public_url:
            original_url = public_url
            public_url = public_url.replace('host.docker.internal', 'localhost')
            logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
        
        # Clean up any temporary files with the same name pattern
        self._cleanup_temp_files(target_bucket, destination_path)
        
        # Calculate upload statistics
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
            "response": response.json() if response else None
        }
        
    def upload_chunked_video(self, file_path: str, destination_path: str = None, chunk_size: int = 5 * 1024 * 1024, bucket: str = "videos", max_retries: int = 3) -> Dict[str, Any]:
        """Upload an extremely large video file to Supabase storage using chunked upload.
        
        This method is a fallback for extremely large files (>50GB) that might not work well
        with direct upload. It:
        1. Reads the file in chunks
        2. Writes chunks to a temporary local file
        3. Uploads the complete temporary file with extended timeout
        4. Provides progress reporting and proper error handling
        5. Handles retries with exponential backoff
        
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            chunk_size: Size of each chunk in bytes (default: 5MB)
            max_retries: Maximum number of retries for upload
            
        Returns:
            Dict with upload status and information
        """
        logger.info(f"Starting chunked upload for extremely large file: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        logger.info(f"Extremely large file size: {file_size} bytes ({file_size / (1024 * 1024 * 1024):.2f} GB)")
        
        # Use the file's basename if no destination path is provided
        if destination_path is None:
            destination_path = os.path.basename(file_path)
            
        # Use the provided bucket parameter
        target_bucket = bucket
        logger.info(f"Using bucket '{target_bucket}' for chunked upload: {destination_path}")
        
        # Ensure we're not creating any nested folders
        destination_path = os.path.basename(destination_path)
        
        # Remove any nested folder prefixes
        for prefix in ['full_videos/', 'combined/', 'exports/', 'media/']:
            if destination_path.startswith(prefix):
                destination_path = destination_path[len(prefix):]
        
        # Try to create the bucket if it doesn't exist
        self._ensure_bucket_exists(target_bucket)
        
        # Start upload process
        start_time = time.time()
        
        # Calculate total chunks
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        logger.info(f"File will be processed in {total_chunks} chunks of {chunk_size / (1024 * 1024):.2f} MB each")
        
        # Create a temporary file to store the chunks
        temp_file_path = f"{file_path}.temp"
        
        # Create an empty temporary file or truncate if it exists
        with open(temp_file_path, 'wb') as temp_file:
            pass
        
        with open(file_path, 'rb') as f:
            for chunk_index in range(total_chunks):
                chunk_start = chunk_index * chunk_size
                f.seek(chunk_start)
                chunk_data = f.read(chunk_size)
                
                # Write chunk to the temporary file
                with open(temp_file_path, 'ab') as temp_file:
                    temp_file.write(chunk_data)
                
                # Calculate and log progress
                progress = (chunk_index + 1) / total_chunks * 100
                logger.info(f"Processed chunk {chunk_index + 1}/{total_chunks} ({progress:.2f}%)")
        
        logger.info(f"All chunks processed and written to temporary file: {temp_file_path}")
        
        # Set proper content type for MP4 files
        content_type = "video/mp4" if file_path.lower().endswith(".mp4") else None
        
        # For MP4 files, we need to ensure proper MIME type and permissions
        file_options = {
            "cache-control": "max-age=3600",
            "upsert": "true"
        }
        
        if content_type:
            file_options["content-type"] = content_type
            logger.info(f"Using content-type: {content_type}")
        
        # Try upload with retries
        retry_count = 0
        success = False
        error = None
        timeout = 1800  # 30 minutes timeout for extremely large files
        
        while retry_count < max_retries and not success:
            try:
                logger.info(f"Upload attempt {retry_count + 1}/{max_retries}")
                
                # Open the temporary file and upload it directly with increased timeout
                with open(temp_file_path, 'rb') as upload_file:
                    # Get the underlying URL for direct upload
                    url = f"{self.supabase_url}/storage/v1/object/{target_bucket}/{destination_path}"
                    
                    # Create headers with the auth token
                    headers = {
                        'Authorization': f'Bearer {self.api_key}',
                        'apiKey': self.api_key
                    }
                    
                    # Create a custom session with increased timeout
                    session = requests.Session()
                    session.headers.update(headers)
                    
                    # Upload the file with progress reporting
                    temp_file_size = os.path.getsize(temp_file_path)
                    temp_file_size_mb = temp_file_size / (1024 * 1024)
                    logger.info(f"Starting upload of {temp_file_size_mb:.2f} MB file with {timeout} seconds timeout")
                    
                    # Use the session to upload the file with increased timeout
                    response = session.post(
                        url,
                        files={"file": upload_file},
                        data=file_options,
                        timeout=timeout
                    )
                    
                    # Check if the upload was successful
                    if response.status_code == 200:
                        success = True
                        logger.info(f"Upload successful with status code {response.status_code}")
                    else:
                        raise Exception(f"Upload failed with status code {response.status_code}: {response.text}")
                
            except Exception as upload_error:
                retry_count += 1
                error = str(upload_error)
                logger.warning(f"Upload attempt {retry_count} failed: {error}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Retrying upload in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} upload attempts failed")
        
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Removed temporary file: {temp_file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Error removing temporary file: {str(cleanup_error)}")
        
        if not success:
            return {
                "success": False,
                "error": error or "Unknown error during upload",
                "file_path": file_path
            }
        
        # Get the public URL for the uploaded file
        public_url = self.client.storage.from_(target_bucket).get_public_url(destination_path)
        
        # Replace host.docker.internal with localhost for external access
        if public_url and 'host.docker.internal' in public_url:
            original_url = public_url
            public_url = public_url.replace('host.docker.internal', 'localhost')
            logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
        
        # Clean up any temporary files with the same name pattern in Supabase
        self._cleanup_temp_files(target_bucket, destination_path)
        
        # Calculate upload statistics
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
            "response": response.json() if response else None
        }
    
    def _ensure_bucket_exists(self, bucket_name: str) -> bool:
        """Ensure that the specified bucket exists and has public access."""
        try:
            # Check if bucket exists first
            buckets = self.client.storage.list_buckets()
            
            bucket_exists = False
            for bucket in buckets:
                if hasattr(bucket, 'name') and bucket.name == bucket_name:
                    bucket_exists = True
                    logger.info(f"Bucket '{bucket_name}' already exists")
                    break
            
            if not bucket_exists:
                logger.warning(f"Bucket '{bucket_name}' does not exist, attempting to create it")
                # Create bucket with public access enabled
                self.client.storage.create_bucket(
                    bucket_name, 
                    {'public': True, 'file_size_limit': None}  # No file size limit
                )
                logger.info(f"Created bucket '{bucket_name}' with public access")
                
                # Ensure bucket has proper public access policy
                self.client.storage.update_bucket(bucket_name, {'public': True})
            
            return True
        except Exception as bucket_error:
            logger.warning(f"Error checking/creating bucket: {str(bucket_error)}, will attempt upload anyway")
            return False
    
    def _cleanup_temp_files(self, bucket_name: str, destination_path: str) -> None:
        """Clean up any temporary files with the same name pattern."""
        try:
            # List all files in the bucket
            all_files = self.client.storage.from_(bucket_name).list()
            
            # Find any temporary chunk files that might have been left from previous uploads
            chunk_files = [file.get('name') for file in all_files if file.get('name', '').startswith(f"{destination_path}.chunk")]
            
            # Remove any found chunk files
            if chunk_files:
                logger.info(f"Found {len(chunk_files)} temporary chunk files to clean up")
                for chunk_file in chunk_files:
                    self.client.storage.from_(bucket_name).remove([chunk_file])
                    logger.info(f"Removed temporary file: {chunk_file}")
        except Exception as cleanup_error:
            logger.warning(f"Error cleaning up temporary files: {str(cleanup_error)}, but continuing")
            
    def get_supabase_client(self) -> Client:
        """Get the Supabase client instance.
        
        Returns:
            The initialized Supabase client
        """
        return self.client
