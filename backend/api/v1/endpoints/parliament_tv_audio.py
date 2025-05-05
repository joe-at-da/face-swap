from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import subprocess
import shlex
import logging
from fastapi import APIRouter, Depends, Path, HTTPException
import json

from backend.api.deps import get_db
from backend.core.security import get_current_active_user, has_permission, UserRole
from backend.db import models
from backend.services.parliament_tv import extract_stream_url

router = APIRouter()
logger = logging.getLogger(__name__)

# Helper function to safely convert objects to JSON serializable format
def make_json_serializable(obj: Any) -> Any:
    """Convert any object to a JSON serializable format"""
    if hasattr(obj, '__dict__'):
        return {k: make_json_serializable(v) for k, v in obj.__dict__.items() 
                if not k.startswith('_')}
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)

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
        
        logger.info(f"Starting audio extraction for capture {capture_id}")
        
        # Get the capture session from the database
        capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
        if not capture:
            logger.error(f"Capture session {capture_id} not found")
            return {
                'success': False,
                'error': f'Capture session {capture_id} not found'
            }
        
        # Check if the capture is in a valid state
        if capture.status not in ['completed', 'active', 'stopped']:
            logger.error(f"Capture session {capture_id} is not in a valid state for audio extraction: {capture.status}")
            return {
                'success': False,
                'error': f'Capture session {capture_id} is not in a valid state for audio extraction: {capture.status}'
            }
        
        # Format the capture ID with leading zeros
        padded_capture_id = str(capture_id).zfill(4)
        
        # Define the output audio file path
        audio_dir = os.path.join('/app/data/temp', "audio_extracts")
        os.makedirs(audio_dir, exist_ok=True)
        output_file = os.path.join(audio_dir, f"capture_{padded_capture_id}.audio.mp3")
        
        # Get the source URL and metadata from the capture
        source_url = capture.source_url
        metadata = capture.metadata
        
        logger.info(f"Source URL: {source_url}")
        
        # Handle metadata serialization safely
        try:
            metadata_str = 'None'
            if metadata:
                # Convert metadata to a serializable format
                if hasattr(metadata, '__dict__'):
                    metadata_dict = metadata.__dict__
                    metadata_str = str(metadata_dict)
                else:
                    metadata_str = str(metadata)
            logger.info(f"Metadata: {metadata_str}")
        except Exception as e:
            logger.warning(f"Could not serialize metadata: {str(e)}")
            logger.info(f"Metadata: [non-serializable object]")

        
        # Determine the input URL for audio extraction
        input_url = None
        
        # First, check if we have a dedicated audio URL in metadata
        if metadata and isinstance(metadata, dict) and 'audio_url' in metadata:
            audio_url = metadata.get('audio_url')
            if audio_url and isinstance(audio_url, str):
                logger.info(f"Using dedicated audio URL from metadata: {audio_url}")
                input_url = audio_url
            else:
                logger.warning(f"Invalid audio URL in metadata: {audio_url}")
        
        # If no valid audio URL in metadata, try to extract from source URL
        if not input_url and source_url:
            logger.info(f"No valid audio URL in metadata, extracting from source URL: {source_url}")
            try:
                # Extract stream info to get fresh audio URL
                stream_info = extract_stream_url(source_url)
                
                # Handle stream_info serialization safely
                try:
                    stream_info_str = 'None'
                    if stream_info:
                        # Convert stream_info to a serializable format
                        if hasattr(stream_info, '__dict__'):
                            stream_info_dict = stream_info.__dict__
                            stream_info_str = str(stream_info_dict)
                        else:
                            stream_info_str = str(stream_info)
                    logger.info(f"Stream info: {stream_info_str}")
                except Exception as e:
                    logger.warning(f"Could not serialize stream_info: {str(e)}")
                    logger.info(f"Stream info: [non-serializable object]")

                
                if stream_info and isinstance(stream_info, dict) and 'audio_url' in stream_info:
                    audio_url = stream_info.get('audio_url')
                    if audio_url and isinstance(audio_url, str):
                        logger.info(f"Using audio URL from stream info: {audio_url}")
                        input_url = audio_url
                    else:
                        logger.warning(f"Invalid audio URL in stream info: {audio_url}")
                else:
                    logger.warning(f"No audio URL found in stream info: {stream_info}")
            except Exception as e:
                logger.error(f"Error extracting stream URL: {str(e)}")
                return {
                    'success': False,
                    'error': f'Error extracting stream URL: {str(e)}'
                }
        
        if not input_url:
            logger.error("No valid input URL found for audio extraction")
            return {
                'success': False,
                'error': 'No valid input URL found for audio extraction'
            }
            
        logger.info(f"Final input URL for audio extraction: {input_url}")
        
        # Create a Python list for the ffmpeg command
        # This avoids any shell parsing issues with special characters in URLs
        cmd = [
            "ffmpeg", "-y",
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-http_persistent", "0",
            "-allowed_extensions", "ALL",
            "-i", input_url,
            "-vn",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            output_file
        ]
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        
        # Run the command with subprocess.run and shell=False
        # This ensures no shell parsing of special characters in URLs
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                shell=False  # CRITICAL: Avoid shell parsing issues with URLs
            )
            
            # Log the command output
            logger.info(f"Command stdout: {process.stdout}")
            logger.info(f"Command stderr: {process.stderr}")
            
            # Check if the command was successful
            if process.returncode != 0:
                logger.error(f"Audio extraction failed with return code {process.returncode}")
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
            logger.error(f"Error executing ffmpeg command: {str(e)}")
            return {
                'success': False,
                'error': f'Error executing ffmpeg command: {str(e)}'
            }
    except Exception as e:
        logger.error(f'Error extracting audio: {str(e)}')
        return {
            'success': False,
            'error': f'Error extracting audio: {str(e)}'
        }
