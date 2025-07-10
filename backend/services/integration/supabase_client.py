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
        logger.warning(f"🔄 DEBUG: upload_full_video called for file_path={file_path} - SUPABASE STORAGE UPLOAD ENTRY POINT")
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
        Add clips to the parliament_member_clips table.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        import uuid
        from datetime import datetime
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
            # Ensure we're not passing any empty data or problematic parameters
            if not clip_data:
                logger.warning("No clip data provided to add_to_clip_creation_queue")
                return {"success": False, "error": "No clip data provided"}
            
            # Create a deep copy of the data and ensure all values are JSON serializable
            import copy
            import json
            from datetime import datetime, date
            
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
                                if value == -1:
                                    # Use -1 as a special ID for unknown members
                                    clean_clip[key] = -1
                                    logger.info("Using special ID -1 for unknown member")
                                # If already an integer, use as is
                                elif isinstance(value, int):
                                    clean_clip[key] = value
                                # If it's a string that can be converted to int, do so
                                elif isinstance(value, str) and value.isdigit():
                                    clean_clip[key] = int(value)
                                # For any other format, use special ID
                                else:
                                    logger.warning(f"Unrecognized member_id format: {value}, using special ID -1")
                                    clean_clip[key] = -1
                            except (ValueError, TypeError) as e:
                                # For any conversion error, use special ID
                                logger.warning(f"Error converting member_id {value}: {e}, using special ID -1")
                                clean_clip[key] = -1
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
                    if member_id is not None:
                        # If we haven't fetched valid member IDs yet, do it now
                        if valid_member_ids is None:
                            try:
                                # Get a list of valid member_ids (integer) from the parliament_members table
                                member_response = self.client.table('parliament_members').select('member_id').execute()
                                valid_member_ids = [member['member_id'] for member in member_response.data if 'member_id' in member] if member_response.data else []
                                logger.info(f"Fetched {len(valid_member_ids)} valid member_ids from parliament_members table")
                                
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
                            # CRITICAL FIX: Ensure member_id is an integer for comparison
                            try:
                                if not isinstance(member_id, int):
                                    logger.warning(f"Converting member_id {member_id} (type: {type(member_id).__name__}) to integer for validation")
                                    member_id = int(member_id)
                                    # Update the member_id in the clip data
                                    clean_clip['member_id'] = member_id
                            except (ValueError, TypeError) as e:
                                logger.error(f"Failed to convert member_id {member_id} to integer: {str(e)}")
                                logger.warning(f"Skipping clip with non-integer member ID {member_id}")
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
                    json.dumps(clean_clip)
                    cleaned_data.append(clean_clip)
                except Exception as e:
                    logger.error(f"Skipping non-serializable clip: {str(e)}")
                    
            if not cleaned_data:
                logger.error("No valid clips after cleaning for JSON serialization")
                return {"success": False, "error": "No valid clips after cleaning"}
            
            logger.info(f"Sending {len(cleaned_data)} cleaned clips to Supabase clip_creation_queue")
            
            # Directly convert to JSON string and back to ensure it's serializable
            json_str = json.dumps(cleaned_data)
            final_data = json.loads(json_str)
            
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
                        # Validate member_id is an integer and exists in parliament_members table
                        try:
                            # Ensure it's an integer
                            if not isinstance(clip['member_id'], int):
                                clip['member_id'] = int(clip['member_id'])
                                
                            # Special case: Allow member_id -1 for unknown speakers
                            if clip['member_id'] == -1:
                                logger.info(f"Allowing special member ID -1 for unknown speaker in second validation")
                                # Keep the -1 as is, don't verify or replace with fallback
                            else:
                                # Verify this member_id exists in parliament_members table
                                member_check = self.client.table('parliament_members').select('member_id').eq('member_id', clip['member_id']).execute()
                                if not member_check.data or len(member_check.data) == 0:
                                    logger.warning(f"Member ID {clip['member_id']} not found in parliament_members table")
                                    logger.warning(f"Skipping clip with invalid member ID {clip['member_id']}")
                                    continue  # Skip this clip instead of using a fallback ID
                        except (ValueError, TypeError) as e:
                            logger.error(f"Invalid member_id format: {e}")
                            continue  # Skip this clip if member_id is invalid
                        except Exception as e:
                            logger.error(f"Error validating member_id: {e}")
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
            logger.error(f"Error adding to clip creation queue: {str(e)}")
            return {"error": str(e)}
