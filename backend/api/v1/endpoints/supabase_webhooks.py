"""
Supabase webhook handlers for integration with external systems.
"""

import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Security, HTTPException, Body, Request, status
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_api_key
from backend.db.models import CaptureSession, ParliamentTranscription
from backend.api.v1.endpoints.recognition import run_recognition_process

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process-video", dependencies=[Security(get_api_key)])
async def process_video_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook handler for processing a video from Supabase.
    
    This endpoint:
    1. Receives a webhook from Supabase when a new video is ready for processing
    2. Extracts the video ID and other metadata from the webhook payload
    3. Triggers the combined recognition process (facial recognition + transcription)
    
    Returns:
        Dict with processing status
    """
    try:
        # Parse the webhook payload
        payload = await request.json()
        logger.info(f"Received Supabase webhook: {payload}")
        
        # Extract video ID from payload
        video_id = payload.get("video_id")
        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing video_id in webhook payload"
            )
        
        # Check if video exists
        video = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found"
            )
        
        # Start the recognition process in the background
        save_output = payload.get("save_output", True)
        user_id = payload.get("user_id")
        
        # Run the recognition process
        process_result = await run_recognition_process(video_id, save_output, db, user_id)
        
        return {
            "success": True,
            "message": "Recognition process started",
            "process_id": process_result.get("process_id"),
            "video_id": video_id,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Error processing Supabase webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )

@router.post("/transcription-status", dependencies=[Security(get_api_key)])
async def transcription_status_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook handler for receiving transcription status updates from Supabase.
    
    This endpoint:
    1. Receives a webhook from Supabase with transcription status updates
    2. Updates the local transcription status accordingly
    
    Returns:
        Dict with status update result
    """
    try:
        # Parse the webhook payload
        payload = await request.json()
        logger.info(f"Received Supabase transcription status webhook: {payload}")
        
        # Extract data from payload
        video_id = payload.get("video_id")
        status = payload.get("status")
        
        if not video_id or not status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing video_id or status in webhook payload"
            )
        
        # Update transcription status
        transcription = db.query(ParliamentTranscription).filter(
            ParliamentTranscription.capture_session_id == video_id
        ).order_by(ParliamentTranscription.created_at.desc()).first()
        
        if not transcription:
            # Create a new transcription record if one doesn't exist
            transcription = ParliamentTranscription(
                capture_session_id=video_id,
                status=status,
                metadata=json.dumps(payload)
            )
            db.add(transcription)
        else:
            # Update existing transcription record
            transcription.status = status
            transcription.metadata = json.dumps(payload)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Transcription status updated to {status}",
            "video_id": video_id
        }
    except Exception as e:
        logger.error(f"Error processing transcription status webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
