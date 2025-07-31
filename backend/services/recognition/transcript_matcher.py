"""
Transcript Matcher Module.

This module provides functions for matching transcripts to diarization segments
based on timestamp overlap.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def match_transcripts_to_diarization_segments(segments: List[Dict[str, Any]], transcript_dir: str) -> List[Dict[str, Any]]:
    """
    Match transcript text to diarization segments based on timestamp overlap.
    
    Args:
        segments: List of diarization segments, each containing at least:
                 - start_time: float (seconds)
                 - end_time: float (seconds)
                 - speaker: str
        transcript_dir: Directory containing transcript chunk files
                       (format: transcript_chunk_*.txt)
    
    Returns:
        List of segments with transcript text added
    """
    if not segments:
        logger.warning("No segments provided for transcript matching")
        return []
    
    if not os.path.exists(transcript_dir):
        logger.warning(f"Transcript directory not found: {transcript_dir}")
        return segments
    
    logger.info(f"Matching transcripts from {transcript_dir} to {len(segments)} diarization segments")
    
    # Load all transcript chunks
    transcript_lines = []
    transcript_files = sorted([f for f in os.listdir(transcript_dir) if f.startswith("transcript_chunk_") and f.endswith(".txt")])
    
    for file_name in transcript_files:
        file_path = os.path.join(transcript_dir, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    # Parse timestamp format: [hh:mm:ss - hh:mm:ss] text
                    match = re.match(r'\[(\d{2}):(\d{2}):(\d{2}) - (\d{2}):(\d{2}):(\d{2})\] (.*)', line.strip())
                    if match:
                        h1, m1, s1, h2, m2, s2, text = match.groups()
                        start_time = int(h1) * 3600 + int(m1) * 60 + int(s1)
                        end_time = int(h2) * 3600 + int(m2) * 60 + int(s2)
                        transcript_lines.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'text': text.strip()
                        })
        except Exception as e:
            logger.error(f"Error reading transcript file {file_path}: {e}")
    
    logger.info(f"Loaded {len(transcript_lines)} transcript lines from {len(transcript_files)} files")
    
    # Match transcript lines to diarization segments
    matched_segments = []
    for segment in segments:
        segment_start = segment.get('start_time', 0)
        segment_end = segment.get('end_time', 0)
        speaker = segment.get('speaker', 'UNKNOWN')
        
        # Find matching transcript lines based on timestamp overlap
        matching_texts = []
        for line in transcript_lines:
            # Check for overlap between segment and transcript line
            if (line['start_time'] <= segment_end and line['end_time'] >= segment_start):
                matching_texts.append(line['text'])
        
        # If matching texts found, join them; otherwise use placeholder
        if matching_texts:
            segment['text'] = ' '.join(matching_texts)
            logger.debug(f"Matched transcript for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
        else:
            segment['text'] = f"Speech segment from {speaker}"
            logger.debug(f"No transcript match for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
        
        matched_segments.append(segment)
    
    # Log statistics
    placeholder_count = sum(1 for s in matched_segments if s['text'].startswith("Speech segment from"))
    match_count = len(matched_segments) - placeholder_count
    match_percentage = (match_count / len(matched_segments) * 100) if matched_segments else 0
    
    logger.info(f"Transcript matching complete: {match_count}/{len(matched_segments)} segments matched ({match_percentage:.1f}%)")
    
    return matched_segments
