#!/usr/bin/env python3
"""
Update Speech Groups in Parliament Clips Database

This script updates existing records in the parliament_clips SQLite database
to assign speech group IDs to clips that don't have them yet.

It uses speaker diarization data when available to create more accurate speech groups.
When diarization data is not available, it falls back to using temporal proximity.
"""

import os
import sys
import json
import sqlite3
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

def find_diarization_file(video_path: Path) -> Optional[Path]:
    """Find the diarization JSON file for a given video path.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Path to the diarization file if found, None otherwise
    """
    # Convert to string for easier handling
    video_path_str = str(video_path)
    
    # Extract video ID from path using multiple methods
    video_ids = []
    
    # Method 1: Extract from basename with underscore pattern (e.g., 803_video.mp4 -> 803)
    video_basename = os.path.basename(video_path_str)
    if '_' in video_basename:
        video_ids.append(video_basename.split('_')[0])
    
    # Method 2: Extract from basename without extension (e.g., 803.mp4 -> 803)
    video_ids.append(os.path.splitext(video_basename)[0])
    
    # Method 3: Try to find any numeric sequence in the filename
    import re
    numeric_matches = re.findall(r'\d+', video_basename)
    video_ids.extend(numeric_matches)
    
    # Method 4: Extract from the full path
    path_parts = video_path_str.split(os.path.sep)
    for part in path_parts:
        if part.isdigit():
            video_ids.append(part)
    
    # Remove duplicates and empty strings
    video_ids = list(set([vid for vid in video_ids if vid]))
    
    logger.info(f"Extracted possible video IDs: {video_ids} from path: {video_path}")
    
    # Base directory for local paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Common locations for diarization files
    possible_paths = []
    
    # Path patterns based on video path
    video_path_without_ext = os.path.splitext(video_path_str)[0]
    possible_paths.extend([
        Path(video_path_without_ext + ".diarization.json"),
        Path(video_path_without_ext + "_diarization.json"),
        Path(video_path_without_ext + "_speakers.json"),
        Path(os.path.join(os.path.dirname(video_path_without_ext), "diarization_" + os.path.basename(video_path_without_ext) + ".json")),
    ])
    
    # Common directory patterns
    search_dirs = [
        "/app/data/temp/audio_extracts",
        "/app/data/temp",
        "/app/data/media",
        os.path.join(base_dir, "data/temp/audio_extracts"),
        os.path.join(base_dir, "data/temp"),
        os.path.join(base_dir, "data/media"),
        # Add more common directories
        "/app/backend/data/temp",
        os.path.join(base_dir, "backend/data/temp"),
        os.path.join(os.path.dirname(video_path_str), "diarization"),
        os.path.dirname(video_path_str),  # Check in the same directory as the video
    ]
    
    # For each video ID, generate possible file paths
    for video_id in video_ids:
        # Docker paths
        possible_paths.extend([
            Path(f"/app/data/media/{video_id}.diarization.json"),
            Path(f"/app/data/temp/{video_id}.diarization.json"),
            Path(f"/app/data/temp/audio_extracts/{video_id}.diarization.json"),
            Path(f"/app/data/temp/audio_extracts/diarization_{video_id}.json"),
            Path(f"/app/data/temp/audio_extracts/{video_id}_diarization.json"),
            Path(f"/app/data/temp/audio_extracts/{video_id}_speakers.json"),
            Path(f"/app/data/temp/{video_id}_speakers.json"),
            Path(f"/app/data/temp/audio_extracts/{video_id}.audio_diarization.json"),
        ])
        
        # Local paths
        possible_paths.extend([
            Path(os.path.join(base_dir, f"data/media/{video_id}.diarization.json")),
            Path(os.path.join(base_dir, f"data/temp/{video_id}.diarization.json")),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/{video_id}.diarization.json")),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/diarization_{video_id}.json")),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/{video_id}_diarization.json")),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/{video_id}_speakers.json")),
            Path(os.path.join(base_dir, f"data/temp/{video_id}_speakers.json")),
            Path(os.path.join(base_dir, f"data/temp/audio_extracts/{video_id}.audio_diarization.json")),
        ])
        
        # Try with numeric video ID variations (in case it's stored with leading zeros)
        try:
            numeric_id = int(video_id)
            # Try with different zero-padding
            for padding in [0, 2, 3, 4]:
                padded_id = f"{numeric_id:0{padding}d}" if padding > 0 else str(numeric_id)
                possible_paths.extend([
                    Path(f"/app/data/temp/audio_extracts/{padded_id}.diarization.json"),
                    Path(f"/app/data/temp/audio_extracts/diarization_{padded_id}.json"),
                    Path(os.path.join(base_dir, f"data/temp/audio_extracts/{padded_id}.diarization.json")),
                    Path(os.path.join(base_dir, f"data/temp/audio_extracts/diarization_{padded_id}.json")),
                ])
        except ValueError:
            pass  # Not a numeric ID, skip these paths
    
    # Check if any of the possible paths exist
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found diarization file: {path}")
            return path
    
    # If no file found, search in common directories for any file containing any of the video_ids
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            logger.info(f"Searching for diarization files in {search_dir}")
            try:
                for file in os.listdir(search_dir):
                    if file.endswith(".json") and ("diarization" in file.lower() or "speaker" in file.lower()):
                        # Check if any of our video IDs are in the filename
                        for video_id in video_ids:
                            if video_id in file:
                                path = Path(os.path.join(search_dir, file))
                                logger.info(f"Found potential diarization file: {path}")
                                return path
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"Error accessing directory {search_dir}: {e}")
    
    # Last resort: search for any JSON file with "diarization" or "speaker" in the name
    # in the same directory as the video
    video_dir = os.path.dirname(video_path_str)
    if os.path.exists(video_dir):
        try:
            json_files = [f for f in os.listdir(video_dir) if f.endswith(".json") and 
                         ("diarization" in f.lower() or "speaker" in f.lower())]
            
            if json_files:
                # Sort by modification time (newest first)
                json_files.sort(key=lambda x: os.path.getmtime(os.path.join(video_dir, x)), reverse=True)
                newest_file = json_files[0]
                path = Path(os.path.join(video_dir, newest_file))
                logger.info(f"Found newest diarization file in video directory: {path}")
                return path
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Error accessing video directory {video_dir}: {e}")
    
    logger.warning(f"No diarization file found for video {video_path}")
    logger.debug(f"Checked paths: {possible_paths[:10]}... and {len(possible_paths)-10} more")
    return None


