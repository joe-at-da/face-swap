import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.db.models.user import UserRole
from backend.api import deps
from backend.db.models.social import SocialPost, SocialPlatform, PostStatus
from backend.schemas.social import (
    SocialPostCreate, 
    SocialPostUpdate, 
    SocialPostResponse, 
    SocialPostBatchCreate,
    SocialPlatformStatus
)
from backend.services.social.manager import SocialMediaManager
from backend.services.tasks.social_tasks import (
    publish_social_post,
    refresh_post_analytics
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize social media manager
social_manager = SocialMediaManager()


@router.post("/posts/", response_model=SocialPostResponse, status_code=201)
async def create_social_post(
    post_data: SocialPostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Create a new social media post.
    
    If scheduled_time is provided, the post will be scheduled for that time.
    Otherwise, it will be posted immediately.
    """
    # Create database record
    db_post = SocialPost(
        content=post_data.content,
        platform=post_data.platform,
        video_clip_id=post_data.video_clip_id,
        scheduled_time=post_data.scheduled_time,
        status=PostStatus.SCHEDULED if post_data.scheduled_time else PostStatus.DRAFT,
        created_by_id=current_user.id
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    # If no scheduled time, publish immediately in the background
    if not post_data.scheduled_time:
        background_tasks.add_task(
            publish_social_post,
            post_id=db_post.id,
            media_paths=post_data.media_paths,
            platform_specific_params=post_data.platform_specific_params
        )
    
    return db_post


@router.post("/posts/batch/", response_model=List[SocialPostResponse], status_code=201)
async def create_batch_social_posts(
    batch_data: SocialPostBatchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Create multiple social media posts across different platforms at once.
    """
    created_posts = []
    
    for platform in batch_data.platforms:
        # Create database record for each platform
        db_post = SocialPost(
            content=batch_data.content,
            platform=platform,
            video_clip_id=batch_data.video_clip_id,
            scheduled_time=batch_data.scheduled_time,
            status=PostStatus.SCHEDULED if batch_data.scheduled_time else PostStatus.DRAFT,
            created_by_id=current_user.id
        )
        
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        created_posts.append(db_post)
        
        # If no scheduled time, publish immediately in the background
        if not batch_data.scheduled_time:
            # Get platform-specific params if any
            platform_params = None
            if batch_data.platform_specific_params:
                platform_params = batch_data.platform_specific_params.get(platform, None)
            
            background_tasks.add_task(
                publish_social_post,
                post_id=db_post.id,
                media_paths=batch_data.media_paths,
                platform_specific_params=platform_params
            )
    
    return created_posts


@router.get("/posts/", response_model=List[SocialPostResponse])
async def list_social_posts(
    request: Request,
    platform: Optional[SocialPlatform] = None,
    status: Optional[PostStatus] = None,
    timeframe: Optional[str] = Query(None, description="Time frame for posts (e.g., '7days', '30days')"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_optional)
):
    """
    List social media posts with optional filtering by platform and status.
    """
    query = db.query(SocialPost)
    
    # Apply filters if provided
    if platform:
        query = query.filter(SocialPost.platform == platform)
        
    if status:
        query = query.filter(SocialPost.status == status)
        
    # Apply timeframe filter if provided
    if timeframe:
        days = 30  # Default
        if timeframe == "7days":
            days = 7
        elif timeframe == "30days":
            days = 30
        elif timeframe == "90days":
            days = 90
        # Add more timeframe options as needed
        
        # Filter by created_at date
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(SocialPost.created_at >= start_date)
    
    # Filter by user unless admin
    if current_user.role != UserRole.ADMIN:
        query = query.filter(SocialPost.created_by_id == current_user.id)
    
    # Order by creation time, newest first
    query = query.order_by(SocialPost.created_at.desc())
    
    # Apply pagination
    posts = query.offset(skip).limit(limit).all()
    
    return posts


@router.get("/posts/{post_id}", response_model=SocialPostResponse)
async def get_social_post(
    post_id: int = Path(..., description="ID of the social post to retrieve"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Get details of a specific social media post.
    """
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Social post not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and post.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this post")
    
    # If the post has been published, get the latest status from the platform
    if post.status == PostStatus.POSTED and post.external_id:
        try:
            platform_status = social_manager.get_post_status(post.platform, post.external_id)
            
            # Add platform URL if available
            if "url" in platform_status:
                post.platform_url = platform_status["url"]
                
        except Exception as e:
            logger.error(f"Error getting platform status for post {post_id}: {str(e)}")
    
    return post


@router.put("/posts/{post_id}", response_model=SocialPostResponse)
async def update_social_post(
    post_data: SocialPostUpdate,
    post_id: int = Path(..., description="ID of the social post to update"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Update a social media post.
    
    Only draft or scheduled posts can be updated.
    """
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Social post not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and post.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # Only allow updates to draft or scheduled posts
    if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Cannot update posts that have already been published")
    
    # Update fields if provided
    if post_data.content is not None:
        post.content = post_data.content
    
    if post_data.platform is not None:
        post.platform = post_data.platform
    
    if post_data.status is not None:
        post.status = post_data.status
    
    if post_data.scheduled_time is not None:
        post.scheduled_time = post_data.scheduled_time
        
        # If setting a scheduled time, update status
        if post_data.scheduled_time > datetime.utcnow():
            post.status = PostStatus.SCHEDULED
    
    db.commit()
    db.refresh(post)
    
    return post


@router.delete("/posts/{post_id}", status_code=204)
async def delete_social_post(
    post_id: int = Path(..., description="ID of the social post to delete"),
    delete_from_platform: bool = Query(False, description="Whether to also delete the post from the platform"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Delete a social media post.
    
    If delete_from_platform is True and the post has been published,
    it will also be deleted from the social media platform.
    """
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Social post not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and post.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    # If requested and the post has been published, delete from platform
    if delete_from_platform and post.status == PostStatus.POSTED and post.external_id:
        try:
            success = social_manager.delete_post(post.platform, post.external_id)
            if not success:
                logger.warning(f"Failed to delete post {post_id} from {post.platform}")
        except Exception as e:
            logger.error(f"Error deleting post {post_id} from {post.platform}: {str(e)}")
    
    # Delete from database
    db.delete(post)
    db.commit()
    
    return None


@router.post("/posts/{post_id}/publish", response_model=SocialPostResponse)
async def publish_post(
    post_id: int = Path(..., description="ID of the social post to publish"),
    media_paths: Optional[List[str]] = None,
    platform_specific_params: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Publish a draft social media post immediately.
    """
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Social post not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and post.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this post")
    
    # Only allow publishing of draft posts
    if post.status != PostStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft posts can be published")
    
    # Update status to indicate publishing in progress
    post.status = PostStatus.SCHEDULED
    db.commit()
    
    # Publish in background
    background_tasks.add_task(
        publish_social_post,
        post_id=post.id,
        media_paths=media_paths,
        platform_specific_params=platform_specific_params
    )
    
    return post


@router.get("/posts/{post_id}/analytics", response_model=Dict[str, Any])
async def get_post_analytics(
    post_id: int = Path(..., description="ID of the social post to get analytics for"),
    refresh: bool = Query(False, description="Whether to refresh analytics from the platform"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Get analytics for a published social media post.
    """
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Social post not found")
    
    # Check permissions
    if current_user.role != UserRole.ADMIN and post.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access analytics for this post")
    
    # Only allow analytics for published posts
    if post.status != PostStatus.POSTED or not post.external_id:
        raise HTTPException(status_code=400, detail="Analytics are only available for published posts")
    
    # If refresh requested, get latest analytics in background
    if refresh:
        background_tasks.add_task(
            refresh_post_analytics,
            post_id=post.id
        )
        
        return {"status": "refreshing", "message": "Analytics refresh has been scheduled"}
    
    # Get analytics from platform
    try:
        analytics = social_manager.get_analytics(post.platform, post.external_id)
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


@router.get("/platforms/status", response_model=List[SocialPlatformStatus])
async def get_platform_status(
    current_user = Depends(deps.get_current_user_with_roles([UserRole.ADMIN, UserRole.MP, UserRole.STAFF]))
):
    """
    Get authentication status for all configured social media platforms.
    """
    status = social_manager.get_platform_status()
    
    result = []
    for platform, authenticated in status.items():
        result.append(SocialPlatformStatus(
            platform=platform,
            authenticated=authenticated,
            error_message=None if authenticated else "Authentication failed"
        ))
    
    return result


@router.get("/stats", response_model=Dict[str, Any])
async def get_social_stats(
    request: Request,
    days: int = Query(30, description="Number of days to include in the statistics"),
    platform: Optional[SocialPlatform] = Query(None, description="Filter by platform"),
    timeframe: Optional[str] = Query(None, description="Time frame for stats (e.g., '7days', '30days')"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user_optional)
):
    """
    Get statistics about social media posts.
    
    Returns aggregated data about posts by platform, status, and time period.
    """
    # Calculate the date range based on timeframe parameter if provided
    end_date = datetime.utcnow()
    
    # Parse timeframe parameter if provided
    if timeframe:
        if timeframe == "7days":
            days = 7
        elif timeframe == "30days":
            days = 30
        elif timeframe == "90days":
            days = 90
        # Add more timeframe options as needed
    
    start_date = end_date - timedelta(days=days)
    
    # Base query for posts within the date range
    query = db.query(SocialPost).filter(SocialPost.created_at >= start_date)
    
    # Apply platform filter if provided
    if platform:
        query = query.filter(SocialPost.platform == platform)
    
    # Get all posts within the date range
    posts = query.all()
    
    # Count posts by platform
    platform_counts = Counter([post.platform for post in posts])
    
    # Count posts by status
    status_counts = Counter([post.status for post in posts])
    
    # Count posts by day (last 7 days)
    last_week = end_date - timedelta(days=7)
    daily_posts = []
    for i in range(7):
        day = end_date - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        day_count = sum(1 for post in posts if day_start <= post.created_at < day_end)
        daily_posts.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": day_count
        })
    
    # Get engagement metrics if available
    engagement = {
        "total_likes": 0,
        "total_shares": 0,
        "total_comments": 0,
        "average_engagement_rate": 0
    }
    
    # Count posts by user
    user_posts = {}
    for post in posts:
        user_id = post.created_by_id
        if user_id in user_posts:
            user_posts[user_id] += 1
        else:
            user_posts[user_id] = 1
    
    # Compile all statistics
    stats = {
        "total_posts": len(posts),
        "platforms": {
            platform.value: count for platform, count in platform_counts.items()
        },
        "status": {
            status.value: count for status, count in status_counts.items()
        },
        "daily_posts": daily_posts,
        "engagement": engagement,
        "top_users": [
            {"user_id": user_id, "post_count": count} 
            for user_id, count in sorted(user_posts.items(), key=lambda x: x[1], reverse=True)[:5]
        ],
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        }
    }
    
    return stats
