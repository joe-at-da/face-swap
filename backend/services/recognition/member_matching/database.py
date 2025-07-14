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
        # Access the client directly from the SupabaseService instance
        # The SupabaseService class initializes client in __init__
        if not hasattr(supabase_service, 'client') or supabase_service.client is None:
            logger.warning("Supabase service has no client attribute or client is None")
            # Try to reinitialize the client if possible
            if hasattr(supabase_service, 'get_supabase_client') and callable(supabase_service.get_supabase_client):
                supabase_service.client = supabase_service.get_supabase_client(use_service_role=True)
            else:
                # Import and create a new client as last resort
                try:
                    from backend.services.integration.supabase_client import get_supabase_client
                    supabase_service.client = get_supabase_client(use_service_role=True)
                except Exception as e:
                    logger.error(f"Failed to create new Supabase client: {str(e)}")
                    return None
        
        client = supabase_service.client
        
        # Fetch parliament members from Supabase with specific columns to ensure proper data format
        # Include photo_uuid which is essential for matching with mp_encodings.json
        try:
            response = client.table('parliament_members').select('id,member_id,house,embedding,photo_uuid,name').execute()
        except Exception as e:
            logger.error(f"Error with initial query: {str(e)}")
            # Try an even more minimal query as fallback, but still include photo_uuid
            try:
                response = client.table('parliament_members').select('id,member_id,photo_uuid').execute()
            except Exception as e2:
                logger.error(f"Error with fallback query: {str(e2)}")
                return None
        members = response.data
        
        if not members:
            logger.warning("No parliament members found in Supabase")
            return None
            
        # Log sample data structure to help diagnose embedding format issues
        if members and len(members) > 0:
            sample_member = members[0]
            logger.info(f"Sample member structure: {list(sample_member.keys())}")
            
            # Check if embedding exists and log its type
            if 'embedding' in sample_member:
                embedding_type = type(sample_member['embedding']).__name__
                embedding_sample = str(sample_member['embedding'])[:100] + '...' if len(str(sample_member['embedding'])) > 100 else str(sample_member['embedding'])
                logger.info(f"Embedding field type: {embedding_type}, sample: {embedding_sample}")
            else:
                logger.warning("No 'embedding' field found in member data")
        
        logger.info(f"Loaded {len(members)} parliament members from Supabase")
        return members
    except Exception as e:
        logger.error(f"Error loading parliament members from Supabase: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def load_members_from_cache(cache_file: str) -> List[Dict[str, Any]]:
    """
    Load parliament members from cache file
    
    Args:
        cache_file: Path to cache file
        
    Returns:
        List of parliament members
    """
    try:
        if not os.path.exists(cache_file):
            logger.warning(f"Cache file {cache_file} not found")
            return None
            
        with open(cache_file, 'r') as f:
            members = json.load(f)
            
        logger.info(f"Loaded {len(members)} parliament members from cache")
        return members
    except Exception as e:
        logger.error(f"Error loading parliament members from cache: {str(e)}")
        return None

def load_sample_members() -> List[Dict[str, Any]]:
    """
    Load sample parliament members as a last resort
    
    Returns:
        List of sample parliament members
    """
    try:
        # Get the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sample_file = os.path.join(current_dir, 'sample_data', 'parliament_members.json')
        
        if not os.path.exists(sample_file):
            logger.warning(f"Sample data file {sample_file} not found")
            return None
            
        with open(sample_file, 'r') as f:
            members = json.load(f)
            
        logger.info(f"Loaded {len(members)} sample parliament members")
        return members
    except Exception as e:
        logger.error(f"Error loading sample parliament members: {str(e)}")
        return None

def load_members(supabase_service, cache_file: str) -> List[Dict[str, Any]]:
    """
    Load parliament members from Supabase, cache, or sample data
    
    Args:
        supabase_service: Supabase service instance
        cache_file: Path to cache file
        
    Returns:
        List of parliament members
    """
    members = load_members_from_supabase(supabase_service)
    if members is None:
        members = load_members_from_cache(cache_file)
    if members is None:
        members = load_sample_members()
    return members

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
