from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, Enum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.db.base_model import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MP = "MP"
    STAFF = "STAFF"

class ClipStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    PUBLISHED = "published"
    FAILED = "failed"

class SocialPlatform(str, enum.Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"

class PostStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.STAFF)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    clips = relationship("VideoClip", back_populates="owner", cascade="all, delete-orphan")

class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    source_url = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)  # in seconds
    status = Column(Enum(ClipStatus, name="clip_status_enum"), nullable=False, default=ClipStatus.DRAFT)
    s3_key = Column(String)
    transcription = Column(String)
    faces_detected = Column(JSON)  # List of detected faces with confidence scores
    clip_metadata = Column(JSON, default={})
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="clips")
    social_posts = relationship("SocialPost", back_populates="clip", cascade="all, delete-orphan")

class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("video_clips.id"), nullable=False)
    platform = Column(Enum(SocialPlatform, name="social_platform_enum"), nullable=False)
    status = Column(Enum(PostStatus, name="post_status_enum"), nullable=False, default=PostStatus.PENDING)
    post_id = Column(String)  # ID from the social media platform
    posted_at = Column(DateTime)
    post_url = Column(String)  # URL of the post
    engagement_metrics = Column(JSON, default={})  # likes, shares, comments, etc.
    post_metadata = Column(JSON, default={})
    
    # Relationships
    clip = relationship("VideoClip", back_populates="social_posts")
