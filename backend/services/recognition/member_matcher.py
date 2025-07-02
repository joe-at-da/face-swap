"""
Module for matching unidentified speakers with parliament members based on facial recognition
This is a compatibility layer that imports from the new modular structure
"""
import logging
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher

logger = logging.getLogger(__name__)

# Re-export the ParliamentMemberMatcher class for backward compatibility
# All functionality is now in the member_matching package
