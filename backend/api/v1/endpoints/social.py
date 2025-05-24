import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, Request

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sqlalchemy.sql import desc

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
    try:
        # Start with a base query
        query = db.query(SocialPost)
        
        # Apply platform filter if provided
        if platform:
            query = query.filter(SocialPost.platform == platform)
        
        # Apply status filter if provided
        if status:
            query = query.filter(SocialPost.status == status)
        
        # Apply timeframe filter if provided
        if timeframe:
            days = 30  # Default to 30 days
            if timeframe == "7days":
                days = 7
            elif timeframe == "30days":
                days = 30
            elif timeframe == "90days":
                days = 90
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(SocialPost.created_at >= cutoff_date)
        
        # Get total count for pagination metadata
        total = query.count()
        
        # Apply pagination
        query = query.order_by(SocialPost.created_at.desc()).offset(skip).limit(limit)
        
        # Execute query and get results
        db_posts = query.all()
        
        # Convert to response models
        posts = []
        for post in db_posts:
            # Create a dictionary with all the fields from the database model
            post_dict = {
                "id": post.id,
                "content": post.content,
                "platform": post.platform,
                "status": post.status,
                "scheduled_time": post.scheduled_time,
                "posted_time": post.posted_time,
                "external_id": post.external_id,
                "error_message": post.error_message,
                "video_clip_id": post.video_clip_id,
                "created_by_id": post.created_by_id,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "platform_url": getattr(post, 'platform_url', None),
                "analytics": getattr(post, 'analytics', None)
            }
            
            # Convert to SocialPostResponse
            posts.append(SocialPostResponse(**post_dict))
        
        # Add pagination headers if request has state attribute
        if hasattr(request, 'state'):
            request.state.pagination = {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": total > (skip + limit)
            }
        
        return posts
    
    except Exception as e:
        # Log the error
        print(f"Error listing social posts: {str(e)}")
        
        # If there's an error, return an empty list
        # In a production environment, you might want to raise an HTTPException instead
        return []


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
    # Parse timeframe parameter if provided
    if timeframe:
        if timeframe == "7days":
            days = 7
        elif timeframe == "30days":
            days = 30
        elif timeframe == "90days":
            days = 90
    
    # Set date range for queries
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        # Base query for social posts within the date range
        base_query = db.query(SocialPost).filter(SocialPost.created_at >= start_date)
        
        # Apply platform filter if provided
        if platform:
            base_query = base_query.filter(SocialPost.platform == platform)
        
        # Get total posts count
        total_posts = base_query.count()
        
        # Get counts by platform
        platform_counts = {}
        for p in SocialPlatform:
            try:
                count = base_query.filter(SocialPost.platform == p).count()
                if count > 0:
                    platform_counts[p.value] = count
            except Exception as e:
                print(f"Error counting platform {p}: {str(e)}")
                # Skip this platform if there's an error
        
        # Get counts by status
        status_counts = {}
        for s in PostStatus:
            count = base_query.filter(SocialPost.status == s).count()
            if count > 0:
                status_counts[s.value] = count
        
        # Generate daily post counts for the last 7 days (or less if days < 7)
        days_to_show = min(days, 7)
        daily_posts = []
        for i in range(days_to_show):
            day = end_date - timedelta(days=i)
            day_start = datetime(day.year, day.month, day.day, 0, 0, 0)
            day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
            
            count = db.query(SocialPost).filter(
                SocialPost.created_at >= day_start,
                SocialPost.created_at <= day_end
            ).count()
            
            daily_posts.append({
                "date": day.strftime("%Y-%m-%d"),
                "count": count
            })
        
        # Get engagement metrics if available (this assumes there's an analytics field or related table)
        # For now, we'll return zeros since we don't have real engagement data
        engagement = {
            "total_likes": 0,
            "total_shares": 0,
            "total_comments": 0,
            "average_engagement_rate": 0
        }
        
        # Get top users by post count
        top_users_query = db.query(
            SocialPost.created_by_id,
            func.count(SocialPost.id).label('post_count')
        ).filter(
            SocialPost.created_at >= start_date
        ).group_by(
            SocialPost.created_by_id
        ).order_by(
            desc('post_count')
        ).limit(5)
        
        top_users = []
        for user_id, post_count in top_users_query:
            top_users.append({
                "user_id": user_id,
                "post_count": post_count
            })
        
        # Compile all statistics
        stats = {
            "total_posts": total_posts,
            "platforms": platform_counts,
            "status": status_counts,
            "daily_posts": daily_posts,
            "engagement": engagement,
            "top_users": top_users,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            }
        }
        
        return stats
    
    except Exception as e:
        # Log the error
        print(f"Error getting social stats: {str(e)}")
        
        # Return empty stats in case of error
        return {
            "total_posts": 0,
            "platforms": {},
            "status": {},
            "daily_posts": [],
            "engagement": {
                "total_likes": 0,
                "total_shares": 0,
                "total_comments": 0,
                "average_engagement_rate": 0
            },
            "top_users": [],
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            }
        }
