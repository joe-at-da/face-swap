from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

from backend.core.security import get_current_active_user
from backend.db.session import get_db
from backend.db.models.user import User as UserModel
from backend.db.models import VideoClip
from backend.db.models.social import SocialPost
from backend.db.models.enums import ClipStatus

router = APIRouter()

@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get dashboard statistics for the current user
    """
    try:
        # Count total clips
        total_clips = db.query(VideoClip).count()
        
        # Count recent clips (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_clips = db.query(VideoClip).filter(VideoClip.created_at >= seven_days_ago).count()
        
        # Count pending captures (videos in processing state)
        pending_captures = db.query(VideoClip).filter(VideoClip.status == ClipStatus.PROCESSING).count()
        
        # Count scheduled social media posts
        scheduled_posts = db.query(SocialPost).filter(SocialPost.scheduled_time > datetime.utcnow()).count()
        
        # Calculate storage stats based on video clips
        # Sum up the size of all video clips (assuming each minute of video is roughly 10MB)
        total_duration = db.query(func.sum(VideoClip.duration)).scalar() or 0
        storage_used_mb = (total_duration / 60) * 10  # Convert seconds to minutes, then to MB
        
        # Format storage values
        if storage_used_mb > 1024:
            storage_used = f"{storage_used_mb / 1024:.1f} GB"
        else:
            storage_used = f"{storage_used_mb:.1f} MB"
            
        # Set a reasonable storage limit
        storage_total = "100 GB"
        
        return {
            "totalClips": total_clips,
            "recentClips": recent_clips,
            "pendingCaptures": pending_captures,
            "scheduledPosts": scheduled_posts,
            "storageUsed": storage_used,
            "storageTotal": storage_total
        }
    except SQLAlchemyError as e:
        # Log the error (in a real app, use a proper logger)
        print(f"Database error in dashboard stats: {str(e)}")
        # Return default values in case of database errors
        return {
            "totalClips": 0,
            "recentClips": 0,
            "pendingCaptures": 0,
            "scheduledPosts": 0,
            "storageUsed": "0 GB",
            "storageTotal": "100 GB"
        }
    except Exception as e:
        # Log the error (in a real app, use a proper logger)
        print(f"Unexpected error in dashboard stats: {str(e)}")
        # Return default values in case of any other errors
        return {
            "totalClips": 0,
            "recentClips": 0,
            "pendingCaptures": 0,
            "scheduledPosts": 0,
            "storageUsed": "0 GB",
            "storageTotal": "100 GB"
        }
