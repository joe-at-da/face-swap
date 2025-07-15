"""
Test script for sentence-aware segmentation.

This script creates mock recognition events with incomplete sentences
and tests if the segmentation logic correctly merges them.
"""
import json
import logging
from typing import Dict, Any, List
from speaker_segmentation import SpeakerSegmentation
from member_clips import save_member_clips_to_supabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_recognition_events() -> Dict[str, Any]:
    """Create mock recognition events with incomplete sentences."""
    events = []
    
    # Speaker 1 with incomplete sentence followed by a continuation after a pause
    events.extend([
        {
            "timestamp": 10.0,
            "speaker_id": 1,
            "name": "Speaker One",
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "This is the first part of a sentence"
        },
        # Gap of 70 seconds (more than the standard 60s threshold)
        {
            "timestamp": 80.0,
            "speaker_id": 1,
            "name": "Speaker One",
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "that should be merged with the previous part."
        },
        # Complete sentence with normal gap
        {
            "timestamp": 100.0,
            "speaker_id": 1,
            "name": "Speaker One",
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "This is a complete sentence with proper punctuation."
        },
        # New speaker
        {
            "timestamp": 120.0,
            "speaker_id": 2,
            "name": "Speaker Two",
            "confidence": 0.7,
            "recognition_method": "facial",
            "transcript": "This is a different speaker."
        }
    ])
    
    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])
    
    return {"events": events}

def test_speaker_segmentation():
    """Test the speaker segmentation with sentence awareness."""
    logger.info("Testing speaker segmentation with sentence awareness...")
    
    # Create mock recognition events
    recognition_results = create_mock_recognition_events()
    
    # Initialize speaker segmentation
    segmentation = SpeakerSegmentation()
    
    # Identify speaking segments
    result = segmentation.identify_speaking_segments(1, recognition_results)
    
    # Print results
    logger.info(f"Found {result['segment_count']} segments")
    for i, segment in enumerate(result["segments"]):
        logger.info(f"Segment {i+1}:")
        logger.info(f"  Speaker ID: {segment['speaker_id']}")
        logger.info(f"  Time: {segment['start_time']} - {segment['end_time']}")
        logger.info(f"  Transcript: {segment['transcript']}")
        logger.info("---")
    
    # Check if the first two events were merged despite the 70-second gap
    if result["segment_count"] == 3:  # Should be 3 segments (2 for Speaker 1, 1 for Speaker 2)
        first_segment = result["segments"][0]
        if "first part of a sentence that should be merged" in first_segment["transcript"]:
            logger.info("SUCCESS: Incomplete sentence was correctly merged despite the time gap!")
        else:
            logger.error("FAIL: Incomplete sentence was not merged correctly")
    else:
        logger.error(f"FAIL: Expected 3 segments but got {result['segment_count']}")

def test_member_clips():
    """Test the member clips creation with sentence awareness."""
    logger.info("Testing member clips creation with sentence awareness...")
    
    # Create mock speaker segments
    speaker_segments = [
        {
            "speaker_id": 1,
            "start_time": 10.0,
            "end_time": 20.0,
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "This is the first part of a sentence"
        },
        # Gap of 70 seconds (more than the standard 60s threshold)
        {
            "speaker_id": 1,
            "start_time": 90.0,
            "end_time": 100.0,
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "that should be merged with the previous part."
        },
        # Complete sentence with normal gap
        {
            "speaker_id": 1,
            "start_time": 120.0,
            "end_time": 130.0,
            "confidence": 0.8,
            "recognition_method": "facial",
            "transcript": "This is a complete sentence with proper punctuation."
        },
        # New speaker
        {
            "speaker_id": 2,
            "start_time": 150.0,
            "end_time": 160.0,
            "confidence": 0.7,
            "recognition_method": "facial",
            "transcript": "This is a different speaker."
        }
    ]
    
    # Create mock transcription data
    transcription_data = {
        "segments": [
            {
                "start": 10.0,
                "end": 20.0,
                "text": "This is the first part of a sentence"
            },
            {
                "start": 90.0,
                "end": 100.0,
                "text": "that should be merged with the previous part."
            },
            {
                "start": 120.0,
                "end": 130.0,
                "text": "This is a complete sentence with proper punctuation."
            },
            {
                "start": 150.0,
                "end": 160.0,
                "text": "This is a different speaker."
            }
        ]
    }
    
    # Mock the necessary parameters for save_member_clips_to_supabase
    # Note: We're not actually saving to Supabase, just testing the merging logic
    class MockDB:
        def query(self, *args, **kwargs):
            class MockQuery:
                def filter(self, *args, **kwargs):
                    return self
                def first(self):
                    return None
            return MockQuery()
    
    class MockSupabase:
        def insert_parliament_member_clips(self, clips):
            return {"success": True, "count": len(clips), "clips": clips}
    
    # Process the speaker segments
    result = save_member_clips_to_supabase(
        video_id="1",
        recognition_results={
            "speaker_segments": speaker_segments,
            "transcription": transcription_data
        },
        db_session=MockDB(),
        supabase_service=MockSupabase(),
        full_video_url="http://example.com/test-video.mp4",
        video_metadata={}
    )
    
    # Print results
    if result and "clips" in result:
        logger.info(f"Created {len(result['clips'])} member clips")
        for i, clip in enumerate(result["clips"]):
            logger.info(f"Clip {i+1}:")
            logger.info(f"  Speaker ID: {clip['speaker_id']}")
            logger.info(f"  Time: {clip['start_time']} - {clip['end_time']}")
            logger.info(f"  Transcript: {clip['transcript']}")
            logger.info("---")
        
        # Check if the first two segments were merged despite the 70-second gap
        if len(result["clips"]) == 3:  # Should be 3 clips (2 for Speaker 1, 1 for Speaker 2)
            first_clip = result["clips"][0]
            if "first part of a sentence that should be merged" in first_clip["transcript"]:
                logger.info("SUCCESS: Incomplete sentence was correctly merged in member clips!")
            else:
                logger.error("FAIL: Incomplete sentence was not merged correctly in member clips")
        else:
            logger.error(f"FAIL: Expected 3 clips but got {len(result['clips'])}")
    else:
        logger.error("Failed to process member clips")

if __name__ == "__main__":
    logger.info("Starting sentence segmentation tests...")
    test_speaker_segmentation()
    logger.info("\n")
    test_member_clips()
    logger.info("Tests completed.")
