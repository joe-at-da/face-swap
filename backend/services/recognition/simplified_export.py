"""
Simplified Parliament Member Clips Export Process

This module provides a simplified approach to normalizing and exporting parliament member clips:
1. Data is correctly set in PostgreSQL parliament_member_clips
2. Data is moved to SQLite for processing
3. Member IDs are normalized across speech groups
4. Normalized data is exported to Supabase
"""

import json
import uuid
import logging
from datetime import datetime
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Union

# Import necessary services
from backend.services.integration.supabase_upload import SupabaseUploader
from backend.services.recognition.member_clips import process_speech_block

# Set up logging
logger = logging.getLogger(__name__)

def normalize_and_export_clips(db, video_id: str, supabase_service=None):
    """
    Simplified process to normalize and export parliament member clips.
    
    This function:
    1. Retrieves clips from SQLite for the given video_id
    2. Groups clips by speaker and normalizes member IDs within speech groups
    3. Exports the normalized clips to Supabase
    
    Args:
        db: SQLite database session
        video_id: ID of the video to process
        supabase_service: Optional Supabase service instance
        
    Returns:
        Dict with results of the normalization and export process
    """
    logger.info(f"Starting simplified normalization and export for video ID {video_id}")
    
    try:
        # Check if we're using SQLite
        is_sqlite = hasattr(db.connection().connection, 'execute')
        if not is_sqlite:
            return {"error": "This function requires an SQLite database connection"}
        
        # Step 1: Retrieve all clips for this video from SQLite
        try:
            # First check if we have any clips for this video
            # Check for video_id in metadata in multiple formats
            logger.info(f"Searching for clips with video_id {video_id} (type: {type(video_id).__name__})")
            
            count_sql = text("""
                SELECT COUNT(*) FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
                   OR json_extract(metadata, '$.video_id') = :video_id_str
                   OR json_extract(metadata, '$.video_id') = :video_id_int
                   OR metadata LIKE :video_id_pattern
            """)
            
            result = db.execute(count_sql, {
                "video_id": video_id, 
                "video_id_str": str(video_id),
                "video_id_int": int(video_id) if str(video_id).isdigit() else -1,
                "video_id_pattern": f'%"video_id": {video_id}%'
            })
            clip_count = result.scalar() or 0
            
            if clip_count == 0:
                logger.warning(f"No clips found in SQLite for video ID {video_id}")
                return {"warning": f"No clips found for video ID {video_id}", "normalized": 0}
            
            logger.info(f"Found {clip_count} clips in SQLite for video ID {video_id}")
            
            # Use the exact schema provided
            logger.info("Using exact schema for parliament_clips table")
            query_sql = text("""
                SELECT id, member_id, transcript, full_video_path, start_timestamp, end_timestamp, 
                       confidence_score, duration_seconds, metadata, speech_group_id
                FROM parliament_clips 
                WHERE json_extract(metadata, '$.video_id') = :video_id
                   OR json_extract(metadata, '$.video_id') = :video_id_str
                   OR json_extract(metadata, '$.video_id') = :video_id_int
                   OR metadata LIKE :video_id_pattern
                ORDER BY start_timestamp
            """)
            
            result = db.execute(query_sql, {
                "video_id": video_id, 
                "video_id_str": str(video_id),
                "video_id_int": int(video_id) if str(video_id).isdigit() else -1,
                "video_id_pattern": f'%"video_id": {video_id}%'
            })
            clips = result.fetchall()
            
            # Convert to list of dictionaries for easier processing
            clip_dicts = []
            for clip in clips:
                # Parse metadata JSON
                metadata = clip[8]  # metadata is now the 9th column (index 8)
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Use speech_group_id from the schema
                speech_group_id = clip[9] if len(clip) > 9 else None
                
                clip_dict = {
                    "id": clip[0],
                    "member_id": clip[1],
                    "transcript": clip[2],
                    "full_video_path": clip[3],  # Added full_video_path
                    "start_time": clip[4],  # Using start_timestamp as start_time (index adjusted)
                    "end_time": clip[5],    # Using end_timestamp as end_time (index adjusted)
                    "confidence_score": clip[6],  # index adjusted
                    "duration_seconds": clip[7],  # index adjusted
                    "metadata": metadata,  # metadata is now at index 8
                    "speech_group_id": speech_group_id  # speech_group_id is now at index 9
                }
                clip_dicts.append(clip_dict)
            
            logger.info(f"Converted {len(clip_dicts)} clips to dictionaries for processing")
            
        except Exception as e:
            logger.error(f"Error retrieving clips from SQLite: {str(e)}")
            return {"error": f"Error retrieving clips from SQLite: {str(e)}"}
        
        # Step 2: Group clips by speech group and normalize member IDs
        try:
            # Group clips by speech_group_id
            speech_groups = {}
            for clip in clip_dicts:
                speech_group_id = clip.get("speech_group_id")
                if not speech_group_id:
                    # If no speech_group_id, use a placeholder
                    speech_group_id = "unknown"
                
                if speech_group_id not in speech_groups:
                    speech_groups[speech_group_id] = []
                
                speech_groups[speech_group_id].append(clip)
            
            # Sort clips within each speech group by start time
            for speech_group_id, clips in speech_groups.items():
                speech_groups[speech_group_id] = sorted(clips, key=lambda x: x["start_time"])
            
            # Process each speech group to find continuous speech segments
            speech_blocks = []
            for speech_group_id, clips in speech_groups.items():
                current_block = []
                
                for clip in clips:
                    if not current_block:
                        # Start a new block
                        current_block.append(clip)
                    else:
                        # Check if this clip is continuous with the previous one
                        prev_clip = current_block[-1]
                        # Allow a small gap (e.g., 2 seconds) between clips
                        if float(clip["start_time"]) - float(prev_clip["end_time"]) <= 2.0:
                            current_block.append(clip)
                        else:
                            # This clip starts a new block
                            speech_blocks.append(current_block)
                            current_block = [clip]
                
                # Don't forget the last block
                if current_block:
                    speech_blocks.append(current_block)
            
            logger.info(f"Identified {len(speech_blocks)} speech blocks across {len(speech_groups)} speakers")
            
            # Process each speech block to find the highest confidence member_id
            # But DON'T generate new speech group IDs - preserve the original ones from SQLite
            speech_groups = []
            for block in speech_blocks:
                # Instead of using process_speech_block which generates new speech_group_ids,
                # we'll just find the highest confidence member_id in each block
                if not block:
                    continue
                    
                # Find the member ID with the highest confidence score in this block
                highest_conf = -1
                highest_conf_member_id = None
                
                # First, prioritize segments with numeric member IDs
                for segment in block:
                    if "member_id" in segment and str(segment["member_id"]).isdigit():
                        conf = segment.get("confidence_score", 0)
                        if conf > highest_conf:
                            highest_conf = conf
                            highest_conf_member_id = str(segment["member_id"])
                
                # Fallback if no numeric member_id found
                if highest_conf_member_id is None and block:
                    # Use the first segment's member_id as fallback
                    highest_conf_member_id = block[0].get("member_id")
                
                # Create a simple speech group with just the member_id and segment_ids
                # but DON'T generate a new speech_group_id
                speech_group = {
                    "member_id": highest_conf_member_id,
                    "segment_ids": [segment.get('id') for segment in block if 'id' in segment],
                }
                speech_groups.append(speech_group)
            
            logger.info(f"Created {len(speech_groups)} speech groups with normalized member IDs")
            
            # Update clips with normalized member IDs only (preserve original speech_group_id)
            normalized_clips = []
            for speech_group in speech_groups:
                normalized_member_id = speech_group["member_id"]
                
                # Find all clips in this speech group
                for segment_id in speech_group["segment_ids"]:
                    # Find the clip with this ID
                    for clip in clip_dicts:
                        if clip["id"] == segment_id:
                            # Create a copy with normalized member_id only
                            normalized_clip = clip.copy()
                            normalized_clip["member_id"] = normalized_member_id
                            # DO NOT modify the speech_group_id - keep the original from SQLite
                            normalized_clips.append(normalized_clip)
                            break
            
            logger.info(f"Normalized {len(normalized_clips)} clips with consistent member IDs within speech groups")
            
            # Update the clips in SQLite with normalized member IDs and speech group IDs
            updated_count = 0
            try:
                for clip in normalized_clips:
                    # Only update the member_id, preserve the original speech_group_id
                    update_sql = text("""
                        UPDATE parliament_clips
                        SET member_id = :member_id
                        WHERE id = :id
                    """)
                    
                    db.execute(update_sql, {
                        "member_id": clip["member_id"],
                        "id": clip["id"]
                    })
                    updated_count += 1
                
                db.commit()
                logger.info(f"Updated {updated_count} clips in SQLite with normalized member IDs")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating clips in SQLite: {str(e)}")
                return {"error": f"Error updating clips in SQLite: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Error normalizing member IDs: {str(e)}")
            return {"error": f"Error normalizing member IDs: {str(e)}"}
        
        # Step 3: Export normalized clips to Supabase
        try:
            # Create a Supabase uploader if one wasn't provided
            uploader = supabase_service
            if not uploader:
                try:
                    uploader = SupabaseUploader(use_service_role=True)
                    logger.info("Created new SupabaseUploader instance")
                except Exception as e:
                    logger.error(f"Failed to create SupabaseUploader: {str(e)}")
                    return {"error": f"Failed to create SupabaseUploader: {str(e)}"}
            
            # Skip Supabase validation - we'll just use the normalized member IDs from SQLite
            logger.info("Skipping member ID validation against Supabase - using normalized IDs from SQLite directly")
            
            # Prepare clips for Supabase export
            supabase_clips = []
            skipped_clips = 0
            invalid_member_ids = set()
            
            for clip in normalized_clips:
                # Get member_id and validate it
                member_id = clip["member_id"]
                
                # Skip clips without member_id or with member_id = 0 (unknown)
                if not member_id or member_id == 0:
                    logger.warning(f"Skipping clip with missing or unknown member_id: {clip['id']}")
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
                
                # No validation against Supabase - we trust the normalized member IDs from SQLite
                # Just log the member ID for transparency
                logger.info(f"Exporting clip with member_id {member_id} and duration {clip['duration_seconds']}s")
                
                # Create a clip record for Supabase
                metadata = clip.get("metadata", {})
                supabase_clip = {
                    "id": str(uuid.uuid4()),  # Generate a new UUID for Supabase
                    "member_id": member_id,
                    "transcript": clip["transcript"],
                    "full_video_path": clip.get("full_video_path", ""),  # Get directly from clip, not metadata
                    "start_timestamp": clip["start_time"],
                    "end_timestamp": clip["end_time"],
                    "confidence_score": clip["confidence_score"],
                    "duration_seconds": clip["duration_seconds"],
                    "speech_group_id": clip["speech_group_id"],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": json.dumps(metadata)
                }
                
                supabase_clips.append(supabase_clip)
            
            if not supabase_clips:
                logger.warning("No valid clips to export to Supabase after filtering")
                if invalid_member_ids:
                    logger.warning(f"Invalid member IDs found: {list(invalid_member_ids)}")
                return {
                    "warning": "No valid clips to export", 
                    "normalized": updated_count, 
                    "inserted": 0, 
                    "skipped": skipped_clips
                }
            
            logger.info(f"Prepared {len(supabase_clips)} clips for export to Supabase (skipped {skipped_clips})")
            
            # Export clips to Supabase in smaller batches to avoid transaction issues
            batch_size = 50  # Process in smaller batches
            total_inserted = 0
            
            for i in range(0, len(supabase_clips), batch_size):
                batch = supabase_clips[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(supabase_clips) + batch_size - 1)//batch_size} with {len(batch)} clips")
                
                try:
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
                "normalized": updated_count,
                "inserted": total_inserted,
                "skipped": skipped_clips,
                "total": clip_count
            }
            
        except Exception as e:
            logger.error(f"Error exporting clips to Supabase: {str(e)}")
            return {"error": f"Error exporting clips to Supabase: {str(e)}"}
        
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Error in normalize_and_export_clips: {error_details}")
        logger.error(traceback.format_exc())
        return {"error": error_details}
