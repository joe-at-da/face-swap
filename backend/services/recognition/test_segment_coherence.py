"""
Test script for improved segment coherence logic.

This script tests the enhanced segment coherence features with a real video capture (747),
focusing on the improved transcript coherence scoring, segment merging, and long segment splitting.
"""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid

# Add the project root to the path to allow imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.services.recognition.member_clips import save_member_clips_to_supabase
from backend.services.recognition.speaker_segmentation import SpeakerSegmentation
from backend.db.models import CaptureSession, Video

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockDB:
    """Mock database session for testing."""
    def query(self, *args, **kwargs):
        class MockQuery:
            def filter(self, *args, **kwargs):
                return self
                
            def first(self):
                # Mock a capture session
                session = CaptureSession()
                session.id = 747
                session.title = "Test Parliament Session"
                session.date = datetime.now().date()
                session.session_type = "regular"
                return session
        return MockQuery()


class MockSupabase:
    """Mock Supabase service for testing."""
    def __init__(self):
        self.clips = []
        
    def client(self):
        return self
        
    def table(self, table_name):
        return self
        
    def insert(self, data):
        class MockResponse:
            def __init__(self, data):
                self.data = data
                
            def execute(self):
                return self
                
        self.clips.extend(data if isinstance(data, list) else [data])
        return MockResponse(data)


def load_test_data(video_id="747"):
    """Load test data for video capture 747 or create mock data if not available."""
    # Try to load real data if available
    data_path = project_root / "data" / f"video_{video_id}_recognition_results.json"
    
    if data_path.exists():
        logger.info(f"Loading real recognition data from {data_path}")
        with open(data_path, "r") as f:
            return json.load(f)
    
    # Otherwise create mock data
    logger.info(f"Real data not found, creating mock data for video {video_id}")
    
    # Create mock speaker segments with various coherence challenges
    speaker_segments = [
        # Speaker 1: Incomplete sentence followed by continuation
        {
            "speaker_id": 101,
            "speaker_name": "John Smith",
            "start_time": 10.0,
            "end_time": 15.0,
            "confidence": 0.85,
            "recognition_method": "facial",
            "transcript": "I would like to address the issue of"
        },
        # Gap of 3 seconds
        {
            "speaker_id": 101,
            "speaker_name": "John Smith",
            "start_time": 18.0,
            "end_time": 25.0,
            "confidence": 0.82,
            "recognition_method": "facial",
            "transcript": "climate change and its impact on our communities."
        },
        
        # Speaker 2: Very short segment
        {
            "speaker_id": 102,
            "speaker_name": "Jane Doe",
            "start_time": 30.0,
            "end_time": 32.0,
            "confidence": 0.75,
            "recognition_method": "facial",
            "transcript": "Thank you."
        },
        
        # Speaker 2: Continuing with short pause
        {
            "speaker_id": 102,
            "speaker_name": "Jane Doe",
            "start_time": 33.0,
            "end_time": 45.0,
            "confidence": 0.78,
            "recognition_method": "facial",
            "transcript": "I appreciate the previous speaker's comments on this important matter."
        },
        
        # Speaker 3: Long segment that should be split
        {
            "speaker_id": 103,
            "speaker_name": "Robert Johnson",
            "start_time": 50.0,
            "end_time": 130.0,  # 80 seconds long
            "confidence": 0.9,
            "recognition_method": "facial",
            "transcript": "I would like to address several points today. First, we need to consider the economic impact of these policies. The data clearly shows that sustainable investments yield long-term benefits. Second, we must acknowledge the scientific consensus on this matter. The evidence is overwhelming and demands our attention. Third, we should focus on practical solutions that can be implemented immediately. Small changes can lead to significant improvements over time. Finally, I urge all members to support this initiative for the benefit of future generations. This is not a partisan issue but a human one that affects us all."
        },
        
        # Speaker 4: Sentence ending with conjunction
        {
            "speaker_id": 104,
            "speaker_name": "Sarah Williams",
            "start_time": 140.0,
            "end_time": 145.0,
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "We need to consider the implications for rural communities and"
        },
        
        # Speaker 4: Continuation after pause
        {
            "speaker_id": 104,
            "speaker_name": "Sarah Williams",
            "start_time": 148.0,
            "end_time": 155.0,
            "confidence": 0.82,
            "recognition_method": "facial",
            "transcript": "ensure that their voices are heard in this discussion."
        }
    ]
    
    # Create mock transcription data to match speaker segments
    transcription_segments = []
    for segment in speaker_segments:
        transcription_segments.append({
            "start": segment["start_time"],
            "end": segment["end_time"],
            "text": segment["transcript"]
        })
    
    return {
        "video_id": video_id,
        "speaker_segments": speaker_segments,
        "transcription": {"segments": transcription_segments}
    }


