"""
Database models for face profiles.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class FaceProfile(Base):
    """Face profile model for storing facial recognition data."""
    __tablename__ = "face_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    party = Column(String(255), nullable=True)
    
    # Link to voice profile if available
    voice_profile_id = Column(Integer, ForeignKey("voice_profiles.id"), nullable=True)
    
    # Metadata and timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Face data
    face_encoding = Column(JSON, nullable=True)  # Facial embedding data
    face_image_path = Column(String(255), nullable=True)  # Path to the best face image
    confidence_score = Column(Float, nullable=True)  # Confidence score for the face profile
    is_verified = Column(Boolean, default=False)  # Whether the profile has been verified
    
    # Additional metadata
    profile_metadata = Column(JSON, nullable=True)
    
    # Relationships
    voice_profile = relationship("VoiceProfile", back_populates="face_profiles")
    face_samples = relationship("FaceSample", back_populates="face_profile")


class FaceSample(Base):
    """Face sample model for storing individual face images for a profile."""
    __tablename__ = "face_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    face_profile_id = Column(Integer, ForeignKey("face_profiles.id"), nullable=False)
    
    # Sample data
    image_path = Column(String(255), nullable=False)  # Path to the face image
    encoding = Column(JSON, nullable=True)  # Facial embedding for this sample
    confidence_score = Column(Float, nullable=True)  # Confidence score for this sample
    
    # Metadata
    source_video_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=True)
    timestamp = Column(Float, nullable=True)  # Timestamp in the video where the face was found
    frame_number = Column(Integer, nullable=True)  # Frame number in the video
    
    # Additional metadata
    sample_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    face_profile = relationship("FaceProfile", back_populates="face_samples")
    source_video = relationship("CaptureSession")
