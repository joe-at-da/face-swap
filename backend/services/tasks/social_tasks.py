import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from celery import shared_task
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.social import SocialPost, PostStatus
from backend.services.social.manager import SocialMediaManager

logger = logging.getLogger(__name__)

# Initialize social media manager
social_manager = SocialMediaManager()


def publish_social_post(
    post_id: int,
    media_paths: Optional[List[str]] = None,
    platform_specific_params: Optional[Dict[str, Any]] = None
):
    """
    Publish a social media post.
    
    Args:
        post_id: ID of the post to publish
        media_paths: Optional list of paths to media files
        platform_specific_params: Optional platform-specific parameters
    """
    logger.info(f"Publishing social post {post_id}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get post from database
        post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
        
        if not post:
            logger.error(f"Social post {post_id} not found")
            return
        
        # Check if post is in a publishable state
        if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
            logger.warning(f"Social post {post_id} is not in a publishable state: {post.status}")
            return
        
        # Publish to platform
        result = social_manager.post_content(
            text=post.content,
            platforms=[post.platform],
            media_paths=media_paths,
            platform_specific_params={post.platform: platform_specific_params} if platform_specific_params else None
        )
        
        # Get result for this platform
        platform_result = result.get(post.platform)
        
        if not platform_result:
            logger.error(f"No result returned for platform {post.platform}")
            post.status = PostStatus.FAILED
            post.error_message = "No result returned from platform"
            db.commit()
            return
        
        # Update post status based on result
        if platform_result.get("status") == "success":
            post.status = PostStatus.POSTED
            post.external_id = platform_result.get("post_id")
            post.posted_time = datetime.utcnow()
            post.error_message = None
            
            # Schedule analytics refresh
            schedule_analytics_refresh.delay(post_id, 60)  # Refresh after 1 hour
            
            logger.info(f"Successfully published social post {post_id} to {post.platform}")
        else:
            post.status = PostStatus.FAILED
            post.error_message = platform_result.get("error", "Unknown error")
            logger.error(f"Failed to publish social post {post_id}: {post.error_message}")
        
        db.commit()
        
    except Exception as e:
        logger.exception(f"Error publishing social post {post_id}: {str(e)}")
        
        try:
            # Update post status to failed
            post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
            if post:
                post.status = PostStatus.FAILED
                post.error_message = str(e)
                db.commit()
        except Exception as inner_e:
            logger.error(f"Error updating post status: {str(inner_e)}")
            
    finally:
        db.close()


@shared_task
def publish_scheduled_posts():
    """
    Publish all scheduled posts that are due.
    """
    logger.info("Checking for scheduled posts to publish")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get all scheduled posts that are due
        now = datetime.utcnow()
        due_posts = db.query(SocialPost).filter(
            SocialPost.status == PostStatus.SCHEDULED,
            SocialPost.scheduled_time <= now
        ).all()
        
        logger.info(f"Found {len(due_posts)} scheduled posts to publish")
        
        # Publish each post
        for post in due_posts:
            try:
                # Update status to indicate publishing in progress
                post.status = PostStatus.DRAFT
                db.commit()
                
                # Publish post
                publish_social_post(post.id)
                
            except Exception as e:
                logger.exception(f"Error publishing scheduled post {post.id}: {str(e)}")
                
                # Update post status to failed
                post.status = PostStatus.FAILED
                post.error_message = str(e)
                db.commit()
                
    except Exception as e:
        logger.exception(f"Error in publish_scheduled_posts: {str(e)}")
        
    finally:
        db.close()


def refresh_post_analytics(post_id: int):
    """
    Refresh analytics for a social media post.
    
    Args:
        post_id: ID of the post to refresh analytics for
    """
    logger.info(f"Refreshing analytics for social post {post_id}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get post from database
        post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
        
        if not post:
            logger.error(f"Social post {post_id} not found")
            return
        
        # Check if post is published
        if post.status != PostStatus.POSTED or not post.external_id:
            logger.warning(f"Social post {post_id} is not published, cannot refresh analytics")
            return
        
        # Get analytics from platform
        analytics = social_manager.get_analytics(post.platform, post.external_id)
        
        if analytics.get("status") != "success":
            logger.error(f"Failed to get analytics for post {post_id}: {analytics.get('error', 'Unknown error')}")
            return
        
        # In a real implementation, you would store these analytics in a database
        # For now, we'll just log them
        logger.info(f"Retrieved analytics for post {post_id}: {analytics.get('metrics', {})}")
        
        # Schedule next refresh based on post age
        post_age_hours = (datetime.utcnow() - post.posted_time).total_seconds() / 3600 if post.posted_time else 0
        
        if post_age_hours < 24:
            # For fresh posts, refresh every hour
            schedule_analytics_refresh.delay(post_id, 60)
        elif post_age_hours < 72:
            # For 1-3 day old posts, refresh every 6 hours
            schedule_analytics_refresh.delay(post_id, 360)
        elif post_age_hours < 168:
            # For 3-7 day old posts, refresh every 12 hours
            schedule_analytics_refresh.delay(post_id, 720)
        else:
            # For older posts, refresh once a day
            schedule_analytics_refresh.delay(post_id, 1440)
        
    except Exception as e:
        logger.exception(f"Error refreshing analytics for post {post_id}: {str(e)}")
        
    finally:
        db.close()


@shared_task
def schedule_analytics_refresh(post_id: int, minutes_delay: int = 60):
    """
    Schedule a refresh of analytics for a social media post.
    
    Args:
        post_id: ID of the post to refresh analytics for
        minutes_delay: Number of minutes to delay the refresh
    """
    # This task simply schedules another task to run after the specified delay
    refresh_post_analytics.apply_async(args=[post_id], countdown=minutes_delay * 60)


@shared_task
def cleanup_failed_posts(max_age_days: int = 30):
    """
    Clean up failed posts older than the specified age.
    
    Args:
        max_age_days: Maximum age in days for failed posts to keep
    """
    logger.info(f"Cleaning up failed posts older than {max_age_days} days")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=max_age_days)
        
        # Get all failed posts older than the cutoff date
        old_failed_posts = db.query(SocialPost).filter(
            SocialPost.status == PostStatus.FAILED,
            SocialPost.updated_at < cutoff_date
        ).all()
        
        logger.info(f"Found {len(old_failed_posts)} old failed posts to clean up")
        
        # Delete each post
        for post in old_failed_posts:
            db.delete(post)
        
        db.commit()
        logger.info(f"Cleaned up {len(old_failed_posts)} old failed posts")
        
    except Exception as e:
        logger.exception(f"Error in cleanup_failed_posts: {str(e)}")
        
    finally:
        db.close()
