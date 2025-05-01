# Import all models here for Alembic to detect them
from backend.db.models.speaker import SpeakerIdentification, Speaker, SpeakerAppearance
from .user import User, UserRole
from .capture import CaptureSession
from .social import SocialPost, SocialPlatform, PostStatus
from .transcription import Transcription
from .video import VideoClip

__all__ = [
    "User",
    "UserRole",
    "CaptureSession",
    "VideoClip",
    "SocialPost",
    "SocialPlatform",
    "PostStatus",
    "Transcription"
]
