"""
Test script to demonstrate improved clip coherence logic.

This script uses the actual clip data from the database to show how the improved
coherence logic would merge and process these clips.
"""
import logging
import json
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for segment merging
MAX_GAP_SECONDS = 60  # Maximum gap between segments to consider merging
EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE = 120  # Extended gap for incomplete sentences

# Helper functions from member_clips.py
def is_sentence_complete(text):
    """Check if text appears to end with sentence-ending punctuation."""
    if not text:
        return False
    # Strip whitespace and check for sentence-ending punctuation
    text = text.strip()
    if not text:
        return False
    return text[-1] in ['.', '!', '?', ':', '"']

def assess_transcript_coherence(text):
    """Assess the semantic coherence of a transcript segment."""
    if not text:
        return 0.0
        
    text = text.strip()
    if not text:
        return 0.0
        
    # Basic coherence indicators
    score = 0.5  # Start with neutral score
    
    # Length-based indicators (longer texts tend to be more coherent)
    words = text.split()
    if len(words) < 3:
        score -= 0.2  # Very short segments are less likely to be coherent
    elif len(words) > 10:
        score += 0.2  # Longer segments are more likely to be complete thoughts
        
    # Sentence completion indicators
    if is_sentence_complete(text):
        score += 0.2  # Complete sentences are more coherent
    else:
        score -= 0.1  # Incomplete sentences may need merging
        
    # Check for sentence starters
    sentence_starters = ['i', 'we', 'they', 'he', 'she', 'it', 'the', 'a', 'an', 'this', 'that', 'these', 'those']
    if words and words[0].lower() in sentence_starters:
        score += 0.1  # Proper sentence starters indicate coherence
        
    # Check for conjunctions at the end
    conjunctions = ['and', 'but', 'or', 'nor', 'for', 'yet', 'so', 'if', 'when', 'because']
    if words and words[-1].lower() in conjunctions:
        score -= 0.3  # Ending with conjunction suggests incomplete thought
        
    # Normalize score to 0-1 range
    return max(0.0, min(1.0, score))

def post_process_segments(segments):
    """Post-process segments to avoid splitting sentences and create more coherent clips."""
    result = []
    i = 0
    while i < len(segments) - 1:
        current = segments[i]
        next_seg = segments[i + 1]
        
        should_merge = False
        merge_reason = ""
        
        # Calculate coherence scores
        current_coherence = assess_transcript_coherence(current["transcript"])
        next_coherence = assess_transcript_coherence(next_seg["transcript"])
        
        # Case 1: Same speaker with incomplete sentence
        if (current["speaker_id"] == next_seg["speaker_id"] and 
            not is_sentence_complete(current["transcript"])):
            
            # Merge with next segment if gap is reasonable (within 2 minutes)
            if next_seg["start_time"] - current["end_time"] <= EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE:
                should_merge = True
                merge_reason = "incomplete sentence"
        
        # Case 2: Check for sentence continuity between segments
        elif (current["speaker_id"] == next_seg["speaker_id"] and
              next_seg["start_time"] - current["end_time"] <= MAX_GAP_SECONDS):
              
            # Check if they might be part of the same speech (look for sentence continuity)
            if current["transcript"] and next_seg["transcript"]:
                # If the next segment doesn't start with a capital letter, it's likely a continuation
                if len(next_seg["transcript"]) > 0 and not next_seg["transcript"].strip()[0].isupper():
                    should_merge = True
                    merge_reason = "sentence continuity"
                # Check for short segments that might be part of the same thought
                elif len(current["transcript"].split()) < 5 or len(next_seg["transcript"].split()) < 5:
                    should_merge = True
                    merge_reason = "short segment"
                # Check if the current segment ends with a conjunction or preposition
                elif any(current["transcript"].strip().lower().endswith(word) for word in ["and", "but", "or", "nor", "for", "yet", "so", "if", "to", "with", "by", "as"]):
                    should_merge = True
                    merge_reason = "ending with conjunction"
                # Use coherence scores to make better merging decisions
                elif current_coherence < 0.4 and next_coherence < 0.6:
                    # Both segments have low-to-medium coherence, likely part of same thought
                    should_merge = True
                    merge_reason = "low coherence segments"
        
        # Case 3: Check for very short pauses between segments of the same speaker
        elif (current["speaker_id"] == next_seg["speaker_id"] and
              next_seg["start_time"] - current["end_time"] <= 2.0):  # 2 second pause threshold
            should_merge = True
            merge_reason = "short pause"
            
        # Case 4: Check for semantic continuity using coherence scores
        elif (current["speaker_id"] == next_seg["speaker_id"] and 
              next_seg["start_time"] - current["end_time"] <= 5.0 and  # 5 second threshold for semantic continuity
              current_coherence < 0.3):  # Current segment has very low coherence
            should_merge = True
            merge_reason = "semantic continuity"
            
        if should_merge:
            logger.info(f"Merging segments due to {merge_reason}: {current['transcript']} + {next_seg['transcript']}")
            merged = current.copy()
            merged["end_time"] = next_seg["end_time"]
            if next_seg["transcript"]:
                if merged["transcript"]:
                    # Add proper spacing between merged segments
                    if is_sentence_complete(merged["transcript"]):
                        merged["transcript"] += " " + next_seg["transcript"]
                    else:
                        # If the first segment doesn't end with punctuation, add a space
                        merged["transcript"] += " " + next_seg["transcript"]
                else:
                    merged["transcript"] = next_seg["transcript"]
            merged["duration_seconds"] = merged["end_time"] - merged["start_time"]
            
            result.append(merged)
            i += 2  # Skip both segments as they're now merged
            continue
                
        result.append(current)
        i += 1
        
    # Add the last segment if we didn't merge it
    if i == len(segments) - 1:
        result.append(segments[i])
        
    return result

