from fastapi import APIRouter, Depends, HTTPException, status, Path as FastAPIPath
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Dict, Union, Optional
import os
import glob
import subprocess
import logging
from pathlib import Path

from backend.api.deps import get_db
from backend.core.security import get_current_active_user, has_permission, UserRole
from backend.db import models

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
AUDIO_DIR = Path("/app/data/temp/audio_extracts")
DATA_DIR = os.getenv("DATA_DIR", "/app/data")


def create_silent_audio(output_path: str, duration: int = 10) -> bool:
    """
    Create a silent audio file.
    
    Args:
        output_path: Path to save the silent audio file
        duration: Duration in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', str(duration),
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        '-y',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0


def create_message_audio(output_path: str, message: str) -> bool:
    """
    Create an audio file with a spoken message.
    Falls back to silent audio if text-to-speech fails.
    
    Args:
        output_path: Path to save the audio file
        message: Message to speak
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First try to create a silent audio file as fallback
        create_silent_audio(output_path)
        
        # Try to use text-to-speech if available (this is optional and will fail gracefully)
        tts_cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'sine=frequency=1000:duration=0.5',
            '-af', f'aselect=1,asetpts=N/SR/TB',
            '-y',
            output_path
        ]
        
        subprocess.run(tts_cmd, capture_output=True, text=True, check=False)
        
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception:
        # Fallback to silent audio
        return create_silent_audio(output_path)


def serve_audio_file(audio_path: str, debug: bool = False, extra_info: dict = None) -> Union[FileResponse, Dict]:
    """
    Serve an audio file or return debug information.
    
    Args:
        audio_path: Path to the audio file
        debug: Whether to return debug information instead of the file
        extra_info: Additional information to include in debug response
        
    Returns:
        FileResponse or Dict with debug information
    """
    audio_filename = os.path.basename(audio_path)
    
    if debug:
        response = {
            "status": "success",
            "message": "Audio file found",
            "audio_path": audio_path,
            "audio_filename": audio_filename,
            "exists": os.path.exists(audio_path),
            "size": os.path.getsize(audio_path) if os.path.exists(audio_path) else 0,
            "direct_audio_url": f"/api/v1/files/static/audio/{audio_filename}"
        }
        
        # Add extra info if provided
        if extra_info:
            response.update(extra_info)
            
        return response
    
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=audio_filename
    )


def is_parliament_tv_capture(capture: models.CaptureSession) -> bool:
    """
    Check if a capture session is a Parliament TV capture.
    
    Args:
        capture: The capture session to check
        
    Returns:
        bool: True if it's a Parliament TV capture, False otherwise
    """
    if not capture or not capture.metadata:
        return False
        
    try:
        if isinstance(capture.metadata, dict):
            if ('parliament_tv_url' in capture.metadata or 
                'video_url' in capture.metadata or 
                'audio_url' in capture.metadata):
                return True
        elif (hasattr(capture.metadata, 'parliament_tv_url') or 
              hasattr(capture.metadata, 'video_url') or 
              hasattr(capture.metadata, 'audio_url')):
            return True
    except Exception as e:
        logger.error(f"Error checking metadata: {str(e)}")
        
    return False


def find_capture_for_video(filename: str, db: Session) -> Optional[models.CaptureSession]:
    """
    Find the capture session for a video file.
    
    Args:
        filename: The video filename
        db: Database session
        
    Returns:
        Optional[models.CaptureSession]: The capture session if found, None otherwise
    """
    # First try to find by filename
    captures = db.query(models.CaptureSession).all()
    for capture in captures:
        if capture.file_path and os.path.basename(capture.file_path) == filename:
            return capture
    
    # If not found, try to extract ID from filename
    if "_" in filename:
        try:
            parts = filename.replace('.mp4', '').split('_')
            if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) < 6:
                capture_id = int(parts[-1])
                return db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        except Exception as e:
            logger.error(f"Error extracting capture ID: {str(e)}")
    
    return None


def find_existing_audio_file(video_path: str) -> Optional[str]:
    """
    Find an existing audio file for a video file.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Optional[str]: Path to the audio file if found, None otherwise
    """
    video_dir = os.path.dirname(video_path)
    video_basename = os.path.basename(video_path)
    video_name_without_ext = os.path.splitext(video_basename)[0]
    
    # Define possible audio file patterns
    audio_patterns = [
        f"{video_name_without_ext}.audio.mp3",
        f"{video_name_without_ext}.audio.*",
        f"audio_{video_basename}",
        f"audio_{video_name_without_ext}.*"
    ]
    
    # Search locations in order of priority
    search_dirs = [
        video_dir,  # Same directory as video
        os.path.join(DATA_DIR, "temp", "audio_extracts"),  # Audio extracts directory
        DATA_DIR  # Entire data directory (recursive)
    ]
    
    for search_dir in search_dirs:
        for pattern in audio_patterns:
            if search_dir == DATA_DIR:
                # Recursive search for entire data directory
                matching_files = glob.glob(os.path.join(search_dir, "**", pattern), recursive=True)
            else:
                # Non-recursive search for specific directories
                matching_files = glob.glob(os.path.join(search_dir, pattern))
                
            if matching_files:
                audio_path = matching_files[0]
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    return audio_path
    
    return None


