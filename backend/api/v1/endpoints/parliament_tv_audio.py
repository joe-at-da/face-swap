from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Dict
import os

from backend.api.deps import get_db
from backend.core.security import get_current_active_user, has_permission, UserRole
from backend.db import models
from backend.services.parliament_tv import ParliamentTVCapture

router = APIRouter()

# Initialize the Parliament TV capture service
parliament_tv_service = ParliamentTVCapture()

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
        
        # Check if the capture is completed
        if capture.status not in ['completed', 'active']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Capture session with ID {capture_id} is not completed or active (status: {capture.status})'
            )
        
        # Call the stop_capture method to extract audio
        result = parliament_tv_service.stop_capture(capture_id)
        
        if result.get('success', False):
            return {
                'success': True,
                'message': 'Audio extraction started successfully',
                'output_file': result.get('output_file', None)
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Unknown error during audio extraction')
            }
    except Exception as e:
        print(f'Error extracting audio: {str(e)}')
        return {
            'success': False,
            'error': f'Error extracting audio: {str(e)}'
        }
