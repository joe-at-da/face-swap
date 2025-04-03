from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from backend.db.base import Base

class SocialPlatform(str, enum.Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"

class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"

class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(Enum(SocialPlatform), nullable=False)
    content = Column(String, nullable=False)
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT)
    scheduled_time = Column(DateTime, nullable=True)
    posted_time = Column(DateTime, nullable=True)
    external_id = Column(String, nullable=True)  # ID from the social media platform
    error_message = Column(String, nullable=True)
    
    # Foreign keys
    video_clip_id = Column(Integer, ForeignKey("video_clips.id"))
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    video_clip = relationship("VideoClip", back_populates="social_posts")
    created_by = relationship("User", back_populates="social_posts")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
