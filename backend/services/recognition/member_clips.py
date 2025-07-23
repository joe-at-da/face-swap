import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.integration.supabase_client import SupabaseService
from backend.services.integration.supabase_upload import SupabaseUploader

logger = logging.getLogger(__name__)

def normalize_speaker_ids(segments):
    """
    Normalize speaker IDs across speech segments by speaker identity only.
    
    This function:
    1. Groups speech segments purely by speaker identity (ignoring time gaps)
    2. Assigns a unique speech group ID to each speaker group
    3. Selects the member ID with the highest confidence score in each group
    4. Updates all segments in the group with this member ID
    
    Args:
        segments: List of speech segments with metadata containing speaker_id, member_id, and timestamps
        
    Returns:
        Tuple of (normalized_segments, speech_groups)
    """
    if not segments:
        return [], []
        
    # Sort segments by start time
    sorted_segments = sorted(segments, key=lambda x: x.get('start_time', 0))
    
    # Group continuous speech segments by speaker
    speech_groups = []
    current_block = []
    current_speaker = None
    
    # Group segments purely by speaker identity, ignoring time gaps
    
    for segment in sorted_segments:
        # Extract speaker_id from metadata if it exists there
        metadata = segment.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
                
        # Try to get speaker_id from metadata first, then from direct property
        speaker_id = metadata.get('speaker_id') or segment.get('speaker_id')
        
        # Skip segments without speaker_id
        if not speaker_id:
            continue
            
        # Start a new block if this is the first segment or if the speaker changed
        if current_speaker is None or speaker_id != current_speaker:
            # Save the previous block if it exists
            if current_block:
                # Process the completed block
                process_speech_block(current_block, speech_groups)
                
            # Start a new block with this segment
            current_block = [segment]
            current_speaker = speaker_id
        else:
            # Add this segment to the current block regardless of time gaps
            # since it's from the same speaker
            if current_block:
                current_block.append(segment)
            else:
                # Should not happen, but just in case
                current_block.append(segment)
    
    # Process the last block
    if current_block:
        process_speech_block(current_block, speech_groups)
    
    # Now update all segments with their speech group IDs and normalized member IDs
    normalized_segments = []
    for segment in sorted_segments:
        # Find the speech group for this segment
        for group in speech_groups:
            if segment.get('id') in group.get('segment_ids', []):
                # Update the segment with the speech group ID and normalized member ID
                segment['speech_group_id'] = group.get('id')
                
                # Only update member_id if the group has a member_id
                if 'member_id' in group:
                    segment['member_id'] = group.get('member_id')
                break
                
        normalized_segments.append(segment)
    
    return normalized_segments, speech_groups

