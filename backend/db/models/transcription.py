from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

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


class ParliamentTranscription(Base):
    """Model for storing Parliament TV video transcriptions."""
    __tablename__ = "parliament_transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    capture_session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=False)
    speaker_identification_id = Column(Integer, ForeignKey("speaker_identifications.id"), nullable=True)
    language = Column(String, default="en")
    format = Column(String, default="txt")  # txt, srt, json, docx
    model = Column(String, default="medium")  # tiny, base, small, medium, large
    status = Column(String, index=True)  # processing, completed, failed
    output_file = Column(String, nullable=True)  # Path to the output file
    error_message = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    capture_session = relationship("CaptureSession", back_populates="transcriptions")
    speaker_identification = relationship("SpeakerIdentification", back_populates="transcriptions")
    created_by = relationship("User", back_populates="parliament_transcriptions")
