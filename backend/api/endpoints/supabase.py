"""
Supabase Integration API Endpoints

These endpoints enable integration with Supabase, including:
- Exporting recognition and transcription data to Supabase
- Checking the status of Supabase integration
- Handling webhook notifications from Supabase
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Security, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.api.deps import get_db, get_api_key
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.recognition.recognition_service import RecognitionService
from backend.services.media.video_service import VideoService
from backend.db.models import CaptureSession, ParliamentTranscription

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=Dict[str, Any])
async def get_supabase_status(
    api_key: str = Security(get_api_key),
    db: Session = Depends(get_db)
):
    """
    Check the status of Supabase integration.
    
    Returns:
        Status information about Supabase integration
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        return {
            "status": "disabled",
            "message": "Supabase integration is not enabled"
        }
    
    try:
        # Initialize Supabase service
        supabase = SupabaseIntegration()
        
        # Check connection to Supabase
        client = supabase.supabase.client
        
        # Attempt a simple operation to verify connection
        response = client.table("health_check").select("*").limit(1).execute()
        
        return {
            "status": "connected",
            "message": "Supabase integration is active and connected",
            "supabase_url": settings.SUPABASE_URL,
            "buckets": {
                "media": settings.SUPABASE_MEDIA_BUCKET,
                "export": settings.SUPABASE_EXPORT_BUCKET
            }
        }
    except Exception as e:
        logger.error(f"Error connecting to Supabase: {str(e)}")
        return {
            "status": "error",
            "message": f"Error connecting to Supabase: {str(e)}",
            "supabase_url": settings.SUPABASE_URL
        }


@router.post("/export/{video_id}", response_model=Dict[str, Any])
async def export_to_supabase(
    video_id: int,
    background_tasks: BackgroundTasks,
    upload_media: bool = False,
    api_key: str = Security(get_api_key),
    db: Session = Depends(get_db)
):
    """
    Export video recognition and transcription data to Supabase.
    
    Args:
        video_id: ID of the video to export
        upload_media: Whether to upload media files to Supabase
        
    Returns:
        Status of the export operation
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase integration is not enabled"
        )
    
    # Get video data
    video = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID {video_id} not found"
        )
    
    # Check if recognition data exists
    recognition_service = RecognitionService(db)
    recognition_data = recognition_service.get_recognition_results(video_id)
    if not recognition_data:
        return {
            "status": "error",
            "message": f"No recognition data found for video ID {video_id}"
        }
    
    # Check if transcription data exists
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    # Get video metadata
    video_service = VideoService(db)
    video_metadata = video_service.get_video_metadata(video_id)
    
    # Ensure we have separate audio and video URLs as per user preference
    if not video_metadata.get("audio_url"):
        return {
            "status": "error",
            "message": "Missing audio URL in video metadata. Audio and video streams must be handled separately."
        }
    
    # Add export to background task to avoid blocking the API
    def export_task():
        try:
            supabase = SupabaseIntegration()
            result = supabase.export_and_upload_recognition(
                video_path=video.file_path,
                recognition_results=recognition_data,
                video_metadata=video_metadata,
                db_session=db,
                video_id=video_id,
                upload_media=upload_media
            )
            
            logger.info(f"Successfully exported video {video_id} to Supabase")
            return result
        except Exception as e:
            logger.error(f"Error exporting to Supabase: {str(e)}")
            return {"error": str(e)}
    
    # Add task to background
    background_tasks.add_task(export_task)
    
    return {
        "status": "processing",
        "message": f"Exporting video {video_id} to Supabase in the background",
        "video_id": video_id,
        "has_recognition": recognition_data is not None,
        "has_transcription": transcription is not None,
        "upload_media": upload_media
    }


@router.post("/webhooks/video-processed", response_model=Dict[str, Any])
async def video_processed_webhook(
    request: Request,
    api_key: str = Security(get_api_key),
    db: Session = Depends(get_db)
):
    """
    Handle webhook notification when a video is processed in Supabase.
    
    Returns:
        Status of the webhook processing
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase integration is not enabled"
        )
    
    # Verify webhook signature if configured
    if settings.SUPABASE_WEBHOOK_SECRET:
        # Implementation of signature verification would go here
        pass
    
    # Parse webhook payload
    try:
        payload = await request.json()
        logger.info(f"Received video processed webhook: {payload}")
        
        # Process webhook data
        video_id = payload.get("video_id")
        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing video_id in webhook payload"
            )
        
        # Update local database with Supabase processing status
        video = db.query(CaptureSession).filter(CaptureSession.external_id == video_id).first()
        if video:
            video.external_status = payload.get("status", "processed")
            video.external_url = payload.get("url", "")
            db.commit()
            
            return {
                "status": "success",
                "message": f"Updated status for video {video_id}",
                "video_id": video_id
            }
        else:
            return {
                "status": "warning",
                "message": f"Video with external ID {video_id} not found in local database",
                "video_id": video_id
            }
    except Exception as e:
        logger.error(f"Error processing video webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.post("/webhooks/clip-created", response_model=Dict[str, Any])
async def clip_created_webhook(
    request: Request,
    api_key: str = Security(get_api_key),
    db: Session = Depends(get_db)
):
    """
    Handle webhook notification when a clip is created in Supabase.
    
    Returns:
        Status of the webhook processing
    """
    if not settings.SUPABASE_INTEGRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase integration is not enabled"
        )
    
    # Verify webhook signature if configured
    if settings.SUPABASE_WEBHOOK_SECRET:
        # Implementation of signature verification would go here
        pass
    
    # Parse webhook payload
    try:
        payload = await request.json()
        logger.info(f"Received clip created webhook: {payload}")
        
        # Process webhook data
        clip_id = payload.get("clip_id")
        video_id = payload.get("video_id")
        
        if not clip_id or not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing clip_id or video_id in webhook payload"
            )
        
        # Update local database with clip information
        # This would typically update a clips table or similar
        
        return {
            "status": "success",
            "message": f"Processed clip creation webhook for clip {clip_id}",
            "clip_id": clip_id,
            "video_id": video_id
        }
    except Exception as e:
        logger.error(f"Error processing clip webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
