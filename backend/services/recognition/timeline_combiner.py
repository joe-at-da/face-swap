"""
Timeline combiner for speaker recognition and transcription data.

This module provides functions to combine speaker recognition timelines
with transcription data to create speaker-attributed transcripts.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

def combine_recognition_and_transcription(
    recognition_results: Dict[str, Any],
    transcription_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine speaker recognition results with transcription data.
    
    This function:
    1. Matches transcription segments with speaker appearances based on timestamps
    2. Creates a combined timeline with both speaker and transcription data
    3. Generates speaker-attributed transcripts
    
    Args:
        recognition_results: Speaker recognition results dictionary
        transcription_data: Transcription data dictionary
        
    Returns:
        Dict with combined timeline and speaker-attributed transcripts
    """
    logger.info("Combining speaker recognition and transcription data")
    
    # Extract speaker appearances from recognition results
    speaker_appearances = []
    if "speakers" in recognition_results:
        for speaker in recognition_results["speakers"]:
            if "appearances" in speaker:
                for appearance in speaker["appearances"]:
                    speaker_appearances.append({
                        "speaker_id": speaker.get("id"),
                        "speaker_name": speaker.get("name", "Unknown"),
                        "start_time": appearance.get("start_time", 0),
                        "end_time": appearance.get("end_time", 0),
                        "confidence": appearance.get("confidence", 0),
                        "type": "speaker_appearance"
                    })
    
    # Sort speaker appearances by start time
    speaker_appearances.sort(key=lambda x: x["start_time"])
    
    # Extract transcription segments
    transcription_segments = []
    if "segments" in transcription_data:
        for segment in transcription_data["segments"]:
            transcription_segments.append({
                "start_time": segment.get("start", 0),
                "end_time": segment.get("end", 0),
                "text": segment.get("text", ""),
                "type": "transcription"
            })
    
    # Create a combined timeline
    combined_timeline = []
    combined_timeline.extend(speaker_appearances)
    combined_timeline.extend(transcription_segments)
    combined_timeline.sort(key=lambda x: x["start_time"])
    
    # Create speaker-attributed transcripts
    speaker_attributed_transcripts = []
    current_speaker = None
    
    for segment in transcription_segments:
        # Find the most likely speaker for this segment
        segment_start = segment["start_time"]
        segment_end = segment["end_time"]
        
        # Find overlapping speaker appearances
        overlapping_speakers = []
        for appearance in speaker_appearances:
            speaker_start = appearance["start_time"]
            speaker_end = appearance["end_time"]
            
            # Check for overlap
            if (speaker_start <= segment_end and speaker_end >= segment_start):
                # Calculate overlap duration
                overlap_start = max(speaker_start, segment_start)
                overlap_end = min(speaker_end, segment_end)
                overlap_duration = overlap_end - overlap_start
                
                overlapping_speakers.append({
                    "speaker_id": appearance["speaker_id"],
                    "speaker_name": appearance["speaker_name"],
                    "overlap_duration": overlap_duration,
                    "confidence": appearance["confidence"]
                })
        
        # Sort by overlap duration and confidence
        overlapping_speakers.sort(key=lambda x: (x["overlap_duration"], x["confidence"]), reverse=True)
        
        # Assign the speaker with the most overlap
        if overlapping_speakers:
            attributed_speaker = overlapping_speakers[0]
        else:
            attributed_speaker = {
                "speaker_id": None,
                "speaker_name": "Unknown Speaker",
                "overlap_duration": 0,
                "confidence": 0
            }
        
        # Create speaker-attributed transcript segment
        speaker_attributed_transcripts.append({
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
            "text": segment["text"],
            "speaker_id": attributed_speaker["speaker_id"],
            "speaker_name": attributed_speaker["speaker_name"],
            "confidence": attributed_speaker["confidence"]
        })
    
    # Create the final combined data
    combined_data = {
        "combined_timeline": combined_timeline,
        "speaker_attributed_transcripts": speaker_attributed_transcripts
    }
    
    return combined_data
