"""
Supabase Integration Module

This module provides functionality to directly integrate with Supabase,
including uploading files to storage, adding data to the database,
and sending jobs to queues.
"""

import os
import logging
from typing import Dict, List, Any, Optional
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
                clips_data = json.load(f)
            
            # Update URLs with Supabase URLs if available
            if "video_url" in result["supabase_urls"]:
                video_data["video_url"] = result["supabase_urls"]["video_url"]
            if "audio_url" in result["supabase_urls"]:
                video_data["audio_url"] = result["supabase_urls"]["audio_url"]
            if "thumbnail_url" in result["supabase_urls"]:
                video_data["thumbnail_url"] = result["supabase_urls"]["thumbnail_url"]
            
            # Add to queues
            video_queue_response = self.add_to_video_processing_queue(video_data)
            result["queue_responses"]["video_processing"] = video_queue_response
            
            clips_queue_response = self.add_to_clip_creation_queue(clips_data)
            result["queue_responses"]["clip_creation"] = clips_queue_response
        except Exception as e:
            logger.error(f"Error adding to Supabase queues: {str(e)}")
            result["queue_responses"]["error"] = str(e)
        
        return result
