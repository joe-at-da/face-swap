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
        
        # Get real storage stats from DockerMetrics
        try:
            # Import here to avoid circular imports
            from backend.services.system.docker_metrics import DockerMetrics
            
            # Get disk usage information
            disk_usage = DockerMetrics.get_disk_usage()
            
            # Extract disk stats
            disk_stats = disk_usage.get("disk_stats", {})
            
            # Get formatted values
            storage_used = disk_stats.get("used", "0 GB")
            storage_total = disk_stats.get("size", "0 GB")
            
            # Log the values we're using
            print(f"Dashboard using real disk stats: Used: {storage_used}, Total: {storage_total}")
        except Exception as disk_error:
            print(f"Dashboard disk metrics failed: {str(disk_error)}. Using zeros.")
            storage_used = "0 GB"
            storage_total = "0 GB"
        
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
