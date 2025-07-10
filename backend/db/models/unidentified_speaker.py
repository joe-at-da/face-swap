"""
UnidentifiedSpeaker model for storing unidentified speakers in video clips.
"""
import json
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.db.base_class import Base

class UnidentifiedSpeaker(Base):
    """
    Model for storing unidentified speakers in video clips.
    
    This model is used to store information about speakers that have not been
    identified in video clips, including their face data, voice data, and
    timestamps.
    """
    __tablename__ = "unidentified_speakers"
    
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(String, index=True)
    start_time = Column(Float)
    end_time = Column(Float)
    face_data = Column(Text)  # JSON string containing face embedding and other data
    voice_data = Column(Text)  # JSON string containing voice embedding and other data
    house_id = Column(String)  # commons, lords, or unknown
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return {
            "id": self.id,
            "clip_id": self.clip_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "face_data": json.loads(self.face_data) if self.face_data else None,
            "voice_data": json.loads(self.voice_data) if self.voice_data else None,
            "house_id": self.house_id
        }
