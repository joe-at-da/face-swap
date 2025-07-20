#!/usr/bin/env python3
"""
Chunked Upload Script for Supabase

This script uploads large files to Supabase Storage using a chunked upload approach
to avoid timeouts and memory issues with large files.
"""

import os
import sys
import time
import logging
import argparse
from typing import Dict, Any, Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("chunked_upload")

# Add the parent directory to the path so we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Supabase client
try:
    from backend.services.integration.supabase_client import SupabaseService, get_supabase_client
    from backend.core.config import settings
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this script from the project root or backend directory")
    sys.exit(1)

def get_file_size(file_path: str) -> int:
    """Get the size of a file in bytes."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    return os.path.getsize(file_path)

def upload_file_in_chunks(
    file_path: str, 
    bucket_name: str = "full_videos",
    destination_path: Optional[str] = None,
    chunk_size: int = 5 * 1024 * 1024,  # 5MB chunks
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Upload a large file to Supabase Storage in chunks.
    
    Args:
        file_path: Path to the file to upload
        bucket_name: Name of the bucket to upload to
        destination_path: Path within the bucket to upload to (defaults to filename)
        chunk_size: Size of each chunk in bytes
        max_retries: Maximum number of retries for each chunk
        
    Returns:
        Dict with upload status and information
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"success": False, "error": f"File not found: {file_path}"}
    
    file_size = get_file_size(file_path)
    if file_size == 0:
        logger.error(f"File exists but is empty (0 bytes): {file_path}")
        return {"success": False, "error": f"File is empty: {file_path}"}
    
    # Use the file's basename if no destination path is provided
    if destination_path is None:
        destination_path = os.path.basename(file_path)
    
    # Initialize Supabase client with service role
    try:
        supabase = get_supabase_client(use_service_role=True)
        logger.info("Initialized Supabase client with service role")
    except Exception as auth_error:
        logger.error(f"Failed to initialize Supabase client: {str(auth_error)}")
        return {"success": False, "error": f"Authentication error: {str(auth_error)}"}

    # Initialize SupabaseService for bucket operations
    supabase_service = SupabaseService()
    
    # Check if bucket exists
    try:
        buckets = supabase.storage.list_buckets()
        logger.info(f"Available buckets: {buckets}")
        
        bucket_exists = False
        for bucket in buckets:
            if hasattr(bucket, 'name') and bucket.name == bucket_name:
                bucket_exists = True
                logger.info(f"Bucket '{bucket_name}' already exists")
                break
        
        if not bucket_exists:
            logger.warning(f"Bucket '{bucket_name}' does not exist, attempting to create it")
            # Create bucket with public access enabled
            supabase.storage.create_bucket(
                bucket_name, 
                {'public': True, 'file_size_limit': None}  # No file size limit
            )
            logger.info(f"Created bucket '{bucket_name}' with public access")
    except Exception as bucket_error:
        logger.warning(f"Error checking/creating bucket: {str(bucket_error)}, will attempt upload anyway")
    
    # Calculate total number of chunks
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    logger.info(f"Uploading file: {file_path}")
    logger.info(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
    logger.info(f"Chunk size: {chunk_size} bytes ({chunk_size / (1024 * 1024):.2f} MB)")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Destination: {bucket_name}/{destination_path}")
    
    # Start upload
    start_time = time.time()
    
    # Create a temporary file for each chunk with a unique name
    temp_dir = "/tmp/supabase_chunks"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique chunk names based on the destination path
    base_name = os.path.splitext(os.path.basename(destination_path))[0]
    extension = os.path.splitext(destination_path)[1]
    
    # Create a list to store chunk paths
    chunk_paths = []
    
    # Upload each chunk
    with open(file_path, 'rb') as f:
        for chunk_index in range(total_chunks):
            chunk_start = chunk_index * chunk_size
            f.seek(chunk_start)
            chunk_data = f.read(chunk_size)
            
            # Create a temporary file for this chunk
            chunk_filename = f"{base_name}_chunk_{chunk_index:04d}{extension}"
            chunk_path = os.path.join(temp_dir, chunk_filename)
            
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk_data)
            
            chunk_paths.append(chunk_path)
            
            # Upload this chunk
            chunk_destination = f"{destination_path}.part{chunk_index:04d}"
            
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    logger.info(f"Uploading chunk {chunk_index + 1}/{total_chunks} ({len(chunk_data) / (1024 * 1024):.2f} MB)")
                    
                    # Set proper content type
                    content_type = "application/octet-stream"
                    if chunk_index == 0 and file_path.lower().endswith(".mp4"):
                        content_type = "video/mp4"
                    
                    # Upload the chunk
                    with open(chunk_path, 'rb') as chunk_file:
                        response = supabase.storage.from_(bucket_name).upload(
                            path=chunk_destination,
                            file=chunk_file,
                            file_options={
                                "cache-control": "max-age=3600",
                                "upsert": "true",
                                "content-type": content_type
                            }
                        )
                    
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
                        # Clean up temporary files
                        for path in chunk_paths:
                            if os.path.exists(path):
                                os.remove(path)
                        return {
                            "success": False,
                            "error": f"Failed to upload chunk {chunk_index + 1}: {str(upload_error)}",
                            "file_path": file_path,
                            "chunks_completed": chunk_index
                        }
    
    # All chunks uploaded successfully
    logger.info(f"All {total_chunks} chunks uploaded successfully")
    
    # Clean up temporary files
    logger.info("Cleaning up temporary chunk files")
    for path in chunk_paths:
        if os.path.exists(path):
            os.remove(path)
    
    # Get the public URL for the uploaded file
    try:
        public_url = supabase.storage.from_(bucket_name).get_public_url(destination_path)
        
        # Replace host.docker.internal with localhost for external access
        if public_url and 'host.docker.internal' in public_url:
            original_url = public_url
            public_url = public_url.replace('host.docker.internal', 'localhost')
            logger.info(f"Converted Docker internal URL '{original_url}' to external URL: '{public_url}'")
        
        logger.info(f"Public URL: {public_url}")
    except Exception as url_error:
        logger.warning(f"Error getting public URL: {str(url_error)}")
        public_url = None
    
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
        "average_speed": avg_speed
    }

def main():
    """Main function to parse arguments and start the upload."""
    parser = argparse.ArgumentParser(description="Upload large files to Supabase Storage in chunks")
    parser.add_argument("file_path", help="Path to the file to upload")
    parser.add_argument("--bucket", default="full_videos", help="Name of the bucket to upload to")
    parser.add_argument("--destination", help="Path within the bucket to upload to (defaults to filename)")
    parser.add_argument("--chunk-size", type=int, default=5 * 1024 * 1024, help="Size of each chunk in bytes (default: 5MB)")
    parser.add_argument("--retries", type=int, default=3, help="Maximum number of retries for each chunk (default: 3)")
    
    args = parser.parse_args()
    
    try:
        result = upload_file_in_chunks(
            file_path=args.file_path,
            bucket_name=args.bucket,
            destination_path=args.destination,
            chunk_size=args.chunk_size,
            max_retries=args.retries
        )
        
        if result["success"]:
            logger.info("Upload completed successfully!")
            logger.info(f"File is available at: {result.get('public_url', 'Unknown URL')}")
            sys.exit(0)
        else:
            logger.error(f"Upload failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
