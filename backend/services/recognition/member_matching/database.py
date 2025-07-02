"""
Module for handling database interactions for parliament members
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

def load_members_from_supabase(supabase_service) -> List[Dict[str, Any]]:
    """
    Load parliament members from Supabase
    
    Args:
        supabase_service: Supabase service instance
        
    Returns:
        List of parliament members
    """
    try:
        # Initialize Supabase client if needed
        if not hasattr(supabase_service.session, 'client'):
            logger.warning("Supabase session has no client attribute, initializing")
            supabase_service.initialize()
        
        # Fetch members from Supabase
        response = supabase_service.session.client.table('parliament_members').select('*').execute()
        members = response.data
        
        logger.info(f"Loaded {len(members)} parliament members from Supabase")
        return members
    except Exception as e:
        logger.error(f"Error loading parliament members from Supabase: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def load_members_from_cache(cache_file: str) -> List[Dict[str, Any]]:
    """
    Load parliament members from cache file
    
    Args:
        cache_file: Path to cache file
        
    Returns:
        List of parliament members
    """
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                members = json.load(f)
            
            logger.info(f"Loaded {len(members)} parliament members from cache")
            return members
        else:
            logger.warning(f"Cache file {cache_file} not found")
            return []
    except Exception as e:
        logger.error(f"Error loading parliament members from cache: {str(e)}")
        return []

def save_members_to_cache(members: List[Dict[str, Any]], cache_file: str) -> bool:
    """
    Save parliament members to cache file
    
    Args:
        members: List of parliament members
        cache_file: Path to cache file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        with open(cache_file, 'w') as f:
            json.dump(members, f)
        
        logger.info(f"Saved {len(members)} parliament members to cache")
        return True
    except Exception as e:
        logger.error(f"Error saving parliament members to cache: {str(e)}")
        return False

def create_speaker_appearance(db: Session, clip_id: str, member_id: str, 
                             start_time: float, end_time: float, 
                             confidence: float, house_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a speaker appearance record in the database
    
    Args:
        db: Database session
        clip_id: ID of the parliament clip
        member_id: ID of the parliament member
        start_time: Start time of the appearance in seconds
        end_time: End time of the appearance in seconds
        confidence: Confidence score of the match
        house_id: ID of the house (commons, lords, etc.)
        
    Returns:
        Created speaker appearance record
    """
    try:
        from backend.models.speaker_appearance import SpeakerAppearance
        
        # Create speaker appearance
        speaker_appearance = SpeakerAppearance(
            clip_id=clip_id,
            member_id=member_id,
            start_time=start_time,
            end_time=end_time,
            confidence=confidence,
            house_id=house_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add to database
        db.add(speaker_appearance)
        db.commit()
        db.refresh(speaker_appearance)
        
        logger.info(f"Created speaker appearance for member {member_id} in clip {clip_id}")
        return speaker_appearance
    except Exception as e:
        logger.error(f"Error creating speaker appearance: {str(e)}")
        db.rollback()
        import traceback
        logger.error(traceback.format_exc())
        return None
