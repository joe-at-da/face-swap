"""
Recognition Event model for storing timeline events.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.base_class import Base

class RecognitionEvent(Base):
    """Model for storing recognition events in the timeline."""
    
    __tablename__ = "recognition_events"
    
    id = Column(Integer, primary_key=True, index=True)
    capture_session_id = Column(Integer, ForeignKey("capture_sessions.id", ondelete="CASCADE"))
    event_type = Column(String(50), index=True)  # face, speaker
    start_time = Column(Float, index=True)  # in seconds from start of video
    end_time = Column(Float)  # in seconds from start of video
    confidence = Column(Float)
    person_id = Column(Integer, index=True, nullable=True)
    person_name = Column(String(255), nullable=True)
    data = Column(JSON, nullable=True)  # Additional event data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    capture_session = relationship("CaptureSession", back_populates="recognition_events")