def load_diarization_data(diarization_file: Path) -> Optional[Dict]:
    """
    Load speaker diarization data from a JSON file.
    
    Args:
        diarization_file: Path to the diarization JSON file
        
    Returns:
        Dict with diarization data if successful, None otherwise
    """
    try:
        with open(diarization_file, 'r') as f:
            data = json.load(f)
        
        # Validate that this is a diarization file
        if 'segments' in data and isinstance(data['segments'], list):
            segments = data['segments']
            logger.info(f"Successfully loaded diarization data with {len(segments)} segments")
            
            # Check if segments have the expected structure
            if segments:
                # Count segments with speaker information
                speakers_count = sum(1 for seg in segments if 'speaker' in seg)
                if speakers_count == 0:
                    logger.warning(f"No speaker information found in any of the {len(segments)} segments")
                    
                    # Try to find speaker information in alternative fields
                    alternative_fields = ['speaker_id', 'speakerId', 'speaker_label', 'label']
                    for field in alternative_fields:
                        if any(field in seg for seg in segments):
                            logger.info(f"Found alternative speaker field: '{field}', converting to 'speaker'")
                            # Convert to standard format
                            for seg in segments:
                                if field in seg:
                                    seg['speaker'] = seg[field]
                            break
                
                # Check for required timing information
                timing_fields = [('start_time', 'end_time'), ('start', 'end')]
                has_timing = False
                
                for start_field, end_field in timing_fields:
                    if all(start_field in seg and end_field in seg for seg in segments[:5]):
                        has_timing = True
                        # If using alternative field names, standardize them
                        if start_field != 'start_time' or end_field != 'end_time':
                            logger.info(f"Converting timing fields from {start_field}/{end_field} to start_time/end_time")
                            for seg in segments:
                                if start_field in seg:
                                    seg['start_time'] = seg[start_field]
                                if end_field in seg:
                                    seg['end_time'] = seg[end_field]
                        break
                
                if not has_timing:
                    logger.warning("Segments missing required timing information")
                    return None
                
                # Log summary of speakers found
                speakers = set(seg.get('speaker', '') for seg in segments if 'speaker' in seg)
                logger.info(f"Found {len(speakers)} unique speakers in diarization data: {speakers}")
                
                return data
            else:
                logger.warning("Diarization file contains empty segments list")
                return None
        elif 'diarization' in data and isinstance(data['diarization'], dict) and 'segments' in data['diarization']:
            # Handle nested structure
            logger.info("Found nested diarization data structure, extracting segments")
            nested_data = {'segments': data['diarization']['segments']}
            return load_diarization_data(nested_data)  # Recursively process the extracted data
        else:
            # Try to find any array that might contain speaker segments
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check if items look like speaker segments
                    if all(isinstance(item, dict) for item in value[:5]):
                        sample_items = value[:5]
                        # Check if they have timing and speaker info
                        has_timing = any(('start_time' in item or 'start' in item) and 
                                        ('end_time' in item or 'end' in item) for item in sample_items)
                        has_speaker = any('speaker' in item or 'speaker_id' in item or 'label' in item 
                                        for item in sample_items)
                        
                        if has_timing and has_speaker:
                            logger.info(f"Found potential segments under key '{key}', attempting to use")
                            # Create a standardized structure
                            standardized_data = {'segments': value}
                            return load_diarization_data(standardized_data)  # Recursively process
            
            logger.warning(f"File {diarization_file} does not appear to be a valid diarization file")
            logger.debug(f"File content keys: {list(data.keys())}")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in diarization file {diarization_file}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading diarization file {diarization_file}: {e}")
        logger.exception(e)
        return None


