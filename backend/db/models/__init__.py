# Import all models here for Alembic to detect them
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, Enum, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db.base_model import Base

# Import models from submodules
from .speaker import SpeakerIdentification, Speaker, SpeakerAppearance
from .user import User, UserRole
from .capture import CaptureSession
from .capture_log import CaptureLog
from .social import SocialPost, SocialPlatform, PostStatus
from .transcription import Transcription
from .face_profile import FaceProfile, FaceSample
from .voice_profile import VoiceProfile, VoiceSample
from .enums import ClipStatus, SocialPlatform, PostStatus

# Define VideoClip directly in __init__.py to avoid circular imports
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Changed from owner_id to user_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = relationship("User", back_populates="video_clips")  # Changed to match user.py
    social_posts = relationship("SocialPost", back_populates="clip", cascade="all, delete-orphan")

__all__ = [
    "User",
    "UserRole",
    "CaptureSession",
    "CaptureLog",
    "VideoClip",
    "SocialPost",
    "SocialPlatform",
    "PostStatus",
    "Transcription",
    "FaceProfile",
    "FaceSample",
    "VoiceProfile",
    "VoiceSample",
    "SpeakerIdentification",
    "Speaker",
    "SpeakerAppearance",
    "ClipStatus"
]
