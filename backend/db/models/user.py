from sqlalchemy import Boolean, Column, Integer, String, Enum
from sqlalchemy.orm import relationship
import enum

from backend.db.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MP = "mp"
    STAFF = "staff"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.STAFF)
    is_active = Column(Boolean, default=True)

    # Relationships
    capture_sessions = relationship("CaptureSession", back_populates="user")
    video_clips = relationship("VideoClip", back_populates="created_by_user")
    social_posts = relationship("SocialPost", back_populates="created_by")
