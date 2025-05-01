from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class CaptureLog(Base):
    __tablename__ = "capture_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, ForeignKey("capture_sessions.id"))
    level = Column(String(50))  # info, warning, error
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    capture_session = relationship("CaptureSession", back_populates="logs")
