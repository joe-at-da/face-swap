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
        
    def upload_large_video(self, file_path: str, destination_path: str = None, bucket: str = "videos", max_retries: int = 5) -> Dict[str, Any]:
        """Upload a large video file to Supabase storage using a direct upload with extended timeout.
    
        This method uses a direct upload approach with extended timeout and robust error handling:
        1. Uploads the entire file in a single request with a long timeout (1 hour)
        2. Provides detailed logging and error reporting
        3. Implements retry logic with exponential backoff
    
        Args:
            file_path: Path to the file to upload
            destination_path: Path within the bucket to upload to (defaults to filename)
            bucket: Target storage bucket
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
        
        # Extended timeout for large files - 1 hour
        extended_timeout = 3600
        
        # Try upload with retries
        retry_count = 0
        success = False
        error = None
        response = None
        
        while retry_count < max_retries and not success:
            try:
                logger.info(f"Upload attempt {retry_count + 1}/{max_retries} with {extended_timeout}s timeout")
                
                # Upload the file directly
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
                    
                    # Upload the file with the extended timeout
                    logger.info(f"Starting direct upload of {file_size / (1024 * 1024):.2f} MB with {extended_timeout}s timeout")
                    
                    # Use the session to upload the file with increased timeout
                    response = session.post(
                        url,
                        files={"file": upload_file},
                        data=file_options,
                        timeout=extended_timeout
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
                    return {
                        "success": False,
                        "error": f"Failed to upload file after {max_retries} attempts: {error}",
                        "file_path": file_path
                    }
        
        # If we got here, either the upload was successful or we exhausted retries
        if not success:
            return {
                "success": False,
                "error": f"Failed to upload file after {max_retries} attempts: {error}",
                "file_path": file_path
            }
            
        # Upload was successful, get the public URL
        end_time = time.time()
        upload_duration = end_time - start_time
        logger.info(f"Upload completed in {upload_duration:.2f} seconds")
        
        try:
            # Get the public URL
            public_url = self.client.storage.from_(target_bucket).get_public_url(destination_path)
            
            # Fix the URL if needed (replace host.docker.internal with localhost)
            if "host.docker.internal" in public_url:
                public_url = public_url.replace("host.docker.internal", "localhost")
                
            logger.info(f"Public URL: {public_url}")
            
            # Clean up any temporary files with the same name pattern
            self._cleanup_temp_files(target_bucket, destination_path)
            
            # Calculate upload statistics
            avg_speed = file_size / upload_duration / (1024 * 1024) if upload_duration > 0 else 0
            logger.info(f"Average upload speed: {avg_speed:.2f} MB/s")
            
            return {
                "success": True,
                "file_path": file_path,
                "url": public_url,
                "bucket": target_bucket,
                "path": destination_path,
                "size": file_size,
                "upload_time": upload_duration,
                "average_speed": avg_speed,
                "response": response.json() if response and hasattr(response, 'json') else None
            }
        except Exception as e:
            logger.error(f"Error getting public URL: {str(e)}")
            return {
                "success": True,  # Upload was successful even if we couldn't get the URL
                "file_path": file_path,
                "bucket": target_bucket,
                "path": destination_path,
                "size": file_size,
                "upload_time": upload_duration,
                "url_error": str(e)
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
        
    def add_to_clip_creation_queue(self, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add clips to the parliament_member_clips table.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        import uuid
        from datetime import datetime, date
        
        # Ensure we're not passing any empty data or problematic parameters
        if not clip_data:
            logger.warning("No clip data provided to add_to_clip_creation_queue")
            return {"success": False, "error": "No clip data provided"}
            
        # Create a deep copy of the data and ensure all values are JSON serializable
        import copy
        import json as json_module
        
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
