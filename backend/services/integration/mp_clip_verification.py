#!/usr/bin/env python3
"""
MP Clip Verification Module

This module provides functions to verify that clips with MP associations
are properly exported to Supabase.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from backend.db import models
from backend.services.integration.supabase_integration import SupabaseIntegration
from backend.services.recognition.member_matcher import ParliamentMemberMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_mp_clips_in_supabase(
    video_id: int,
    db_session: Session,
    export_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify that clips with MP associations are properly exported to Supabase.
    
    Args:
        video_id: ID of the video in the database
        db_session: Database session
        export_result: Result from SupabaseIntegration.export_and_upload_recognition
        
    Returns:
        Dictionary with verification results
    """
    # Initialize result
    result = {
        "success": False,
        "mp_clips_count": 0,
        "total_clips_count": 0,
        "mp_ids_found": [],
        "mp_names_found": [],
        "clips_export_path": None,
        "verification_details": {}
    }
    
    try:
        # Get the clips export path from the export result with comprehensive fallback strategy
        clips_export_path = None
        
        # First try the standard path in export_paths dictionary
        if "export_paths" in export_result and isinstance(export_result["export_paths"], dict):
            clips_export_path = export_result["export_paths"].get("clips_export_path")
            if clips_export_path:
                logger.info(f"Found clips_export_path in export_paths: {clips_export_path}")
        
        # If not found in export_paths, try direct access in export_result
        if not clips_export_path and "clips_export_path" in export_result:
            clips_export_path = export_result["clips_export_path"]
            logger.info(f"Found clips_export_path directly in export_result: {clips_export_path}")
            
            # Ensure export_paths exists for consistent structure
            if "export_paths" not in export_result:
                export_result["export_paths"] = {}
            export_result["export_paths"]["clips_export_path"] = clips_export_path
        
        # If still not found, search for any key containing 'clip' and ending with .json
        if not clips_export_path:
            # Try to find any key that might contain clip data
            for key, value in export_result.items():
                if isinstance(value, str) and "clip" in key.lower() and os.path.exists(value) and value.endswith(".json"):
                    clips_export_path = value
                    logger.info(f"Found potential clips export path: {key} -> {clips_export_path}")
                    
                    # Update export_paths for consistency
                    if "export_paths" not in export_result:
                        export_result["export_paths"] = {}
                    export_result["export_paths"]["clips_export_path"] = clips_export_path
                    break
            
            if not clips_export_path:
                logger.error("Could not find any valid clips export path in export_result")
                result["error"] = "No valid clips export path found"
                result["export_result_keys"] = list(export_result.keys())
                return result
            
        # Check if the clips_export_path exists and is valid
        if not clips_export_path or not os.path.exists(clips_export_path):
            logger.warning(f"No valid clips_export_path found: {clips_export_path}")
            result["error"] = "No valid clips_export_path found"
            
            # Try to find alternative paths that might contain clip data
            alternative_paths = []
            
            # Check in export_paths
            for key, path in export_result.get("export_paths", {}).items():
                if isinstance(path, str) and ("clip" in key.lower() or "json" in key.lower()):
                    alternative_paths.append((key, path))
            
            # Check in root of export_result
            for key, path in export_result.items():
                if isinstance(path, str) and ("clip" in key.lower() or "json" in key.lower()) and os.path.exists(path):
                    alternative_paths.append((key, path))
            
            # Look for clips JSON files in common export directories
            data_dir = "/app/data"
            export_dirs = [
                os.path.join(data_dir, "temp", "supabase_export"),
                os.path.join(data_dir, "exports"),
                os.path.join(data_dir, "temp")
            ]
            
            for export_dir in export_dirs:
                if os.path.exists(export_dir):
                    for root, _, files in os.walk(export_dir):
                        for file in files:
                            if file.endswith(".json") and ("clip" in file.lower() or "export" in file.lower()):
                                file_path = os.path.join(root, file)
                                alternative_paths.append(("found_in_exports", file_path))
            
            if alternative_paths:
                logger.info(f"Found {len(alternative_paths)} potential alternative clip paths")
                result["alternative_paths"] = alternative_paths
                
                # Try the alternative paths
                for alt_key, alt_path in alternative_paths:
                    if os.path.exists(alt_path) and alt_path.endswith(".json"):
                        # Verify this is actually a clips JSON file by checking content
                        try:
                            with open(alt_path, "r") as f:
                                sample_content = json.load(f)
                                if isinstance(sample_content, list) and len(sample_content) > 0:
                                    # Check if it has clip-like structure
                                    first_item = sample_content[0]
                                    if isinstance(first_item, dict) and any(key in first_item for key in ["speaker_id", "start_time", "end_time", "transcript"]):
                                        logger.info(f"Using validated alternative path: {alt_key} -> {alt_path}")
                                        clips_export_path = alt_path
                                        
                                        # Update export_paths for consistency
                                        if "export_paths" not in export_result:
                                            export_result["export_paths"] = {}
                                        export_result["export_paths"]["clips_export_path"] = clips_export_path
                                        break
                        except Exception as e:
                            logger.warning(f"Error validating alternative path {alt_path}: {str(e)}")
                            continue
            
            # If we still don't have a valid path, return error
            if not clips_export_path or not os.path.exists(clips_export_path):
                logger.error("Could not find any valid clips export path after checking alternatives")
                return result
        
        # Final check if the file exists and is readable
        if not os.path.exists(clips_export_path):
            logger.error(f"Clips export file does not exist at path: {clips_export_path}")
            result["error"] = f"Clips export file not found at {clips_export_path}"
            return result
            
        # Check if file is readable and has content
        try:
            file_size = os.path.getsize(clips_export_path)
            if file_size == 0:
                logger.error(f"Clips export file exists but is empty: {clips_export_path}")
                result["error"] = f"Clips export file is empty: {clips_export_path}"
                return result
        except Exception as e:
            logger.error(f"Error accessing clips export file: {str(e)}")
            result["error"] = f"Error accessing clips export file: {str(e)}"
            return result
            
        result["clips_export_path"] = clips_export_path
        
        # Load the clips data from the export file with proper error handling
        try:
            with open(clips_export_path, "r") as f:
                clips_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in clips export file: {str(e)}")
            result["error"] = f"Invalid JSON in clips export file: {str(e)}"
            return result
        except Exception as e:
            logger.error(f"Error reading clips export file: {str(e)}")
            result["error"] = f"Error reading clips export file: {str(e)}"
            return result
            
        # Handle different data structures
        if isinstance(clips_data, str):
            logger.warning(f"Clips data is a string, not a list or dictionary: {clips_data}")
            result["error"] = "Clips data is a string, not a list or dictionary"
            result["mp_clips_count"] = 0
            result["total_clips_count"] = 0
            return result
            
        # Handle case where clips_data is a dictionary with a 'clips' key (our empty file format)
        if isinstance(clips_data, dict) and "clips" in clips_data:
            clips_list = clips_data.get("clips", [])
            if not isinstance(clips_list, list):
                logger.warning(f"Clips data 'clips' key is not a list: {type(clips_list)}")
                result["error"] = f"Clips data 'clips' key is not a list: {type(clips_list)}"
                result["mp_clips_count"] = 0
                result["total_clips_count"] = 0
                return result
            clips_data = clips_list
            
        # Ensure clips_data is a list
        if not isinstance(clips_data, list):
            logger.warning(f"Clips data is not a list: {type(clips_data)}")
            result["error"] = f"Clips data is not a list: {type(clips_data)}"
            result["mp_clips_count"] = 0
            result["total_clips_count"] = 0
            return result
            
        # Count clips with MP associations
        mp_clips = [clip for clip in clips_data if isinstance(clip, dict) and clip.get("speaker_id") is not None]
        result["mp_clips_count"] = len(mp_clips)
        result["total_clips_count"] = len(clips_data)
        
        # Get unique MP IDs and names
        mp_ids = set()
        mp_names = set()
        for clip in mp_clips:
            if clip.get("speaker_id"):
                mp_ids.add(clip.get("speaker_id"))
            if clip.get("speaker_name"):
                mp_names.add(clip.get("speaker_name"))
                
        result["mp_ids_found"] = list(mp_ids)
        result["mp_names_found"] = list(mp_names)
        
        # Check if clips were added to Supabase queue
        queue_responses = export_result.get("queue_responses", {})
        clip_creation_response = queue_responses.get("clip_creation", {})
        
        if "error" in clip_creation_response:
            logger.error(f"Error in clip creation queue: {clip_creation_response.get('error')}")
            result["verification_details"]["queue_error"] = clip_creation_response.get("error")
        elif clip_creation_response:
            result["verification_details"]["queue_success"] = True
            result["verification_details"]["queue_response"] = clip_creation_response
            
        # Check if the video has speaker appearances in the database
        speaker_identifications = db_session.query(models.SpeakerIdentification).filter(
            models.SpeakerIdentification.capture_session_id == video_id
        ).all()
        
        speaker_appearances = []
        for identification in speaker_identifications:
            appearances = db_session.query(models.SpeakerAppearance).filter(
                models.SpeakerAppearance.identification_id == identification.id
            ).all()
            speaker_appearances.extend(appearances)
            
        result["verification_details"]["db_speaker_identifications"] = len(speaker_identifications)
        result["verification_details"]["db_speaker_appearances"] = len(speaker_appearances)
        
        # Success criteria:
        # 1. If we have MP clips, they must be added to the queue successfully
        # 2. If we have no MP clips, that's also considered a success (empty export is valid)
        if result["mp_clips_count"] > 0:
            # If we have clips, they must be added to the queue successfully
            result["success"] = "queue_success" in result["verification_details"]
            if not result["success"]:
                result["error"] = "Clips were found but not successfully added to the queue"
        else:
            # No clips is a valid scenario - consider it a success
            result["success"] = True
            result["note"] = "No MP clips found, but this is a valid scenario"
        
        return result
        
    except Exception as e:
        logger.exception(f"Error verifying MP clips: {str(e)}")
        result["error"] = str(e)
        return result