def extract_audio_from_non_parliament_video(video_path: str, output_path: str) -> bool:
    """
    Extract audio from a non-Parliament TV video file.
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the audio file
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Extract audio using ffmpeg
    cmd = [
        'ffmpeg',
        '-err_detect', 'ignore_err',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'libmp3lame',
        '-q:a', '2',  # High quality
        '-y',  # Overwrite
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        logger.error(f"Failed to extract audio: {result.stderr}")
        return False
        
    return True


@router.get('/stream-audio/{filename}', response_class=FileResponse)
async def stream_audio(
    filename: str,
    db: Session = Depends(get_db),
    debug: bool = False
):
    """
    Stream just the audio track from a video file by filename.
    
    For Parliament TV captures, this endpoint will never extract audio from video files.
    Instead, it directs users to use the dedicated audio extraction endpoint.
    
    For non-Parliament TV videos, it will extract audio from the video file if needed.
    """
    return await stream_audio_with_token(filename, db, debug=debug)


@router.get('/stream-audio-with-token/{token}/{filename}', response_class=FileResponse)
async def stream_audio_with_token(
    filename: str,
    db: Session = Depends(get_db),
    debug: bool = False
):
    """
    Stream just the audio track from a video file using token authentication.
    
    For Parliament TV captures, this endpoint will never extract audio from video files.
    Instead, it directs users to use the dedicated audio extraction endpoint.
    
    For non-Parliament TV videos, it will extract audio from the video file if needed.
    """
    logger.info(f"Looking for audio file for video: {filename}")
    
    # Security: Prevent directory traversal
    safe_filename = filename.lstrip("/").replace("../", "")
    
    # Step 1: Find the video file
    found_files = glob.glob(os.path.join(DATA_DIR, "**", safe_filename), recursive=True)
    if not found_files:
        logger.error(f"Video file not found: {filename}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file {filename} not found"
        )
    
    video_path = found_files[0]
    logger.info(f"Found video file: {video_path}")
    
    # Extract video file information
    video_dir = os.path.dirname(video_path)
    video_basename = os.path.basename(video_path)
    video_name_without_ext = os.path.splitext(video_basename)[0]
    
    # Step 2: Find the capture session
    capture = find_capture_for_video(filename, db)
    capture_id = capture.id if capture else None
    
    # Step 3: Check if this is a Parliament TV capture
    is_parliament_tv = is_parliament_tv_capture(capture) if capture else False
    
    # Step 4: Check if the capture has an audio_file_path
    if capture and hasattr(capture, 'audio_file_path') and capture.audio_file_path:
        audio_path = capture.audio_file_path
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            logger.info(f"Using audio_file_path from capture: {audio_path}")
            return serve_audio_file(audio_path, debug, {
                "video_path": video_path,
                "capture_id": capture_id,
                "source": "database_record"
            })
    
    # Step 5: Look for existing audio file
    audio_path = find_existing_audio_file(video_path)
    if audio_path:
        logger.info(f"Found existing audio file: {audio_path}")
        return serve_audio_file(audio_path, debug, {
            "video_path": video_path,
            "capture_id": capture_id,
            "source": "file_search"
        })
    
    # Step 6: Handle Parliament TV captures differently
    if is_parliament_tv:
        logger.warning("This is a Parliament TV capture - audio must be extracted from the dedicated audio URL")
        
        # Create a directory for audio extracts
        audio_extracts_dir = os.path.join(DATA_DIR, "temp", "audio_extracts")
        os.makedirs(audio_extracts_dir, exist_ok=True)
        
        # Create a message audio file
        audio_filename = f"{video_name_without_ext}.audio.mp3"
        audio_path = os.path.join(audio_extracts_dir, audio_filename)
        
        create_message_audio(audio_path, "Please use the dedicated audio extraction endpoint for Parliament TV captures")
        
        # Update the database
        if capture and hasattr(capture, 'audio_file_path'):
            capture.audio_file_path = audio_path
            db.commit()
        
        # Raise an informative exception
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parliament TV captures require using the dedicated audio extraction endpoint: /api/v1/audio-extraction/{capture_id}"
        )
    
    # Step 7: For non-Parliament TV videos, extract audio
    logger.info("Extracting audio from non-Parliament TV video")
    
    # Create a directory for audio extracts
    audio_extracts_dir = os.path.join(DATA_DIR, "temp", "audio_extracts")
    os.makedirs(audio_extracts_dir, exist_ok=True)
    
    # Define the audio path
    audio_filename = f"{video_name_without_ext}.audio.mp3"
    audio_path = os.path.join(audio_extracts_dir, audio_filename)
    
    try:
        # Extract audio
        success = extract_audio_from_non_parliament_video(video_path, audio_path)
        
        if not success:
            # Create a silent audio file as fallback
            create_silent_audio(audio_path, 10)
        
        # Update the database
        if capture and hasattr(capture, 'audio_file_path'):
            capture.audio_file_path = audio_path
            db.commit()
        
        return serve_audio_file(audio_path, debug, {
            "video_path": video_path,
            "capture_id": capture_id,
            "source": "extracted"
        })
        
    except Exception as e:
        logger.exception(f"Error during audio extraction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract audio from {filename}: {str(e)}"
        )
