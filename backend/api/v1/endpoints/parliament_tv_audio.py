from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing import Dict
import os
import subprocess
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
    Extract audio from Parliament TV stream and save it as a separate file.
    This endpoint is called by the frontend to trigger audio extraction.
    '''
    try:
        # Check permissions
        has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
        
        # Get the capture
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            return {'success': False, 'error': f'Capture {capture_id} not found'}
            
        # Get the audio URL directly from metadata
        metadata = capture.metadata
        if not metadata:
            return {'success': False, 'error': 'No metadata found for capture'}
            
        # Get ONLY the audio URL - Parliament TV provides separate audio streams
        audio_url = None
        if isinstance(metadata, dict) and 'audio_url' in metadata:
            audio_url = metadata['audio_url']
        elif hasattr(metadata, 'audio_url'):
            audio_url = metadata.audio_url
            
        if not audio_url:
            return {'success': False, 'error': 'No audio URL found in metadata'}
        
        # Create output file path
        output_file = f"/app/data/temp/audio_extracts/capture_{capture_id:04d}.audio.mp3"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Simple ffmpeg command to download audio
        cmd = [
            "ffmpeg", "-y",
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-i", audio_url,
            "-c:a", "libmp3lame",
            "-q:a", "2",
            output_file
        ]
        
        # Run the command
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Log the output
        with open(f"/app/data/temp/ffmpeg_log_{capture_id}.txt", 'w') as f:
            f.write(process.stderr)
        
        # Check success
        if process.returncode != 0:
            return {'success': False, 'error': 'Failed to extract audio'}
        
        # Update database
        capture.audio_file_path = output_file
        db.commit()
        
        return {'success': True, 'output_file': output_file}
        
    except Exception as e:
        logger.error(f'Error: {str(e)}')
        return {'success': False, 'error': str(e)}
