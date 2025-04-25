from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError

from backend.core.security import get_current_active_user
from backend.db.session import get_db
from backend.db.models.user import User as UserModel
from backend.db.models.video import VideoClip
from backend.db.models.social import SocialPost

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
        
        # Count pending captures (if applicable)
        # This is a placeholder - implement based on your actual data model
        pending_captures = 0
        
        # Count scheduled social media posts
        scheduled_posts = db.query(SocialPost).filter(SocialPost.scheduled_at > datetime.utcnow()).count()
        
        # Get storage stats (placeholder values - implement based on your actual storage system)
        # In a real implementation, you might query your storage system or database
        storage_used = "2.4 GB"
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
