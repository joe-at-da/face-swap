from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from backend.db.models.social import SocialPlatform, PostStatus

class SocialPostBase(BaseModel):
    """Base schema for social media posts"""
    content: str = Field(..., description="Text content of the post")
    platform: SocialPlatform = Field(..., description="Social media platform")
    video_clip_id: Optional[int] = Field(None, description="ID of the associated video clip")
    scheduled_time: Optional[datetime] = Field(None, description="When to publish the post")

class SocialPostCreate(SocialPostBase):
    """Schema for creating a new social media post"""
    media_paths: Optional[List[str]] = Field(None, description="Paths to media files to include")
    platform_specific_params: Optional[Dict[str, Any]] = Field(None, description="Platform-specific parameters")

class SocialPostUpdate(BaseModel):
    """Schema for updating an existing social media post"""
    content: Optional[str] = Field(None, description="Text content of the post")
    platform: Optional[SocialPlatform] = Field(None, description="Social media platform")
    status: Optional[PostStatus] = Field(None, description="Status of the post")
    scheduled_time: Optional[datetime] = Field(None, description="When to publish the post")
    platform_specific_params: Optional[Dict[str, Any]] = Field(None, description="Platform-specific parameters")

class SocialPostInDB(SocialPostBase):
    """Schema for a social media post as stored in the database"""
    id: int
    status: PostStatus
    external_id: Optional[str] = None
    error_message: Optional[str] = None
    posted_time: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class SocialPostResponse(SocialPostInDB):
    """Schema for returning a social media post"""
    platform_url: Optional[str] = Field(None, description="URL to the post on the platform")
    analytics: Optional[Dict[str, Any]] = Field(None, description="Analytics data for the post")

class SocialPostAnalytics(BaseModel):
    """Schema for social media post analytics"""
    post_id: int
    platform: SocialPlatform
    external_id: str
    metrics: Dict[str, Any]
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

class SocialPostBatchCreate(BaseModel):
    """Schema for creating multiple social media posts at once"""
    content: str = Field(..., description="Text content of the post")
    platforms: List[SocialPlatform] = Field(..., description="List of platforms to post to")
    video_clip_id: Optional[int] = Field(None, description="ID of the associated video clip")
    media_paths: Optional[List[str]] = Field(None, description="Paths to media files to include")
    scheduled_time: Optional[datetime] = Field(None, description="When to publish the post")
    platform_specific_params: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Platform-specific parameters")

class SocialPlatformStatus(BaseModel):
    """Schema for platform authentication status"""
    platform: SocialPlatform
    authenticated: bool
    error_message: Optional[str] = None
