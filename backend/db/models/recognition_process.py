"""
Recognition Process model for tracking facial recognition processing.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from backend.db.base_class import Base

class RecognitionProcess(Base):
    """Model for tracking facial recognition processing for videos."""
    
    __tablename__ = "recognition_processes"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    process_type = Column(String(50), index=True, default="facial")  # facial, voice, multimodal
    status = Column(String(50), index=True)  # pending, processing, completed, failed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    results = Column(JSON, nullable=True)  # Recognition results
    process_metadata = Column('metadata', JSON, nullable=True)  # Additional metadata including combined_av_url
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    video = relationship("Video", back_populates="recognition_processes")