def test_segment_coherence(video_id="747"):
    """Test the improved segment coherence logic."""
    logger.info(f"Testing improved segment coherence with video {video_id}...")
    
    # Load test data
    recognition_results = load_test_data(video_id)
    
    # Create mock database and Supabase service
    db_session = MockDB()
    supabase_service = MockSupabase()
    
    # Process the speaker segments
    result = save_member_clips_to_supabase(
        video_id=video_id,
        recognition_results=recognition_results,
        db_session=db_session,
        supabase_service=supabase_service,
        full_video_url=f"http://example.com/video_{video_id}.mp4",
        video_metadata={"title": f"Test Video {video_id}", "date": datetime.now().isoformat()}
    )
    
    # Analyze results
    logger.info("\n=== SEGMENT COHERENCE TEST RESULTS ===")
    
    if not result or "success" not in result or not result["success"]:
        logger.error("Failed to process member clips")
        return
    
    # Check if clips were created
    clips = supabase_service.clips
    logger.info(f"Created {len(clips)} member clips")
    
    # Analyze each clip
    for i, clip in enumerate(clips):
        logger.info(f"\nClip {i+1}:")
        logger.info(f"  Speaker: {clip.get('member_name', 'Unknown')} (ID: {clip.get('member_id', 'Unknown')})")
        logger.info(f"  Time: {clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s")
        logger.info(f"  Duration: {clip.get('duration_seconds', 0):.1f}s")
        logger.info(f"  Transcript: {clip.get('transcript', '')}")
    
    # Check for specific improvements
    logger.info("\n=== COHERENCE IMPROVEMENTS ANALYSIS ===")
    
    # 1. Check for merged incomplete sentences
    merged_incomplete = any(
        "I would like to address the issue of climate change" in clip.get("transcript", "")
        for clip in clips
    )
    logger.info(f"1. Merged incomplete sentences: {'SUCCESS' if merged_incomplete else 'FAIL'}")
    
    # 2. Check for merged short segments
    merged_short = any(
        "Thank you. I appreciate" in clip.get("transcript", "")
        for clip in clips
    )
    logger.info(f"2. Merged short segments: {'SUCCESS' if merged_short else 'FAIL'}")
    
    # 3. Check for split long segments
    long_segment_split = sum(
        1 for clip in clips
        if clip.get("member_id") == 103 and 10.0 <= clip.get("duration_seconds", 0) <= 60.0
    )
    logger.info(f"3. Split long segments: {'SUCCESS' if long_segment_split > 1 else 'FAIL'} ({long_segment_split} segments)")
    
    # 4. Check for merged segments with conjunctions
    merged_conjunction = any(
        "implications for rural communities and ensure" in clip.get("transcript", "")
        for clip in clips
    )
    logger.info(f"4. Merged segments with conjunctions: {'SUCCESS' if merged_conjunction else 'FAIL'}")
    
    return result


if __name__ == "__main__":
    logger.info("Starting segment coherence tests...")
    video_id = "747"
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
    test_segment_coherence(video_id)
    logger.info("Tests completed.")
