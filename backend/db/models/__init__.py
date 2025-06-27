# Import all models here for Alembic to detect them
from .speaker import SpeakerIdentification, Speaker, SpeakerAppearance
from .user import User, UserRole
from .capture import CaptureSession
from .capture_log import CaptureLog
from .social import SocialPost, SocialPlatform, PostStatus
from .transcription import Transcription
from .video import VideoClip  # Import VideoClip from video.py
from .face_profile import FaceProfile, FaceSample
from .voice_profile import VoiceProfile, VoiceSample
from .enums import ClipStatus, SocialPlatform, PostStatus
from .recognition_event import RecognitionEvent  # Import RecognitionEvent model
from .recognition_process import RecognitionProcess  # Import RecognitionProcess model

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
    "SpeakerAppearance",
    "ClipStatus",
    "RecognitionEvent",
    "RecognitionProcess"
]
