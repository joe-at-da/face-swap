"""
Recognition package for facial and voice recognition services.
"""

from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.voice_recognition import VoiceRecognitionService

__all__ = ["FacialRecognitionService", "VoiceRecognitionService"]
