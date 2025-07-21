"""
Enhanced member clips processing for Parliament TV
This module provides functions to create member clips from recognition results,
including support for unidentified speakers.
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.db.models import ParliamentTranscription
from backend.services.integration.supabase_client import SupabaseService
from backend.services.integration.supabase_upload import SupabaseUploader
from backend.services.utils import make_json_serializable

logger = logging.getLogger(__name__)


def normalize_speaker_ids(segments):
    """
    Ensure consistent speaker attribution across continuous speech segments.
    
    For segments that are close together in time (likely part of the same continuous speech),
    use the speaker ID with the highest confidence score for all segments in that continuous block.
    
    Args:
        segments: List of speaker segments
        
    Returns:
        Tuple of (normalized_segments, speech_groups) where:
        - normalized_segments is a list of segments with normalized speaker IDs
        - speech_groups is a list of dicts with speech group information for database updates
    """
    if not segments:
        return [], []
        
    # Sort segments by start time
    sorted_segments = sorted(segments, key=lambda x: x["start_time"])
    
    # Define what constitutes a continuous speech block (max gap in seconds)
    MAX_CONTINUOUS_SPEECH_GAP = 1.5  # 1.5 seconds max gap between segments to be considered continuous
    
    # Identify continuous speech blocks
    speech_blocks = []
    current_block = [sorted_segments[0]]
    
    for i in range(1, len(sorted_segments)):
        current_segment = sorted_segments[i]
        previous_segment = sorted_segments[i-1]
        
        # If this segment starts soon after the previous one ends, add it to the current block
        if current_segment["start_time"] - previous_segment["end_time"] <= MAX_CONTINUOUS_SPEECH_GAP:
            current_block.append(current_segment)
        else:
            # This segment is not continuous with the previous one, start a new block
            speech_blocks.append(current_block)
            current_block = [current_segment]
    
    # Add the last block
    if current_block:
        speech_blocks.append(current_block)
        
    # For each continuous speech block, find the segment with highest confidence
    # and use its speaker_id for all segments in the block
    normalized_segments = []
    speech_groups = []
    
    for block_idx, block in enumerate(speech_blocks):
        # Generate a unique speech group ID
        speech_group_id = f"speech_group_{block_idx}_{int(block[0]['start_time'])}"
        
        # Find the segment with the highest confidence in this block
        # IMPORTANT: Prioritize numeric member IDs (like 4621) over UUIDs or generic speaker IDs
        # This ensures we use the real member IDs from facial recognition when available
        
        # First, check if any segment has a numeric member_id (from facial recognition)
        numeric_id_segments = [seg for seg in block if "member_id" in seg and isinstance(seg.get("member_id"), (int, float, str)) 
                              and str(seg.get("member_id")).isdigit()]
        
        if numeric_id_segments:
            # If we have segments with numeric member IDs, find the one with highest confidence
            highest_conf_segment = max(numeric_id_segments, key=lambda x: x.get("confidence", 0))
            highest_conf = highest_conf_segment.get("confidence", 0)
            
            # Use the member_id as the speaker_id for normalization
            highest_conf_speaker_id = str(highest_conf_segment["member_id"])
            logger.info(f"Using numeric member_id {highest_conf_speaker_id} with confidence {highest_conf} for speech group")
        else:
            # Fall back to using the highest confidence segment's speaker_id
            highest_conf_segment = max(block, key=lambda x: x.get("confidence", 0))
            highest_conf_speaker_id = highest_conf_segment["speaker_id"]
            highest_conf = highest_conf_segment.get("confidence", 0)
            logger.info(f"No numeric member_id found, using speaker_id {highest_conf_speaker_id} with confidence {highest_conf}")
        
        # Log what we're doing
        if len(block) > 1:
            logger.info(f"Normalizing speaker IDs for continuous speech block with {len(block)} segments")
            logger.info(f"Using ID {highest_conf_speaker_id} with confidence {highest_conf}")
        
        # Store information about this speech group for database updates
        segment_ids = []
        
        # Apply the highest confidence speaker_id to all segments in this block
        for segment in block:
            # Store the original segment ID for database updates
            # Check for different possible ID fields based on the database schema
            segment_id = None
            if "id" in segment:
                segment_id = segment["id"]
                logger.info(f"Found segment ID: {segment_id} from 'id' field")
            elif "segment_id" in segment:
                segment_id = segment["segment_id"]
                logger.info(f"Found segment ID: {segment_id} from 'segment_id' field")
            elif "db_id" in segment:
                segment_id = segment["db_id"]
                logger.info(f"Found segment ID: {segment_id} from 'db_id' field")
            
            if segment_id is not None:
                segment_ids.append(segment_id)
                
            # Update the speaker ID in memory
            if segment["speaker_id"] != highest_conf_speaker_id:
                logger.info(f"Changing speaker_id from {segment['speaker_id']} to {highest_conf_speaker_id} based on confidence")
                segment["speaker_id"] = highest_conf_speaker_id
                
            # Make sure member_id is also set to match the speaker_id for consistency
            # This ensures that when the database is updated, it uses the correct member ID
            if "member_id" in segment and str(segment["member_id"]) != highest_conf_speaker_id:
                logger.info(f"Updating member_id from {segment['member_id']} to {highest_conf_speaker_id} for consistency")
                segment["member_id"] = highest_conf_speaker_id
                
            # Add speech_group_id to the segment
            segment["speech_group_id"] = speech_group_id
            normalized_segments.append(segment)
        
        # Add this speech group to our list for database updates
        speech_groups.append({
            "speech_group_id": speech_group_id,
            "segment_ids": segment_ids,
            "speaker_id": highest_conf_speaker_id,
            "member_id": highest_conf_speaker_id,  # Ensure member_id is also set correctly
            "confidence": highest_conf,
            "start_time": block[0]["start_time"],
            "end_time": block[-1]["end_time"]
        })
    
    return normalized_segments, speech_groups


def update_sqlite_with_normalized_speakers(db, video_id, speech_groups, member_id_mapping):
    """
    Update the SQLite database with normalized speaker IDs.
    
    This function only updates clips that don't already have a valid member_id,
    preserving member IDs from facial recognition while ensuring consistent speaker attribution
    for clips without a valid member_id.
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        speech_groups: List of speech groups with segment IDs and normalized speaker IDs
        member_id_mapping: Dictionary mapping speaker IDs to member IDs
        
    Returns:
        Number of segments updated in the database
    """
    if not speech_groups:
        logger.info("No speech groups to update in database")
        return 0
        
    logger.info(f"Updating SQLite database with {len(speech_groups)} normalized speech groups")
    
    # Determine if we're using SQLite or PostgreSQL
    is_sqlite = False
    try:
        # Try to get the dialect name
        dialect = db.bind.dialect.name
        logger.info(f"Database dialect: {dialect}")
        is_sqlite = dialect == 'sqlite'
    except Exception as e:
        logger.warning(f"Could not determine database dialect: {str(e)}")
        # Try to infer from the connection object
        import sqlite3
        is_sqlite = hasattr(db.connection(), 'connection') and isinstance(db.connection().connection, sqlite3.Connection)
        logger.info(f"Inferred SQLite connection: {is_sqlite}")
    
    # For SQLite, verify that the speech_group_id column exists
    if is_sqlite:
        try:
            # Check if speech_group_id column exists using SQLite syntax
            check_column_sql = text("PRAGMA table_info(parliament_clips)")
            result = db.execute(check_column_sql)
            columns = [row[1] for row in result]
            
            if 'speech_group_id' not in columns:
                # Add the speech_group_id column if it doesn't exist
                logger.info("Adding speech_group_id column to parliament_clips table")
                alter_table_sql = text("ALTER TABLE parliament_clips ADD COLUMN speech_group_id TEXT")
                db.execute(alter_table_sql)
                db.commit()
                logger.info("Successfully added speech_group_id column")
        except Exception as e:
            logger.error(f"Error checking/adding speech_group_id column in SQLite: {str(e)}")
            db.rollback()
            # Continue anyway, as the column might exist but we just failed to check
    else:
        # For PostgreSQL, we don't need to check or modify the parliament_clips table
        # since it's only used in SQLite. This avoids errors when the table doesn't exist.
        logger.info("Skipping PostgreSQL parliament_clips table check - table is only used in SQLite")
        # If we're using PostgreSQL, we're likely not working with parliament clips
        # so we can return early
        if not speech_groups:
            return 0
    
    total_updated = 0
    
    # Initialize a transaction status flag to track if we need to rollback
    transaction_error = False
    
    try:
        # First, query the database to get the actual IDs of clips for this video
        # This ensures we're using the correct database IDs for the update
        db_clips = {}
        
        if is_sqlite:
            # SQLite version using json_extract
            video_clips_sql = text("""
                SELECT id, start_timestamp, end_timestamp 
                FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
            """)
            
            try:
                result = db.execute(video_clips_sql, {"video_id": video_id})
                for row in result:
                    db_id = row[0]  # Database ID
                    start_time = float(row[1]) if row[1] else 0
                    end_time = float(row[2]) if row[2] else 0
                    # Create a key based on timestamps that we can match with our segments
                    db_clips[(start_time, end_time)] = db_id
            except Exception as e:
                logger.error(f"Error querying SQLite database: {str(e)}")
                # Try an alternative approach without json_extract
                try:
                    # Try a LIKE query as a fallback
                    video_clips_sql = text("""
                        SELECT id, start_timestamp, end_timestamp 
                        FROM parliament_clips 
                        WHERE metadata LIKE :pattern
                    """)
                    
                    result = db.execute(video_clips_sql, {"pattern": f"%\"video_id\":{video_id}%"})
                    for row in result:
                        db_id = row[0]  # Database ID
                        start_time = float(row[1]) if row[1] else 0
                        end_time = float(row[2]) if row[2] else 0
                        db_clips[(start_time, end_time)] = db_id
                except Exception as e2:
                    logger.error(f"Error with fallback SQLite query: {str(e2)}")
                    # No need to rollback for SQLite as it auto-commits
        else:
            logger.info("Skipping PostgreSQL parliament_clips queries - table only exists in SQLite")
            # Return early since we can't proceed with PostgreSQL for parliament clips
            return 0
        
        logger.info(f"Found {len(db_clips)} clips in database for video {video_id}")
        
        for speech_group in speech_groups:
            speaker_id = speech_group["speaker_id"]
            
            # Check if this speech group has a member_id already (from facial recognition)
            # This ensures we preserve the original member_id if it exists
            if "member_id" in speech_group and speech_group["member_id"] is not None:
                member_id = speech_group["member_id"]
                logger.info(f"Using existing member_id {member_id} from speech group")
            # Check if the speaker_id is a numeric member ID (from facial recognition)
            # If it is, use it directly instead of looking it up in the mapping
            elif isinstance(speaker_id, str) and speaker_id.isdigit():
                member_id = int(speaker_id)
                logger.info(f"Using numeric speaker_id {speaker_id} directly as member_id {member_id}")
            else:
                member_id = member_id_mapping.get(speaker_id)
                if member_id is not None:
                    logger.info(f"Mapped speaker_id {speaker_id} to member_id {member_id} using mapping")
                else:
                    logger.warning(f"No mapping found for speaker_id {speaker_id}, member_id will be NULL")
            
            speech_group_id = speech_group["speech_group_id"]
            segment_ids = speech_group.get("segment_ids", [])
            
            # Skip if no segment IDs
            if not segment_ids:
                logger.warning(f"No segment IDs for speech group {speech_group_id}, skipping")
                continue
            
            # Format the segment IDs for the SQL query
            segment_ids_str = ", ".join([f"'{id}'" if isinstance(id, str) else str(id) for id in segment_ids if id is not None])
            if not segment_ids_str:
                logger.warning(f"No valid segment IDs for speech group {speech_group_id}, skipping")
                continue
            
            # Log the update operation with detailed information
            if member_id is not None:
                logger.info(f"Updating segments {segment_ids_str} with member_id {member_id} (from speaker_id {speaker_id})")
            
            try:
                # Update SQL statements to set speech_group_id and member_id for segments
                if segment_ids:
                    segment_ids_str = ", ".join([f"'{id}'" for id in segment_ids if id])
                    
                    # Update speech_group_id for all segments in this group
                    update_group_sql = text(f"""UPDATE parliament_clips SET speech_group_id = :speech_group_id WHERE id IN ({segment_ids_str})""")
                    db.execute(update_group_sql, {"speech_group_id": speech_group_id})
                    
                    # Only update member_id for segments that don't already have a valid member_id
                    # This preserves member IDs from facial recognition
                    if member_id is not None:
                        update_member_sql = text(f"""UPDATE parliament_clips SET member_id = :member_id 
                                              WHERE id IN ({segment_ids_str}) 
                                              AND (member_id IS NULL OR member_id = '')""")
                        result = db.execute(update_member_sql, {"member_id": member_id})
                        updated_count = result.rowcount
                        logger.info(f"Updated {updated_count} clips without valid member_ids in speech group {speech_group_id} with member_id {member_id}")
                    
                    if not is_sqlite:
                        db.commit()
                    
                logger.info(f"Updated {updated_count} segments in speech group {speech_group_id} with member_id {member_id}")
                
            except Exception as e:
                logger.error(f"Error updating speech group {speech_group_id}: {str(e)}")
                # Check if this is a transaction abort error
                if "InFailedSqlTransaction" in str(e) or "current transaction is aborted" in str(e):
                    transaction_error = True
                    logger.error("Transaction is aborted, will exit function early")
                    # No point continuing with other speech groups
                    break
                    
                if not is_sqlite:  # PostgreSQL needs explicit rollback
                    try:
                        db.rollback()
                        logger.info(f"Rolled back failed update for speech group {speech_group_id}")
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                        transaction_error = True
                        break
                # Continue with the next speech group
        
        # Check if we had a transaction error
        if transaction_error:
            if not is_sqlite:  # PostgreSQL needs explicit rollback
                try:
                    db.rollback()
                    logger.info("Rolled back all updates due to transaction error")
                except Exception as rollback_error:
                    logger.error(f"Final rollback error: {str(rollback_error)}")
            return 0  # Return 0 updates since we're rolling back
        
        # Final commit for SQLite (PostgreSQL commits after each update)
        if is_sqlite:
            db.commit()
            logger.info(f"Committed all updates for SQLite database")
        
        logger.info(f"Successfully updated {total_updated} segments with normalized speaker IDs")
        
        # Verify updates
        if is_sqlite:
            try:
                # Check how many clips have speech_group_id set
                verify_sql = text("SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id IS NOT NULL")
                result = db.execute(verify_sql)
                with_speech_group = result.scalar() or 0
                
                # Check total clips
                total_sql = text("""
                            SELECT COUNT(*) FROM parliament_clips 
                            WHERE json_extract(metadata, '$.video_id') = :video_id
                        """)
                
                try:
                    result = db.execute(total_sql, {"video_id": video_id})
                    total_clips = result.scalar() or 0
                except Exception as e:
                    # Try a fallback query
                    total_sql = text("""
                            SELECT COUNT(*) FROM parliament_clips 
                            WHERE metadata LIKE :pattern
                        """)
                    result = db.execute(total_sql, {"pattern": f"%\"video_id\":{video_id}%"})
                    total_clips = result.scalar() or 0
                    
                logger.info(f"Verification: {with_speech_group}/{total_clips} clips have speech_group_id set")
                
                # Calculate percentage
                if total_clips > 0:
                    percentage = (with_speech_group / total_clips) * 100
                    logger.info(f"Speech group coverage: {percentage:.1f}%")
            except Exception as e:
                logger.error(f"Error verifying updates: {str(e)}")
        else:
            # Skip verification for PostgreSQL since parliament_clips table doesn't exist there
            logger.info("Skipping verification for PostgreSQL - parliament_clips table only exists in SQLite")
    
    except Exception as e:
        logger.error(f"Error updating database with normalized speakers: {str(e)}")
        if not is_sqlite:  # PostgreSQL needs explicit rollback
            try:
                db.rollback()
                logger.info("Rolled back all updates due to error")
            except Exception as rollback_error:
                logger.error(f"Error during final rollback: {str(rollback_error)}")
    
    return total_updated


def save_member_clips_to_supabase(
    db: Session,
    video_id: int,
    full_video_url: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    supabase_service: Union[SupabaseService, SupabaseUploader],
    video_path: Optional[str] = None,
    audio_path: Optional[str] = None,
    use_diarization: bool = False
) -> Dict[str, Any]:
    """
    Process recognition results and save individual member clips to the Supabase parliament_member_clips table.
    
    This function:
    1. Processes recognition results to identify speaker segments
    2. Merges segments by the same speaker if they are close together (less than 60 seconds apart)
    3. Creates detailed clip metadata including timestamps, transcript segments, and confidence scores
    4. Saves clips to the Supabase parliament_member_clips table
    5. Handles unidentified speakers by assigning temporary IDs
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        full_video_url: URL to the full video in Supabase storage
        recognition_results: Recognition results from facial and voice recognition
        video_metadata: Metadata about the video
        supabase_service: Initialized Supabase service (either SupabaseService or SupabaseUploader) with appropriate permissions
        video_path: Optional path to the video file for diarization
        audio_path: Optional path to the audio file for diarization
        use_diarization: Whether to use speaker diarization to enhance speaker segments
        
    Returns:
        Dictionary with results of the clip saving process
    """
    logger.info(f"Processing member clips for video ID: {video_id}")
    
    # Get session information from metadata
    session_info = {
        "title": video_metadata.get("title", f"Parliament TV Session {video_id}"),
        "date": video_metadata.get("capture_date", datetime.now().isoformat()),
        "description": video_metadata.get("description", ""),
        "original_url": video_metadata.get("original_url", "")
    }
    
    # Apply speaker diarization if enabled and audio path is available
    if use_diarization and audio_path and os.path.exists(audio_path):
        logger.info(f"Using speaker diarization for video ID: {video_id}")
        recognition_results = enhance_segments_with_diarization(
            audio_path=audio_path,
            recognition_results=recognition_results,
            video_path=video_path
        )
        logger.info("Speaker diarization completed")
    elif use_diarization:
        logger.warning(f"Speaker diarization requested but audio path not available or invalid: {audio_path}")
    
    
    # Get transcription data if available
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    transcript_data = None
    if transcription and transcription.output_file and os.path.exists(transcription.output_file):
        try:
            with open(transcription.output_file, 'r') as f:
                transcript_data = json.load(f)
            logger.info(f"Loaded transcription data from {transcription.output_file}")
        except Exception as e:
            logger.error(f"Error loading transcription file: {str(e)}")
    
    # Create a mapping of speaker IDs to proper member IDs from the database
    def get_member_id_mapping(db, speaker_ids):
        """Query the database to get the correct integer member_ids for speaker IDs.
        
        Args:
            db: Database session
            speaker_ids: List of speaker IDs from recognition results
            
        Returns:
            Dictionary mapping speaker IDs to integer member_ids
        """
        # Initialize the mapping
        member_id_mapping = {}
        
        # Skip if no speaker IDs
        if not speaker_ids:
            return member_id_mapping
            
        try:
            # Query the parliament_members table to get the correct member_ids
            # This assumes there's a table that maps between recognition system IDs and database member IDs
            from sqlalchemy import text
            
            # Convert list to tuple for SQL IN clause
            speaker_ids_tuple = tuple(speaker_ids) if len(speaker_ids) > 1 else f"('{speaker_ids[0]}')" 
            
            # Query to get member_id mapping
            query = text(f"""SELECT id, member_id FROM parliament_members 
                          WHERE id IN {speaker_ids_tuple}
                       """)
                       
            result = db.execute(query).fetchall()
            
            # Create the mapping
            for row in result:
                recognition_id = row[0]  # UUID from recognition system
                db_member_id = row[1]    # Integer member_id from database
                member_id_mapping[recognition_id] = db_member_id
                
            logger.info(f"Found {len(member_id_mapping)} member ID mappings in database")
            
        except Exception as e:
            logger.error(f"Error querying member ID mapping: {str(e)}")
            
        return member_id_mapping
    
    # Extract speaker segments from recognition results
    speaker_segments = []
    speaker_ids = []  # Collect all speaker IDs for mapping
    
    # Process identified speakers from facial recognition
    if "identified_speakers" in recognition_results:
        for speaker in recognition_results["identified_speakers"]:
            speaker_id = speaker.get("mp_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id or not speaker_name:
                continue
                
            # Collect speaker ID for mapping
            if speaker_id not in speaker_ids:
                speaker_ids.append(speaker_id)
                
            for segment in speaker.get("segments", []):
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "facial",
                    "transcript": ""
                })
    
    # Process diarized speaker segments if available
    if "diarized_speaker_segments" in recognition_results and recognition_results["diarized_speaker_segments"]:
        logger.info("Processing diarized speaker segments")
        
        # First check if we have speech groups available
        if "speech_groups" in recognition_results and recognition_results["speech_groups"]:
            logger.info(f"Using {len(recognition_results['speech_groups'])} speech groups for clip generation")
            
            # Process each speech group as a single segment
            for group_id, group_data in recognition_results["speech_groups"].items():
                # Skip groups with no segments
                if not group_data or "segments" not in group_data or not group_data["segments"]:
                    continue
                    
                # Get speaker info from the first segment
                first_segment = group_data["segments"][0]
                speaker_id = first_segment.get("speaker_id", "")
                speaker_name = first_segment.get("speaker_name", "Unknown Speaker")
                
                # Combine all transcripts in the group
                combined_transcript = " ".join([s.get("transcript", "") for s in group_data["segments"] if s.get("transcript")])
                
                # Calculate average confidence
                confidences = [s.get("confidence", 0.7) for s in group_data["segments"] if s.get("confidence") is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7
                
                # Add the speech group as a single segment
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "start_time": group_data.get("start_time", 0),
                    "end_time": group_data.get("end_time", 0),
                    "confidence": avg_confidence,
                    "recognition_method": "diarizer",
                    "transcript": combined_transcript,
                    "speech_group_id": group_id
                })
        else:
            # Fall back to individual segments if no speech groups
            logger.info("No speech groups found, processing individual diarized segments")
            for segment in recognition_results["diarized_speaker_segments"]:
                speaker_segments.append({
                    "speaker_id": segment["speaker_id"],
                    "speaker_name": segment["speaker_name"],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.7),
                    "recognition_method": "diarizer",
                    "transcript": segment.get("transcript", ""),
                    "speech_group_id": segment.get("speech_group_id")
                })
    
    # Process speaker segments from voice recognition if available
    elif transcript_data and "speakers" in transcript_data:
        for speaker in transcript_data["speakers"]:
            speaker_id = speaker.get("profile_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id:
                continue
                
            for segment in speaker.get("segments", []):
                # Find corresponding transcript text
                transcript_text = ""
                if "segments" in transcript_data:
                    for transcript_segment in transcript_data["segments"]:
                        if (transcript_segment["start"] >= segment["start_time"] and 
                            transcript_segment["end"] <= segment["end_time"]):
                            transcript_text += " " + transcript_segment["text"]
                
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name or "Unknown Speaker",
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "voice",
                    "transcript": transcript_text.strip()
                })
    
    # Process recognition events if no identified speakers were found
    if len(speaker_segments) == 0 and "recognition_events" in recognition_results:
        logger.info("No identified speakers found. Processing recognition events to create unidentified speaker segments.")
        
        # Group recognition events by time to create segments
        events = recognition_results["recognition_events"]
        if isinstance(events, list):
            # Sort events by time
            events.sort(key=lambda x: x.get("time", 0))
            
            # Create segments from recognition events
            current_segment = None
            unidentified_count = 0
            
            for event in events:
                event_time = event.get("time", 0)
                event_text = event.get("segment_text", "")
                
                if not current_segment:
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,  # Default 5 second segment
                        "confidence": 0.5,  # Medium confidence for unidentified speakers
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
                elif event_time - current_segment["end_time"] <= 60:  # If within 60 seconds
                    # Extend the current segment
                    current_segment["end_time"] = event_time + 5
                    current_segment["transcript"] += " " + event_text
                    current_segment["events"].append(event)
                else:
                    # Finalize the current segment and start a new one
                    speaker_segments.append({
                        "speaker_id": current_segment["speaker_id"],
                        "speaker_name": current_segment["speaker_name"],
                        "start_time": current_segment["start_time"],
                        "end_time": current_segment["end_time"],
                        "confidence": current_segment["confidence"],
                        "recognition_method": current_segment["recognition_method"],
                        "transcript": current_segment["transcript"].strip()
                    })
                    
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,
                        "confidence": 0.5,
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
            
            # Add the last segment if there is one
            if current_segment:
                speaker_segments.append({
                    "speaker_id": current_segment["speaker_id"],
                    "speaker_name": current_segment["speaker_name"],
                    "start_time": current_segment["start_time"],
                    "end_time": current_segment["end_time"],
                    "confidence": current_segment["confidence"],
                    "recognition_method": current_segment["recognition_method"],
                    "transcript": current_segment["transcript"].strip()
                })
    
    # If still no segments, create a single segment for the entire video
    if len(speaker_segments) == 0:
        logger.info("No speaker segments found. Creating a single segment for the entire video.")
        
        # Get video duration from metadata or default to 60 seconds
        duration = video_metadata.get("duration", 60)
        
        # Log the full_video_url to help with debugging
        logger.info(f"Using full_video_url: {full_video_url} for unidentified speaker clip")
        
        speaker_segments.append({
            "speaker_id": f"unidentified_{video_id}_full",
            "speaker_name": "Unidentified Speaker",
            "start_time": 0,
            "end_time": duration,
            "confidence": 0.3,  # Low confidence
            "recognition_method": "default",
            "transcript": "No transcript available"
        })
    
    # Sort segments by start time
    speaker_segments.sort(key=lambda x: x["start_time"])
    
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
        
    # Helper function to assess transcript coherence
    def assess_transcript_coherence(text):
        """Assess the semantic coherence of a transcript segment.
        Returns a value between 0-1 where higher values indicate more coherent, complete thoughts."""
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
    
    # Merge segments by the same speaker if they are close together (less than 60 seconds apart)
    # or if the previous segment's transcript doesn't end with sentence-ending punctuation
    MAX_GAP_SECONDS = 60
    EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE = 120  # 2 minutes for incomplete sentences
    merged_segments = []
    
    current_segment = None
    for segment in speaker_segments:
        if current_segment is None:
            current_segment = segment.copy()
            continue
            
        # Determine if current segment's transcript is a complete sentence
        sentence_complete = is_sentence_complete(current_segment["transcript"])
        
        # Use extended gap threshold for incomplete sentences
        threshold = EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE if not sentence_complete else MAX_GAP_SECONDS
        
        # If same speaker and either gap is small enough OR sentence is incomplete, merge segments
        if (segment["speaker_id"] == current_segment["speaker_id"] and 
            (segment["start_time"] - current_segment["end_time"] <= threshold or not sentence_complete)):
            
            # Merge transcripts if available
            if segment["transcript"] and current_segment["transcript"]:
                current_segment["transcript"] += " " + segment["transcript"]
            elif segment["transcript"]:
                current_segment["transcript"] = segment["transcript"]
                
            # Update end time and confidence (use max confidence)
            current_segment["end_time"] = segment["end_time"]
            current_segment["confidence"] = max(current_segment["confidence"], segment["confidence"])
        else:
            # Different speaker or gap too large, add current segment and start a new one
            merged_segments.append(current_segment)
            current_segment = segment.copy()
    
    # Add the last segment if there is one
    if current_segment is not None:
        merged_segments.append(current_segment)
    
    # TEMPORARILY COMMENTED OUT: Normalize speaker IDs across continuous speech segments based on confidence scores
    # This ensures consistent speaker attribution across segments that are likely part of the same speech
    # merged_segments, speech_groups = normalize_speaker_ids(merged_segments)
    # logger.info(f"Applied speaker ID normalization based on confidence scores")
    
    # Instead, create speech_groups directly from the unnormalized segments
    # This will preserve the original speaker IDs and member IDs from facial recognition
    speech_groups = []
    for idx, segment in enumerate(merged_segments):
        speech_group_id = f"speech_group_unnormalized_{idx}_{int(segment['start_time'])}"
        segment["speech_group_id"] = speech_group_id
        
        # Create a speech group for each segment
        segment_id = None
        if "id" in segment:
            segment_id = segment["id"]
        elif "segment_id" in segment:
            segment_id = segment["segment_id"]
        elif "db_id" in segment:
            segment_id = segment["db_id"]
            
        segment_ids = [segment_id] if segment_id is not None else []
        
        # Check if we have a member_id from facial recognition
        # If the speaker_id is numeric, it's likely from facial recognition
        member_id = None
        if "member_id" in segment and segment["member_id"] is not None:
            member_id = segment["member_id"]
            logger.info(f"Using existing member_id {member_id} from segment")
        elif isinstance(segment["speaker_id"], str) and segment["speaker_id"].isdigit():
            member_id = int(segment["speaker_id"])
            logger.info(f"Using numeric speaker_id {segment['speaker_id']} as member_id {member_id}")
        
        speech_groups.append({
            "speech_group_id": speech_group_id,
            "segment_ids": segment_ids,
            "speaker_id": segment["speaker_id"],
            "member_id": member_id,  # Include member_id in the speech group
            "confidence": segment.get("confidence", 0),
            "start_time": segment["start_time"],
            "end_time": segment["end_time"]
        })
        
    logger.info(f"Created {len(speech_groups)} unnormalized speech groups (normalization disabled)")

    
    # Get member ID mapping from database
    member_id_mapping = get_member_id_mapping(db, speaker_ids)
    logger.info(f"Retrieved member ID mapping for {len(member_id_mapping)} speakers")
    
    # Update the SQLite database with normalized speaker IDs
    try:
        update_sqlite_with_normalized_speakers(db, video_id, speech_groups, member_id_mapping)
        logger.info(f"Updated SQLite database with normalized speaker IDs for {len(speech_groups)} speech groups")
    except Exception as e:
        logger.error(f"Error updating database with normalized speaker IDs: {str(e)}")
        # Explicitly rollback the transaction to prevent cascading failures in PostgreSQL
        try:
            db.rollback()
            logger.info("Successfully rolled back transaction after normalization error")
        except Exception as rollback_error:
            logger.error(f"Error during transaction rollback: {str(rollback_error)}")
        # Continue with original segments if normalization fails
        logger.warning("Continuing with original speaker segments due to normalization error")
        
    # Post-process segments to further avoid splitting sentences
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
                logger.debug(f"Merging segments due to {merge_reason}: {current['transcript']} + {next_seg['transcript']}")
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
                merged["confidence"] = max(current["confidence"], next_seg["confidence"])
                
                result.append(merged)
                i += 2  # Skip both segments as they're now merged
                continue
                    
            result.append(current)
            i += 1
            
        # Add the last segment if we didn't merge it
        if i == len(segments) - 1:
            result.append(segments[i])
            
        return result

    # Apply post-processing to further merge segments with incomplete sentences
    merged_segments = post_process_segments(merged_segments)
    
    # Split overly long segments at natural pause points
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
                sub_segments.append(sub_segment)
            
            # Add all sub-segments to result
            result.extend(sub_segments)
            logger.info(f"Split long segment ({duration:.1f}s) into {len(sub_segments)} sub-segments")
        
        return result
    
    # Split segments that are too long (over 60 seconds)
    # Store the original segments before splitting for potential recombination later
    original_merged_segments = merged_segments.copy()
    
    # Split segments for local processing and detailed analysis
    merged_segments = split_long_segments(merged_segments, max_duration=60)
    
    # Log the member ID mapping for debugging
    if member_id_mapping:
        logger.info(f"Using member ID mapping: {member_id_mapping}")
    else:
        logger.warning("No member ID mapping found. Using original speaker IDs.")
    
    # Create clips for Supabase parliament_member_clips table
    member_clips = []
    for segment in merged_segments:
        # Generate a unique clip ID
        clip_id = str(uuid.uuid4())
        
        # Calculate duration
        duration = segment["end_time"] - segment["start_time"]
        
        # Format timestamps as HH:MM:SS
        def format_timestamp(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
        start_timestamp = format_timestamp(segment["start_time"])
        end_timestamp = format_timestamp(segment["end_time"])
        
        # Get speaker_id and map to proper member_id if available
        original_speaker_id = segment["speaker_id"]
        
        # Check if we have a mapping for this speaker ID
        if original_speaker_id in member_id_mapping:
            # Use the mapped integer member_id from the database
            speaker_id = member_id_mapping[original_speaker_id]
            logger.debug(f"Mapped speaker ID {original_speaker_id} to member_id {speaker_id}")
        else:
            # No mapping found, use the original speaker_id
            speaker_id = original_speaker_id
            
            # Handle unidentified speakers
            if isinstance(speaker_id, str) and speaker_id.startswith("unidentified_"):
                # Keep as is for now, we'll handle this during insertion
                logger.debug(f"Unidentified speaker: {speaker_id}")
            else:
                # Try to convert to integer if possible
                try:
                    speaker_id = int(speaker_id)
                except (ValueError, TypeError):
                    logger.debug(f"Could not convert speaker_id to integer: {speaker_id}")
                    # Keep as is for now, we'll handle this during insertion
                    pass
        
        # Create clip metadata - simplified to match the actual Supabase schema
        clip_data = {
            "id": clip_id,
            # Removed video_id as it's not in the Supabase schema
            "member_id": speaker_id,  # Now guaranteed to be an integer
            # Removed member_name as it's not in the Supabase schema
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "duration_seconds": duration,
            "transcript": segment["transcript"],
            "full_video_url": full_video_url if full_video_url else "pending_combined_av_upload",
            # Removed session_title as it's not in the Supabase schema
            "created_at": datetime.now().isoformat()
            # Removed is_unidentified as it's not in the Supabase schema
        }
        
        member_clips.append(clip_data)
    
    # Define a function to recombine segments from the same speaker for export
    def recombine_segments_for_export(clips):
        """Recombine split segments from the same speaker into continuous speech segments for export."""
        # Group clips by member_id
        clips_by_member = {}
        for clip in clips:
            member_id = clip.get("member_id")
            # Skip unidentified speakers or invalid member_ids
            if isinstance(member_id, str) and member_id.startswith("unidentified_"):
                continue
            try:
                member_id = int(member_id)
                if member_id <= 0:
                    continue
            except (ValueError, TypeError):
                continue
                
            if member_id not in clips_by_member:
                clips_by_member[member_id] = []
            clips_by_member[member_id].append(clip)
        
        # Sort clips for each member by start_time
        for member_id, member_clips in clips_by_member.items():
            member_clips.sort(key=lambda x: x.get("start_time", 0))
        
        # Recombine adjacent clips from the same speaker
        recombined_clips = []
        for member_id, sorted_clips in clips_by_member.items():
            current_combined = None
            
            for clip in sorted_clips:
                if current_combined is None:
                    current_combined = clip.copy()
                    continue
                
                # If this clip starts right after the previous one ends (or with small gap)
                if abs(clip.get("start_time", 0) - current_combined.get("end_time", 0)) <= 1.0:  # 1 second tolerance
                    # Extend the current combined clip
                    current_combined["end_time"] = clip.get("end_time", 0)
                    current_combined["end_timestamp"] = clip.get("end_timestamp", "")
                    current_combined["duration_seconds"] = current_combined.get("end_time", 0) - current_combined.get("start_time", 0)
                    
                    # Combine transcripts
                    if clip.get("transcript"):
                        if current_combined.get("transcript"):
                            current_combined["transcript"] += " " + clip.get("transcript")
                        else:
                            current_combined["transcript"] = clip.get("transcript")
                else:
                    # This clip is not adjacent, add the current combined and start a new one
                    recombined_clips.append(current_combined)
                    current_combined = clip.copy()
            
            # Add the last combined clip
            if current_combined:
                recombined_clips.append(current_combined)
        
        # Add back any clips that weren't recombined (like unidentified speakers)
        for clip in clips:
            member_id = clip.get("member_id")
            if (isinstance(member_id, str) and member_id.startswith("unidentified_")) or \
               (not isinstance(member_id, int) or member_id <= 0):
                recombined_clips.append(clip)
        
        return recombined_clips
    
    # Recombine segments for Supabase export
    recombined_clips = recombine_segments_for_export(member_clips)
    logger.info(f"Recombined {len(member_clips)} segments into {len(recombined_clips)} continuous speech segments for export")
    
    # Save recombined clips to Supabase parliament_member_clips table
    saved_clips = []
    failed_clips = []
    
    for clip in recombined_clips:
        try:
            # Ensure clip data is serializable and matches the Supabase schema
            try:
                # Create a clean serializable version of the clip
                # Ensure member_id is an integer and skip unidentified speakers
                member_id = clip.get("member_id")
                
                # Check if this is an original speaker ID that needs mapping
                if member_id in member_id_mapping:
                    # Use the mapped integer member_id from the database
                    member_id = member_id_mapping[member_id]
                    logger.info(f"Using mapped member_id {member_id} for clip {clip.get('id')}")
                
                # Handle unidentified speakers
                if isinstance(member_id, str) and member_id.startswith("unidentified_"):
                    # Skip unidentified speakers instead of using member_id = 0
                    logger.warning(f"Skipping unidentified speaker clip {clip.get('id')} - cannot be inserted due to foreign key constraints")
                    failed_clips.append({"clip_id": clip.get("id"), "warn": "Skipped unidentified speaker"})
                    continue
                else:
                    try:
                        member_id = int(member_id)
                        # Skip if member_id is 0 or negative
                        if member_id <= 0:
                            logger.warning(f"Skipping clip {clip.get('id')} with invalid member_id {member_id} - must be positive integer")
                            failed_clips.append({"clip_id": clip.get("id"), "error": f"Invalid member_id: {member_id}"})
                            continue
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping clip {clip.get('id')} with non-integer member_id {member_id}")
                        failed_clips.append({"clip_id": clip.get("id"), "error": f"Non-integer member_id: {member_id}"})
                        continue
                
                serializable_clip = {
                    "id": clip.get("id"),
                    # Removed video_id as it's not in the Supabase schema
                    "member_id": member_id,  # Now guaranteed to be a positive integer
                    # Removed member_name as it's not in the Supabase schema
                    "start_timestamp": str(clip.get("start_time", 0)),  # Convert to string for Supabase
                    "end_timestamp": str(clip.get("end_time", 0)),  # Convert to string for Supabase
                    "duration_seconds": float(clip.get("duration_seconds", 0)),
                    "transcript": (clip.get("transcript", "") or "")[:1000],  # Truncate long transcripts
                    "full_video_path": clip.get("full_video_url", "").replace("host.docker.internal", "localhost") if clip.get("full_video_url") else "",
                    # Removed session_title as it's not in the Supabase schema
                    "created_at": datetime.now().isoformat()
                    # Removed is_unidentified as it's not in the Supabase schema
                }
                
                # Log the clip data we're about to insert
                logger.info(f"Inserting clip for member ID {serializable_clip['member_id']} with ID {serializable_clip['id']}")
                
                # Insert clip into parliament_member_clips table
                response = supabase_service.client.table('parliament_member_clips').insert(serializable_clip).execute()
                
                if response and hasattr(response, 'data') and response.data:
                    saved_clips.append(clip["id"])
                    logger.info(f"Saved clip {clip['id']} for member ID {clip['member_id']} to Supabase")
                else:
                    failed_clips.append({
                        "clip_id": clip["id"],
                        "error": "No data returned from Supabase"
                    })
                    logger.warning(f"No data returned when saving clip {clip['id']} to Supabase")
            except Exception as e:
                logger.error(f"Error inserting clip {clip.get('id', 'unknown')}: {str(e)}")
                failed_clips.append({
                    "clip_id": clip["id"],
                    "error": str(e)
                })
        except Exception as e:
            failed_clips.append({
                "clip_id": clip["id"],
                "error": str(e)
            })
            logger.error(f"Error saving clip {clip['id']} to Supabase: {str(e)}")
    
    return {
        "success": True,
        "video_id": video_id,
        "clip_count": len(saved_clips),
        "saved_clips": saved_clips,
        "failed_clips": failed_clips
    }


def enhance_segments_with_diarization(
    audio_path: str, 
    recognition_results: Dict[str, Any],
    video_path: Optional[str] = None,
    max_duration: int = 1800
) -> Dict[str, Any]:
    """
    Use speaker diarization to enhance the accuracy of speaker segments without necessarily
    identifying the MP. This focuses on distinguishing different speakers based on voice characteristics.
    
    Args:
        audio_path: Path to the audio file
        recognition_results: Current recognition results
        video_path: Optional path to the video file
        max_duration: Maximum duration in seconds for the diarization process
        
    Returns:
        Enhanced recognition results with improved speaker segmentation
    """
    logger.info(f"Enhancing speaker segments with diarization for audio: {audio_path}")
    
    try:
        # Import the speaker diarizer
        from backend.utils.speaker_diarizer import SpeakerDiarizer
    except ImportError:
        logger.error("Could not import SpeakerDiarizer. Make sure the module is installed.")
        return recognition_results
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return recognition_results
    
    try:
        # Extract transcription data from recognition results
        transcription = {"segments": []}
        
        # Convert recognition events to transcription format expected by diarizer
        if "recognition_events" in recognition_results:
            events = recognition_results["recognition_events"]
            if isinstance(events, list):
                # Sort events by time
                events.sort(key=lambda x: x.get("time", 0))
                
                for event in events:
                    event_time = event.get("time", 0)
                    event_text = event.get("segment_text", "")
                    
                    if event_text:  # Only add events with text
                        # Estimate segment duration (2 seconds is a reasonable default)
                        transcription["segments"].append({
                            "start": event_time,
                            "end": event_time + 2.0,
                            "text": event_text
                        })
        
        # If we have a transcription file, use that instead
        if "transcription_file" in recognition_results:
            transcription_file = recognition_results["transcription_file"]
            if os.path.exists(transcription_file):
                try:
                    with open(transcription_file, 'r') as f:
                        file_transcription = json.load(f)
                    if "segments" in file_transcription and file_transcription["segments"]:
                        transcription = file_transcription
                        logger.info(f"Using transcription from file: {transcription_file}")
                except Exception as e:
                    logger.error(f"Error loading transcription file: {str(e)}")
        
        # If we don't have any segments, we can't perform diarization
        if not transcription["segments"]:
            logger.warning("No transcription segments found for diarization")
            return recognition_results
        
        # Initialize the speaker diarizer
        diarizer = SpeakerDiarizer()
        
        # Run diarization on the audio file
        # We're using a simple timeout mechanism to prevent hanging
        import threading
        import time
        
        result = None
        error = None
        
        def run_diarization():
            nonlocal result, error
            try:
                # Use basic speaker identification without requiring voice profiles
                result = diarizer.diarize(audio_path, transcription, video_path)
            except Exception as e:
                error = str(e)
        
        # Start diarization in a separate thread
        thread = threading.Thread(target=run_diarization)
        thread.daemon = True
        thread.start()
        
        # Wait for the thread to finish or timeout
        thread.join(timeout=max_duration)
        
        if thread.is_alive():
            logger.error(f"Speaker diarization timed out after {max_duration} seconds")
            return recognition_results
        
        if error:
            logger.error(f"Error in speaker diarization: {error}")
            return recognition_results
        
        if not result:
            logger.error("Speaker diarization returned no results")
            return recognition_results
        
        # Process the diarization results
        diarized_segments = []
        speaker_segments = {}
        speech_groups = {}
        
        # First pass: Group segments by speaker and speech group
        for segment in result.get("segments", []):
            if "speaker" not in segment:
                continue
                
            speaker_info = segment["speaker"]
            speaker_id = speaker_info.get("name", "")  # Use name as ID for anonymous speakers
            member_id = speaker_info.get("id")  # Get member_id if available from facial recognition
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "")
            confidence = speaker_info.get("confidence", 0.7)
            
            # Get speech group ID if available, otherwise use a default
            speech_group_id = segment.get("speech_group_id", None)
            
            # Initialize speaker dict if not exists
            if speaker_id not in speaker_segments:
                speaker_segments[speaker_id] = []
            
            # Add this segment to the speaker's list
            segment_data = {
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
                "confidence": confidence,
                "speech_group_id": speech_group_id,
                "speaker_id": speaker_id
            }
            
            # Preserve member_id from facial recognition if available
            if member_id is not None:
                segment_data["member_id"] = member_id
                logger.info(f"Preserving member_id {member_id} from facial recognition in segment {start_time}-{end_time}")
            speaker_segments[speaker_id].append(segment_data)
            
            # Group by speech_group_id if available
            if speech_group_id is not None:
                if speech_group_id not in speech_groups:
                    speech_groups[speech_group_id] = []
                speech_groups[speech_group_id].append(segment_data)
        
        logger.info(f"Found {len(speaker_segments)} unique speakers in diarization results")
        
        # Second pass: Use speech groups if available, otherwise merge adjacent segments by speaker
        MAX_MERGE_GAP = 2.0  # Maximum gap in seconds to merge segments
        
        # If we have speech groups from the diarizer, use those directly
        if speech_groups:
            logger.info(f"Using {len(speech_groups)} speech groups from diarization results")
            
            # Process each speech group
            for group_id, group_segments in speech_groups.items():
                # Sort segments by start time
                group_segments.sort(key=lambda x: x["start_time"])
                
                # Get the first segment's speaker as the group speaker
                speaker_id = group_segments[0]["speaker_id"] if "speaker_id" in group_segments[0] else ""
                
                # Find the highest confidence segment with a member_id from facial recognition
                segments_with_member_id = [seg for seg in group_segments if "member_id" in seg]
                member_id = None
                if segments_with_member_id:
                    highest_conf_segment = max(segments_with_member_id, key=lambda x: x.get("confidence", 0))
                    member_id = highest_conf_segment["member_id"]
                    logger.info(f"Using member_id {member_id} from highest confidence segment in speech group {group_id}")
                
                # Combine all text in the group
                combined_text = " ".join([s["text"] for s in group_segments if s["text"]])
                
                # Get start and end times from the group
                start_time = min([s["start_time"] for s in group_segments])
                end_time = max([s["end_time"] for s in group_segments])
                
                # Average confidence across segments
                avg_confidence = sum([s["confidence"] for s in group_segments]) / len(group_segments) if group_segments else 0.7
                
                # Create a segment for this speech group
                segment_data = {
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_id,  # For now, just use the speaker ID as the name
                    "start_time": start_time,
                    "end_time": end_time,
                    "confidence": avg_confidence,
                    "recognition_method": "diarizer",
                    "transcript": combined_text,
                    "speech_group_id": group_id
                }
                
                # Preserve member_id from facial recognition if available
                if member_id is not None:
                    segment_data["member_id"] = member_id
                    logger.info(f"Preserving member_id {member_id} in speech group {group_id}")
                    
                diarized_segments.append(segment_data)
        else:
            # Fall back to the original merging logic if no speech groups are available
            logger.info("No speech groups found, falling back to segment merging logic")
            
            for speaker_id, segments in speaker_segments.items():
                # Sort segments by start time
                segments.sort(key=lambda x: x["start_time"])
                
                # Merge adjacent segments with small gaps
                merged_segments = []
                current_segment = None
                current_group_id = None
                
                for segment in segments:
                    if current_segment is None:
                        current_segment = segment.copy()
                        current_group_id = segment.get("speech_group_id")
                        continue
                    
                    # If this segment has a different speech group ID, don't merge
                    segment_group_id = segment.get("speech_group_id")
                    if current_group_id is not None and segment_group_id is not None and current_group_id != segment_group_id:
                        merged_segments.append(current_segment)
                        current_segment = segment.copy()
                        current_group_id = segment_group_id
                        continue
                    
                    # If gap is small enough, merge segments
                    if segment["start_time"] - current_segment["end_time"] <= MAX_MERGE_GAP:
                        # Extend current segment
                        current_segment["end_time"] = segment["end_time"]
                        if segment["text"]:
                            if current_segment["text"]:
                                current_segment["text"] += " " + segment["text"]
                            else:
                                current_segment["text"] = segment["text"]
                        # Use max confidence
                        current_segment["confidence"] = max(current_segment["confidence"], segment["confidence"])
                    else:
                        # Add current segment and start a new one
                        merged_segments.append(current_segment)
                        current_segment = segment.copy()
                        current_group_id = segment_group_id
                
                # Add the last segment
                if current_segment:
                    merged_segments.append(current_segment)
                
                # Create final speaker segments
                for segment in merged_segments:
                    segment_data = {
                        "speaker_id": speaker_id,
                        "speaker_name": speaker_id,  # For now, just use the speaker ID as the name
                        "start_time": segment["start_time"],
                        "end_time": segment["end_time"],
                        "confidence": segment["confidence"],
                        "recognition_method": "diarizer",
                        "transcript": segment["text"],
                        "speech_group_id": segment.get("speech_group_id")
                    }
                    
                    # Preserve member_id from facial recognition if available in the original segment
                    if "member_id" in segment:
                        segment_data["member_id"] = segment["member_id"]
                        logger.info(f"Preserving member_id {segment['member_id']} in merged segment {segment['start_time']}-{segment['end_time']}")
                        
                    diarized_segments.append(segment_data)
            
            logger.info(f"Speaker {speaker_id}: {len(segments)} raw segments merged into {len(merged_segments)} coherent segments")
        
        # Create enhanced recognition results
        enhanced_results = recognition_results.copy()
        
        # Replace or merge speaker segments
        if diarized_segments:
            logger.info(f"Found {len(diarized_segments)} diarized speaker segments")
            
            # Group segments by speech_group_id for easier access
            grouped_segments = {}
            for segment in diarized_segments:
                group_id = segment.get("speech_group_id")
                if group_id:
                    if group_id not in grouped_segments:
                        grouped_segments[group_id] = []
                    grouped_segments[group_id].append(segment)
            
            # Add speech groups information if available
            if grouped_segments:
                logger.info(f"Organized segments into {len(grouped_segments)} speech groups")
                enhanced_results["speech_groups"] = grouped_segments
            
            # For now, we'll completely replace the speaker segments with diarized ones
            # Later, we could implement a more sophisticated merging strategy
            enhanced_results["diarized_speaker_segments"] = diarized_segments
            
            return enhanced_results
        
        return recognition_results
    
    except Exception as e:
        logger.exception(f"Error enhancing segments with diarization: {str(e)}")
        return recognition_results