def create_speech_blocks_from_diarization(clips: List[Tuple], diarization_data: Dict) -> Tuple[List[List[Tuple]], Dict]:
    """
    Create speech blocks based on diarization data.
    
    Args:
        clips: List of clips (id, member_id, start_timestamp, end_timestamp)
        diarization_data: Dict with diarization data
        
    Returns:
        Tuple containing:
            - List of speech blocks, where each block is a list of clips
            - Dictionary mapping clip IDs to speaker labels
    """
    # Extract diarization segments
    diarization_segments = diarization_data.get('segments', [])
    if not diarization_segments:
        logger.warning("No diarization segments found in diarization data")
        # Return empty lists in the expected tuple format
        return [], {}
    
    # Log diarization data summary
    num_segments = len(diarization_segments)
    speakers = set(segment.get('speaker', '') for segment in diarization_segments)
    num_speakers = len(speakers)
    logger.info(f"Diarization data contains {num_segments} segments from {num_speakers} distinct speakers")
    logger.debug(f"Speaker IDs: {speakers}")
    
    # Sort clips by start time for easier matching
    sorted_clips = sorted(clips, key=lambda c: float(c[2]) if c[2] else 0)
    
    # First, assign each clip to a speaker based on diarization data
    clip_speaker_map = {}
    unassigned_clips = []
    
    for clip in sorted_clips:
        clip_id, member_id, start_timestamp, end_timestamp = clip
        clip_start = float(start_timestamp) if start_timestamp else 0
        clip_end = float(end_timestamp) if end_timestamp else clip_start + 1
        clip_duration = clip_end - clip_start
        
        # Find the diarization segment that contains this clip
        matching_segment = None
        best_overlap = 0
        
        for segment in diarization_segments:
            segment_start = segment.get('start_time', 0)
            segment_end = segment.get('end_time', 0)
            
            # Check if clip overlaps with this segment
            overlap_start = max(clip_start, segment_start)
            overlap_end = min(clip_end, segment_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            overlap_percentage = overlap_duration / clip_duration if clip_duration > 0 else 0
            
            # Keep track of the segment with the best overlap
            if overlap_percentage > best_overlap:
                best_overlap = overlap_percentage
                matching_segment = segment
        
        # A clip is considered part of a segment if it overlaps by at least 30%
        # (reduced from 50% to catch more clips)
        if matching_segment and best_overlap >= 0.3:
            segment_speaker = matching_segment.get('speaker', '')
            clip_speaker_map[clip_id] = segment_speaker
            logger.debug(f"Clip {clip_id} ({clip_start:.2f}-{clip_end:.2f}) assigned to speaker {segment_speaker} with {best_overlap:.1%} overlap")
        else:
            # No matching segment found with sufficient overlap
            clip_speaker_map[clip_id] = None
            unassigned_clips.append(clip)
            logger.debug(f"Clip {clip_id} ({clip_start:.2f}-{clip_end:.2f}) could not be assigned to any speaker (best overlap: {best_overlap:.1%})")
    
    # Log assignment statistics
    assigned_count = len(clip_speaker_map) - len(unassigned_clips)
    total_count = len(sorted_clips)
    logger.info(f"Assigned {assigned_count}/{total_count} clips to speakers ({assigned_count/total_count:.1%})")
    
    if unassigned_clips:
        logger.warning(f"Could not assign {len(unassigned_clips)} clips to any speaker")
    
    # Group clips by speaker
    speaker_clips = {}
    for clip in sorted_clips:
        clip_id = clip[0]
        speaker = clip_speaker_map.get(clip_id)
        if speaker not in speaker_clips:
            speaker_clips[speaker] = []
        speaker_clips[speaker].append(clip)
    
    # Create speech blocks from speaker groups
    speech_blocks = []
    
    # Process clips with identified speakers first
    for speaker, speaker_group in speaker_clips.items():
        if speaker is not None and speaker != '':
            # For clips with a speaker, keep them in one group
            # Sort clips within the speaker group by timestamp
            sorted_speaker_group = sorted(speaker_group, key=lambda c: float(c[2]) if c[2] else 0)
            if sorted_speaker_group:
                speech_blocks.append(sorted_speaker_group)
    
    # Then process unassigned clips using temporal proximity
    if None in speaker_clips:
        unassigned_group = speaker_clips[None]
        temp_blocks = []
        current_block = []
        
        for clip in sorted(unassigned_group, key=lambda c: float(c[2]) if c[2] else 0):
            if not current_block:
                current_block = [clip]
            else:
                prev_clip = current_block[-1]
                prev_end = float(prev_clip[3]) if prev_clip[3] else float(prev_clip[2]) + 1
                clip_start = float(clip[2]) if clip[2] else 0
                
                # Use temporal proximity
                MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds
                if clip_start - prev_end <= MAX_CONTINUOUS_SPEECH_GAP:
                    current_block.append(clip)
                else:
                    temp_blocks.append(current_block)
                    current_block = [clip]
        
        if current_block:
            temp_blocks.append(current_block)
        
        speech_blocks.extend(temp_blocks)
    
    # Sort speech blocks by the start time of their first clip
    speech_blocks.sort(key=lambda block: float(block[0][2]) if block[0][2] else 0)
    
    logger.info(f"Created {len(speech_blocks)} speech blocks based on speaker changes in diarization data")
    
    # Ensure we're not creating too many blocks
    if len(speech_blocks) > num_speakers * 2 and num_speakers > 0:
        logger.warning(f"Created many more speech blocks ({len(speech_blocks)}) than speakers ({num_speakers}). This may indicate a problem with grouping.")
    
    # Debug info
    for i, block in enumerate(speech_blocks[:5]):  # Log only first 5 blocks to avoid excessive logging
        first_clip = block[0]
        last_clip = block[-1]
        first_start = float(first_clip[2]) if first_clip[2] else 0
        last_end = float(last_clip[3]) if last_clip[3] else 0
        speaker = clip_speaker_map.get(first_clip[0])
        logger.info(f"Speech block {i}: {len(block)} clips, {first_start:.2f}-{last_end:.2f}, speaker: {speaker}")
    
    if len(speech_blocks) > 5:
        logger.info(f"... and {len(speech_blocks) - 5} more speech blocks")
    
    return speech_blocks, clip_speaker_map


def create_speech_blocks_by_proximity(clips: List[Tuple]) -> List[List[Tuple]]:
    """
    Create speech blocks based on temporal proximity only.
    
    Args:
        clips: List of clips (id, member_id, start_timestamp, end_timestamp)
        
    Returns:
        List of speech blocks, where each block is a list of clips
    """
    MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds max gap between segments
    
    # Sort clips by start time
    sorted_clips = sorted(clips, key=lambda c: float(c[2]) if c[2] else 0)
    
    current_block = []
    speech_blocks = []
    
    for clip in sorted_clips:
        clip_id, member_id, start_timestamp, end_timestamp = clip
        
        # Convert timestamps to float for comparison
        start_time = float(start_timestamp) if start_timestamp else 0
        
        if not current_block:
            current_block = [clip]
        else:
            # Check time proximity only
            prev_clip = current_block[-1]
            prev_end_time = float(prev_clip[3]) if prev_clip[3] else float(prev_clip[2]) + 1
            
            if start_time - prev_end_time <= MAX_CONTINUOUS_SPEECH_GAP:
                # Continuous speech (regardless of member_id)
                current_block.append(clip)
            else:
                # Gap too large, start a new block
                speech_blocks.append(current_block)
                current_block = [clip]
    
    # Add the last block
    if current_block:
        speech_blocks.append(current_block)
    
    logger.info(f"Created {len(speech_blocks)} speech blocks based on temporal proximity")
    return speech_blocks


def update_speech_groups(video_id=None, debug=False, force=False):
    """
    Update speech group IDs for clips in the parliament_clips table.
    
    Args:
        video_id: Optional ID of the video to update. If None, update all videos.
        debug: Whether to enable debug logging
        force: Whether to force update speech groups even if already assigned
    
    Returns:
        Dict with results of the operation
    """
    # Set up logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"Updating speech groups for video_id={video_id}, debug={debug}, force={force}")
    
    # Connect to the database
    conn = None
    try:
        # Try multiple possible paths for the database
        possible_db_paths = [
            "/app/backend/parliament_clips.db",  # Docker container path
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/parliament_clips.db"),  # Local dev path
            "./backend/parliament_clips.db"  # Relative path
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                logger.info(f"Found database at {db_path}")
                break
                
        if not db_path:
            logger.error(f"Database not found in any of the expected locations: {possible_db_paths}")
            return {"success": False, "error": f"Database not found in any of the expected locations: {possible_db_paths}"}
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the speech_group_id column exists
        cursor.execute("PRAGMA table_info(parliament_clips)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'speech_group_id' not in columns:
            logger.info("Adding speech_group_id column to parliament_clips table")
            cursor.execute("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
            conn.commit()
        
        # If force flag is provided, clear existing speech group IDs for the specified video
        if force and video_id:
            # Clear speech group IDs for the specified video
            cursor.execute(
                "UPDATE parliament_clips SET speech_group_id = NULL WHERE full_video_path LIKE ?",
                (f"%{video_id}%",)
            )
            conn.commit()
            affected_rows = cursor.rowcount
            logger.info(f"Cleared speech group IDs for {affected_rows} clips with video ID {video_id}")
        
        # Get all videos that need updating
        if video_id:
            cursor.execute("SELECT DISTINCT full_video_path FROM parliament_clips WHERE full_video_path LIKE ? AND (speech_group_id IS NULL OR speech_group_id = '')",
                          (f"%{video_id}%",))
        else:
            cursor.execute("SELECT DISTINCT full_video_path FROM parliament_clips WHERE speech_group_id IS NULL OR speech_group_id = ''")
        
        video_paths = cursor.fetchall()
        logger.info(f"Found {len(video_paths)} videos that need speech group updates")
        
        total_updated = 0
        diarization_used = 0
        
        for (video_path,) in video_paths:
            # Extract video ID from path if possible
            try:
                # Try to extract numeric video ID from the path
                filename = os.path.basename(video_path)
                # First try with underscore pattern (e.g., 803_video.mp4)
                if '_' in filename:
                    path_video_id = int(filename.split('_')[0])
                # Then try with just the filename (e.g., 803.mp4)
                else:
                    path_video_id = int(filename.split('.')[0])
                logger.info(f"Extracted video ID: {path_video_id} from path: {video_path}")
            except (ValueError, IndexError):
                path_video_id = hash(video_path) % 10000  # Use a hash if we can't extract an ID
                logger.warning(f"Could not extract video ID from path: {video_path}, using hash: {path_video_id}")
            
            # Get all clips for this video, ordered by start_timestamp
            cursor.execute("""
                SELECT id, member_id, start_timestamp, end_timestamp 
                FROM parliament_clips 
                WHERE full_video_path = ? 
                ORDER BY CAST(start_timestamp AS REAL)
            """, (video_path,))
            
            clips = cursor.fetchall()
            logger.info(f"Found {len(clips)} clips for video path {video_path}")
            
            # Try to find and load diarization data
            diarization_file = find_diarization_file(video_path)
            speech_blocks = []
            
            if diarization_file:
                diarization_data = load_diarization_data(diarization_file)
                if diarization_data:
                    # Create speech blocks based on diarization data
                    speech_blocks, clip_speaker_map = create_speech_blocks_from_diarization(clips, diarization_data)
                    diarization_used += 1
                    logger.info(f"Using diarization data to create speech groups for {video_path}")
                    
                    # Validate that we have the expected number of speech blocks
                    num_speakers = len(set(segment.get('speaker', '') for segment in diarization_data.get('segments', [])))
                    if num_speakers > 0 and len(speech_blocks) != num_speakers:
                        logger.warning(f"Expected {num_speakers} speech blocks (one per speaker), but created {len(speech_blocks)}. This may indicate a problem with grouping.")
                    
                    # Debug: Print clip to speaker assignments if debug mode is enabled
                    if debug:
                        logger.debug(f"Clip to speaker assignments for {video_path}:")
                        for clip_id, speaker in clip_speaker_map.items():
                            cursor.execute("SELECT start_timestamp, end_timestamp FROM parliament_clips WHERE id = ?", (clip_id,))
                            clip_info = cursor.fetchone()
                            if clip_info:
                                start_time, end_time = clip_info
                                logger.debug(f"  Clip {clip_id} ({start_time}-{end_time}): Speaker {speaker}")
                            else:
                                logger.debug(f"  Clip {clip_id}: Speaker {speaker}")
                    
            
            # If no diarization data or blocks couldn't be created, fall back to temporal proximity
            if not speech_blocks:
                logger.info(f"Falling back to temporal proximity for {video_path}")
                speech_blocks = create_speech_blocks_by_proximity(clips)
            
            logger.info(f"Grouped {len(clips)} clips into {len(speech_blocks)} speech blocks")
            
            # Verify that each speech block has at least one clip
            empty_blocks = [i for i, block in enumerate(speech_blocks) if not block]
            if empty_blocks:
                logger.warning(f"Found {len(empty_blocks)} empty speech blocks: {empty_blocks}")
                # Remove empty blocks
                speech_blocks = [block for block in speech_blocks if block]
            
            # Update speech_group_id for each speech block
            block_updates = 0
            for block_idx, block in enumerate(speech_blocks):
                if not block:  # Skip empty blocks
                    continue
                    
                # Generate a unique speech group ID
                first_clip = block[0]
                first_start_time = float(first_clip[2]) if first_clip[2] else 0
                speech_group_id = f"speech_group_{path_video_id}_{block_idx}_{int(first_start_time)}"
                
                # Update all clips in this block
                for clip in block:
                    clip_id = clip[0]
                    cursor.execute(
                        "UPDATE parliament_clips SET speech_group_id = ? WHERE id = ?",
                        (speech_group_id, clip_id)
                    )
                    block_updates += 1
            
            conn.commit()
            logger.info(f"Updated {block_updates} clips with speech group IDs for video {video_path}")
            total_updated += block_updates
        
        # Verify updates
        cursor.execute("SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id IS NOT NULL")
        non_null_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM parliament_clips")
        total_count = cursor.fetchone()[0]
        
        if total_count > 0:
            coverage_percentage = (non_null_count / total_count) * 100
            logger.info(f"Total clips with speech_group_id: {non_null_count}/{total_count} ({coverage_percentage:.1f}%)")
        else:
            logger.info(f"No clips found in the database")
        
        return {
            "success": True,
            "total_updated": total_updated,
            "videos_processed": len(video_paths),
            "diarization_used": diarization_used,
            "clips_with_speech_group": non_null_count,
            "total_clips": total_count
        }
        
    except Exception as e:
        logger.error(f"Error updating speech groups: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if conn:
            conn.close()

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update speech group IDs in parliament_clips database')
    parser.add_argument('--video-id', type=str, help='Optional video ID to update')
    parser.add_argument('--force', action='store_true', help='Force update of speech groups even if already assigned')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Find the database path
    possible_db_paths = [
        "/app/backend/parliament_clips.db",  # Docker container path
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend/parliament_clips.db"),  # Local dev path
        "./backend/parliament_clips.db"  # Relative path
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            logger.info(f"Found database at {db_path}")
            break
            
    if not db_path:
        logger.error(f"Database not found in any of the expected locations: {possible_db_paths}")
        return
    
    # Connect to the database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current state of speech group IDs before any changes
        if args.video_id:
            cursor.execute(
                "SELECT COUNT(*) FROM parliament_clips WHERE full_video_path LIKE ?", 
                (f"%{args.video_id}%",)
            )
            total_clips = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT DISTINCT speech_group_id FROM parliament_clips WHERE full_video_path LIKE ?", 
                (f"%{args.video_id}%",)
            )
            current_groups = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Before update: Found {total_clips} clips with video ID {args.video_id}")
            logger.info(f"Current speech group IDs: {current_groups}")
            
            # Check if all clips have the same temporary speech group ID
            if len(current_groups) == 1 and current_groups[0] and current_groups[0].startswith("temp_speech_group_"):
                logger.warning(f"All clips have the same temporary speech group ID: {current_groups[0]}")
        
        # The force flag handling is now moved to the update_speech_groups function
        
        # Close the connection before calling update_speech_groups
        conn.close()
        
        # Run the update process
        logger.info(f"Starting speech group update for video_id={args.video_id}, debug={args.debug}, force={args.force}")
        result = update_speech_groups(args.video_id, args.debug, args.force)
        
        if result["success"]:
            logger.info(f"Successfully updated {result['total_updated']} clips in {result['videos_processed']} videos")
            logger.info(f"Used diarization data for {result['diarization_used']} videos")
            
            # Reconnect to verify the results
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if args.video_id:
                # Check the updated speech group IDs
                cursor.execute(
                    "SELECT DISTINCT speech_group_id FROM parliament_clips WHERE full_video_path LIKE ?", 
                    (f"%{args.video_id}%",)
                )
                updated_groups = [row[0] for row in cursor.fetchall()]
                
                # Count clips per speech group
                cursor.execute(
                    "SELECT speech_group_id, COUNT(*) FROM parliament_clips WHERE full_video_path LIKE ? GROUP BY speech_group_id", 
                    (f"%{args.video_id}%",)
                )
                group_counts = cursor.fetchall()
                
                logger.info(f"After update: Speech group IDs: {updated_groups}")
                logger.info(f"Clips per speech group:")
                for group_id, count in group_counts:
                    logger.info(f"  {group_id}: {count} clips")
                
                # Check if we still have temporary speech group IDs
                temp_groups = [g for g in updated_groups if g and g.startswith("temp_speech_group_")]
                if temp_groups:
                    logger.warning(f"Still have {len(temp_groups)} temporary speech group IDs after update: {temp_groups}")
                    logger.warning("This may indicate that diarization data was not found or could not be used")
            
            conn.close()
            
            if result['total_clips'] > 0:
                coverage_percentage = (result['clips_with_speech_group'] / result['total_clips']) * 100
                logger.info(f"Speech group coverage: {result['clips_with_speech_group']}/{result['total_clips']} clips ({coverage_percentage:.1f}%)")
            else:
                logger.info("No clips found in the database")
        else:
            logger.error(f"Failed to update speech groups: {result['error']}")
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        logger.exception(e)

if __name__ == "__main__":
    main()
