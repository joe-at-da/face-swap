"""
Recognition Configuration Module

This module centralizes configuration parameters for audio/video processing, transcription,
and diarization to ensure consistency across all services and scripts.

Usage:
    To toggle between test and production values:
    1. Set TEST_MODE = True for short durations (30s chunks, 30s max non-chunked)
    2. Set TEST_MODE = False for production values (1hr chunks, 10min max non-chunked)
    
    You can set TEST_MODE via environment variable:
    export TEST_MODE=true  # For test values
    export TEST_MODE=false  # For production values
    
    Or directly modify the TEST_MODE variable in this file.
"""

import os
from typing import Dict, Any

# Environment-based configuration
# Set DEBUG_MODE to True to use smaller values for faster processing during development
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

# Test mode configuration - set to True to use very short durations for testing chunking behavior
# This can be toggled independently from DEBUG_MODE
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() in ("true", "1", "yes")

# Print configuration mode at import time for visibility
print(f"Recognition config loaded with TEST_MODE={'ON' if TEST_MODE else 'OFF'}, DEBUG_MODE={'ON' if DEBUG_MODE else 'OFF'}")

# Audio processing configuration
class AudioConfig:
    """Audio processing configuration parameters."""
    
    # Default chunk size in seconds
    # - Production: 1200 seconds (20 minutes)
    # - Debug: 60 seconds (1 minute)
    # - Test: 30 seconds (for rapid testing of chunking behavior)
    DEFAULT_CHUNK_SIZE = 30 if TEST_MODE else (60 if DEBUG_MODE else 1200)
    
    # Default audio duration fallback when unable to determine actual duration
    # - Production: 90000 seconds (2.5 hour) - changed from 3600 seconds (1 hour)
    # - Debug: 30 seconds
    # - Test: 30 seconds (for rapid testing of chunking behavior)
    DEFAULT_AUDIO_DURATION = 30 if TEST_MODE or DEBUG_MODE else 90000
    
    # Maximum duration for non-chunked transcription in seconds
    # - Production: 90000 seconds (2.5 hour) - changed from 600 seconds (10 minutes)
    # - Debug: 30 seconds
    # - Test: 15 seconds (to force chunking for most test files)
    MAX_NON_CHUNKED_DURATION = 15 if TEST_MODE else (30 if DEBUG_MODE else 90000)
    
    # Minimum segment duration in seconds
    MIN_SEGMENT_DURATION = 0.5
    
    # Maximum silence duration between segments from the same speaker (in seconds)
    MAX_SILENCE_DURATION = 2.0

# Diarization configuration
class DiarizationConfig:
    """Speaker diarization configuration parameters."""
    
    # Maximum gap between segments from same speaker to be considered same speech group (in seconds)
    MAX_SPEAKER_GAP = 1.0
    
    # Minimum confidence score for speaker identification
    MIN_SPEAKER_CONFIDENCE = 0.6
    
    # Default diarization model size
    DEFAULT_MODEL = "base"  # Options: tiny, base, small, medium, large
    
    # Segment duration thresholds for frame extraction intervals
    SHORT_SEGMENT_THRESHOLD = 10.0
    SHORT_SEGMENT_FRAME_INTERVAL = 1.0
    LONG_SEGMENT_FRAME_INTERVAL = 4.0
    
    # Maximum time gap for proximity matching in seconds
    PROXIMITY_MATCHING_TIME_GAP = 1.0

# Member matcher configuration
class MemberMatcherConfig:
    """Parliament member matcher configuration parameters."""
    
    # Matching parameters
    MIN_CONFIDENCE_THRESHOLD = 0.5
    MIN_CONFIDENCE_GAP = 0.15  # Minimum gap between top match and second match
    
    # Diversity promotion parameters
    COOLDOWN_PERIOD = 60  # seconds
    MAX_CONSECUTIVE_MATCHES = 3
    DIVERSITY_BOOST_FACTOR = 0.05
    
    # Statistical validation parameters
    MAX_VALID_SIMILARITY = 1.05  # Slightly above 1.0 to allow for floating point errors
    MIN_VALID_SIMILARITY = -1.05  # Slightly below -1.0 to allow for floating point errors
    SIMILARITY_ANOMALY_THRESHOLD = 3.0  # Standard deviations from mean

