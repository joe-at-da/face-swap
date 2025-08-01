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

def match_transcripts_to_diarization_segments(segments: List[Dict[str, Any]], transcript_dir: Optional[str] = None) -> List[Dict[str, Any]]:
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
    
    # Use the simple transcript finder to get a valid directory
    from backend.services.recognition.transcript_finder import find_transcript_directory
    
    # If transcript_dir is not provided or invalid, find a valid one
    if not transcript_dir or not os.path.exists(transcript_dir):
        transcript_dir = find_transcript_directory()
        
    # If still no valid directory, return original segments
    if not transcript_dir or not os.path.exists(transcript_dir):
        logger.warning("No valid transcript directory found. Returning original segments.")
        return segments
    
    logger.info(f"Matching transcripts from {transcript_dir} to {len(segments)} diarization segments")
    
    # Load all transcript chunks - try multiple formats and locations
    transcript_lines = []
    
    # Look for transcript files with various naming patterns
    transcript_patterns = [
        "transcript_chunk_*.txt",
        "transcript_*.txt",
        "*.transcript.txt",
        "*.txt"  # Fallback to any text file as last resort
    ]
    
    # Try each pattern until we find transcript files
    found_files = False
    for pattern in transcript_patterns:
        try:
            import fnmatch
            matching_files = sorted([f for f in os.listdir(transcript_dir) if fnmatch.fnmatch(f, pattern)])
            if matching_files:
                logger.info(f"Found {len(matching_files)} transcript files matching pattern '{pattern}'")
                found_files = True
                
                for file_name in matching_files:
                    file_path = os.path.join(transcript_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for line in lines:
                                # Try multiple timestamp formats
                                # Format 1: [hh:mm:ss - hh:mm:ss] text
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
                                    continue
                                    
                                # Format 2: [MM:SS.mmm -> MM:SS.mmm] text
                                match = re.match(r'\[(\d+):(\d+)\.(\d+) -> (\d+):(\d+)\.(\d+)\] (.*)', line.strip())
                                if match:
                                    m1, s1, ms1, m2, s2, ms2, text = match.groups()
                                    start_time = int(m1) * 60 + int(s1) + int(ms1)/1000
                                    end_time = int(m2) * 60 + int(s2) + int(ms2)/1000
                                    transcript_lines.append({
                                        'start_time': start_time,
                                        'end_time': end_time,
                                        'text': text.strip()
                                    })
                                    continue
                                    
                                # Format 3: just look for timestamps in the format hh:mm:ss anywhere in the line
                                timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2})', line.strip())
                                if len(timestamps) >= 2:
                                    h1, m1, s1 = timestamps[0]
                                    h2, m2, s2 = timestamps[1]
                                    start_time = int(h1) * 3600 + int(m1) * 60 + int(s1)
                                    end_time = int(h2) * 3600 + int(m2) * 60 + int(s2)
                                    # Extract text after the second timestamp
                                    text_match = re.search(r'\d{2}:\d{2}:\d{2}.*?\d{2}:\d{2}:\d{2}(.*)', line.strip())
                                    text = text_match.group(1).strip() if text_match else line.strip()
                                    transcript_lines.append({
                                        'start_time': start_time,
                                        'end_time': end_time,
                                        'text': text
                                    })
                    except Exception as e:
                        logger.error(f"Error reading transcript file {file_path}: {e}")
                
                # If we found and processed files with this pattern, no need to try other patterns
                if transcript_lines:
                    break
        except Exception as e:
            logger.error(f"Error processing pattern {pattern}: {e}")
    
    if not found_files:
        logger.warning(f"No transcript files found in {transcript_dir} matching any known patterns")
        return segments
    
    logger.info(f"Loaded {len(transcript_lines)} transcript lines from transcript files")
    
    # Sort transcript lines by start time for more efficient matching
    transcript_lines.sort(key=lambda x: x['start_time'])
    
    # Match transcript lines to diarization segments with improved algorithm
    matched_segments = []
    for segment in segments:
        segment_start = segment.get('start_time', 0)
        segment_end = segment.get('end_time', 0)
        speaker = segment.get('speaker', 'UNKNOWN')
        
        # Find matching transcript lines based on timestamp overlap
        matching_texts = []
        
        # Use a more flexible matching approach with tolerance
        time_tolerance = 1.5  # Increased tolerance for timestamp matching
        
        # First pass: Look for direct overlaps with standard tolerance
        for line in transcript_lines:
            # Check for significant overlap between segment and transcript line
            # A line matches if either:
            # 1. It overlaps with the segment by at least 50% of the line duration
            # 2. It's completely contained within the segment
            # 3. It contains the segment completely
            # 4. The segment start or end is within the line with tolerance
            
            line_duration = line['end_time'] - line['start_time']
            segment_duration = segment_end - segment_start
            
            # Calculate overlap
            overlap_start = max(segment_start, line['start_time'])
            overlap_end = min(segment_end, line['end_time'])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            # Check if there's significant overlap
            significant_overlap = (
                (overlap_duration > 0.5 * line_duration) or  # >50% of line overlaps
                (line['start_time'] >= segment_start - time_tolerance and line['end_time'] <= segment_end + time_tolerance) or  # Line within segment (with tolerance)
                (segment_start >= line['start_time'] - time_tolerance and segment_end <= line['end_time'] + time_tolerance) or  # Segment within line (with tolerance)
                (abs(segment_start - line['start_time']) < time_tolerance) or  # Segment start matches line start (with tolerance)
                (abs(segment_end - line['end_time']) < time_tolerance)  # Segment end matches line end (with tolerance)
            )
            
            if significant_overlap:
                matching_texts.append(line['text'])
        
        # If matching texts found, join them; otherwise try second pass with more relaxed matching
        if matching_texts:
            segment['text'] = ' '.join(matching_texts)
            logger.debug(f"Matched transcript for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
        else:
            # Second pass: Try with even more relaxed matching if no matches found
            for line in transcript_lines:
                # Just check if the line is somewhat close to the segment
                if (abs(line['start_time'] - segment_start) < 5.0 or  # Within 5 seconds of start (increased from 3)
                    abs(line['end_time'] - segment_end) < 5.0 or      # Within 5 seconds of end (increased from 3)
                    (segment_start <= line['start_time'] <= segment_end) or  # Line starts within segment
                    (segment_start <= line['end_time'] <= segment_end) or    # Line ends within segment
                    (line['start_time'] <= segment_start and line['end_time'] >= segment_end)):  # Segment fully contained in line
                    matching_texts.append(line['text'])
            
            if matching_texts:
                segment['text'] = ' '.join(matching_texts)
                logger.debug(f"Matched transcript in second pass for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
            else:
                # Third pass: If still no match, try to find the closest transcript line by timestamp
                closest_line = None
                min_distance = float('inf')
                
                for line in transcript_lines:
                    # Calculate distance between segment midpoint and line midpoint
                    segment_mid = (segment_start + segment_end) / 2
                    line_mid = (line['start_time'] + line['end_time']) / 2
                    distance = abs(segment_mid - line_mid)
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_line = line
                
                # Use the closest line if it's within a reasonable distance (10 seconds)
                if closest_line and min_distance < 10.0:
                    segment['text'] = closest_line['text']
                    logger.debug(f"Matched transcript in third pass (closest) for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
                else:
                    segment['text'] = f"Speech segment from {speaker}"
                    logger.debug(f"No transcript match for segment {segment_start:.2f}-{segment_end:.2f} (speaker {speaker})")
                    
                    # Log detailed information about the segment for debugging
                    logger.debug(f"Segment details: start={segment_start}, end={segment_end}, duration={segment_end-segment_start}")
                    if transcript_lines:
                        logger.debug(f"First transcript line: start={transcript_lines[0]['start_time']}, end={transcript_lines[0]['end_time']}")
                        logger.debug(f"Last transcript line: start={transcript_lines[-1]['start_time']}, end={transcript_lines[-1]['end_time']}")
                    else:
                        logger.debug("No transcript lines available")

        
        matched_segments.append(segment)
    
    # Log statistics
    placeholder_count = sum(1 for s in matched_segments if s['text'].startswith("Speech segment from"))
    match_count = len(matched_segments) - placeholder_count
    match_percentage = (match_count / len(matched_segments) * 100) if matched_segments else 0
    
    logger.info(f"Transcript matching complete: {match_count}/{len(matched_segments)} segments matched ({match_percentage:.1f}%)")
    
    return matched_segments
