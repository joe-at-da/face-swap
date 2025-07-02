"""
Parliament Video model for tracking Parliament TV videos.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base_class import Base

class ParliamentVideo(Base):
    """Model for Parliament TV videos."""
    
    __tablename__ = "parliament_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    parliament_id = Column(String, nullable=False, index=True)  # Parliament TV video ID
    session_date = Column(Date, nullable=False, index=True)
    video_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="parliament_videos")