def split_long_segments(segments, max_duration=60):
    """Split segments that are too long at natural pause points or sentence boundaries."""
    result = []
    
    for segment in segments:
        duration = segment["end_time"] - segment["start_time"]
        
        # If segment is not too long, keep it as is
        if duration <= max_duration:
            result.append(segment)
            continue
            
        # Try to split at sentence boundaries for long segments
        transcript = segment["transcript"]
        if not transcript or len(transcript) < 20:  # Skip if transcript is too short
            result.append(segment)
            continue
            
        # Look for sentence-ending punctuation to find natural split points
        sentence_endings = []
        for i, char in enumerate(transcript):
            if char in ['.', '!', '?'] and (i+1 >= len(transcript) or transcript[i+1] == ' '):
                sentence_endings.append(i)
        
        # If no sentence endings found, don't split
        if not sentence_endings:
            result.append(segment)
            continue
            
        # Calculate ideal split points based on duration
        num_splits = int(duration / max_duration) + 1
        ideal_split_points = []
        
        for i in range(1, num_splits):
            ideal_time = segment["start_time"] + (i * duration / num_splits)
            ideal_position = int(len(transcript) * (i / num_splits))
            
            # Find the closest sentence ending to this ideal position
            closest_idx = min(range(len(sentence_endings)), 
                            key=lambda j: abs(sentence_endings[j] - ideal_position)) if sentence_endings else -1
            
            if closest_idx >= 0:
                ideal_split_points.append(sentence_endings[closest_idx])
        
        # Sort split points and remove duplicates
        ideal_split_points = sorted(set(ideal_split_points))
        
        # Create sub-segments
        if not ideal_split_points:
            # No good split points found
            result.append(segment)
            continue
            
        # Create the sub-segments
        sub_segments = []
        start_idx = 0
        start_time = segment["start_time"]
        
        for split_idx in ideal_split_points:
            # Calculate proportional time for this split point
            split_ratio = (split_idx + 1) / len(transcript)
            split_time = segment["start_time"] + (duration * split_ratio)
            
            # Create sub-segment
            sub_segment = segment.copy()
            sub_segment["start_time"] = start_time
            sub_segment["end_time"] = split_time
            sub_segment["transcript"] = transcript[start_idx:split_idx+1].strip()
            sub_segment["duration_seconds"] = sub_segment["end_time"] - sub_segment["start_time"]
            sub_segments.append(sub_segment)
            
            # Update for next segment
            start_idx = split_idx + 1
            start_time = split_time
        
        # Add final sub-segment if needed
        if start_idx < len(transcript):
            sub_segment = segment.copy()
            sub_segment["start_time"] = start_time
            sub_segment["end_time"] = segment["end_time"]
            sub_segment["transcript"] = transcript[start_idx:].strip()
            sub_segment["duration_seconds"] = sub_segment["end_time"] - sub_segment["start_time"]
            sub_segments.append(sub_segment)
        
        # Add all sub-segments to result
        result.extend(sub_segments)
        logger.info(f"Split long segment ({duration:.1f}s) into {len(sub_segments)} sub-segments")
    
    return result

# Test data based on actual clips from the database
test_clips = [
    {
        "id": 30,
        "speaker_id": 5357,
        "start_time": 119.52,
        "end_time": 120.0,
        "duration_seconds": 0.48,
        "transcript": "In the recent spending review, the Chancellor outlined plans for a multi-million-pound investment"
    },
    {
        "id": 32,
        "speaker_id": 5081,
        "start_time": 122.4,
        "end_time": 123.0,
        "duration_seconds": 0.6,
        "transcript": "for essential building works at the public academy in Waiamurf."
    },
    {
        "id": 31,
        "speaker_id": 5217,
        "start_time": 124.8,
        "end_time": 127.0,
        "duration_seconds": 2.2,
        "transcript": "We welcome this new investment in our town for local schools, which will enable Budmurf"
    },
    {
        "id": 33,
        "speaker_id": 5323,
        "start_time": 129.12,
        "end_time": 130.0,
        "duration_seconds": 0.88,
        "transcript": "to finally upgrade their school buildings."
    },
    {
        "id": 34,
        "speaker_id": 5008,
        "start_time": 131.04,
        "end_time": 135.0,
        "duration_seconds": 3.96,
        "transcript": "Looking ahead, will the Chancellor work with me to speedily deliver this new investment"
    },
    {
        "id": 35,
        "speaker_id": 4564,
        "start_time": 137.28,
        "end_time": 140.0,
        "duration_seconds": 2.72,
        "transcript": "and ensure that the public academy gets the richly deserved upgrade as soon as possible?"
    },
    {
        "id": 36,
        "speaker_id": 452,
        "start_time": 140.64,
        "end_time": 143.0,
        "duration_seconds": 2.36,
        "transcript": "I can't be relevant to the question unfortunately."
    }
]

