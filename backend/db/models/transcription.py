from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class Transcription(Base):
    """Model for storing video transcriptions."""
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    video_clip_id = Column(Integer, ForeignKey("video_clips.id"))
    language = Column(String, default="en")
    text = Column(String)  # Full transcription text
    segments = Column(JSON)  # Segments with timestamps in JSON format
    status = Column(String, index=True)  # processing, ready, failed
    error_message = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    video_clip = relationship("VideoClip", back_populates="transcription")
