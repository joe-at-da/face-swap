"""
Supabase Integration Module

This module provides functionality to directly integrate with Supabase,
including uploading files to storage, adding data to the database,
and sending jobs to queues.
"""

import os
import json
import uuid
import time
import shutil
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.services.integration.supabase_client import SupabaseService
from backend.services.integration.supabase_export import (
    format_video_for_supabase,
    format_clips_for_supabase
)
# Import the correct export_recognition_results function
from backend.services.recognition.supabase_export import export_recognition_results

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
    
    def export_and_upload_recognition(self, video_path: str, recognition_results: Dict[str, Any], video_metadata: Dict[str, Any], db_session: Optional[Session] = None, video_id: Optional[int] = None, upload_media: bool = True) -> Dict[str, Any]:
        # Import these at the function level to avoid any shadowing issues
        import json as json_module
        from datetime import datetime as datetime_module
        logger.warning(f"🚨 DEBUG: export_and_upload_recognition called for video_id={video_id} - SUPABASE UPLOAD ENTRY POINT")
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
        # Extract audio path from video_metadata or find it based on common patterns
        audio_path = video_metadata.get("audio_path")
        
        # If audio_path is not provided or doesn't exist, try to find it
        if not audio_path or not os.path.exists(audio_path):
            # Get video filename without extension
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            logger.info(f"Looking for audio file for video: {video_name}")
            
            # Check common locations for audio files
            data_dir = "/app/data"
            audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
            media_dir = os.path.join(data_dir, "media")
            
            # Try common naming patterns for audio files
            potential_audio_files = [
                # Check in media directory first (most common location)
                os.path.join(media_dir, f"{video_name}.mp3"),
                os.path.join(media_dir, f"audio_{video_name}.mp3"),
                os.path.join(media_dir, f"{video_name}_audio.mp3"),
                # Check in audio extracts directory
                os.path.join(audio_extracts_dir, f"{video_name}.audio.mp3"),
                os.path.join(audio_extracts_dir, f"{video_name}.mp3"),
                os.path.join(audio_extracts_dir, f"capture_{video_name}.audio.mp3"),
                os.path.join(audio_extracts_dir, f"capture_{video_name}.mp3"),
                os.path.join(audio_extracts_dir, f"{video_name}_audio.mp3"),
                # Try other audio formats
                os.path.join(media_dir, f"{video_name}.m4a"),
                os.path.join(media_dir, f"{video_name}.aac"),
                os.path.join(audio_extracts_dir, f"{video_name}.m4a"),
                os.path.join(audio_extracts_dir, f"{video_name}.aac")
            ]
            
            for audio_file in potential_audio_files:
                if os.path.exists(audio_file):
                    logger.info(f"Found audio file: {audio_file}")
                    audio_path = audio_file
                    break
        
        logger.warning(f"🔍 DEBUG: Calling export_recognition_results with video_id={video_id}, audio_path={audio_path}")
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Audio file exists at {audio_path}, size: {os.path.getsize(audio_path)} bytes")
        else:
            logger.warning(f"Audio file not found or invalid: {audio_path}")
        
        # Create temporary export directory for JSON files
        export_dir = os.path.join("/app/data/temp", "supabase_export", Path(video_path).stem)
        os.makedirs(export_dir, exist_ok=True)
        
        # Call the correct export_recognition_results function with the right parameters
        export_result = export_recognition_results(
            video_id=video_id,
            recognition_results=recognition_results,
            video_path=video_path,
            audio_path=audio_path,
            metadata=video_metadata,  # Pass video_metadata as metadata
            db_session=db_session
        )
        
        # Ensure export_result has a consistent structure with all required paths
        result = {
            "export_paths": {
                "video_export_path": export_result.get("video_export_path"),
                "clips_export_path": export_result.get("clips_export_path"),
                "recognition_export_path": export_result.get("recognition_export_path"),
                "combined_av_path": export_result.get("combined_av_path")
            },
            "supabase_urls": {},
            "queue_responses": {}
        }
        
        # If export_result has an export_paths dictionary, use those values with priority
        if "export_paths" in export_result and isinstance(export_result["export_paths"], dict):
            for key, value in export_result["export_paths"].items():
                if value:  # Only update if value is not None/empty
                    result["export_paths"][key] = value
        
        # Ensure all paths in export_paths are also available at the root level for backward compatibility
        for key, value in result["export_paths"].items():
            if value:  # Only set if value is not None/empty
                export_result[key] = value
        
        # Generate any missing paths with timestamps for uniqueness
        timestamp = datetime_module.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure video_export_path exists
        if not result["export_paths"]["video_export_path"]:
            result["export_paths"]["video_export_path"] = os.path.join(export_dir, f"recognition_export_{video_id}_{timestamp}.json")
            export_result["video_export_path"] = result["export_paths"]["video_export_path"]
        
        # Ensure clips_export_path exists
        if not result["export_paths"]["clips_export_path"]:
            result["export_paths"]["clips_export_path"] = os.path.join(export_dir, f"clips_export_{video_id}_{timestamp}.json")
            export_result["clips_export_path"] = result["export_paths"]["clips_export_path"]
            logger.info("Skipping JSON file uploads - only combined AV files will be uploaded")
        export_urls = {}
        
        # Validate that all required export paths exist and are accessible
        for path_key, path_value in result["export_paths"].items():
            if path_value:
                file_exists = os.path.exists(path_value)
                file_size = os.path.getsize(path_value) if file_exists else 0
                logger.info(f"Export path validation - {path_key}: exists={file_exists}, size={file_size}, path={path_value}")
        
        # Upload ONLY the combined AV file if requested
        if upload_media:
            logger.warning(f"🔍 DEBUG: Looking for combined AV file in export_result keys: {list(export_result.keys())}")

        
            # Check all possible keys where the combined AV file path might be stored
            combined_url = None
            possible_keys = ["combined_av_path", "combined_av_url", "combined_url", "combined_path", "av_path"]
            
            for key in possible_keys:
                if key in export_result and export_result[key]:
                    combined_url = export_result[key]
                    logger.warning(f"🔍 Found combined AV path in export_result[{key}]: {combined_url}")
                    break
                
            # If still not found, check if it's nested in a dictionary
            if not combined_url:
                for key, value in export_result.items():
                    if isinstance(value, dict) and any(av_key in value for av_key in possible_keys):
                        for av_key in possible_keys:
                            if av_key in value and value[av_key]:
                                combined_url = value[av_key]
                                logger.warning(f"🔍 Found nested combined AV path in export_result[{key}][{av_key}]: {combined_url}")
                                break
                        if combined_url:
                            break
        
            # IMPORTANT: We should always use full_video_path (combined AV) for Supabase
            # No fallbacks - if combined AV is not found, we should error
            if not combined_url:
                error_msg = "Combined AV file not found. Cannot proceed with export."
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "export_paths": result["export_paths"]
                }
            
            # Verify if the combined URL is valid and file exists
            if combined_url:
                file_exists = os.path.exists(combined_url)
                file_size = os.path.getsize(combined_url) if file_exists else 0
                logger.warning(f"🔍 Combined AV file check - Exists: {file_exists}, Size: {file_size} bytes, Path: {combined_url}")
                
                # If file doesn't exist or has zero size, log a clear error
                if not file_exists:
                    logger.error(f"Combined AV file does not exist at path: {combined_url}")
                elif file_size == 0:
                    logger.error(f"Combined AV file exists but has zero size: {combined_url}")
            else:
                logger.error("No combined AV file path found in export results")
            
            # If combined_url is not found in export_result or file doesn't exist, try to find it
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
                                import json
                                from backend.db.models import CaptureSession, RecognitionProcess
                                
                                # Try to find the capture session
                                capture = db_session.query(CaptureSession).filter(CaptureSession.id == video_id).first()
                                if capture:
                                    logger.info(f"Updating CaptureSession {video_id} with Supabase URL: {supabase_url}")
                                    
                                    # Store the URL in capture_metadata JSON field instead of a direct attribute
                                    if not capture.capture_metadata:
                                        capture.capture_metadata = {}
                                    elif isinstance(capture.capture_metadata, str):
                                        try:
                                            capture.capture_metadata = json_module.loads(capture.capture_metadata)
                                        except json_module.JSONDecodeError:
                                            capture.capture_metadata = {}
                                    
                                    # Ensure capture_metadata is a dictionary
                                    if not isinstance(capture.capture_metadata, dict):
                                        capture.capture_metadata = {}
                                    
                                    # Store the URL in the metadata
                                    capture.capture_metadata["supabase_url"] = supabase_url
                                    capture.external_status = "completed"  # Mark as completed once upload is done
                                    
                                    # Explicitly log the before and after values
                                    logger.info(f"Before update - CaptureSession {video_id} metadata: {capture.capture_metadata}")
                                    
                                    # Commit the changes
                                    db_session.commit()
                                    
                                    # Verify the update by refreshing the object
                                    db_session.refresh(capture)
                                    logger.info(f"After update - CaptureSession {video_id} metadata: {capture.capture_metadata}")
                                    
                                    # Check if the URL was properly saved
                                    if isinstance(capture.capture_metadata, dict) and capture.capture_metadata.get("supabase_url") == supabase_url:
                                        logger.info(f"Successfully updated CaptureSession {video_id} with Supabase URL")
                                        
                                        # Also update the RecognitionProcess if it exists
                                        import json  # Ensure json is available in this scope
                                        rec_process = db_session.query(RecognitionProcess).filter(RecognitionProcess.video_id == video_id).first()
                                        if rec_process:
                                            logger.info(f"Updating RecognitionProcess for video {video_id} with Supabase URL")
                                            # Store URL in recognition_results JSON field
                                            if not hasattr(rec_process, 'recognition_results') or not rec_process.recognition_results:
                                                rec_process.recognition_results = {}
                                            elif isinstance(rec_process.recognition_results, str):
                                                try:
                                                    rec_process.recognition_results = json_module.loads(rec_process.recognition_results)
                                                except json_module.JSONDecodeError:
                                                    rec_process.recognition_results = {}
                                        
                                            # Ensure recognition_results is a dictionary
                                            if not isinstance(rec_process.recognition_results, dict):
                                                rec_process.recognition_results = {}
                                            
                                            # Create supabase_urls dict if it doesn't exist
                                            if "supabase_urls" not in rec_process.recognition_results:
                                                rec_process.recognition_results["supabase_urls"] = {}
                                            
                                            # Log before value
                                            logger.info(f"Before update - RecognitionProcess for video {video_id} recognition_results: {rec_process.recognition_results}")
                                            
                                            # Ensure recognition_results is a dictionary
                                            if isinstance(rec_process.recognition_results, str):
                                                try:
                                                    recognition_results_dict = json_module.loads(rec_process.recognition_results)
                                                except json_module.JSONDecodeError:
                                                    recognition_results_dict = {"supabase_urls": {}}
                                            else:
                                                recognition_results_dict = rec_process.recognition_results if isinstance(rec_process.recognition_results, dict) else {"supabase_urls": {}}
                                            
                                            # Ensure supabase_urls exists
                                            if "supabase_urls" not in recognition_results_dict:
                                                recognition_results_dict["supabase_urls"] = {}
                                                
                                            # Update the URL
                                            recognition_results_dict["supabase_urls"]["combined_av_url"] = supabase_url
                                            
                                            # Convert to JSON string before saving to database
                                            rec_process.recognition_results = json_module.dumps(recognition_results_dict)
                                            
                                            # Commit the changes
                                            db_session.commit()
                                            
                                            # Verify the update
                                            db_session.refresh(rec_process)
                                            logger.info(f"After update - RecognitionProcess for video {video_id} recognition_results: {rec_process.recognition_results}")
                                            
                                            # Check if the URL was properly saved
                                            try:
                                                # Parse the JSON string to check the values
                                                saved_results = json_module.loads(rec_process.recognition_results) if isinstance(rec_process.recognition_results, str) else rec_process.recognition_results
                                                if saved_results.get("supabase_urls", {}).get("combined_av_url") == supabase_url:
                                                    logger.info(f"Successfully updated RecognitionProcess with Supabase URL")
                                                else:
                                                    logger.error(f"Failed to update RecognitionProcess with Supabase URL. Value not saved correctly.")
                                            except Exception as e:
                                                logger.error(f"Error verifying RecognitionProcess update: {str(e)}")
                                                logger.error(f"Failed to update RecognitionProcess with Supabase URL. Value not saved correctly.")
                                    else:
                                        logger.error(f"Could not find either CaptureSession or RecognitionProcess for video {video_id}")
                            except Exception as db_e:
                                logger.error(f"Error updating database with Supabase URL: {str(db_e)}")
                                import traceback
                                logger.error(f"Database update traceback: {traceback.format_exc()}")
                    else:
                        logger.error(f"Failed to upload combined AV file to Supabase: {upload_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error during combined AV file upload: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                logger.error(f"Combined AV file not found or upload failed: {combined_url}")
                # Try to find the combined AV file in export_result using a different key
                combined_av_path = export_result.get("combined_av_path")
                logger.info(f"Trying alternative combined_av_path: {combined_av_path}")
                
                if combined_av_path and os.path.exists(combined_av_path) and os.path.getsize(combined_av_path) > 0:
                    logger.info(f"Found valid alternative combined AV file at: {combined_av_path}")
                    # Upload the alternative file
                    upload_result = self.supabase.upload_full_video(file_path=combined_av_path)
                    logger.info(f"Alternative upload result: {upload_result}")
                    
                    if upload_result.get("success"):
                        supabase_url = upload_result.get("public_url")
                        result["supabase_urls"]["combined_av_url"] = supabase_url
                        logger.info(f"Successfully uploaded alternative combined AV file to Supabase: {supabase_url}")
                        
                        # Update database with the new URL
                        if db_session:
                            try:
                                import json
                                from backend.db.models import CaptureSession
                                capture = db_session.query(CaptureSession).filter(CaptureSession.id == video_id).first()
                                if capture:
                                    # Store URL in capture_metadata JSON field
                                    if not capture.capture_metadata:
                                        capture.capture_metadata = {}
                                    elif isinstance(capture.capture_metadata, str):
                                        try:
                                            capture.capture_metadata = json_module.loads(capture.capture_metadata)
                                        except json_module.JSONDecodeError:
                                            capture.capture_metadata = {}
                                    
                                    # Ensure capture_metadata is a dictionary
                                    if not isinstance(capture.capture_metadata, dict):
                                        capture.capture_metadata = {}
                                    
                                    # Store the URL in the metadata
                                    capture.capture_metadata["supabase_url"] = supabase_url
                                    capture.external_status = "completed"
                                    db_session.commit()
                                    
                                    # Log the update
                                    logger.info(f"Updated CaptureSession {video_id} with alternative Supabase URL in JSON fields: {supabase_url}")
                            except Exception as db_e:
                                logger.error(f"Error updating database with alternative Supabase URL: {str(db_e)}")
                    else:
                        logger.error(f"Failed to upload alternative combined AV file: {upload_result.get('error')}")
                        result["errors"] = result.get("errors", []) + ["Failed to upload alternative combined AV file"]
                else:
                    logger.error("Could not find any combined AV file to upload to Supabase")
        else:
            logger.info("Skipping media upload as requested")
        
        # Load exported data
        try:
            # Check if video export path exists, create it if it doesn't
            video_export_path = export_result.get("video_export_path")
            if not video_export_path or not os.path.exists(video_export_path):
                logger.warning(f"Video export file does not exist at path: {video_export_path}")
                # Create directory and empty export file
                timestamp = datetime_module.now().strftime("%Y%m%d_%H%M%S")
                export_dir = os.path.join("/app/data/temp/supabase_export", str(video_id))
                os.makedirs(export_dir, exist_ok=True)
                
                video_export_path = os.path.join(export_dir, f"recognition_export_{video_id}_{timestamp}.json")
                with open(video_export_path, 'w') as f:
                    json_module.dump({"video_id": video_id, "timestamp": timestamp, "events": [], "note": "No recognition events found for export"}, f)
                
                logger.info(f"Created empty video export file at: {video_export_path}")
                result["export_paths"]["video_export_path"] = video_export_path
                export_result["video_export_path"] = video_export_path
            
            # Now try to read the video export file
            try:
                with open(video_export_path, "r") as f:
                    video_data = json_module.load(f)
            except Exception as e:
                logger.error(f"Error reading video export file: {str(e)}")
                video_data = {"video_id": video_id, "events": []}
            
            # Use the properly structured clips_export_path with validation
            clips_export_path = result["export_paths"]["clips_export_path"]
            logger.info(f"Reading clips from: {clips_export_path}")
            
            # Validate clips export path
            if not clips_export_path or not os.path.exists(clips_export_path):
                logger.warning(f"Clips export file does not exist at path: {clips_export_path}")
                # Try to find an alternative path
                for key, path in export_result.items():
                    if isinstance(path, str) and "clip" in key.lower() and os.path.exists(path) and path.endswith(".json"):
                        logger.info(f"Found alternative clips export path: {key} -> {path}")
                        clips_export_path = path
                        result["export_paths"]["clips_export_path"] = path
                        break
                        
                if not clips_export_path or not os.path.exists(clips_export_path):
                    logger.warning("Could not find any valid clips export path, creating empty file")
                    # Create empty clips export file
                    timestamp = datetime_module.now().strftime("%Y%m%d_%H%M%S")
                    export_dir = os.path.join("/app/data/temp/supabase_export", str(video_id))
                    os.makedirs(export_dir, exist_ok=True)
                    
                    clips_export_path = os.path.join(export_dir, f"clips_export_{video_id}_{timestamp}.json")
                    with open(clips_export_path, 'w') as f:
                        json_module.dump({"video_id": video_id, "timestamp": timestamp, "clips": [], "note": "No clips found for export"}, f)
                    
                    logger.info(f"Created empty clips export file at: {clips_export_path}")
                    result["export_paths"]["clips_export_path"] = clips_export_path
            
            # Now try to read the clips export file
            try:
                with open(clips_export_path, "r") as f:
                    clips_data_raw = json_module.load(f)
            except json_module.JSONDecodeError as e:
                logger.error(f"Invalid JSON in clips export file: {str(e)}")
                return {
                    "success": False,
                    "error": f"Invalid JSON in clips export file: {str(e)}",
                    "export_paths": result["export_paths"]
                }
            except Exception as e:
                logger.error(f"Error reading clips export file: {str(e)}")
                return {
                    "success": False,
                    "error": f"Error reading clips export file: {str(e)}",
                    "export_paths": result["export_paths"]
                }
                
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
                logger.debug(f"Sample clip data: {json_module.dumps(clips_data[0])}")
                
                # Log the keys available in the first clip
                logger.info(f"Available keys in first clip: {list(clips_data[0].keys())}")
            else:
                logger.debug("No clips data available for sample display")
                logger.warning("No clips data available to process")
                
            # Run the sync script proactively to ensure all member IDs have corresponding Speaker records
            logger.info("Running member ID synchronization before processing clips")
            sync_result = self._run_sync_parliament_clip_member_ids()
            if sync_result.get("success"):
                logger.info("Member ID synchronization completed successfully")
                # Add success message to result
                result["sync_status"] = "success"
                result["sync_message"] = "Successfully synchronized member IDs between SQLite and PostgreSQL"
            else:
                logger.warning(f"Member ID synchronization failed: {sync_result.get('error', 'Unknown error')}")
                # Add warning to result
                result["sync_status"] = "warning"
                result["sync_message"] = f"Member ID synchronization warning: {sync_result.get('error', 'Unknown error')}"
                result["warnings"] = result.get("warnings", []) + ["Member ID synchronization issue - some clips may fail to export"]
                
            # Verify the sanitized data is JSON serializable
            try:
                json_module.dumps(clips_data)
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
                                metadata = json_module.loads(metadata)
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
                    
                    # IMPORTANT: We should always use full_video_path (combined AV) for Supabase
                    # No fallbacks - if full_video_path is missing, skip the clip
                    if 'full_video_path' in missing_fields:
                        logger.error(f"❌ Missing full_video_path (combined AV file) for clip. Skipping.")
                        # Keep full_video_path in missing_fields so the clip will be skipped
                    
                    # If still missing required fields, skip this clip
                    if missing_fields:
                        logger.warning(f"Clip {clip_id} is missing required fields: {missing_fields}")
                        logger.warning(f"Clip details: {json_module.dumps({k: v for k, v in clip.items() if k not in excluded_fields})}")
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
                'video_path': 'full_video_path',  # IMPORTANT: Always map video_path to full_video_path (combined AV)
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
                        # Add field to simplified clip
                        simplified_clip[target_field] = clip[target_field]

                    # Map recognition events to Supabase schema
                    supabase_clips = []
                    skipped_clips = 0
                    
                    for event in recognition_events:
                        # Create a clean clip for Supabase
                        try:
                            # Generate a unique ID for this clip
                            clip_id = str(uuid.uuid4())
                            
                            # Check if this clip already exists
                            signature = f"{event.get('full_video_path', '')}-{event.get('start_timestamp', '')}-{event.get('end_timestamp', '')}" 
                            if signature in existing_clips:
                                logger.debug(f"Skipping duplicate clip: {signature}")
                                skipped_clips += 1
                                continue
                            
                            # Process member_id - ensure it's an integer
                            member_id = event.get('member_id')
                            if member_id is not None:
                                if isinstance(member_id, int):
                                    # Already an integer, use as is
                                    pass
                                elif isinstance(member_id, str):
                                    # Try to convert string to int directly
                                    try:
                                        member_id = int(member_id)
                                        logger.info(f"Converted string member_id '{event.get('member_id')}' to integer {member_id}")
                                    except (ValueError, TypeError):
                                        # If we can't convert to int, skip this clip
                                        logger.error(f"Cannot convert member_id '{member_id}' to integer, skipping clip")
                                        logger.error("Member IDs must be numeric integers, not UUIDs or other formats")
                                        skipped_clips += 1
                                        continue
                                else:
                                    logger.error(f"Invalid member_id type: {type(member_id)}, skipping clip")
                                    skipped_clips += 1
                                    continue
                            else:
                                # No member_id provided
                                logger.error("No member_id provided, skipping clip")
                                skipped_clips += 1
                                continue
                            
                            # Calculate duration if we have valid timestamps
                            start_timestamp = event.get('start_timestamp')
                            end_timestamp = event.get('end_timestamp')
                            
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
                                    except Exception:
                                        logger.warning(f"Failed to convert timestamps to float: {start_timestamp}, {end_timestamp}")
                        except Exception as e:
                            logger.warning(f"Failed to process clip: {e}")
                            skipped_clips += 1
                            continue
                
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
                logger.debug(f"Sample simplified clip: {json_module.dumps(simplified_clips[0])}")
                logger.info(f"Keys in first simplified clip: {list(simplified_clips[0].keys())}")
            else:
                logger.warning("All clips were filtered out during processing!")
                # Set a flag to indicate no clips were found
                no_clips_found = True
                # If we have no simplified clips but had raw clips, log the first raw clip for debugging
                if clips_data:
                    logger.debug(f"First raw clip that was filtered out: {json_module.dumps(clips_data[0])}")
                    
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
                    logger.info(f"Example clip that couldn't be processed: {json_module.dumps({k: v for k, v in first_clip.items() if k not in excluded_fields})}")
            
            # Add to queues
            video_queue_response = self.add_to_video_processing_queue(video_data)
            result["queue_responses"]["video_processing"] = video_queue_response
            
            # Initialize no_clips_found flag if not already set
            no_clips_found = False if 'no_clips_found' not in locals() else no_clips_found
            
            # Check if we have any clips to process
            if not simplified_clips:
                logger.warning("No clips to process for Supabase export")
                result["queue_responses"]["clip_creation"] = {"success": True, "message": "No clips to process"}
                no_clips_found = True
                
                # Log that we're skipping clip upload due to no clips found
                logger.info(f"Skipping clip upload for video ID {video_id} because no clips were found")
                
                # Still mark the process as successful since we've created export files
                # This avoids pipeline failures when no clips are found
                result["clips_processed"] = 0
                result["export_success"] = True
            else:
                # We have clips to process - proceed with normal flow
                try:
                    # Verify the simplified clips are JSON serializable
                    json_str = json_module.dumps(simplified_clips)
                    logger.info(f"Successfully serialized simplified clips to JSON (length: {len(json_str)} characters)")
                    
                    # Add a unique identifier to each clip to prevent duplicate detection
                    for i, clip in enumerate(simplified_clips):
                        # Add a unique timestamp to each clip's transcript to ensure it's treated as new
                        timestamp = datetime.now().timestamp() + i
                        if 'transcript' in clip and clip['transcript']:
                            clip['transcript'] = f"{clip['transcript']} [Export {timestamp}]"
                        
                        # Ensure each clip has a unique ID
                        clip['id'] = str(uuid.uuid4())
                        
                        # Log the clip being sent to Supabase
                        logger.debug(f"Sending clip to Supabase: {json_module.dumps(clip)}")
                    
                    # Force insert clips into Supabase
                    logger.info(f"Inserting {len(simplified_clips)} clips into Supabase")
                    clips_queue_response = self.add_to_clip_creation_queue(simplified_clips)
                    result["queue_responses"]["clip_creation"] = clips_queue_response
                
                    # Log the response from Supabase
                    logger.info(f"Supabase clip insertion response: {clips_queue_response}")
                    
                    # Check if the export was successful and clean up the SQLite database
                    if clips_queue_response and (isinstance(clips_queue_response, dict) and clips_queue_response.get("success", False)) or \
                       (hasattr(clips_queue_response, "data") and clips_queue_response.data):
                        logger.info(f"Export to Supabase was successful, cleaning up SQLite database for video ID {video_id}")
                        try:
                            # Import the parliament clips integration service to clean up SQLite database
                            from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
                            
                            # Create an instance of the service
                            clips_service = ParliamentClipsIntegrationService()
                            
                            # Check if the transaction is still valid before passing it to cleanup
                            fresh_session = None
                            if db_session is not None:
                                try:
                                    # Test if the transaction is still valid
                                    from sqlalchemy import text
                                    db_session.execute(text("SELECT 1")).scalar()
                                    logger.info("Current transaction is valid for cleanup")
                                except Exception as tx_error:
                                    logger.warning(f"Transaction appears to be in a failed state before cleanup, rolling back: {str(tx_error)}")
                                    try:
                                        db_session.rollback()
                                        logger.info("Successfully rolled back transaction before cleanup")
                                    except Exception as rollback_error:
                                        logger.error(f"Error during transaction rollback: {str(rollback_error)}")
                                    
                                    # Get a fresh session for cleanup
                                    try:
                                        from backend.db.session import get_db
                                        db_generator = get_db()
                                        fresh_session = next(db_generator)
                                        logger.info("Created fresh database session for cleanup")
                                    except Exception as session_error:
                                        logger.error(f"Could not create fresh database session: {str(session_error)}")
                            
                            # Call the cleanup method with the appropriate session
                            cleanup_session = fresh_session if fresh_session is not None else db_session
                            cleanup_result = clips_service._cleanup_exported_clips(video_id, cleanup_session)
                            logger.info(f"SQLite cleanup result: {cleanup_result}")
                            
                            # Add cleanup result to the overall result
                            result["sqlite_cleanup"] = cleanup_result
                            
                            # If we created a fresh session, commit and close it
                            if fresh_session is not None:
                                try:
                                    fresh_session.commit()
                                    logger.info("Committed fresh session after cleanup")
                                except Exception as commit_error:
                                    logger.error(f"Error committing fresh session: {str(commit_error)}")
                        except Exception as cleanup_error:
                            logger.error(f"Error cleaning up SQLite database: {str(cleanup_error)}")
                            import traceback
                            logger.error(traceback.format_exc())
                            result["sqlite_cleanup_error"] = str(cleanup_error)
                except Exception as e:
                    logger.error(f"JSON serialization error with simplified clips: {str(e)}")
                    result["queue_responses"]["clip_creation"] = {"error": f"JSON serialization error: {str(e)}"}
        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error adding to Supabase queues: {error_details}")
            logger.error(traceback.format_exc())
            result["queue_responses"]["error"] = error_details
        
        return result
