from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Optional
import os
import subprocess
import logging
from pathlib import Path as FilePath

from backend.api.deps import get_db
from backend.core.security import get_current_active_user, has_permission, UserRole
from backend.db import models

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
VIDEO_DIR = FilePath("/app/data/temp/video_downloads")
VIDEO_FORMAT = "mp4"
VIDEO_QUALITY = "medium"  # Options: low, medium, high

class VideoDownloader:
    """
    Handles downloading of video from Parliament TV streams.
    Parliament TV provides separate audio and video streams.
    This class ONLY handles video streams - it never deals with audio streams.
    """
    
    @staticmethod
    def get_video_url(capture: models.CaptureSession) -> Optional[str]:
        """Get the video URL from capture metadata."""
        if not capture or not capture.metadata:
            return None
            
        metadata = capture.metadata
        
        # Check dict format
        if isinstance(metadata, dict) and 'video_url' in metadata:
            return metadata['video_url']
            
        # Check object format
        if hasattr(metadata, 'video_url'):
            return metadata.video_url
            
        return None
    
    @staticmethod
    def get_output_path(capture_id: int) -> str:
        """Generate the output file path for the video file."""
        return str(VIDEO_DIR / f"capture_{capture_id:04d}.video.{VIDEO_FORMAT}")
    
    @staticmethod
    def download_video(video_url: str, output_path: str) -> Dict:
        """
        Download video from the provided video URL.
        Returns a dict with success status and error message if applicable.
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create ffmpeg command for video download
            cmd = [
                "ffmpeg", "-y",
                "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                "-i", video_url,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",  # Quality setting (lower = better quality)
                "-an",  # No audio - we handle audio separately
                output_path
            ]
            
            # Execute command
            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                check=False
            )
            
            # Check result
            if process.returncode != 0:
                logger.error(f"Video download failed: {process.stderr}")
                return {
                    "success": False,
                    "error": f"ffmpeg error: {process.stderr.strip()}",
                    "command": ' '.join(cmd)
                }
                
            # Verify file exists and has content
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {
                    "success": False,
                    "error": "Output file is empty or does not exist",
                    "command": ' '.join(cmd)
                }
                
            return {
                "success": True,
                "output_file": output_path
            }
            
        except Exception as e:
            logger.exception(f"Error during video download: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

@router.post('/{capture_id}', response_model=Dict)
async def download_video_for_capture(
    capture_id: int = Path(..., description='ID of the capture to download video for'),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Dict:
    '''
    Download video from Parliament TV stream and save it as a file.
    
    Parliament TV provides completely separate audio and video streams.
    This endpoint ONLY handles the video stream - it never deals with audio.
    
    Returns:
        Dict: Success status and output file path or error message
    '''
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the capture
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Capture {capture_id} not found'
        )
    
    # Get the video URL
    video_url = VideoDownloader.get_video_url(capture)
    if not video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No video URL found in capture metadata'
        )
    
    # Generate output path
    output_path = VideoDownloader.get_output_path(capture_id)
    
    # Download video
    result = VideoDownloader.download_video(video_url, output_path)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    # Update database with video file path
    capture.video_file_path = output_path
    db.commit()
    
    return {
        "success": True,
        "message": "Video downloaded successfully",
        "output_file": output_path,
        "capture_id": capture_id
    }

@router.get('/{capture_id}/status', response_model=Dict)
async def get_video_download_status(
    capture_id: int = Path(..., description='ID of the capture to check video status for'),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Dict:
    '''
    Check if video has been downloaded for a capture session.
    
    Returns:
        Dict: Status information about the video download
    '''
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the capture
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Capture {capture_id} not found'
        )
    
    # Check if video file exists
    video_path = capture.video_file_path
    video_exists = video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 0
    
    # Check if video URL exists in metadata
    video_url = VideoDownloader.get_video_url(capture)
    
    return {
        "capture_id": capture_id,
        "video_downloaded": video_exists,
        "video_file_path": video_path if video_exists else None,
        "video_url_available": video_url is not None,
        "can_download": video_url is not None and not video_exists
    }
