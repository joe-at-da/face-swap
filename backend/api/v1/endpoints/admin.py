from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel, Field
import logging

from backend.api import deps
from backend.db.models.user import User, UserRole
from backend.schemas.auth import UserCreate, UserUpdate, User as UserResponse
from backend.schemas.admin import SystemStats
from backend.core.security import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get system statistics for the admin dashboard.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Import here to avoid circular imports
        from backend.services.system.docker_metrics import DockerMetrics
        from backend.db.models import VideoClip
        from backend.db.models.enums import ClipStatus
        from backend.db.models.social import SocialPost, PostStatus
        import os
        import shutil
        
        # Get user stats
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.is_active == False).scalar() or 0
        
        # Get clip stats
        total_clips = db.query(func.count(VideoClip.id)).scalar() or 0
        processing_clips = db.query(func.count(VideoClip.id)).filter(VideoClip.status == ClipStatus.PROCESSING).scalar() or 0
        completed_clips = db.query(func.count(VideoClip.id)).filter(VideoClip.status == ClipStatus.READY).scalar() or 0
        failed_clips = db.query(func.count(VideoClip.id)).filter(VideoClip.status == ClipStatus.FAILED).scalar() or 0
        
        # Get capture session stats
        # Try to get real capture session data from the database
        # Import here to avoid circular imports
        from backend.db.models.capture import CaptureSession
        from backend.db.models.enums import SessionStatus
        
        total_captures = db.query(func.count(CaptureSession.id)).scalar() or 0
        active_captures = db.query(func.count(CaptureSession.id)).filter(
            CaptureSession.status == SessionStatus.ACTIVE
        ).scalar() or 0
        completed_captures = db.query(func.count(CaptureSession.id)).filter(
            CaptureSession.status == SessionStatus.COMPLETED
        ).scalar() or 0
        failed_captures = db.query(func.count(CaptureSession.id)).filter(
            CaptureSession.status == SessionStatus.ERROR
        ).scalar() or 0
        
        # Get social stats
        total_posts = db.query(func.count(SocialPost.id)).scalar() or 0
        
        # Handle the database enum mismatch by using raw string values
        # instead of enum values to avoid type mismatches
        try:
            # Use raw SQL with text() to query for scheduled posts
            scheduled_posts_result = db.execute(
                text("SELECT COUNT(*) FROM social_posts WHERE status = 'scheduled' OR status = 'SCHEDULED'")
            ).scalar()
            scheduled_posts = scheduled_posts_result or 0
            logger.info(f"Found {scheduled_posts} scheduled posts")
        except Exception as e:
            logger.error(f"Error querying scheduled posts: {str(e)}")
            scheduled_posts = 0
            
        try:
            # Use raw SQL with text() to query for published/posted posts
            published_posts_result = db.execute(
                text("SELECT COUNT(*) FROM social_posts WHERE status = 'published' OR status = 'posted' OR status = 'PUBLISHED' OR status = 'POSTED'")
            ).scalar()
            published_posts = published_posts_result or 0
            logger.info(f"Found {published_posts} published posts")
        except Exception as e:
            logger.error(f"Error querying published posts: {str(e)}")
            published_posts = 0
        
        # Get disk info using our improved method
        try:
            # Use the improved get_disk_usage method that matches Docker Desktop
            disk_usage = DockerMetrics.get_disk_usage()
            
            # Extract disk stats from the disk_usage response
            disk_stats = disk_usage.get("disk_stats", {})
            
            # Use the disk_stats values which include total_bytes, used_bytes, and free_bytes
            disk_info = {
                "total_bytes": disk_stats.get("total_bytes", 0),
                "used_bytes": disk_stats.get("used_bytes", 0),
                "free_bytes": disk_stats.get("free_bytes", 0)
            }
            
            # Print the disk_info for debugging
            print(f"DEBUG: disk_info: {disk_info}")
            print(f"Dashboard using disk stats: Total: {disk_info['total_bytes'] / (1024**3):.2f} GB, Used: {disk_info['used_bytes'] / (1024**3):.2f} GB")
        except Exception as docker_error:
            print(f"Dashboard disk metrics failed: {str(docker_error)}. Using fallback method.")
            # Fallback to direct disk usage if Docker fails
            try:
                total, used, free = shutil.disk_usage("/")
                disk_info = {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free
                }
            except Exception as disk_error:
                print(f"Dashboard disk usage fallback failed: {str(disk_error)}. Using Docker Desktop values.")
                # If all else fails, use zero values
                disk_info = {
                    "total_bytes": 0,
                    "used_bytes": 0,
                    "free_bytes": 0
                }
        
        return {
            "storage": {
                "total": disk_info.get("total_bytes", 0),
                "used": disk_info.get("used_bytes", 0),
                "available": disk_info.get("free_bytes", 0)
            },
            "clips": {
                "total": total_clips,
                "processing": processing_clips,
                "completed": completed_clips,
                "failed": failed_clips
            },
            "captures": {
                "total": total_captures,
                "active": active_captures,
                "completed": completed_captures,
                "failed": failed_captures
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users
            },
            "social": {
                "total_posts": total_posts,
                "scheduled_posts": scheduled_posts,
                "published_posts": published_posts
            }
        }
    except Exception as e:
        import traceback
        print(f"Error in get_system_stats: {str(e)}")
        print(traceback.format_exc())
        
        # Return default values instead of throwing an error
        return {
            "storage": {
                "total": 0,
                "used": 0,
                "available": 0
            },
            "clips": {
                "total": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            },
            "captures": {
                "total": 0,
                "active": 0,
                "completed": 0,
                "failed": 0
            },
            "users": {
                "total": 0,
                "active": 0,
                "inactive": 0
            },
            "social": {
                "total_posts": 0,
                "scheduled_posts": 0,
                "published_posts": 0
            }
        }


