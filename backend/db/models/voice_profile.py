"""
Database models for voice profiles.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class VoiceProfile(Base):
    """Voice profile model for storing speaker recognition data."""
    __tablename__ = "voice_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    party = Column(String(255), nullable=True)
    
    # Metadata and timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Voice data
    voice_embedding = Column(JSON, nullable=True)  # Voice embedding data
    sample_count = Column(Integer, default=0)  # Number of voice samples
    confidence_score = Column(Float, nullable=True)  # Confidence score for the voice profile
    is_verified = Column(Boolean, default=False)  # Whether the profile has been verified
    
    # Additional metadata
    profile_metadata = Column(JSON, nullable=True)
    
    # Relationships
    face_profiles = relationship("FaceProfile", back_populates="voice_profile")
    voice_samples = relationship("VoiceSample", back_populates="voice_profile")


class VoiceSample(Base):
    """Voice sample model for storing individual voice samples for a profile."""
    __tablename__ = "voice_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    voice_profile_id = Column(Integer, ForeignKey("voice_profiles.id"), nullable=False)
    
    # Sample data
    audio_path = Column(String(255), nullable=False)  # Path to the audio sample
    embedding = Column(JSON, nullable=True)  # Voice embedding for this sample
    duration = Column(Float, nullable=True)  # Duration of the audio sample in seconds
    confidence_score = Column(Float, nullable=True)  # Confidence score for this sample
    
    # Metadata
    source_video_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=True)
    start_time = Column(Float, nullable=True)  # Start time in the video
    end_time = Column(Float, nullable=True)  # End time in the video
    
    # Additional metadata
    sample_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    voice_profile = relationship("VoiceProfile", back_populates="voice_samples")
    source_video = relationship("CaptureSession")
