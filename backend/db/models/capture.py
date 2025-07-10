from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text, JSON, Float
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
    error_message = Column(Text, nullable=True)  # Changed from String(255) to Text to allow longer error messages
    file_path = Column(String(255), nullable=True)  # Legacy field - use video_path instead
    video_path = Column(String(255), nullable=True)  # Path to the video file
    audio_path = Column(String(255), nullable=True)  # Path to the audio file
    audio_file_path = Column(String(255), nullable=True)  # Legacy field - use audio_path instead
    file_size = Column(BigInteger, nullable=True)  # in bytes
    duration = Column(Integer, nullable=True)  # in seconds
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Recognition fields
    facial_recognition_path = Column(String(255), nullable=True)  # Path to video with facial recognition
    speaker_identification_path = Column(String(255), nullable=True)  # Path to video with speaker identification
    speaker_identification_results = Column(String(255), nullable=True)  # Path to speaker identification results file
    voice_identification_results = Column(String(255), nullable=True)  # Path to voice identification results file
    combined_recognition_results = Column(String(255), nullable=True)  # Path to combined recognition results file
    recognition_progress = Column(Text, nullable=True)  # JSON string with recognition progress information
    recognition_status = Column(String(50), nullable=True)  # Status of recognition process: not_started, processing, completed, error
    recognition_started_at = Column(DateTime(timezone=True), nullable=True)  # When recognition process started
    recognition_completed_at = Column(DateTime(timezone=True), nullable=True)  # When recognition process completed
    recognition_results = Column(Text, nullable=True)  # JSON string with recognition results
    
    # Transcription fields
    transcription_status = Column(String(50), nullable=True)  # Status of transcription process: not_started, processing, completed, error
    transcription_path = Column(Text, nullable=True)  # Path to the transcription file
    transcription_error = Column(Text, nullable=True)  # Error message if transcription failed
    transcription_completed_at = Column(DateTime(timezone=True), nullable=True)  # When transcription process completed
    transcription_results = Column(Text, nullable=True)  # JSON string with transcription results
    
    # Use capture_metadata as the attribute name to avoid conflict with SQLAlchemy's metadata
    # This maps to the 'metadata' column in the database
    capture_metadata = Column('metadata', JSON, nullable=True, default=dict)
    
    # New recognition fields
    face_detection_results = Column(Text, nullable=True)  # JSON string with face detection results
    timeline_data = Column(Text, nullable=True)  # JSON string with timeline data
    
    # Relationships
    user = relationship("User", back_populates="capture_sessions")
    video_clips = relationship("VideoClip", back_populates="capture_session")
    speaker_identifications = relationship("SpeakerIdentification", back_populates="capture_session")
    transcriptions = relationship("ParliamentTranscription", back_populates="capture_session")
    logs = relationship("CaptureLog", back_populates="capture_session")
    recognition_events = relationship("RecognitionEvent", back_populates="capture_session", cascade="all, delete-orphan")
    recognition_processes = relationship("RecognitionProcess", back_populates="capture_session", cascade="all, delete-orphan")