class StorageSettings(BaseModel):
    max_file_size: int
    allowed_extensions: list[str]
    auto_delete_days: int
    storage_path: str


class StorageCategory(BaseModel):
    clips: int
    captures: int
    thumbnails: int
    transcriptions: int
    other: int

class StorageBreakdown(BaseModel):
    video_clips_bytes: int
    capture_sessions_bytes: int
    thumbnails_bytes: int
    transcriptions_bytes: int
    other_bytes: int

class OldestFiles(BaseModel):
    video_clips: List[Dict[str, Any]]
    capture_sessions: List[Dict[str, Any]]
    thumbnails: List[Dict[str, Any]]
    transcriptions: List[Dict[str, Any]]

class StorageStats(BaseModel):
    total_space: int = Field(alias="total")
    used_space: int = Field(alias="used")
    free_space: int = Field(alias="available")
    file_count: int
    average_file_size: int

class DetailedStorageStats(BaseModel):
    total: int
    used: int
    available: int
    usage_percent: float
    file_count: int
    average_file_size: int
    categories: StorageCategory
    breakdown: StorageBreakdown
    oldest_files: OldestFiles

@router.get("/storage/stats", response_model=DetailedStorageStats)
async def get_storage_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get detailed storage statistics.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Import here to avoid circular imports
        from backend.services.system.docker_metrics import DockerMetrics
        from backend.db.models import VideoClip
        from backend.db.models.enums import ClipStatus
        import shutil
        import os
        from datetime import datetime, timedelta
        
        # Get file count from database
        file_count = db.query(func.count(VideoClip.id)).scalar() or 0
        
        # Get disk info with fallback mechanisms
        disk_info = {}
        disk_usage = {}
        
        try:
            # Get disk usage from our improved method
            disk_usage = DockerMetrics.get_disk_usage()
            
            # Extract disk stats from the disk_usage response
            disk_stats = disk_usage.get("disk_stats", {})
            
            # Use the disk_stats values which include total_bytes, used_bytes, and free_bytes
            disk_info = {
                "total_bytes": disk_stats.get("total_bytes", 0),
                "used_bytes": disk_stats.get("used_bytes", 0),
                "free_bytes": disk_stats.get("free_bytes", 0)
            }
            
            # Log the values we're using
            print(f"Using disk stats: Total: {disk_info['total_bytes'] / (1024**3):.2f} GB, Used: {disk_info['used_bytes'] / (1024**3):.2f} GB, Free: {disk_info['free_bytes'] / (1024**3):.2f} GB")
            print(f"Raw disk_stats from DockerMetrics: {disk_stats}")
            
        except Exception as docker_error:
            print(f"Docker metrics failed: {str(docker_error)}. Using fallback method.")
            # Fallback to direct disk usage if Docker fails
            try:
                total, used, free = shutil.disk_usage("/")
                disk_info = {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free
                }
                disk_usage = {
                    "total_volume_bytes": used,  # Estimate total volume bytes as used space
                    "volumes": {}
                }
            except Exception as disk_error:
                print(f"Disk usage fallback failed: {str(disk_error)}. Using default values.")
                disk_info = {
                    "total_bytes": 0,
                    "used_bytes": 0,
                    "free_bytes": 0
                }
                disk_usage = {
                    "total_volume_bytes": 0,
                    "volumes": {}
                }
        
        # Calculate average file size if there are files
        average_file_size = 0
        if file_count > 0:
            total_volume_bytes = disk_usage.get("total_volume_bytes", 0)
            average_file_size = total_volume_bytes // file_count if file_count > 0 else 0
        
        # Get storage breakdown by category
        try:
            # Get storage breakdown from Docker volumes
            storage_breakdown = DockerMetrics.get_storage_breakdown()
        except Exception as breakdown_error:
            print(f"Storage breakdown failed: {str(breakdown_error)}. Using estimates.")
            # Estimate storage breakdown based on file count and average size
            total_used = disk_info.get("used_bytes", 0)
            
            # Get clip counts by type
            video_clips_count = db.query(func.count(VideoClip.id)).filter(VideoClip.status == ClipStatus.READY).scalar() or 0
            processing_clips_count = db.query(func.count(VideoClip.id)).filter(VideoClip.status == ClipStatus.PROCESSING).scalar() or 0
            
            # Estimate sizes based on counts and total used space
            if file_count > 0:
                video_ratio = video_clips_count / file_count if file_count > 0 else 0.6
                capture_ratio = processing_clips_count / file_count if file_count > 0 else 0.1
                thumbnail_ratio = 0.05  # Thumbnails typically small
                transcription_ratio = 0.05  # Transcriptions typically small
                other_ratio = 1 - (video_ratio + capture_ratio + thumbnail_ratio + transcription_ratio)
                
                storage_breakdown = {
                    "video_clips_bytes": int(total_used * video_ratio),
                    "capture_sessions_bytes": int(total_used * capture_ratio),
                    "thumbnails_bytes": int(total_used * thumbnail_ratio),
                    "transcriptions_bytes": int(total_used * transcription_ratio),
                    "other_bytes": int(total_used * other_ratio)
                }
            else:
                # Default breakdown if no files
                storage_breakdown = {
                    "video_clips_bytes": 0,
                    "capture_sessions_bytes": 0,
                    "thumbnails_bytes": 0,
                    "transcriptions_bytes": 0,
                    "other_bytes": 0
                }
        
        # Get oldest files by category
        try:
            # Try to get oldest files from Docker volumes
            oldest_files = DockerMetrics.get_oldest_files(limit=5)
            
            # If we have database records, merge them with filesystem data
            try:
                oldest_video_clips = db.query(VideoClip).order_by(VideoClip.created_at).limit(5).all()
                oldest_video_clips_data = [
                    {
                        "id": clip.id,
                        "name": clip.title or f"Clip {clip.id}",
                        "created_at": clip.created_at.isoformat() if clip.created_at else None,
                        "size_bytes": clip.file_size or 0
                    } for clip in oldest_video_clips
                ]
                
                # If we have database records, use them instead of filesystem data for video clips
                if oldest_video_clips_data:
                    oldest_files["video_clips"] = oldest_video_clips_data
            except Exception as db_error:
                print(f"Getting oldest files from database failed: {str(db_error)}. Using filesystem data.")
        except Exception as oldest_error:
            print(f"Getting oldest files failed: {str(oldest_error)}. Using empty lists.")
            # Default empty structure
            oldest_files = {
                "video_clips": [],
                "capture_sessions": [],
                "thumbnails": [],
                "transcriptions": []
            }
            
            # Try to get at least the database records
            try:
                oldest_video_clips = db.query(VideoClip).order_by(VideoClip.created_at).limit(5).all()
                oldest_files["video_clips"] = [
                    {
                        "id": clip.id,
                        "name": clip.title or f"Clip {clip.id}",
                        "created_at": clip.created_at.isoformat() if clip.created_at else None,
                        "size_bytes": clip.file_size or 0
                    } for clip in oldest_video_clips
                ]
            except Exception:
                pass
        
        # Calculate usage percentage
        total_bytes = disk_info.get("total_bytes", 1)  # Avoid division by zero
        used_bytes = disk_info.get("used_bytes", 0)
        usage_percent = round((used_bytes / total_bytes) * 100, 2) if total_bytes > 0 else 0
        
        # Map storage breakdown to the format expected by the frontend
        categories = {
            "clips": storage_breakdown.get("video_clips_bytes", 0),
            "captures": storage_breakdown.get("capture_sessions_bytes", 0),
            "thumbnails": storage_breakdown.get("thumbnails_bytes", 0),
            "transcriptions": storage_breakdown.get("transcriptions_bytes", 0),
            "other": storage_breakdown.get("other_bytes", 0)
        }
        
        # Check if we have valid data, otherwise return error indicators
        if disk_info.get("total_bytes", 0) == 0:
            return {
                "total": 0,
                "used": 0,
                "available": 0,
                "usage_percent": 0,
                "file_count": 0,
                "average_file_size": 0,
                "categories": categories,
                "oldest_files": oldest_files,
                "error": "Unable to retrieve storage metrics. Docker may not be available."
            }
        else:
            return {
                "total": disk_info.get("total_bytes", 0),
                "used": disk_info.get("used_bytes", 0),
                "available": disk_info.get("free_bytes", 0),
                "usage_percent": usage_percent,
                "file_count": file_count,
                "average_file_size": average_file_size,
                "categories": categories,
                "breakdown": storage_breakdown,  # Keep original for backward compatibility
                "oldest_files": oldest_files
            }
    except Exception as e:
        import traceback
        # Log the error with traceback
        print(f"Error getting storage stats: {str(e)}")
        print(traceback.format_exc())
        
        # Calculate default usage percentage
        total_bytes = 0
        used_bytes = 0
        usage_percent = 0.0
        
        # Return default values in case of error in the format expected by the frontend
        return {
            "total": total_bytes,
            "used": used_bytes,
            "available": total_bytes - used_bytes,
            "usage_percent": usage_percent,
            "file_count": file_count if 'file_count' in locals() else 0,
            "average_file_size": 0,
            "categories": {
                "clips": 0,
                "captures": 0,
                "thumbnails": 0,
                "transcriptions": 0,
                "other": 0
            },
            "breakdown": {
                "video_clips_bytes": 0,
                "capture_sessions_bytes": 0,
                "thumbnails_bytes": 0,
                "transcriptions_bytes": 0,
                "other_bytes": 0
            },
            "oldest_files": {
                "video_clips": [],
                "capture_sessions": [],
                "thumbnails": [],
                "transcriptions": []
            }
        }