# Processing timeouts
class TimeoutConfig:
    """Timeout configuration for various processing tasks."""
    
    # Maximum processing time for recognition tasks (in seconds)
    # - Production: 600 seconds (10 minutes)
    # - Debug: 60 seconds (1 minute)
    # - Test: 30 seconds (for rapid testing)
    MAX_RECOGNITION_PROCESSING_TIME = 30 if TEST_MODE else (60 if DEBUG_MODE else 9000)
    
    # Maximum processing time for transcription tasks (in seconds)
    # - Production: 600 seconds (10 minutes)
    # - Debug: 60 seconds (1 minute)
    # - Test: 30 seconds (for rapid testing)
    MAX_TRANSCRIPTION_PROCESSING_TIME = 30 if TEST_MODE else (60 if DEBUG_MODE else 9000)
    
    # Upload timeout for large files (in seconds)
    # - Production: 1800 seconds (30 minutes)
    # - Debug: 300 seconds (5 minutes)
    # - Test: 60 seconds (for rapid testing)
    UPLOAD_TIMEOUT = 60 if TEST_MODE else (300 if DEBUG_MODE else 9000)
    
    # HTTP request timeout (in seconds)
    # - Production: 30 seconds
    # - Debug: 10 seconds
    # - Test: 5 seconds (for rapid testing)
    REQUEST_TIMEOUT = 5 if TEST_MODE else (10 if DEBUG_MODE else 900)

# Get all configuration as a dictionary
def get_config() -> Dict[str, Any]:
    """Get all configuration parameters as a dictionary."""
    return {
        "debug_mode": DEBUG_MODE,
        "test_mode": TEST_MODE,
        "audio": {
            "default_chunk_size": AudioConfig.DEFAULT_CHUNK_SIZE,
            "default_audio_duration": AudioConfig.DEFAULT_AUDIO_DURATION,
            "max_non_chunked_duration": AudioConfig.MAX_NON_CHUNKED_DURATION,
            "min_segment_duration": AudioConfig.MIN_SEGMENT_DURATION,
            "max_silence_duration": AudioConfig.MAX_SILENCE_DURATION,
        },
        "diarization": {
            "max_speaker_gap": DiarizationConfig.MAX_SPEAKER_GAP,
            "min_speaker_confidence": DiarizationConfig.MIN_SPEAKER_CONFIDENCE,
            "default_model": DiarizationConfig.DEFAULT_MODEL,
            "short_segment_threshold": DiarizationConfig.SHORT_SEGMENT_THRESHOLD,
            "short_segment_frame_interval": DiarizationConfig.SHORT_SEGMENT_FRAME_INTERVAL,
            "long_segment_frame_interval": DiarizationConfig.LONG_SEGMENT_FRAME_INTERVAL,
            "proximity_matching_time_gap": DiarizationConfig.PROXIMITY_MATCHING_TIME_GAP,
        },
        "member_matcher": {
            "min_confidence_threshold": MemberMatcherConfig.MIN_CONFIDENCE_THRESHOLD,
            "min_confidence_gap": MemberMatcherConfig.MIN_CONFIDENCE_GAP,
            "cooldown_period": MemberMatcherConfig.COOLDOWN_PERIOD,
            "max_consecutive_matches": MemberMatcherConfig.MAX_CONSECUTIVE_MATCHES,
            "diversity_boost_factor": MemberMatcherConfig.DIVERSITY_BOOST_FACTOR,
            "max_valid_similarity": MemberMatcherConfig.MAX_VALID_SIMILARITY,
            "min_valid_similarity": MemberMatcherConfig.MIN_VALID_SIMILARITY,
            "similarity_anomaly_threshold": MemberMatcherConfig.SIMILARITY_ANOMALY_THRESHOLD,
        },
        "timeouts": {
            "max_recognition_processing_time": TimeoutConfig.MAX_RECOGNITION_PROCESSING_TIME,
            "max_transcription_processing_time": TimeoutConfig.MAX_TRANSCRIPTION_PROCESSING_TIME,
            "upload_timeout": TimeoutConfig.UPLOAD_TIMEOUT,
        },
    }
