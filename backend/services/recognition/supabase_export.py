"""
Supabase export functionality for recognition results.

This module provides functions to export recognition results to a format
that can be consumed by the Supabase integration, including creating combined
audio-video files while maintaining separate streams internally.
"""

import os
import json
import logging
import shutil
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess

from backend.core.config import settings
from backend.services.av_combiner import combine_audio_video

# Set up logging
logger = logging.getLogger(__name__)

def export_recognition_results(
    video_id: int,
    recognition_results: Dict[str, Any],
    video_path: str,
    audio_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Export recognition results for Supabase integration.
    
    This function:
    1. Creates a combined audio-video file for Supabase
    2. Exports recognition results to a JSON file
    3. Updates the metadata with export information
    
    Args:
        video_id: ID of the video
        recognition_results: Recognition results dictionary
        video_path: Path to the video file
        audio_path: Path to the audio file (optional)
        metadata: Additional metadata (optional)
        
    Returns:
        Dict with export status and paths
    """
    logger.info(f"Exporting recognition results for video ID {video_id} to Supabase format")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return {
            "success": False,
            "error": f"Video file not found: {video_path}",
            "export_path": None,
            "combined_av_path": None
        }
    
    # Create export directory if it doesn't exist
    export_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "exports", "supabase")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate export filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"recognition_export_{video_id}_{timestamp}.json"
    export_path = os.path.join(export_dir, export_filename)
    
    combined_av_filename = f"combined_av_{video_id}_{timestamp}.mp4"
    combined_av_path = os.path.join(export_dir, combined_av_filename)
    
    # Create combined audio-video file for Supabase
    # This maintains separate streams internally while providing a combined file for Supabase
    try:
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Creating combined audio-video file using separate audio: {audio_path}")
            combine_result = combine_audio_video(video_path, audio_path, combined_av_path)
            
            if not combine_result.get("success", False):
                logger.error(f"Failed to create combined audio-video file: {combine_result.get('error')}")
                # Continue with export even if combining fails
        else:
            logger.info(f"No separate audio file provided, copying video file as combined file")
            # Just copy the video file if no separate audio file is provided
            shutil.copy2(video_path, combined_av_path)
    except Exception as e:
        logger.error(f"Error creating combined audio-video file: {str(e)}")
        # Continue with export even if combining fails
    
    # Prepare export data
    export_data = {
        "video_id": video_id,
        "export_timestamp": datetime.now().isoformat(),
        "recognition_results": recognition_results,
        "metadata": metadata or {}
    }
    
    # Add combined AV file path to metadata
    if os.path.exists(combined_av_path):
        export_data["metadata"]["combined_av_path"] = combined_av_path
        export_data["metadata"]["combined_av_url"] = f"/api/v1/media/file?path={os.path.basename(combined_av_path)}"
    
    # Write export data to JSON file
    try:
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"Successfully exported recognition results to {export_path}")
    except Exception as e:
        logger.error(f"Error writing export file: {str(e)}")
        return {
            "success": False,
            "error": f"Error writing export file: {str(e)}",
            "export_path": None,
            "combined_av_path": combined_av_path if os.path.exists(combined_av_path) else None
        }
    
    return {
        "success": True,
        "export_path": export_path,
        "combined_av_path": combined_av_path if os.path.exists(combined_av_path) else None,
        "combined_av_url": f"/api/v1/media/file?path={os.path.basename(combined_av_path)}" if os.path.exists(combined_av_path) else None
    }