@router.get("/storage/settings", response_model=StorageSettings)
async def get_storage_settings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get storage settings.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    try:
        # Import here to avoid circular imports
        from backend.services.system.docker_metrics import DockerMetrics
        import os
        from backend.core.config import settings
        
        # Get Docker volume info
        disk_usage = DockerMetrics.get_disk_usage()
        volumes = disk_usage.get("volumes", {})
        
        # Find the media storage path
        storage_path = getattr(settings, "MEDIA_STORAGE_PATH", "/data/videos")
        
        # Get allowed extensions from settings or use defaults
        allowed_extensions = getattr(settings, "ALLOWED_VIDEO_EXTENSIONS", ["mp4", "mov", "avi", "mkv"])
        
        # Get max file size from settings or use default (5GB)
        max_file_size = getattr(settings, "MAX_FILE_SIZE", 5000000000)
        
        # Get auto-delete days from settings or use default (30 days)
        auto_delete_days = getattr(settings, "AUTO_DELETE_DAYS", 30)
        
        return {
            "max_file_size": max_file_size,
            "allowed_extensions": allowed_extensions,
            "auto_delete_days": auto_delete_days,
            "storage_path": storage_path
        }
    except Exception as e:
        # Log the error
        print(f"Error getting storage settings: {str(e)}")
        
        # Return default values in case of error
        return {
            "max_file_size": 5000000000,  # 5 GB
            "allowed_extensions": ["mp4", "mov", "avi", "mkv"],
            "auto_delete_days": 30,
            "storage_path": "/data/videos"
        }


@router.put("/storage/settings", response_model=StorageSettings)
async def update_storage_settings(
    settings: StorageSettings,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update storage settings.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # In a real implementation, we would update the settings in the database
    # For now, just return the settings that were sent
    return settings


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Retrieve all users with optional filtering.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    query = db.query(User)
    
    # Apply filters if provided
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            User.email.ilike(search_term) | 
            User.full_name.ilike(search_term)
        )
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/users", response_model=UserResponse)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Create new user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Check if user with this email already exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get a specific user by id.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update a user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update user fields
    update_data = user_in.dict(exclude_unset=True)
    
    # If password is being updated, hash it
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"]
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Delete a user.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Prevent deleting self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    db.delete(user)
    db.commit()
    return user


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update a user's active status.
    Only accessible to admin users.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Prevent deactivating self
    if user_id == current_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
