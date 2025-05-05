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
        
        # Check if we have source URL and metadata with audio URL
        source_url = capture.source_url
        audio_url = None
        
        if capture.metadata and isinstance(capture.metadata, dict):
            audio_url = capture.metadata.get('audio_url')
        
        if not source_url and not audio_url:
            return {
                'success': False,
                'error': 'No source URL or audio URL available for this capture'
            }
            
        # Define the output file path
        audio_extracts_dir = '/app/data/temp/audio_extracts'
        os.makedirs(audio_extracts_dir, exist_ok=True)
        
        # Format capture ID with leading zeros
        padded_capture_id = str(capture_id).zfill(4)
        output_file = os.path.join(audio_extracts_dir, f"capture_{padded_capture_id}.audio.mp3")
        
        # If we have a direct audio URL, use it
        if audio_url:
            logger.info(f"Using audio URL from metadata: {audio_url}")
            input_url = audio_url
        else:
            # If no audio URL in metadata, try to extract from source URL
            logger.info(f"Extracting audio URL from source URL: {source_url}")
            
            # Import the extract_stream_url function from the service module
            from backend.services.parliament_tv import parliament_tv_capture
            
            try:
                # Extract stream info to get audio URL
                stream_info = parliament_tv_capture.extract_stream_url(source_url)
                fresh_audio_url = stream_info.get("audio_url")
                
                if fresh_audio_url and isinstance(fresh_audio_url, str):
                    logger.info(f"Found audio URL: {fresh_audio_url}")
                    input_url = fresh_audio_url
                else:
                    # If no audio URL found, use the video URL
                    video_url = stream_info.get("video_url")
                    if video_url and isinstance(video_url, str):
                        logger.info(f"No audio URL found, using video URL: {video_url}")
                        input_url = video_url
                    else:
                        # If no video URL found, use the source URL
                        logger.info(f"No video URL found, using source URL: {source_url}")
                        input_url = source_url
            except Exception as e:
                logger.error(f"Error extracting stream URL: {str(e)}")
                return {
                    'success': False,
                    'error': f'Error extracting stream URL: {str(e)}'
                }
        
        # Use ffmpeg directly with the HLS stream
        # For HLS streams, we need to use ffmpeg with special options
        logger.info(f"Processing HLS audio stream: {input_url}")
        
        try:
            # Define the temporary directory
            temp_dir = '/app/data/temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a command that properly handles HLS streams
            cmd = [
                "ffmpeg", "-y",
                "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                "-http_persistent", "0",  # Disable persistent connections
                "-allowed_extensions", "ALL",
                "-i", input_url,
                "-vn",  # No video
                "-c:a", "libmp3lame",
                "-q:a", "2",
                output_file
            ]
            
            logger.info(f"Using direct ffmpeg command for HLS stream to: {output_file}")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # We'll use a direct approach without shell=True to avoid shell parsing issues
            
            logger.info(f"Converting downloaded audio to MP3: {output_file}")
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            return {
                'success': False,
                'error': f'Error downloading audio: {str(e)}'
            }
        
        # Log the command
        logger.info(f"Running ffmpeg command to extract audio directly from URL")
        
        # Run the command
        # Explicitly set shell=False to avoid shell parsing issues with URLs containing special characters
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            shell=False  # Explicitly set shell=False to avoid syntax errors with special characters
        )
        
        # Check if the command was successful
        if process.returncode != 0:
            logger.error(f"Audio extraction failed: {process.stderr}")
            return {
                'success': False,
                'error': f'Audio extraction failed: {process.stderr}'
            }
            
        # Audio extraction completed successfully
        logger.info(f"Audio extraction completed successfully: {output_file}")
        
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
