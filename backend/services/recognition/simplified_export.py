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
import re
from datetime import datetime
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Union

# Import necessary services
from backend.services.integration.supabase_upload import SupabaseUploader
from backend.services.recognition.member_clips import process_speech_block

# Set up logging
logger = logging.getLogger(__name__)

def normalize_and_export_clips(db, video_id: str = None, supabase_service=None):
    """
    Simplified process to normalize and export parliament member clips.
    
    This function:
    1. Retrieves clips from SQLite (optionally filtered by video_id)
    2. Groups clips by speaker and normalizes member IDs within speech groups
    3. Exports the normalized clips to Supabase
    
    Args:
        db: SQLite database session
        video_id: Optional ID of the video to process. If None, processes all clips.
        supabase_service: Optional Supabase service instance
        
    Returns:
        Dict with results of the normalization and export process
    """
    if video_id:
        logger.info(f"Starting simplified normalization and export for video ID {video_id}")
    else:
        logger.info("Starting simplified normalization and export for ALL clips")
    
    try:
        # Check if we're using SQLite - more robust check
        try:
            # First try the standard SQLAlchemy approach
            is_sqlite = hasattr(db.connection().connection, 'execute')
        except Exception as e:
            logger.warning(f"First SQLite check failed: {str(e)}, trying alternative check")
            try:
                # Try alternative check - look at the engine URL
                engine_url = str(db.get_bind().url)
                is_sqlite = 'sqlite' in engine_url.lower()
                logger.info(f"Using alternative SQLite check: {engine_url} -> is_sqlite={is_sqlite}")
            except Exception as e2:
                logger.warning(f"Alternative SQLite check failed: {str(e2)}, assuming not SQLite")
                is_sqlite = False
        
        if not is_sqlite:
            logger.error("Database connection is not SQLite. This function requires an SQLite database connection.")
            return {"error": "This function requires an SQLite database connection"}
        else:
            logger.info("Confirmed SQLite database connection")
        
        # Step 1: Retrieve clips from SQLite (all or filtered by video_id)
        try:
            if video_id:
                # Filter by video_id if provided
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
                    "video_id_str": str(video_id) if video_id is not None else "",
                    "video_id_int": int(video_id) if video_id is not None and str(video_id).isdigit() else -1,
                    "video_id_pattern": f'%"video_id": {video_id}%' if video_id is not None else "%"
                })
                clip_count = result.scalar() or 0
                
                if clip_count == 0:
                    logger.warning(f"No clips found in SQLite for video ID {video_id}")
                    return {"warning": f"No clips found for video ID {video_id}", "normalized": 0}
                
                logger.info(f"Found {clip_count} clips in SQLite for video ID {video_id}")
                
                # Use the exact schema provided with video_id filter
                logger.info("Using exact schema for parliament_clips table with video_id filter")
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
                
                params = {
                    "video_id": video_id, 
                    "video_id_str": str(video_id) if video_id is not None else "",
                    "video_id_int": int(video_id) if video_id is not None and str(video_id).isdigit() else -1,
                    "video_id_pattern": f'%"video_id": {video_id}%' if video_id is not None else "%"
                }
            else:
                # Get all clips if no video_id is provided
                logger.info("Retrieving ALL clips from SQLite")
                
                count_sql = text("SELECT COUNT(*) FROM parliament_clips")
                result = db.execute(count_sql)
                clip_count = result.scalar() or 0
                
                if clip_count == 0:
                    logger.warning("No clips found in SQLite database")
                    return {"warning": "No clips found in SQLite database", "normalized": 0}
                
                logger.info(f"Found {clip_count} total clips in SQLite")
                
                # Query all clips that haven't been exported yet
                logger.info("Using exact schema for parliament_clips table, filtering out already exported clips")
                query_sql = text("""
                    SELECT id, member_id, transcript, full_video_path, start_timestamp, end_timestamp, 
                           confidence_score, duration_seconds, metadata, speech_group_id
                    FROM parliament_clips 
                    WHERE json_extract(metadata, '$.exported') IS NULL OR json_extract(metadata, '$.exported') != 'true'
                    ORDER BY start_timestamp
                """)
                
                params = {}
            
            result = db.execute(query_sql, params)
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
            
            # Process each speech group to find the highest confidence member_id
            # We'll work directly with speech groups instead of creating speech blocks
            normalized_speech_groups = {}
            for speech_group_id, clips in speech_groups.items():
                if not clips:
                    continue
                
                # Find the member ID with the highest confidence score in this speech group
                highest_conf = -1
                highest_conf_member_id = None
                
                # Find the clip with the highest confidence score
                for clip in clips:
                    member_id = clip.get("member_id")
                    if member_id:  # Any non-empty member_id is considered
                        conf = clip.get("confidence_score", 0)
                        if conf > highest_conf:
                            highest_conf = conf
                            highest_conf_member_id = member_id
                
                # If no valid member_id found, skip this speech group
                if highest_conf_member_id is None:
                    logger.warning(f"No valid member_id found in speech group {speech_group_id}, skipping normalization")
                    continue
                
                logger.info(f"Speech group {speech_group_id}: selected member_id {highest_conf_member_id} with confidence {highest_conf}")
                
                # Store the best member_id for this speech group
                normalized_speech_groups[speech_group_id] = {
                    "member_id": highest_conf_member_id,
                    "clips": clips
                }
            
            logger.info(f"Found highest confidence member IDs for {len(normalized_speech_groups)} speech groups")
            
            logger.info(f"Created {len(speech_groups)} speech groups with normalized member IDs")
            
            # Update ALL clips in each speech group with the highest confidence member ID
            # Always preserve original speech_group_id
            normalized_clips = []
            for speech_group_id, group_data in normalized_speech_groups.items():
                normalized_member_id = group_data["member_id"]
                
                # Process all clips in this speech group
                for clip in group_data["clips"]:
                    # Create a copy of the clip
                    normalized_clip = clip.copy()
                    
                    # Update all clips with the highest confidence member_id
                    original_member_id = clip.get("member_id")
                    normalized_clip["member_id"] = normalized_member_id
                    
                    if original_member_id != normalized_member_id:
                        logger.debug(f"Updating clip {clip['id']} from member_id {original_member_id} to {normalized_member_id}")
                    
                    # DO NOT modify the speech_group_id - keep the original from SQLite
                    normalized_clips.append(normalized_clip)
            
            logger.info(f"Normalized {len(normalized_clips)} clips with consistent member IDs within speech groups")
            
            # Update the clips in SQLite with normalized member IDs and speech group IDs
            updated_count = 0
            try:
                for clip in normalized_clips:
                    # Update the member_id for ALL clips in the speech group
                    # Always preserve the original speech_group_id
                    update_sql = text("""
                        UPDATE parliament_clips
                        SET member_id = :member_id
                        WHERE id = :id
                    """)
                    
                    result = db.execute(update_sql, {
                        "member_id": clip["member_id"],
                        "id": clip["id"]
                    })
                    
                    # Check if a row was actually updated
                    if hasattr(result, 'rowcount') and result.rowcount > 0:
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
            
            # Group clips by speech_group_id for export
            logger.info("Grouping normalized clips by speech_group_id before export")
            grouped_clips_by_speech_id = {}
            skipped_clips = 0
            invalid_member_ids = set()
            
            # First pass: group clips by speech_group_id
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
                
                # Get speech_group_id - this is the key for grouping
                speech_group_id = clip.get("speech_group_id")
                if not speech_group_id:
                    logger.warning(f"Clip {clip['id']} has no speech_group_id, using clip ID as group")
                    speech_group_id = f"single_{clip['id']}"
                
                # Add to the appropriate group
                if speech_group_id not in grouped_clips_by_speech_id:
                    grouped_clips_by_speech_id[speech_group_id] = []
                
                # Add the clip to its speech group with the validated member_id
                clip_with_valid_member_id = clip.copy()
                clip_with_valid_member_id["member_id"] = member_id  # Use the validated integer member_id
                grouped_clips_by_speech_id[speech_group_id].append(clip_with_valid_member_id)
            
            logger.info(f"Grouped {len(normalized_clips)} clips into {len(grouped_clips_by_speech_id)} speech groups")
            
            # Second pass: merge clips within each speech group
            supabase_clips = []
            for speech_group_id, group_clips in grouped_clips_by_speech_id.items():
                if not group_clips:
                    continue
                
                # Sort clips by start time
                group_clips.sort(key=lambda x: float(x["start_time"]) if isinstance(x["start_time"], (int, float, str)) else 0)
                
                # Get the member_id (should be the same for all clips in the group after normalization)
                member_id = group_clips[0]["member_id"]
                
                # Find min start and max end timestamps
                min_start = min([float(clip["start_time"]) if isinstance(clip["start_time"], (int, float, str)) else 0 for clip in group_clips])
                max_end = max([float(clip["end_time"]) if isinstance(clip["end_time"], (int, float, str)) else 0 for clip in group_clips])
                
                # Concatenate transcripts, removing any placeholder text
                transcripts = []
                for clip in group_clips:
                    transcript = clip.get("transcript", "")
                    # Skip placeholder text like "EXPORT TEXT" or empty strings
                    if transcript and transcript.strip() and not transcript.strip().upper() == "EXPORT TEXT":
                        transcripts.append(transcript.strip())
                
                concatenated_transcript = " ".join(transcripts)
                
                # Get the highest confidence score
                max_confidence = max([clip.get("confidence_score", 0.0) for clip in group_clips])
                
                # Calculate total duration
                duration = max_end - min_start
                
                # Create a merged clip for Supabase
                metadata = group_clips[0].get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                # Add merged clip metadata
                metadata.update({
                    "speech_group_id": speech_group_id,
                    "merged_clip_count": len(group_clips),
                    "original_clip_ids": [clip.get("id") for clip in group_clips],
                    "merged_at": datetime.now().isoformat()
                })
                
                # Create the merged clip for Supabase
                merged_clip = {
                    "id": str(uuid.uuid4()),  # Generate a new UUID for Supabase
                    "member_id": member_id,
                    "transcript": concatenated_transcript,
                    "full_video_path": group_clips[0].get("full_video_path", ""),
                    "start_timestamp": str(min_start),
                    "end_timestamp": str(max_end),
                    "confidence_score": max_confidence,
                    "duration_seconds": duration,
                    "speech_group_id": speech_group_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": json.dumps(metadata)
                }
                
                logger.info(f"Created merged clip for speech_group_id {speech_group_id} with {len(group_clips)} original clips")
                supabase_clips.append(merged_clip)
            
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
            exported_clip_ids = []  # Track successfully exported clip IDs for cleanup
            
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
                        
                        # If successful, track the clip IDs for later cleanup
                        if inserted > 0:
                            batch_clip_ids = [clip['id'] for clip in batch]
                            exported_clip_ids.extend(batch_clip_ids)
                        
                except Exception as batch_error:
                    logger.error(f"Error processing batch: {str(batch_error)}")
                    # Continue with next batch
            
            # Clean up SQLite database after successful export
            # Mark clips as exported even if they were skipped (already in Supabase)
            clips_to_mark = exported_clip_ids if exported_clip_ids else [clip['id'] for clip in supabase_clips]
            if clips_to_mark:
                try:
                    # Mark clips as exported in SQLite to avoid re-exporting
                    logger.info(f"Marking {len(clips_to_mark)} clips as exported in SQLite")
                    
                    # Option 1: Delete the exported clips from SQLite
                    # This is commented out as it might be too destructive
                    # db.execute(
                    #     text("DELETE FROM parliament_clips WHERE id IN :clip_ids"),
                    #     {"clip_ids": tuple(exported_clip_ids) if len(exported_clip_ids) > 1 else (exported_clip_ids[0],)}
                    # )
                    
                    # Option 2: Mark clips as exported by adding an 'exported' flag to metadata
                    # This preserves the data but prevents re-export
                    for clip_id in clips_to_mark:
                        db.execute(
                            text("""
                                UPDATE parliament_clips 
                                SET metadata = json_set(metadata, '$.exported', 'true', '$.exported_at', :timestamp) 
                                WHERE id = :clip_id
                            """),
                            {"clip_id": clip_id, "timestamp": datetime.now().isoformat()}
                        )
                    
                    db.commit()
                    logger.info(f"Successfully marked {len(clips_to_mark)} clips as exported in SQLite")
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up SQLite after export: {str(cleanup_error)}")
                    # Don't fail the overall process if cleanup fails
            
            logger.info(f"Export complete: {total_inserted} clips inserted, {skipped_clips} skipped")
            return {
                "success": total_inserted > 0,
                "normalized": updated_count,
                "inserted": total_inserted,
                "skipped": skipped_clips,
                "total": clip_count,
                "cleaned_up": len(clips_to_mark)
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