def get_mp_data_summary(db_session: Session) -> Dict[str, Any]:
    """
    Get a summary of MP data in the database.
    
    Args:
        db_session: Database session
        
    Returns:
        Dictionary with MP data summary
    """
    try:
        # Initialize member matcher to access MP data
        member_matcher = ParliamentMemberMatcher(db_session)
        member_matcher.load_parliament_members()
        
        # Get summary data
        result = {
            "total_members": len(member_matcher.members),
            "members_with_photos": 0,
            "members_with_embeddings": 0,
            "members_by_house": {},
            "sample_members": []
        }
        
        # Count members with photos and embeddings
        for member in member_matcher.members:
            # Check if member has photo
            has_photo = member.get("photo_path") is not None and os.path.exists(member.get("photo_path", ""))
            if has_photo:
                result["members_with_photos"] += 1
                
            # Check if member has embedding
            has_embedding = member.get("face_embedding") is not None
            if has_embedding:
                result["members_with_embeddings"] += 1
                
            # Count by house
            house = member.get("house", "unknown")
            if house not in result["members_by_house"]:
                result["members_by_house"][house] = 0
            result["members_by_house"][house] += 1
            
        # Add sample members (first 5)
        for i, member in enumerate(member_matcher.members[:5]):
            result["sample_members"].append({
                "id": member.get("id"),
                "name": member.get("name"),
                "house": member.get("house"),
                "has_photo": member.get("photo_path") is not None,
                "has_embedding": member.get("face_embedding") is not None
            })
            
        return result
        
    except Exception as e:
        logger.exception(f"Error getting MP data summary: {str(e)}")
        return {"error": str(e)}
