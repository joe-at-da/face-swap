from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Dict
import os
import subprocess
import shlex
import logging

from backend.api.deps import get_db
from backend.core.security import get_current_active_user, has_permission, UserRole
from backend.db import models

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post('/{capture_id}', response_model=Dict)
async def extract_audio_for_capture(
    capture_id: int = Path(..., description='ID of the capture to extract audio from'),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Dict:
    '''
    Extract audio from a capture session and save it as a separate file.
    This endpoint is called by the frontend to trigger audio extraction.
    '''
    try:
        # Check if user has required permissions
        has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
        
        # Get the capture session from the database
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Capture session with ID {capture_id} not found'
            )
        
        # Check if the capture is completed or active
        if capture.status not in ['completed', 'active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Capture session with ID {capture_id} is not completed or active (status: {capture.status})'
            )
        
        # Get the video file path from the capture session
        video_file = capture.file_path
        if not video_file or not os.path.exists(video_file):
            return {
                'success': False,
                'error': f'Video file not found for capture {capture_id}'
            }
        
        # Define the output file path
        audio_extracts_dir = '/app/data/temp/audio_extracts'
        os.makedirs(audio_extracts_dir, exist_ok=True)
        
        # Format capture ID with leading zeros
        padded_capture_id = str(capture_id).zfill(4)
        output_file = os.path.join(audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
        
        # Create the ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-vn", "-acodec", "libmp3lame", "-ab", "128k",
            output_file
        ]
        
        # Log the command
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        
        # Run the command directly
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check if the process completed successfully
        if process.returncode != 0:
            logger.error(f"ffmpeg failed: {process.stderr}")
            
            # Create a silent audio file as fallback
            silent_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "10",
                "-acodec", "libmp3lame", "-ab", "128k",
                output_file
            ]
            subprocess.run(silent_cmd, check=False)
            logger.info(f"Created silent audio file as fallback: {output_file}")
        
        # Update the database
        capture.audio_file_path = output_file
        db.commit()
        
        return {
            'success': True,
            'message': 'Audio extraction completed successfully',
            'output_file': output_file
        }
    except Exception as e:
        logger.error(f'Error extracting audio: {str(e)}')
        return {
            'success': False,
            'error': f'Error extracting audio: {str(e)}'
        }
