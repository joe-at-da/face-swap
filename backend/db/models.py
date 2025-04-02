from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    clips = relationship("VideoClip", back_populates="owner")

class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    source_url = Column(String)
    start_time = Column(DateTime)
    duration = Column(Integer)  # in seconds
    status = Column(String)  # draft, processing, ready, published
    s3_key = Column(String)
    transcription = Column(String)
    clip_metadata = Column(JSON)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="clips")
    social_posts = relationship("SocialPost", back_populates="clip")

class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("video_clips.id"))
    platform = Column(String)  # twitter, facebook, instagram, etc.
    status = Column(String)  # pending, published, failed
    post_id = Column(String)  # ID from the social media platform
    posted_at = Column(DateTime)
    post_metadata = Column(JSON)  # renamed from metadata to post_metadata
    
    clip = relationship("VideoClip", back_populates="social_posts")
