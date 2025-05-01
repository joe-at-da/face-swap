# Import all the models, so that Base has them before being imported by Alembic
from backend.db.base_class import Base

# Import models directly to avoid circular imports
from backend.db.models.user import User
from backend.db.models.video import VideoClip
from backend.db.models.social import SocialPost
from backend.db.models.capture import CaptureSession
from backend.db.models.speaker import SpeakerIdentification
from backend.db.models.transcription import ParliamentTranscription
