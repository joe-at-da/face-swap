# This file is a compatibility layer that imports from backend.db.models/__init__.py
# It's maintained for backward compatibility with existing code

# Import models from the models package
from backend.db.models import (
    User, UserRole, VideoClip, SocialPost, SocialPlatform, PostStatus,
    ClipStatus, CaptureSession, CaptureLog, Transcription, ParliamentTranscription
)

# This comment is to indicate that this file is now just a compatibility layer
# New code should import directly from backend.db.models

# All model definitions have been moved to backend.db.models/__init__.py
# This file now only serves as a compatibility layer for existing imports
