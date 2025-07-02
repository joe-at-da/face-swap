"""
Parliament Member Clip model for storing clips of MPs speaking.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base_class import Base

class ParliamentMemberClip(Base):
    """Model for clips of Parliament members speaking."""
    
    __tablename__ = "parliament_member_clips"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False, index=True)  # Numeric member ID
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    start_time = Column(Float, nullable=False)  # in seconds
    end_time = Column(Float, nullable=False)  # in seconds
    duration = Column(Float, nullable=False)  # in seconds
    confidence = Column(Float, nullable=False)  # confidence score of the match
    clip_url = Column(String, nullable=True)  # URL to the clip
    transcript = Column(String, nullable=True)  # Transcript of the clip
    clip_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="member_clips")
