from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class VideoClip(Base):
    __tablename__ = "video_clips"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    storage_path = Column(String)
    duration = Column(Float)  # in seconds
    status = Column(String, index=True)  # processing, ready, failed
    error_message = Column(String, nullable=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"))
    capture_session_id = Column(Integer, ForeignKey("capture_sessions.id"))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    start_time = Column(DateTime(timezone=True))  # When the clip starts in the original stream
    end_time = Column(DateTime(timezone=True))    # When the clip ends in the original stream
    
    # Relationships
    user = relationship("User", back_populates="video_clips")
    capture_session = relationship("CaptureSession", back_populates="video_clips")
