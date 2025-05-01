from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base_class import Base

class SpeakerIdentification(Base):
    """Speaker identification model for Parliament TV videos."""
    __tablename__ = "speaker_identifications"
    
    id = Column(Integer, primary_key=True, index=True)
    capture_session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=False)
    status = Column(String, index=True)  # pending, processing, completed, failed
    results = Column(JSON, nullable=True)
    output_file = Column(String, nullable=True)
    threshold = Column(Float, default=0.6)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    capture_session = relationship("CaptureSession", back_populates="speaker_identifications")
    created_by = relationship("User", back_populates="speaker_identifications")
    transcriptions = relationship("ParliamentTranscription", back_populates="speaker_identification")

class Speaker(Base):
    """Speaker model for identified MPs."""
    __tablename__ = "speakers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    parliament_id = Column(String, index=True, nullable=True)
    party = Column(String, nullable=True)
    constituency = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    face_encoding = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appearances = relationship("SpeakerAppearance", back_populates="speaker")

class SpeakerAppearance(Base):
    """Speaker appearance in a video."""
    __tablename__ = "speaker_appearances"
    
    id = Column(Integer, primary_key=True, index=True)
    speaker_id = Column(Integer, ForeignKey("speakers.id"), nullable=False)
    identification_id = Column(Integer, ForeignKey("speaker_identifications.id"), nullable=False)
    start_time = Column(Float, nullable=False)  # in seconds
    end_time = Column(Float, nullable=False)  # in seconds
    duration = Column(Float, nullable=False)  # in seconds
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    speaker = relationship("Speaker", back_populates="appearances")
    identification = relationship("SpeakerIdentification")
