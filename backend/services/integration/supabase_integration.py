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
        self.supabase = SupabaseService()
        self.media_bucket = settings.SUPABASE_MEDIA_BUCKET or "parliament-tv-media"
        self.export_bucket = settings.SUPABASE_EXPORT_BUCKET or "parliament-tv-exports"
    
    def upload_media_to_supabase(
        self, 
        video_path: str, 
        audio_path: str,
        thumbnail_path: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload media files to Supabase storage.
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            thumbnail_path: Path to thumbnail image (optional)
            
        Returns:
            Dictionary with URLs for uploaded files
        """
        result = {}
        
        # Upload video file
        if os.path.exists(video_path):
            video_filename = os.path.basename(video_path)
            # Upload directly to root of bucket
            storage_path = video_filename
            
            try:
                self.supabase.upload_file(self.media_bucket, storage_path, video_path)
                video_url = self.supabase.get_public_url(self.media_bucket, storage_path)
                result["video_url"] = video_url
                logger.info(f"Uploaded video to Supabase: {video_url}")
            except Exception as e:
                logger.error(f"Error uploading video to Supabase: {str(e)}")
        else:
            logger.warning(f"Video file not found: {video_path}")
        
        # Upload audio file - using the separate audio URL as provided
        if os.path.exists(audio_path):
            audio_filename = os.path.basename(audio_path)
            # Upload directly to root of bucket
            storage_path = audio_filename
            
            try:
                self.supabase.upload_file(self.media_bucket, storage_path, audio_path)
                audio_url = self.supabase.get_public_url(self.media_bucket, storage_path)
                result["audio_url"] = audio_url
                logger.info(f"Uploaded audio to Supabase: {audio_url}")
            except Exception as e:
                logger.error(f"Error uploading audio to Supabase: {str(e)}")
        else:
            logger.warning(f"Audio file not found: {audio_path}")
        
        # Upload thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumbnail_filename = os.path.basename(thumbnail_path)
            # Upload directly to root of bucket
            storage_path = thumbnail_filename
            
            try:
                self.supabase.upload_file(self.media_bucket, storage_path, thumbnail_path)
                thumbnail_url = self.supabase.get_public_url(self.media_bucket, storage_path)
                result["thumbnail_url"] = thumbnail_url
                logger.info(f"Uploaded thumbnail to Supabase: {thumbnail_url}")
            except Exception as e:
                logger.error(f"Error uploading thumbnail to Supabase: {str(e)}")
        
        return result
    
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
        
        # Upload media files if requested
        if upload_media:
            # Get audio path from metadata - respecting the separate audio/video streams
            audio_path = video_metadata.get("audio_path", "")
            if not audio_path and "audio_url" in video_metadata:
                # Try to find local audio file based on metadata
                audio_url = video_metadata.get("audio_url", "")
                if audio_url:
                    audio_filename = os.path.basename(audio_url)
                    audio_path = os.path.join(os.path.dirname(video_path), audio_filename)
            
            # Get thumbnail path if available
            thumbnail_path = video_metadata.get("thumbnail_path", "")
            
            # Check if combined AV file was created and upload it directly
            combined_url = export_result.get("combined_url", "")
            if combined_url and os.path.exists(combined_url):
                logger.info(f"Uploading combined audio-video file: {combined_url}")
                try:
                    # Upload the combined file directly to the root of the bucket
                    # Use the original filename as the destination path to preserve the combined_av_XXX_TIMESTAMP.mp4 format
                    upload_result = self.supabase.upload_full_video(file_path=combined_url)
                    if upload_result.get("success"):
                        result["supabase_urls"]["combined_av_url"] = upload_result.get("public_url")
                        logger.info(f"Successfully uploaded combined AV file to Supabase: {upload_result.get('public_url')}")
                    else:
                        logger.error(f"Failed to upload combined AV file: {upload_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error uploading combined AV file: {str(e)}")
            
            # Upload media files
            media_urls = self.upload_media_to_supabase(
                video_path=video_path,
                audio_path=audio_path,
                thumbnail_path=thumbnail_path
            )
            result["supabase_urls"].update(media_urls)
        
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