# Create a second test case with same speaker IDs to demonstrate merging
test_clips_same_speaker = [
    {
        "id": 101,
        "speaker_id": 5357,
        "start_time": 119.52,
        "end_time": 120.0,
        "duration_seconds": 0.48,
        "transcript": "In the recent spending review, the Chancellor outlined plans for a multi-million-pound investment"
    },
    {
        "id": 102,
        "speaker_id": 5357,
        "start_time": 122.4,
        "end_time": 123.0,
        "duration_seconds": 0.6,
        "transcript": "for essential building works at the public academy in Waiamurf."
    },
    {
        "id": 103,
        "speaker_id": 5357,
        "start_time": 124.8,
        "end_time": 127.0,
        "duration_seconds": 2.2,
        "transcript": "We welcome this new investment in our town for local schools, which will enable Budmurf"
    },
    {
        "id": 104,
        "speaker_id": 5357,
        "start_time": 129.12,
        "end_time": 130.0,
        "duration_seconds": 0.88,
        "transcript": "to finally upgrade their school buildings."
    },
    {
        "id": 105,
        "speaker_id": 5008,
        "start_time": 131.04,
        "end_time": 135.0,
        "duration_seconds": 3.96,
        "transcript": "Looking ahead, will the Chancellor work with me to speedily deliver this new investment"
    },
    {
        "id": 106,
        "speaker_id": 5008,
        "start_time": 137.28,
        "end_time": 140.0,
        "duration_seconds": 2.72,
        "transcript": "and ensure that the public academy gets the richly deserved upgrade as soon as possible?"
    }
]

# Create a test case for long segment splitting
test_long_segment = [
    {
        "id": 201,
        "speaker_id": 6001,
        "start_time": 200.0,
        "end_time": 280.0,  # 80 seconds long
        "duration_seconds": 80.0,
        "transcript": "I would like to address several points today. First, we need to consider the economic impact of these policies. The data clearly shows that sustainable investments yield long-term benefits. Second, we must acknowledge the scientific consensus on this matter. The evidence is overwhelming and demands our attention. Third, we should focus on practical solutions that can be implemented immediately. Small changes can lead to significant improvements over time. Finally, I urge all members to support this initiative for the benefit of future generations. This is not a partisan issue but a human one that affects us all."
    }
]

def test_coherence_improvements():
    """Test the coherence improvements with real clip data."""
    logger.info("=== TESTING COHERENCE IMPROVEMENTS ===")
    
    # Test 1: Different speakers with fragmented clips
    logger.info("\n\n=== TEST 1: ORIGINAL CLIPS (DIFFERENT SPEAKERS) ===")
    for clip in test_clips:
        logger.info(f"Clip {clip['id']}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Process the clips
    logger.info("\n=== AFTER PROCESSING (DIFFERENT SPEAKERS) ===")
    processed_clips = post_process_segments(test_clips)
    for i, clip in enumerate(processed_clips):
        logger.info(f"Processed Clip {i+1}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Test 2: Same speaker with fragmented clips
    logger.info("\n\n=== TEST 2: ORIGINAL CLIPS (SAME SPEAKER) ===")
    for clip in test_clips_same_speaker:
        logger.info(f"Clip {clip['id']}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Process the clips
    logger.info("\n=== AFTER PROCESSING (SAME SPEAKER) ===")
    processed_clips_same_speaker = post_process_segments(test_clips_same_speaker)
    for i, clip in enumerate(processed_clips_same_speaker):
        logger.info(f"Processed Clip {i+1}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Test 3: Long segment splitting
    logger.info("\n\n=== TEST 3: LONG SEGMENT SPLITTING ===")
    logger.info("Original long segment:")
    for clip in test_long_segment:
        logger.info(f"Clip {clip['id']}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Process the long segment
    logger.info("\n=== AFTER SPLITTING ===")
    split_clips = split_long_segments(test_long_segment)
    for i, clip in enumerate(split_clips):
        logger.info(f"Split Clip {i+1}: Speaker {clip['speaker_id']} - {clip['duration_seconds']:.2f}s - '{clip['transcript']}'")
    
    # Summary
    logger.info("\n\n=== SUMMARY OF IMPROVEMENTS ===")
    logger.info(f"Original clips (different speakers): {len(test_clips)}")
    logger.info(f"Processed clips (different speakers): {len(processed_clips)}")
    logger.info(f"Original clips (same speaker): {len(test_clips_same_speaker)}")
    logger.info(f"Processed clips (same speaker): {len(processed_clips_same_speaker)}")
    logger.info(f"Original long segments: {len(test_long_segment)}")
    logger.info(f"Split long segments: {len(split_clips)}")

if __name__ == "__main__":
    test_coherence_improvements()
