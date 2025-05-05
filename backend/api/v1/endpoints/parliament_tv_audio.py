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
        
        # Get the metadata from the capture
        metadata = capture.metadata
        
        # Handle metadata serialization safely
        try:
            metadata_str = 'None'
            if metadata:
                # Convert metadata to a serializable format
                serializable_metadata = make_json_serializable(metadata)
                metadata_str = str(serializable_metadata)
            logger.info(f"Metadata: {metadata_str}")
        except Exception as e:
            logger.warning(f"Could not serialize metadata: {str(e)}")
            logger.info(f"Metadata: [non-serializable object]")
        
        # Get the video file path from the capture
        video_file_path = capture.file_path
        if not video_file_path:
            # Try to extract the stream URL from the metadata
            try:
                if metadata and hasattr(metadata, 'stream_url'):
                    input_url = metadata.stream_url
                    logger.info(f"Using stream URL from metadata: {input_url}")
                elif metadata and hasattr(metadata, 'url'):
                    # Extract the stream URL from the Parliament TV URL
                    original_url = metadata.url
                    logger.info(f"Extracting stream URL from original URL: {original_url}")
                    
                    # Extract the stream URL
                    stream_info = extract_stream_url(original_url)
                    
                    # Handle stream_info serialization safely
                    try:
                        stream_info_str = 'None'
                        if stream_info:
                            # Convert stream_info to a serializable format
                            serializable_stream_info = make_json_serializable(stream_info)
                            stream_info_str = str(serializable_stream_info)
                        logger.info(f"Stream info: {stream_info_str}")
                    except Exception as e:
                        logger.warning(f"Could not serialize stream_info: {str(e)}")
                        logger.info(f"Stream info: [non-serializable object]")
                    
                    # Get the audio URL from the stream info
                    if stream_info and hasattr(stream_info, 'audio_url'):
                        input_url = stream_info.audio_url
                        logger.info(f"Using audio URL from stream info: {input_url}")
                    elif stream_info and hasattr(stream_info, 'video_url'):
                        input_url = stream_info.video_url
                        logger.info(f"Using video URL from stream info: {input_url}")
                    else:
                        return {
                            'success': False,
                            'error': "Could not extract stream URL from metadata"
                        }
                else:
                    return {
                        'success': False,
                        'error': "No video file path or stream URL available"
                    }
            except Exception as e:
                logger.error(f"Error extracting stream URL: {str(e)}")
                return {
                    'success': False,
                    'error': f"Error extracting stream URL: {str(e)}"
                }
        else:
            # Use the video file path as the input URL
            input_url = video_file_path
            logger.info(f"Using video file path: {input_url}")
        
        # Create the output file path
        output_file = f"/app/data/temp/audio_extracts/capture_{capture_id:04d}.audio.mp3"
        logger.info(f"Output file: {output_file}")
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Create a Python list for the ffmpeg command with all arguments as strings
        # This completely avoids any shell parsing issues
        cmd = [
            "ffmpeg",
            "-y",
            "-protocol_whitelist",
            "file,http,https,tcp,tls,crypto",
            "-http_persistent",
            "0",
            "-allowed_extensions",
            "ALL",
            "-i",
            str(input_url),  # Explicitly convert to string
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_file)  # Explicitly convert to string
        ]
        
        # Log the command for debugging without joining (to avoid any string formatting issues)
        logger.info(f"Running ffmpeg command with arguments: {cmd}")
        
        try:
            # Use subprocess.run with shell=False to avoid shell parsing issues
            process = subprocess.run(
                cmd,  # Use the list directly
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                shell=False  # CRITICAL: Avoid shell parsing issues
            )
            
            # Log the command output
            logger.info(f"Command stdout: {process.stdout}")
            logger.info(f"Command stderr: {process.stderr}")
            
            # Check if the command was successful
            if process.returncode != 0:
                error_message = process.stderr if process.stderr else "Unknown error"
                logger.error(f"Audio extraction failed with return code {process.returncode}: {error_message}")
                return {
                    'success': False,
                    'error': f'Audio extraction failed: {error_message}'
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
