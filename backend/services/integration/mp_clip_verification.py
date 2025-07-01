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
        # Get the clips export path from the export result
        clips_export_path = export_result.get("export_paths", {}).get("clips_export_path")
        if not clips_export_path or not os.path.exists(clips_export_path):
            logger.error(f"Clips export file not found: {clips_export_path}")
            result["error"] = "Clips export file not found"
            return result
            
        result["clips_export_path"] = clips_export_path
        
        # Load the clips data from the export file
        with open(clips_export_path, "r") as f:
            clips_data = json.load(f)
            
        # Count clips with MP associations
        mp_clips = [clip for clip in clips_data if clip.get("speaker_id") is not None]
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
        
        # Success if we have MP clips and they were added to the queue
        result["success"] = result["mp_clips_count"] > 0 and "queue_success" in result["verification_details"]
        
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
