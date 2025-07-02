# Import all models here for Alembic to detect them
from .speaker import SpeakerIdentification, Speaker, SpeakerAppearance
from .user import User, UserRole
from .capture import CaptureSession
from .capture_log import CaptureLog
from .social import SocialPost, SocialPlatform, PostStatus
from .transcription import Transcription, ParliamentTranscription
from .video import VideoClip, Video  # Import VideoClip and Video from video.py
from .parliament_video import ParliamentVideo  # Import ParliamentVideo model
from .parliament_member_clip import ParliamentMemberClip  # Import ParliamentMemberClip model
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
    "Video",
    "ParliamentVideo",
    "ParliamentMemberClip",
    "SocialPost",
    "SocialPlatform",
    "PostStatus",
    "Transcription",
    "ParliamentTranscription",
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
