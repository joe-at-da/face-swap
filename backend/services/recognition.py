"""
Recognition services module.
"""

from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.voice_recognition import VoiceRecognitionService

__all__ = ["FacialRecognitionService", "VoiceRecognitionService"]
