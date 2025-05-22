# Import all models here for Alembic to detect them
from backend.db.models.speaker import SpeakerIdentification, Speaker, SpeakerAppearance
from .user import User, UserRole
from .capture import CaptureSession
from .capture_log import CaptureLog
from .social import SocialPost, SocialPlatform, PostStatus
from .transcription import Transcription
from .video import VideoClip
from .face_profile import FaceProfile, FaceSample
from .voice_profile import VoiceProfile, VoiceSample

__all__ = [
    "User",
    "UserRole",
    "CaptureSession",
    "CaptureLog",
    "VideoClip",
    "SocialPost",
    "SocialPlatform",
    "PostStatus",
    "Transcription",
    "FaceProfile",
    "FaceSample",
    "VoiceProfile",
    "VoiceSample",
    "SpeakerIdentification",
    "Speaker",
    "SpeakerAppearance"
]
