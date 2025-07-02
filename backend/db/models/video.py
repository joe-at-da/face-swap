from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base_class import Base
from backend.db.models.enums import ClipStatus

class Video(Base):
    """Model for videos in the system."""
    
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    source_url = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # in seconds
    status = Column(String, nullable=False)  # uploaded, processing, completed, failed
    metadata = Column(JSON, nullable=True)  # Additional metadata
    error_message = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recognition_processes = relationship("RecognitionProcess", back_populates="video", cascade="all, delete-orphan")
    parliament_videos = relationship("ParliamentVideo", back_populates="video", cascade="all, delete-orphan")
    member_clips = relationship("ParliamentMemberClip", back_populates="video", cascade="all, delete-orphan")

class VideoClip(Base):
    __tablename__ = "video_clips"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    source_url = Column(String, nullable=False)  # Changed from storage_path to source_url
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)  # in seconds
    status = Column(Enum(ClipStatus, name="clip_status_enum"), nullable=False, default=ClipStatus.DRAFT)
    s3_key = Column(String)
    transcription = Column(String)
    faces_detected = Column(JSON)  # List of detected faces with confidence scores
    clip_metadata = Column(JSON, default={})
    error_message = Column(String, nullable=True)
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Changed from user_id to owner_id to match DB schema
    capture_session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="clips")  # Changed from created_by_user to owner to match DB schema
    capture_session = relationship("CaptureSession", back_populates="video_clips")
    social_posts = relationship("SocialPost", back_populates="video_clip", cascade="all, delete-orphan")
    transcription = relationship("Transcription", back_populates="video_clip", uselist=False)
