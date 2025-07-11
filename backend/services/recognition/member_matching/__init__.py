"""
Parliament Member Matching package for facial recognition of MPs
"""

from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher

__all__ = ["ParliamentMemberMatcher"]
from backend.services.recognition.member_matching.enhanced_matcher import EnhancedParliamentMemberMatcher
