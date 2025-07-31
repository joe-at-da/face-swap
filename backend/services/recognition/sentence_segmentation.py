"""
Sentence Segmentation Module.

This module provides functions for handling sentence segmentation in recognition events,
particularly for merging incomplete sentences across multiple recognition events.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def merge_incomplete_sentences(recognition_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge recognition events that contain incomplete sentences.
    
    This function looks for recognition events from the same speaker that might contain
    incomplete sentences and merges them to form complete sentences where appropriate.
    
    Args:
        recognition_events: List of recognition events, each containing at least:
                           - speaker_id/member_id
                           - timestamp/start_time
                           - transcript/text
    
    Returns:
        List of recognition events with merged incomplete sentences
    """
    if not recognition_events:
        return []
        
    # Sort events by start time
    events = sorted(recognition_events, key=lambda x: x.get('timestamp', x.get('start_time', 0)))
    
    # Constants for time thresholds
    MAX_GAP_SECONDS = 60
    EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE = 120  # 2 minutes for incomplete sentences
    
    # Helper function to check if a transcript appears to end with sentence-ending punctuation
    def is_sentence_complete(text):
        """Check if text appears to end with sentence-ending punctuation."""
        if not text:
            return False
        # Strip whitespace and check for sentence-ending punctuation
        text = text.strip()
        if not text:
            return False
        return text[-1] in ['.', '!', '?', ':', '"']
    
    result = []
    i = 0
    
    while i < len(events) - 1:
        current = events[i]
        next_event = events[i + 1]
        
        # Get speaker IDs (handle different field names)
        current_speaker = current.get('speaker_id', current.get('member_id'))
        next_speaker = next_event.get('speaker_id', next_event.get('member_id'))
        
        # Get timestamps (handle different field names)
        current_start = current.get('timestamp', current.get('start_time', 0))
        current_end = current.get('end_time', current_start + 10)  # Default to 10 seconds if no end_time
        next_start = next_event.get('timestamp', next_event.get('start_time', 0))
        next_end = next_event.get('end_time', next_start + 10)  # Default to 10 seconds if no end_time
        
        # Get transcripts (handle different field names)
        current_transcript = current.get('transcript', current.get('text', ''))
        next_transcript = next_event.get('transcript', next_event.get('text', ''))
        
        should_merge = False
        
        # Case 1: Same speaker with incomplete sentence
        if (current_speaker == next_speaker and 
            not is_sentence_complete(current_transcript)):
            
            # Merge with next segment if gap is reasonable (within extended gap)
            if next_start - current_end <= EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE:
                should_merge = True
        
        # Case 2: Check for sentence continuity between segments
        elif (current_speaker == next_speaker and
              next_start - current_end <= MAX_GAP_SECONDS):
              
            # Check if they might be part of the same speech (look for sentence continuity)
            if current_transcript and next_transcript:
                # If the next segment doesn't start with a capital letter, it's likely a continuation
                if len(next_transcript) > 0 and not next_transcript.strip()[0].isupper():
                    should_merge = True
        
        if should_merge:
            merged = current.copy()
            
            # Update end time
            if 'end_time' in next_event:
                merged['end_time'] = next_event['end_time']
            
            # Merge transcripts
            transcript_key = 'transcript' if 'transcript' in current else 'text'
            if transcript_key in next_event:
                if transcript_key in merged and merged[transcript_key]:
                    merged[transcript_key] += " " + next_event[transcript_key]
                else:
                    merged[transcript_key] = next_event[transcript_key]
            
            # Update confidence
            if 'confidence' in current and 'confidence' in next_event:
                merged['confidence'] = max(current['confidence'], next_event['confidence'])
            
            result.append(merged)
            i += 2  # Skip both events as they're now merged
            continue
                
        result.append(current)
        i += 1
        
    # Add the last event if we didn't merge it
    if i == len(events) - 1:
        result.append(events[i])
        
    # Log statistics
    logger.info(f"Sentence segmentation: {len(recognition_events)} events merged into {len(result)} events")
    
    return result