def process_speech_block(block, speech_groups):
    """
    Process a block of continuous speech segments by the same speaker.
    
    This function:
    1. Assigns a unique speech group ID to the block
    2. Finds the member ID with the highest confidence score in the block
    3. Updates the speech_groups list with the new group
    
    Args:
        block: List of continuous speech segments by the same speaker
        speech_groups: List to append the new speech group to
    """
    if not block:
        return
        
    # Get the speaker ID from the first segment's metadata or direct property
    first_segment = block[0]
    metadata = first_segment.get('metadata', {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except:
            metadata = {}
    
    speaker_id = metadata.get('speaker_id') or first_segment.get('speaker_id')
    
    # Generate a simple sequential ID for this speech group
    speech_group_id = f"speech_group_{speaker_id}_{len(speech_groups)}"
    
    # Debug information about the speech group
    print(f"Creating speech group: {speech_group_id} for speaker {speaker_id}")
    print(f"  Segments: {len(block)} from {block[0].get('start_time', 0)} to {block[-1].get('end_time', 0)}")
    print(f"  First segment text: {block[0].get('text', '[No text]')[:50]}...")
    print(f"  Last segment text: {block[-1].get('text', '[No text]')[:50]}...")
    
    # Log confidence scores for debugging
    confidences = []
    for segment in block:
        seg_metadata = segment.get('metadata', {})
        if isinstance(seg_metadata, str):
            try:
                seg_metadata = json.loads(seg_metadata)
            except:
                seg_metadata = {}
        
        conf = seg_metadata.get("confidence_score", 
               seg_metadata.get("confidence", 
               segment.get("confidence_score", 
               segment.get("confidence", 0))))
        confidences.append(conf)
    
    print(f"  Confidence scores: min={min(confidences) if confidences else 'N/A'}, max={max(confidences) if confidences else 'N/A'}, avg={sum(confidences)/len(confidences) if confidences else 'N/A'}")
    print("  " + "-"*50)
    
    # Find the member ID with the highest confidence score in this block
    highest_conf = -1
    highest_conf_speaker_id = None
    highest_conf_member_id = None
    
    # First, prioritize segments with numeric member IDs (from facial recognition)
    for segment in block:
        # Get metadata for confidence
        seg_metadata = segment.get('metadata', {})
        if isinstance(seg_metadata, str):
            try:
                seg_metadata = json.loads(seg_metadata)
            except:
                seg_metadata = {}
                
        if "member_id" in segment and str(segment["member_id"]).isdigit():
            # Try to get confidence from metadata first, then from direct property
            # Check for both 'confidence' and 'confidence_score' fields
            conf = seg_metadata.get("confidence_score", 
                   seg_metadata.get("confidence", 
                   segment.get("confidence_score", 
                   segment.get("confidence", 0))))
            if conf > highest_conf:
                highest_conf = conf
                highest_conf_speaker_id = seg_metadata.get('speaker_id') or segment.get('speaker_id')
                highest_conf_member_id = str(segment["member_id"])
    
    # Fallback if no numeric member_id found
    if highest_conf_member_id is None:
        # Use the first segment's member_id or speaker_id as fallback
        for segment in block:
            if "member_id" in segment and segment["member_id"]:
                highest_conf_member_id = segment["member_id"]
                break
        
        # If still no member_id, use speaker_id
        if highest_conf_member_id is None:
            highest_conf_member_id = speaker_id
    
    # Create the speech group
    speech_group = {
        "id": speech_group_id,
        "speaker_id": speaker_id,
        "member_id": highest_conf_member_id,
        "segment_ids": [segment.get('id') for segment in block if 'id' in segment],
        "start_time": min(segment.get('start_time', 0) for segment in block),
        "end_time": max(segment.get('end_time', 0) for segment in block),
        "confidence": highest_conf
    }
    
    speech_groups.append(speech_group)

def update_sqlite_with_normalized_speakers(db, video_id, speech_groups, member_id_mapping):
    """
    Update the SQLite database with normalized speaker IDs and member IDs from speech groups.
    For PostgreSQL, this function returns early as the parliament_clips table doesn't exist.
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        speech_groups: List of speech groups with normalized speaker IDs
        member_id_mapping: Mapping of speaker IDs to member IDs
        
    Returns:
        Number of segments updated
    """
    total_updated = 0
    transaction_error = False
    
    try:
        # Check if we're using SQLite or PostgreSQL
        is_sqlite = db.bind.dialect.name == 'sqlite'
        
        # For PostgreSQL, we don't have a parliament_clips table
        # The normalized data will be exported to PostgreSQL later in the pipeline
        if not is_sqlite:
            # We'll just store the normalized data in memory and return it
            logger.info("Using PostgreSQL database - normalization will be applied in memory only")
            logger.info("Normalized member IDs will be used when exporting to PostgreSQL tables")
            
            # We'll return early with the number of segments that would be updated
            # This ensures we don't try to update non-existent tables in PostgreSQL
            total_segments = sum(len(sg.get('segment_ids', [])) for sg in speech_groups)
            logger.info(f"Would update {total_segments} segments with normalized speaker IDs")
            return total_segments
        
        # Get existing clips from the database to match with our segments
        db_clips = {}  # Map of (start_time, end_time) to database ID
        
        # For SQLite, we need to extract video_id from the metadata JSON
        try:
            video_clips_sql = text("""
                SELECT id, start_timestamp, end_timestamp 
                FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
            """)
            
            result = db.execute(video_clips_sql, {"video_id": video_id})
            for row in result:
                db_id = row[0]  # Database ID
                start_time = float(row[1]) if row[1] else 0
                end_time = float(row[2]) if row[2] else 0
                # Create a key based on timestamps that we can match with our segments
                db_clips[(start_time, end_time)] = db_id
                
            logger.info(f"Found {len(db_clips)} clips in SQLite for video {video_id}")
        except Exception as e:
            logger.error(f"Error querying SQLite database: {str(e)}")
            # Try a fallback query with LIKE
            try:
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
        
        # Verify that the speech_group_id column exists in the SQLite database
        try:
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
        
        logger.info(f"Found {len(db_clips)} clips in database for video {video_id}")
        
        # Update speech_group_id and member_id for all segments in each speech group
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
            
            speech_group_id = speech_group["id"]
            segment_ids = speech_group.get("segment_ids", [])
            
            # Skip if no segment IDs
            if not segment_ids:
                logger.warning(f"No segment IDs for speech group {speech_group_id}, skipping")
                continue
                
            # Convert segment IDs to comma-separated string for SQL IN clause
            segment_ids_str = ", ".join([f"'{id}'" for id in segment_ids])
            
            # Update speech_group_id for all segments in this group
            update_sql = text(f"UPDATE parliament_clips SET speech_group_id = :speech_group_id WHERE id IN ({segment_ids_str})")
            
            try:
                db.execute(update_sql, {"speech_group_id": speech_group_id})
                
                # Always update member_id with highest confidence member_id for all segments in group
                # Also store speaker_id in the metadata JSON field since there's no speaker_id column
                update_member_sql = text(f"""
                    UPDATE parliament_clips 
                    SET member_id = :member_id,
                        metadata = json_patch(metadata, json_object('speaker_id', :speaker_id))
                    WHERE id IN ({segment_ids_str})
                """)
                
                try:
                    # Try with json_patch function (available in newer SQLite versions)
                    result = db.execute(update_member_sql, {"member_id": member_id, "speaker_id": speaker_id})
                    updated_count = result.rowcount
                except Exception as json_error:
                    # Fallback for older SQLite versions without json_patch
                    logger.warning(f"json_patch not available, using simpler update: {str(json_error)}")
                    update_member_sql = text(f"UPDATE parliament_clips SET member_id = :member_id WHERE id IN ({segment_ids_str})")
                    result = db.execute(update_member_sql, {"member_id": member_id})
                    updated_count = result.rowcount
                
                total_updated += updated_count
                logger.info(f"Updated {updated_count} segments in speech group {speech_group_id} with member_id {member_id}")
                
            except Exception as e:
                logger.error(f"Error updating speech group {speech_group_id}: {str(e)}")
                # Continue with other speech groups even if one fails
        
        # Final commit for SQLite
        db.commit()
        logger.info(f"Committed all updates for SQLite database")
        
        logger.info(f"Successfully updated {total_updated} segments with normalized speaker IDs")
        
        # Verify updates - only for SQLite since we return early for PostgreSQL
        try:
            # Check how many clips have speech_group_id set
            verify_sql = text("SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id IS NOT NULL")
            result = db.execute(verify_sql)
            with_speech_group = result.scalar() or 0
            
            # Check total clips for this video
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
                
            logger.info(f"Verification: {with_speech_group}/{total_clips} clips have speech_group_id set in parliament_clips table")
            
            # Calculate percentage
            if total_clips > 0:
                percentage = (with_speech_group / total_clips) * 100
                logger.info(f"Speech group coverage: {percentage:.1f}%")
                
            # Check member_id consistency within speech groups
            if with_speech_group > 0:
                # Get count of distinct speech groups
                speech_group_sql = text("SELECT COUNT(DISTINCT speech_group_id) FROM parliament_clips WHERE speech_group_id IS NOT NULL")
                result = db.execute(speech_group_sql)
                distinct_groups = result.scalar() or 0
                
                logger.info(f"Found {distinct_groups} distinct speech groups in parliament_clips table")
                
                # Check for inconsistent member_ids within speech groups
                inconsistent_sql = text("""
                    SELECT speech_group_id, COUNT(DISTINCT member_id) as distinct_members
                    FROM parliament_clips
                    WHERE speech_group_id IS NOT NULL
                    GROUP BY speech_group_id
                    HAVING COUNT(DISTINCT member_id) > 1
                """)
                
                result = db.execute(inconsistent_sql)
                inconsistent_groups = result.fetchall()
                
                if inconsistent_groups:
                    logger.warning(f"Found {len(inconsistent_groups)} speech groups with inconsistent member IDs")
                    for group in inconsistent_groups[:5]:  # Show details for up to 5 groups
                        logger.warning(f"Speech group {group[0]} has {group[1]} different member IDs")
                else:
                    logger.info(f"All speech groups have consistent member_ids - normalization successful!")
                    
        except Exception as e:
            logger.error(f"Error verifying updates: {str(e)}")
            logger.error(f"Verification failed but updates may still have succeeded")
            # Don't fail the entire process just because verification failed
    
    except Exception as e:
        logger.error(f"Error updating database with normalized speakers: {str(e)}")
        if not is_sqlite:  # PostgreSQL needs explicit rollback
            try:
                db.rollback()
                logger.info("Rolled back all updates due to error")
            except Exception as rollback_error:
                logger.error(f"Error during final rollback: {str(rollback_error)}")
    
    return total_updated


def save_member_clips_to_supabase(db, video_id, full_video_url=None, recognition_results=None, 
                               video_metadata=None, supabase_service=None, video_path=None, 
                               audio_path=None, use_diarization=False):
    """
    Save normalized member clips to Supabase (PostgreSQL).
    
    This function exports clips from the SQLite database to the PostgreSQL database via Supabase,
    ensuring that member IDs are properly normalized and consistent within speech groups.
    
    Args:
        db: Database session
        video_id: ID of the video
        full_video_url: URL of the full video in Supabase storage
        recognition_results: Recognition results from the recognition process
        video_metadata: Metadata for the video
        supabase_service: Supabase service instance (if None, a new one will be created)
        video_path: Path to the video file
        audio_path: Path to the audio file
        use_diarization: Whether to use diarization results
        
    Returns:
        Dictionary with results of the clip saving process
    """
    logger.info(f"Exporting normalized member clips to Supabase for video ID {video_id}")
    
    try:
        # Check if we're using SQLite or PostgreSQL
        is_sqlite = hasattr(db.connection().connection, 'execute')
        
        if not is_sqlite:
            logger.warning("This function is designed to export from SQLite to PostgreSQL. "
                          "The current database connection appears to be PostgreSQL already.")
        
        # Create a Supabase uploader if one wasn't provided
        uploader = supabase_service
        if not uploader:
            try:
                uploader = SupabaseUploader(use_service_role=True)
                logger.info("Created new SupabaseUploader instance")
            except Exception as e:
                logger.error(f"Failed to create SupabaseUploader: {str(e)}")
                return {"error": f"Failed to create SupabaseUploader: {str(e)}"}
        
        # First, get valid member IDs from PostgreSQL to ensure we only export valid IDs
        valid_member_ids = []
        try:
            # Get valid member IDs from the speakers table in PostgreSQL using parliament_id field
            member_response = uploader.client.table('speakers').select('parliament_id').execute()
            if hasattr(member_response, 'data') and member_response.data:
                valid_member_ids = [speaker['parliament_id'] for speaker in member_response.data if 'parliament_id' in speaker]
                logger.info(f"Found {len(valid_member_ids)} valid parliament_ids in PostgreSQL speakers table")
                if valid_member_ids:
                    sample_ids = valid_member_ids[:10] if len(valid_member_ids) > 10 else valid_member_ids
                    logger.info(f"Sample valid parliament_ids: {sample_ids}")
            
            if not valid_member_ids:
                logger.warning("No valid parliament_ids found in PostgreSQL speakers table. Clips may be rejected during export.")
        except Exception as e:
            logger.warning(f"Could not fetch valid parliament_ids from PostgreSQL: {str(e)}")
            logger.warning("Proceeding with export, but clips may be rejected if member IDs don't exist in PostgreSQL.")
        
        # Query the SQLite database for clips with the given video_id
        try:
            # First, check if we have any clips for this video
            count_sql = text("""
                SELECT COUNT(*) FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
            """)
            
            result = db.execute(count_sql, {"video_id": video_id})
            clip_count = result.scalar() or 0
            
            if clip_count == 0:
                logger.warning(f"No clips found in SQLite for video ID {video_id}")
                return {"warning": f"No clips found for video ID {video_id}", "inserted": 0}
            
            logger.info(f"Found {clip_count} clips in SQLite for video ID {video_id}")
            
            # Query for all clips with this video_id
            query_sql = text("""
                SELECT id, member_id, transcript, start_timestamp, end_timestamp, 
                       confidence_score, duration_seconds, metadata, speech_group_id
                FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
            """)
            
            result = db.execute(query_sql, {"video_id": video_id})
            clips = result.fetchall()
            
            # Prepare clips for Supabase export
            supabase_clips = []
            skipped_clips = 0
            invalid_member_ids = set()
            
            for clip in clips:
                # Parse metadata JSON
                metadata = clip[7]  # metadata is the 8th column
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Get member_id and validate it
                member_id = clip[1]  # member_id is the 2nd column
                
                # Skip clips without member_id or with member_id = 0 (unknown)
                if not member_id or member_id == 0:
                    logger.warning(f"Skipping clip with missing or unknown member_id: {clip[0]}")
                    skipped_clips += 1
                    continue
                
                # Convert member_id to integer if it's a string
                if isinstance(member_id, str):
                    try:
                        member_id = int(member_id)
                    except ValueError:
                        logger.warning(f"Skipping clip with non-integer member_id: {member_id}")
                        skipped_clips += 1
                        invalid_member_ids.add(member_id)
                        continue
                
                # Check if member_id is valid in PostgreSQL (if we have valid IDs)
                if valid_member_ids and member_id not in valid_member_ids:
                    logger.warning(f"Member ID {member_id} not found in PostgreSQL speakers table as parliament_id")
                    skipped_clips += 1
                    invalid_member_ids.add(member_id)
                    continue
                
                # Create a clip record for Supabase
                supabase_clip = {
                    "id": str(uuid.uuid4()),  # Generate a new UUID for Supabase
                    "member_id": member_id,
                    "transcript": clip[2],  # transcript
                    "full_video_path": full_video_url or metadata.get("full_video_path", ""),
                    "start_timestamp": clip[3],  # start_timestamp
                    "end_timestamp": clip[4],  # end_timestamp
                    "confidence_score": clip[5],  # confidence_score
                    "duration_seconds": clip[6],  # duration_seconds
                    "speech_group_id": clip[8],  # speech_group_id
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": json.dumps(metadata)
                }
                
                supabase_clips.append(supabase_clip)
            
            if not supabase_clips:
                logger.warning("No valid clips to export to Supabase after filtering")
                if invalid_member_ids:
                    logger.warning(f"Invalid member IDs found: {list(invalid_member_ids)}")
                return {"warning": "No valid clips to export", "inserted": 0, "skipped": skipped_clips}
            
            logger.info(f"Prepared {len(supabase_clips)} clips for export to Supabase (skipped {skipped_clips})")
            
            # Export clips to Supabase in smaller batches to avoid transaction issues
            batch_size = 50  # Process in smaller batches
            total_inserted = 0
            
            for i in range(0, len(supabase_clips), batch_size):
                batch = supabase_clips[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(supabase_clips) + batch_size - 1)//batch_size} with {len(batch)} clips")
                
                try:
                    # Use the modified uploader that validates against speakers.parliament_id
                    result = uploader.add_to_clip_creation_queue(batch)
                    
                    if "error" in result:
                        logger.error(f"Error exporting batch to Supabase: {result['error']}")
                        # Continue with next batch instead of failing completely
                    else:
                        inserted = result.get("inserted", 0) if isinstance(result, dict) else 0
                        total_inserted += inserted
                        logger.info(f"Successfully exported batch with {inserted} clips")
                        
                except Exception as batch_error:
                    logger.error(f"Error processing batch: {str(batch_error)}")
                    # Continue with next batch
            
            logger.info(f"Export complete: {total_inserted} clips inserted, {skipped_clips} skipped")
            return {
                "success": total_inserted > 0,
                "inserted": total_inserted,
                "skipped": skipped_clips,
                "total": clip_count
            }
            
        except Exception as e:
            logger.error(f"Error querying SQLite database: {str(e)}")
            return {"error": f"Error querying SQLite database: {str(e)}"}
    
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Error saving member clips to Supabase: {error_details}")
        logger.error(traceback.format_exc())
        return {"error": error_details}
