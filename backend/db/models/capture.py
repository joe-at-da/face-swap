from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class CaptureSession(Base):
    __tablename__ = "capture_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)  # Using Text type to handle longer URLs
    status = Column(String(50), index=True)  # active, scheduled, completed, failed, processing
    error_message = Column(String(255), nullable=True)
    file_path = Column(String(255), nullable=True)
    audio_file_path = Column(String(255), nullable=True)  # Path to the audio file
    file_size = Column(BigInteger, nullable=True)  # in bytes
    duration = Column(Integer, nullable=True)  # in seconds
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="capture_sessions")
    video_clips = relationship("VideoClip", back_populates="capture_session")
    speaker_identifications = relationship("SpeakerIdentification", back_populates="capture_session")
    transcriptions = relationship("ParliamentTranscription", back_populates="capture_session")
    logs = relationship("CaptureLog", back_populates="capture_session")
