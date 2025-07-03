"""
Supabase Integration Module

This module provides functionality to directly integrate with Supabase,
including uploading files to storage, adding data to the database,
and sending jobs to queues.
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.services.integration.supabase_client import SupabaseService
from backend.services.integration.supabase_export import (
    format_video_for_supabase,
    format_clips_for_supabase,
    export_recognition_results
)

logger = logging.getLogger(__name__)


class SupabaseIntegration:
    """
    Service for integrating Parliament TV data with Supabase.
    """
    
    def __init__(self):
        """
        Initialize Supabase integration.
        """
        self.supabase = SupabaseService(use_service_role=True)
        # Only using full_videos_bucket for combined AV files
        self.full_videos_bucket = settings.SUPABASE_FULL_VIDEOS_BUCKET or "full_videos"
        logger.info(f"Initialized SupabaseIntegration with full_videos_bucket: {self.full_videos_bucket}")
    
    def upload_media_to_supabase(
        self, 
        video_path: str, 
        audio_path: str = None, 
        thumbnail_path: str = None
    ) -> Dict[str, str]:
        """
        Upload media files to Supabase storage.
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file (ignored)
            thumbnail_path: Path to thumbnail file (ignored)
            
        Returns:
            Dictionary with URLs for uploaded files
        """
        # We're not uploading any media files except combined AV files
        # And those are handled separately in export_and_upload_recognition
        logger.info("Skipping regular media uploads - only combined AV files will be uploaded")
        
        # Check if this is a combined AV file (should have combined_av_ in the filename)
        filename = os.path.basename(video_path)
        if 'combined_av_' in filename and os.path.exists(video_path):
            logger.info(f"Found combined AV file: {video_path}")
            try:
                # Upload the combined AV file to the full_videos bucket
                upload_result = self.supabase.upload_full_video(file_path=video_path)
                if upload_result.get("success"):
                    logger.info(f"Successfully uploaded combined AV file to Supabase: {upload_result.get('public_url')}")
                    return {"combined_av_url": upload_result.get("public_url")}
                else:
                    logger.error(f"Failed to upload combined AV file: {upload_result.get('error')}")
            except Exception as e:
                logger.error(f"Error uploading combined AV file: {str(e)}")
        else:
            logger.info(f"Skipping upload of non-combined AV file: {filename}")
            
        return {}
    
    def upload_export_files(self, export_paths: Dict[str, str]) -> Dict[str, str]:
        """
        Upload export files to Supabase storage.
        
        Args:
            export_paths: Dictionary of export paths
            
        Returns:
            Dictionary with URLs for uploaded files
        """
        # We're not uploading any JSON files to Supabase anymore
        # Only combined AV files should be uploaded directly via upload_full_video
        logger.info("Skipping JSON file uploads - only combined AV files will be uploaded")
        return {}
        
        # The original code below is commented out to prevent JSON file uploads
        '''
        result = {}
        
        for key, path in export_paths.items():
            if os.path.exists(path):
                # Upload directly to the root of the bucket
                filename = os.path.basename(path)
                storage_path = filename
                
                try:
                    # Always use the full_videos bucket since that's the only one that exists
                    self.supabase.upload_file("full_videos", storage_path, path)
                    url = self.supabase.get_public_url("full_videos", storage_path)
                    result[key] = url
                    logger.info(f"Uploaded {key} to Supabase: {url}")
                except Exception as e:
                    logger.error(f"Error uploading {key} to Supabase: {str(e)}")
            else:
                logger.warning(f"Export file not found: {path}")
        
        return result
        '''
    
    def add_to_video_processing_queue(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a job to the video_processing queue.
        
        Args:
            video_data: Video data to process
            
        Returns:
            Response from Supabase
        """
        try:
            response = self.supabase.add_to_video_processing_queue(video_data)
            logger.info(f"Added video to processing queue: {video_data.get('video_id')}")
            return response
        except Exception as e:
            logger.error(f"Error adding video to processing queue: {str(e)}")
            return {"error": str(e)}
    
    def _run_sync_parliament_clip_member_ids(self) -> Dict[str, Any]:
        """
        Run the sync_parliament_clip_member_ids.py script to ensure all member IDs in SQLite
        have corresponding Speaker records in PostgreSQL.
        
        Returns:
            Dict with sync results
        """
        try:
            logger.info("Running sync_parliament_clip_member_ids.py script to ensure all member IDs have Speaker records")
            import subprocess
            import sys
            import os
            
            # Get the path to the script
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      "backend/scripts/sync_parliament_clip_member_ids.py")
            
            # Check if we're running in Docker or locally
            if os.path.exists("/app/backend/scripts/sync_parliament_clip_member_ids.py"):
                script_path = "/app/backend/scripts/sync_parliament_clip_member_ids.py"
                
            logger.info(f"Sync script path: {script_path}")
            
            # Run the script using the Python interpreter
            result = subprocess.run([sys.executable, script_path], 
                                   capture_output=True, 
                                   text=True)
            
            if result.returncode == 0:
                logger.info("Successfully ran sync_parliament_clip_member_ids.py script")
                logger.info(f"Script output: {result.stdout}")
                return {"success": True, "output": result.stdout}
            else:
                logger.error(f"Error running sync_parliament_clip_member_ids.py script: {result.stderr}")
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"Error running sync_parliament_clip_member_ids.py script: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def add_to_clip_creation_queue(self, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add jobs to the clip_creation queue.
        
        Args:
            clip_data: List of clip data to process
            
        Returns:
            Response from Supabase
        """
        try:
            response = self.supabase.add_to_clip_creation_queue(clip_data)
            logger.info(f"Added {len(clip_data)} clips to creation queue")
            return response
        except Exception as e:
            logger.error(f"Error adding clips to creation queue: {str(e)}")
            return {"error": str(e)}
    
    def export_and_upload_recognition(
        self,
        video_path: str,
        recognition_results: Dict[str, Any],
        video_metadata: Dict[str, Any],
        db_session: Optional[Session] = None,
        video_id: Optional[int] = None,
        upload_media: bool = True
    ) -> Dict[str, Any]:
        """
        Export recognition results, upload to Supabase, and add to queues.
        
        Args:
            video_path: Path to video file
            recognition_results: Recognition results from facial recognition
            video_metadata: Metadata about the video
            db_session: Database session for accessing transcription data
            video_id: ID of the video in the database
            upload_media: Whether to upload media files to Supabase
            
        Returns:
            Dictionary with results of the export and upload
        """
        # Create temporary export directory using Docker container paths
        export_dir = os.path.join("/app/data/temp", "supabase_export", Path(video_path).stem)
        os.makedirs(export_dir, exist_ok=True)
        
        # Export recognition results to JSON files
        export_result = export_recognition_results(
            video_path=video_path,
            recognition_results=recognition_results,
            video_metadata=video_metadata,
            export_dir=export_dir,
            create_combined_av=True,
            db_session=db_session,
            video_id=video_id
        )
        
        result = {
            "export_paths": export_result,
            "supabase_urls": {},
            "queue_responses": {}
        }
                # Skip uploading JSON files to Supabase
        logger.info("Skipping JSON file uploads - only combined AV files will be uploaded")
        export_urls = {}
        
        # Upload ONLY the combined AV file if requested
        if upload_media:
            # Check if combined AV file was created and upload it directly
            combined_url = export_result.get("combined_av_path", "") or export_result.get("combined_url", "")
            logger.info(f"Combined AV path from export_result: {combined_url}")
            
            # If combined_url is not found in export_result, try to construct it
            if not combined_url or not os.path.exists(combined_url):
                # Try to find the combined AV file in the media directory
                from backend.core.config import settings
                media_dir = settings.MEDIA_STORAGE_PATH
                logger.info(f"Looking for combined AV files in media directory: {media_dir}")
                
                # Look for files with combined_av_{video_id} pattern
                import glob
                combined_files = glob.glob(os.path.join(media_dir, f"combined_av_{video_id}_*.mp4"))
                if combined_files:
                    # Use the most recent file if multiple exist
                    combined_files.sort(key=os.path.getmtime, reverse=True)
                    combined_url = combined_files[0]
                    logger.info(f"Found combined AV file: {combined_url}")
            
            if combined_url and os.path.exists(combined_url):
                logger.info(f"Uploading combined audio-video file: {combined_url}")
                try:
                    # Verify file exists and has proper size
                    file_size = os.path.getsize(combined_url)
                    logger.info(f"Combined AV file exists: {os.path.exists(combined_url)}, size: {file_size} bytes")
                    
                    # Make sure filename has combined_av_ prefix
                    filename = os.path.basename(combined_url)
                    if 'combined_av_' not in filename:
                        logger.warning(f"Combined AV file does not have combined_av_ prefix: {filename}")
                        # Rename the file to include the combined_av_ prefix if needed
                        new_filename = f"combined_av_{video_id}_{int(time.time())}.mp4"
                        new_path = os.path.join(os.path.dirname(combined_url), new_filename)
                        logger.info(f"Renaming file to include combined_av_ prefix: {new_path}")
                        shutil.copy(combined_url, new_path)
                        combined_url = new_path
                    
                    # Force re-initialize the Supabase client with service role
                    self.supabase = SupabaseService(use_service_role=True)
                    logger.info("Re-initialized Supabase client with service role")
                    
                    # Upload the combined file directly to the full_videos bucket
                    # Use the original filename as the destination path to preserve the combined_av_XXX_TIMESTAMP.mp4 format
                    logger.info(f"Starting upload of combined AV file to Supabase: {combined_url}")
                    upload_result = self.supabase.upload_full_video(file_path=combined_url)
                    logger.info(f"Upload result: {upload_result}")
                    
                    if upload_result.get("success"):
                        supabase_url = upload_result.get("public_url")
                        result["supabase_urls"]["combined_av_url"] = supabase_url
                        logger.info(f"Successfully uploaded combined AV file to Supabase: {supabase_url}")
                        
                        # Update the database with the Supabase URL if we have a session
                        if db_session:
                            try:
                                from backend.db.models import CaptureSession, RecognitionProcess
                                
                                # Try to find the capture session
                                capture = db_session.query(CaptureSession).filter(CaptureSession.id == video_id).first()
                                if capture:
                                    logger.info(f"Updating CaptureSession {video_id} with Supabase URL: {supabase_url}")
                                    capture.supabase_url = supabase_url
                                    capture.external_status = "completed"  # Mark as completed once upload is done
                                    db_session.commit()
                                    logger.info(f"Successfully updated CaptureSession {video_id} with Supabase URL")
                                else:
                                    logger.warning(f"Could not find CaptureSession with ID {video_id}")
                                    
                                    # Try to update RecognitionProcess as fallback
                                    rec_process = db_session.query(RecognitionProcess).filter(
                                        RecognitionProcess.video_id == video_id
                                    ).first()
                                    
                                    if rec_process:
                                        logger.info(f"Updating RecognitionProcess for video {video_id} with Supabase URL")
                                        rec_process.supabase_url = supabase_url
                                        db_session.commit()
                                        logger.info(f"Successfully updated RecognitionProcess with Supabase URL")
                            except Exception as db_e:
                                logger.error(f"Error updating database with Supabase URL: {str(db_e)}")
                    else:
                        logger.error(f"Failed to upload combined AV file to Supabase: {upload_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error during combined AV file upload: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                logger.warning(f"Combined AV file not found at path: {combined_url}")
                # Try to find the combined AV file in export_result
                combined_av_path = export_result.get("combined_av_path")
                logger.info(f"Trying alternative combined_av_path: {combined_av_path}")
                if combined_av_path and os.path.exists(combined_av_path):
                    logger.info(f"Found alternative combined AV file at: {combined_av_path}")
                    # Recursively call this block with the new path
                    upload_result = self.supabase.upload_full_video(file_path=combined_av_path)
                    if upload_result.get("success"):
                        supabase_url = upload_result.get("public_url")
                        result["supabase_urls"]["combined_av_url"] = supabase_url
                        logger.info(f"Successfully uploaded alternative combined AV file to Supabase: {supabase_url}")
                        
                        # Update database with the new URL
                        if db_session:
                            try:
                                from backend.db.models import CaptureSession
                                capture = db_session.query(CaptureSession).filter(CaptureSession.id == video_id).first()
                                if capture:
                                    capture.supabase_url = supabase_url
                                    capture.external_status = "completed"
                                    db_session.commit()
                            except Exception as db_e:
                                logger.error(f"Error updating database with alternative Supabase URL: {str(db_e)}")
                else:
                    logger.error("Could not find any combined AV file to upload to Supabase")
        else:
            logger.info("Skipping media upload as requested")
        
        # Load exported data
        try:
            with open(export_result["video_export_path"], "r") as f:
                import json
                video_data = json.load(f)
            
            with open(export_result["clips_export_path"], "r") as f:
                clips_data_raw = json.load(f)
                
            # Sanitize clips data to ensure it's JSON serializable
            from datetime import datetime, date
            import copy
            
            def sanitize_for_json(obj):
                """Recursively sanitize an object for JSON serialization"""
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: sanitize_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_for_json(i) for i in obj]
                elif isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                else:
                    return str(obj)
            
            # Create a sanitized copy of clips_data
            clips_data = sanitize_for_json(clips_data_raw)
            
            # Log the data we're working with
            logger.info(f"Processing {len(clips_data)} clips for Supabase export")
            if clips_data:
                logger.debug(f"Sample clip data: {json.dumps(clips_data[0] if clips_data else {})}")
                
                # Log the keys available in the first clip
                logger.info(f"Available keys in first clip: {list(clips_data[0].keys())}")
            else:
                logger.warning("No clips data available to process")
                
            # Run the sync script proactively to ensure all member IDs have corresponding Speaker records
            logger.info("Running member ID synchronization before processing clips")
            sync_result = self._run_sync_parliament_clip_member_ids()
            if sync_result.get("success"):
                logger.info("Member ID synchronization completed successfully")
            else:
                logger.warning("Member ID synchronization failed or was not needed")
                
            # Verify the sanitized data is JSON serializable
            try:
                json.dumps(clips_data)
                logger.info("Successfully sanitized clips data for JSON serialization")
            except Exception as e:
                logger.error(f"Failed to serialize sanitized clips data: {str(e)}")
                # Filter out clips without required fields
                valid_clips = []
                for clip_id, clip in enumerate(clips_data):
                    missing_fields = []
                    for required_field in required_fields:
                        if required_field not in clip or clip[required_field] is None:
                            missing_fields.append(required_field)
                    
                    # Try to fix missing fields if possible
                    if 'member_id' in missing_fields and 'metadata' in clip and clip['metadata']:
                        # Try to extract member_id from metadata
                        metadata = clip['metadata']
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except:
                                pass
                        
                        if isinstance(metadata, dict):
                            # Try different possible metadata fields for member_id
                            possible_member_id_fields = ['member_id', 'parliament_id', 'speaker_id', 'uuid']
                            for field in possible_member_id_fields:
                                if field in metadata and metadata[field]:
                                    clip['member_id'] = metadata[field]
                                    logger.info(f"Extracted member_id {clip['member_id']} from metadata.{field}")
                                    missing_fields.remove('member_id')
                                    break
                    
                    if 'full_video_path' in missing_fields and 'video_path' in clip and clip['video_path']:
                        # Use video_path as fallback for full_video_path
                        clip['full_video_path'] = clip['video_path']
                        logger.info(f"Using video_path as fallback for full_video_path: {clip['full_video_path']}")
                        missing_fields.remove('full_video_path')
                    
                    # If still missing required fields, skip this clip
                    if missing_fields:
                        logger.warning(f"Clip {clip_id} is missing required fields: {missing_fields}")
                        logger.warning(f"Clip details: {json.dumps({k: v for k, v in clip.items() if k not in excluded_fields})}")
                        continue
                    
                    valid_clips.append(clip)  # Verify this clip is serializable
                clips_data = valid_clips
                logger.info(f"After filtering out invalid clips: {len(clips_data)} clips remain")
            
            # Update URLs with Supabase URLs if available
            if "video_url" in result["supabase_urls"]:
                video_data["video_url"] = result["supabase_urls"]["video_url"]
            if "audio_url" in result["supabase_urls"]:
                video_data["audio_url"] = result["supabase_urls"]["audio_url"]
            if "thumbnail_url" in result["supabase_urls"]:
                video_data["thumbnail_url"] = result["supabase_urls"]["thumbnail_url"]
                
            # Create a simplified version of clips_data with only essential fields
            simplified_clips = []
            
            # Valid columns in parliament_member_clips table based on schema
            # Starred fields are required
            required_fields = [
                'member_id',          # integer not null
                'transcript',         # text not null
                'full_video_path',    # text not null
                'start_timestamp',    # text not null
                'end_timestamp',      # text not null
            ]
            
            optional_fields = [
                'id',                # uuid primary key
                'transcript_embedding', # vector null
                'clip_url',          # text null
                'session_date',      # date null
                'session_type',      # text null
                'debate_topic',      # text null
                'status',            # enum parliament_clip_status null default 'pending_review'
                'processing_notes',  # text null
                'confidence_score',  # numeric(4, 3) null
                'audio_quality_score', # numeric(4, 3) null
                'duration_seconds',  # numeric(10, 3) null
            ]
            
            # Fields that should NOT be included in the insert
            excluded_fields = [
                'is_deleted',         # boolean not null default false
                'deleted_at',        # timestamp with time zone null
                'last_synced_at',    # timestamp with time zone null default now()
                'created_at',        # timestamp with time zone null default now()
                'updated_at',        # timestamp with time zone null default now()
            ]
            
            valid_columns = required_fields + optional_fields
            
            # Map from our field names to the expected column names in parliament_member_clips table
            field_mapping = {
                'confidence': 'confidence_score',
                'duration': 'duration_seconds',
                'full_video_url': 'full_video_path',
                'start_time': 'start_timestamp',  # Use timestamp fields instead of time fields
                'end_time': 'end_timestamp',
                'speaker_id': 'member_id'  # Map speaker_id to member_id
            }
            
            for clip in clips_data:
                simplified_clip = {}
                
                # Process each valid column
                for target_field in valid_columns:
                    # Check if the field is in the clip data directly
                    if target_field in clip:
                        value = clip[target_field]
                        simplified_clip[target_field] = value
                    # Check if we need to map from a different field name
                    elif target_field in field_mapping.values():
                        # Find the original field name that maps to this target field
                        original_field = next((k for k, v in field_mapping.items() if v == target_field), None)
                        if original_field and original_field in clip:
                            value = clip[original_field]
                            simplified_clip[target_field] = value
                
                # Ensure all values are simple types and properly formatted
                for field, value in list(simplified_clip.items()):
                    # Handle specific field types
                    if field == 'session_date' and value:
                        # Ensure session_date is in the correct format (YYYY-MM-DD)
                        try:
                            # If it's not already a date string in YYYY-MM-DD format, convert it
                            if not isinstance(value, str) or len(value) != 10 or value[4] != '-':
                                from datetime import datetime
                                if isinstance(value, (int, float)):
                                    # Assume it's a timestamp
                                    date_obj = datetime.fromtimestamp(value)
                                    simplified_clip[field] = date_obj.strftime('%Y-%m-%d')
                                else:
                                    # Default to today's date
                                    simplified_clip[field] = datetime.now().strftime('%Y-%m-%d')
                        except Exception as e:
                            logger.warning(f"Failed to format session_date: {e}")
                            simplified_clip[field] = None  # Set to None if we can't parse it
                    elif field == 'member_id':
                        try:
                            # Ensure member_id is an integer
                            if value is not None:
                                try:
                                    # First try to convert directly to int
                                    simplified_clip[field] = int(value)
                                    logger.info(f"Successfully converted member_id {value} to int: {simplified_clip[field]}")
                                except (ValueError, TypeError):
                                    # If it's a UUID, try multiple approaches to find the Speaker
                                    member_id_str = str(value)
                                    logger.info(f"Looking up Speaker for UUID member_id: {member_id_str}")
                                    
                                    # Try to find Speaker by parliament_id (most reliable)
                                    speaker = db_session.query(Speaker).filter(Speaker.parliament_id == member_id_str).first()
                                    if speaker:
                                        logger.info(f"Found Speaker by parliament_id: {speaker.id}")
                                        # Use the Speaker's ID as the member_id
                                        simplified_clip[field] = speaker.id
                                    else:
                                        # Try to find by UUID in any field
                                        try:
                                            uuid_obj = uuid.UUID(member_id_str)
                                            speaker = db_session.query(Speaker).filter(
                                                (Speaker.id.cast(String) == member_id_str) | 
                                                (Speaker.parliament_id == member_id_str) | 
                                                (Speaker.member_id == member_id_str)
                                            ).first()
                                            
                                            if speaker:
                                                logger.info(f"Found Speaker by UUID search: {speaker.id}")
                                                simplified_clip[field] = speaker.id
                                            else:
                                                logger.warning(f"No Speaker found for UUID {member_id_str}, running sync script")
                                                # Don't run the sync script again to avoid recursion
                                                # Just log the issue and continue
                                                logger.warning(f"No Speaker found for UUID {member_id_str}, but skipping sync to avoid recursion")
                                                simplified_clip[field] = None
                                        except (ValueError, TypeError):
                                            logger.warning(f"Invalid UUID format: {member_id_str}")
                                            simplified_clip[field] = None
                        except Exception as e:
                            logger.error(f"Error processing member_id {value}: {str(e)}")
                            simplified_clip[field] = None
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        simplified_clip[field] = str(value)
                
                # Remove any excluded fields
                for field in excluded_fields:
                    if field in simplified_clip:
                        del simplified_clip[field]
                
                # Ensure all required fields are present
                if 'id' not in simplified_clip:
                    simplified_clip['id'] = str(uuid.uuid4())
                    
                # Set default status if not present
                if 'status' not in simplified_clip:
                    # Use 'completed' as the status
                    simplified_clip['status'] = 'completed'  # Valid values: processing, completed, failed, pending_review
                
                # Calculate duration_seconds if not present but we have start and end timestamps
                if 'duration_seconds' not in simplified_clip and 'start_timestamp' in simplified_clip and 'end_timestamp' in simplified_clip:
                    try:
                        start_timestamp = simplified_clip['start_timestamp']
                        end_timestamp = simplified_clip['end_timestamp']
                        
                        # Check if timestamps are already numeric
                        if isinstance(start_timestamp, (int, float)) and isinstance(end_timestamp, (int, float)):
                            # Direct calculation if they're already numeric
                            simplified_clip['duration_seconds'] = round(float(end_timestamp) - float(start_timestamp), 3)
                        elif isinstance(start_timestamp, str) and isinstance(end_timestamp, str):
                            # Try to parse string timestamps (format: HH:MM:SS)
                            try:
                                start_parts = start_timestamp.split(':')
                                end_parts = end_timestamp.split(':')
                                
                                if len(start_parts) == 3 and len(end_parts) == 3:
                                    start_seconds = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
                                    end_seconds = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
                                    simplified_clip['duration_seconds'] = round(end_seconds - start_seconds, 3)
                            except Exception as e:
                                logger.warning(f"Failed to parse string timestamps: {e}")
                                # Try direct conversion as fallback
                                try:
                                    start_seconds = float(start_timestamp)
                                    end_seconds = float(end_timestamp)
                                    simplified_clip['duration_seconds'] = round(end_seconds - start_seconds, 3)
                                except:
                                    pass
                    except Exception as e:
                        logger.warning(f"Failed to calculate duration_seconds: {e}")
                
                # Ensure all required fields are present
                missing_required = [field for field in required_fields if field not in simplified_clip]
                if missing_required:
                    logger.warning(f"Clip {simplified_clip.get('id', 'unknown')} is missing required fields: {missing_required}")
                    # Log the current state of the clip for debugging
                    logger.debug(f"Current clip state: {simplified_clip}")
                    # Skip clips with missing required fields
                    continue
                
                simplified_clips.append(simplified_clip)
            
            # Log the simplified clips
            logger.info(f"Prepared {len(simplified_clips)} simplified clips for Supabase export")
            if simplified_clips:
                logger.debug(f"Sample simplified clip: {json.dumps(simplified_clips[0])}")
                logger.info(f"Keys in first simplified clip: {list(simplified_clips[0].keys())}")
            else:
                logger.warning("All clips were filtered out during processing!")
                # If we have no simplified clips but had raw clips, log the first raw clip for debugging
                if clips_data:
                    logger.debug(f"First raw clip that was filtered out: {json.dumps(clips_data[0])}")
                    
                    # Check what required fields are missing from the first raw clip
                    first_clip = clips_data[0]
                    missing_in_first = []
                    for req_field in required_fields:
                        if req_field not in first_clip:
                            # Check if it could be mapped from another field
                            mapped = False
                            for orig_field, target_field in field_mapping.items():
                                if target_field == req_field and orig_field in first_clip:
                                    mapped = True
                                    break
                            if not mapped:
                                missing_in_first.append(req_field)
                    
                    logger.warning(f"First raw clip is missing these required fields: {missing_in_first}")
                    logger.warning(f"Available fields in first raw clip: {list(first_clip.keys())}")
                    
                    # Instead of creating debug clips, log the issue and run the sync script automatically
                    logger.warning("No valid clips found. This may be due to member_id mapping issues.")
                    logger.warning("Running sync_parliament_clip_member_ids.py script to create Speaker records for all member IDs.")
                    
                    # Run the sync script but don't retry to avoid recursion
                    sync_result = self._run_sync_parliament_clip_member_ids()
                    
                    if sync_result.get("success"):
                        logger.info("Successfully synchronized member IDs with Speaker records")
                        logger.info("However, not retrying clip processing to avoid recursion")
                        
                        # Instead of recursively calling ourselves, just continue with what we have
                        # This may result in no clips being exported, but it avoids the recursion error
                        logger.warning("No valid clips could be processed after synchronization")
                        
                        # Return a partial result indicating the sync was successful but no clips were processed
                        result["clips_processed"] = 0
                        result["sync_successful"] = True
                    else:
                        logger.error(f"Failed to synchronize member IDs: {sync_result.get('error')}")
                        
                    # Log details about the first clip for debugging
                    logger.info(f"Example clip that couldn't be processed: {json.dumps({k: v for k, v in first_clip.items() if k not in excluded_fields})}")
            
            # Add to queues
            video_queue_response = self.add_to_video_processing_queue(video_data)
            result["queue_responses"]["video_processing"] = video_queue_response
            
            # Verify the simplified clips are JSON serializable
            try:
                json_str = json.dumps(simplified_clips)
                logger.info(f"Successfully serialized simplified clips to JSON (length: {len(json_str)} characters)")
                
                clips_queue_response = self.add_to_clip_creation_queue(simplified_clips)
                result["queue_responses"]["clip_creation"] = clips_queue_response
            except Exception as e:
                logger.error(f"JSON serialization error with simplified clips: {str(e)}")
                result["queue_responses"]["clip_creation"] = {"error": f"JSON serialization error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error adding to Supabase queues: {str(e)}")
            result["queue_responses"]["error"] = str(e)
        
        return result
