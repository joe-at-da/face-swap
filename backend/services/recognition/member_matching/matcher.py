"""
Main module for the ParliamentMemberMatcher class
"""
import os
import logging
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from backend.services.integration.supabase_client import SupabaseService
from backend.services.recognition.face_recognition import FaceRecognitionService
from backend.services.recognition.member_matching.embedding import compute_similarity
from backend.services.recognition.member_matching.defaults import get_default_member_for_house
from backend.services.recognition.member_matching.photo_management import PhotoManager
from backend.services.recognition.member_matching.database import (
    load_members_from_supabase,
    load_members_from_cache,
    save_members_to_cache,
    create_speaker_appearance,
    load_members
)

logger = logging.getLogger(__name__)

# Global variable to track if UnidentifiedSpeaker is available
UNIDENTIFIED_SPEAKER_AVAILABLE = False

class ParliamentMemberMatcher:
    """
    Class for matching unidentified speakers with parliament members
    based on facial recognition and other available data.
    
    IMPORTANT: Before using this class, ensure that MP photos have been downloaded
    by running the download_mp_photos.py script. This script downloads photos from
    the UK Parliament website and generates face embeddings for all MPs.
    
    Example:
        # Run this first to download MP photos
        python download_mp_photos.py
        
        # Then use the matcher
        matcher = ParliamentMemberMatcher(db_session)
        matcher.load_parliament_members()
        matcher.match_unidentified_speakers(clip_id)
    """
    
    def __init__(self, db=None, cache_dir="/app/data/cache", supabase_service=None, face_recognition_service=None, photo_manager=None):
        """
        Initialize the matcher
        
        Args:
            db: Database session
            cache_dir: Directory for caching data
            supabase_service: Supabase service
            face_recognition_service: Face recognition service
            photo_manager: Photo manager
        """
        self.db = db
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize Supabase service
        self.supabase = supabase_service or SupabaseService()
        
        # Initialize face recognition service
        self.face_recognition = face_recognition_service or FaceRecognitionService()
        
        # Initialize photo manager
        # Look for embeddings in both the standard location and the download_mp_photos.py location
        self.mp_photos_dir = "/app/data/mp_photos"
        self.photo_manager = photo_manager or PhotoManager(
            photos_dir=os.path.join(self.cache_dir, "mp_photos"),
            embeddings_dir=os.path.join(self.cache_dir, "mp_embeddings")
        )
        
        # Initialize member data
        self.members = []
        self.member_embeddings = {}
        self.member_cache_file = os.path.join(self.cache_dir, "parliament_members.json")
        
        # Always load members on initialization
        self.load_parliament_members()
    
    def load_parliament_members(self):
        """
        Load parliament members from Supabase, cache, or sample data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load members from Supabase, cache, or sample data
            self.members = load_members(self.supabase, self.member_cache_file)
            
            if not self.members:
                logger.error("Failed to load parliament members from any source")
                return False
                
            # Save to cache if loaded from Supabase or sample data
            try:
                save_members_to_cache(self.members, self.member_cache_file)
            except Exception as e:
                logger.warning(f"Could not save members to cache: {str(e)}")
            
            logger.info(f"Successfully loaded {len(self.members)} parliament members")
            
            # Load embeddings for each member
            self._load_member_embeddings()
            
            return True
        except Exception as e:
            logger.error(f"Error loading parliament members: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _load_member_embeddings(self):
        """
        Load embeddings for all members
        """
        try:
            # Check if we have members loaded
            if not self.members:
                logger.error("No parliament members loaded. Call load_parliament_members() first.")
                return
            
            # Reset embeddings
            self.member_embeddings = {}
            
            # Load embeddings for each member
            for member in self.members:
                # Prioritize numeric ID over UUID
                numeric_id = member.get('member_id')  # Numeric ID
                uuid_id = member.get('id')  # UUID
                
                # Skip if no numeric ID
                if not numeric_id:
                    logger.warning(f"Member {uuid_id} has no numeric member_id, skipping")
                    continue
                
                # Convert numeric_id to string for consistent key usage
                member_key = str(numeric_id)
                
                # Try to load embedding from file - first check with numeric ID
                embedding_file = os.path.join(
                    self.photo_manager.embeddings_dir, 
                    f"{numeric_id}.json"
                )
                
                # If not found, check the download_mp_photos.py location with numeric ID
                if not os.path.exists(embedding_file):
                    embedding_file = os.path.join(
                        self.mp_photos_dir,
                        f"{numeric_id}.json"
                    )
                
                # If still not found and we have a UUID, try with that as fallback
                if not os.path.exists(embedding_file) and uuid_id:
                    # Try standard location with UUID
                    embedding_file = os.path.join(
                        self.photo_manager.embeddings_dir, 
                        f"{uuid_id}.json"
                    )
                    
                    # If not found, try download_mp_photos.py location with UUID
                    if not os.path.exists(embedding_file):
                        embedding_file = os.path.join(
                            self.mp_photos_dir,
                            f"{uuid_id}.json"
                        )
                
                if os.path.exists(embedding_file):
                    try:
                        with open(embedding_file, 'r') as f:
                            embedding_data = json.load(f)
                            
                        # Handle both formats: direct array or object with 'embedding' key
                        if isinstance(embedding_data, list):
                            # Direct array format from download_mp_photos.py
                            embedding = np.array(embedding_data)
                        elif isinstance(embedding_data, dict) and 'embedding' in embedding_data:
                            # Object with 'embedding' key format
                            embedding = embedding_data['embedding']
                            if isinstance(embedding, list):
                                embedding = np.array(embedding)
                        else:
                            logger.warning(f"Unknown embedding format for member {member_key}")
                            continue
                        
                        # Store with numeric ID as the primary key
                        self.member_embeddings[member_key] = {
                            'embedding': embedding,
                            'member': member
                        }
                        
                        # Log success
                        logger.debug(f"Loaded embedding for member {member.get('display_name')} (ID: {member_key})")
                    except Exception as e:
                        logger.warning(f"Error loading embedding for member {member_key}: {str(e)}")
                else:
                    logger.debug(f"No embedding file found for member {member_key}")
            
            logger.info(f"Loaded {len(self.member_embeddings)} member embeddings")
        except Exception as e:
            logger.error(f"Error loading member embeddings: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def match_face_to_member(self, face_embedding, confidence_threshold=0.5, house=None):
        """
        Match a face embedding to a parliament member
        
        Args:
            face_embedding: Face embedding
            confidence_threshold: Confidence threshold
            house: House ID to filter by
            
        Returns:
            dict: Match result
        """
        # Create face data dictionary
        face_data = {'embedding': face_embedding}
        
        # Call internal method
        return self._match_face_to_member(face_data, confidence_threshold, house)
    
    def _match_face_to_member(self, face_data, confidence_threshold=0.5, house=None):
        """
        Match a face to a parliament member
        
        Args:
            face_data: Face data
            confidence_threshold: Confidence threshold
            house: House ID to filter by
            
        Returns:
            dict: Match result
        """
        # Get the face embedding
        face_embedding = face_data.get('embedding')
        if face_embedding is None:
            logger.error("No embedding found in face data")
            return {'matched': False}
        
        # Find the best match
        best_match = None
        best_confidence = 0
        
        # Track all matches for debugging
        all_matches = []
        
        # Process all members
        for member in self.members:
            member_id = str(member.get('member_id'))
            member_house = member.get('house_id')
            member_name = member.get('display_name', 'Unknown')
            
            # Skip members from the wrong house if house is specified
            if house is not None and str(member_house) != str(house):
                logger.debug(f"Skipping member {member_id} from house {member_house} (looking for {house})")
                continue
            
            # Skip if no embedding
            if member_id not in self.member_embeddings:
                logger.debug(f"No embedding for member {member_id}")
                continue
            
            # Get the member embedding
            member_embedding = self.member_embeddings[member_id].get('embedding')
            if member_embedding is None:
                logger.debug(f"No embedding data for member {member_id}")
                continue
            
            # Compute similarity
            confidence = compute_similarity(face_embedding, member_embedding)
            
            # Add to all matches for debugging
            all_matches.append({
                'member_id': member_id,
                'name': member_name,
                'confidence': confidence
            })
            
            # Update best match if this is better
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    'member_id': member_id,
                    'name': member_name,
                    'confidence': confidence
                }
        
        # Sort all matches for debugging
        all_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Log top 5 matches for debugging
        if all_matches:
            logger.info(f"Top 5 matches:")
            for i, match in enumerate(all_matches[:5]):
                logger.info(f"{i+1}. {match['name']} (ID: {match['member_id']}): {match['confidence']:.6f}")
        
        # Check if the best match is above the threshold
        if best_match and best_match['confidence'] >= confidence_threshold:
            best_match['matched'] = True
            logger.info(f"Matched {best_match['name']} with confidence {best_match['confidence']:.4f} (threshold: {confidence_threshold:.4f})")
            return best_match
        
        # If no match found, return transparent error
        if not best_match:
            logger.warning(f"No match found above threshold {confidence_threshold}")
            return {'matched': False}
        
        logger.info(f"Best match {best_match['name']} with confidence {best_match['confidence']:.4f} below threshold {confidence_threshold}")
        return {'matched': False}

    def match_unidentified_speakers(self, clip_id: str) -> Dict[str, Any]:
        """
        Match unidentified speakers in a video clip to parliament members
        
        Args:
            clip_id: ID of the parliament clip
            
        Returns:
            Dictionary with results of the matching
        """
        try:
            # Ensure we have member data loaded
            if not self.member_embeddings:
                success = self.load_parliament_members()
                if not success:
                    return {
                        "success": False,
                        "error": "Failed to load parliament members"
                    }
            
            # Get unidentified speaker metadata for this clip
            # Import locally to avoid circular imports
            try:
                from backend.models.unidentified_speaker import UnidentifiedSpeaker
            except ImportError:
                try:
                    # Try alternative import path for Docker environment
                    from models.unidentified_speaker import UnidentifiedSpeaker
                except ImportError:
                    # Try backend.db.models path
                    from backend.db.models.unidentified_speaker import UnidentifiedSpeaker
            
            if not UNIDENTIFIED_SPEAKER_AVAILABLE:
                logger.warning("UnidentifiedSpeaker model not available, skipping query")
                return {}
                
            unidentified_speakers = self.db.query(UnidentifiedSpeaker).filter(
                UnidentifiedSpeaker.clip_id == clip_id
            ).all()
            
            if not unidentified_speakers:
                logger.info(f"No unidentified speakers found for clip {clip_id}")
                return {
                    "success": True,
                    "matched": 0,
                    "unmatched": 0,
                    "total": 0
                }
            
            matched_count = 0
            unmatched_count = 0
            
            # Process each unidentified speaker
            for speaker in unidentified_speakers:
                # Get face data
                face_data = json.loads(speaker.face_data) if speaker.face_data else {}
                
                if not face_data or 'embedding' not in face_data:
                    logger.warning(f"No face embedding found for speaker {speaker.id}")
                    unmatched_count += 1
                    continue
                
                # Match face to member
                match_result = self._match_face_to_member(
                    face_data, 
                    house=speaker.house_id if speaker.house_id else "unknown",
                    confidence_threshold=0.1
                )
                
                if match_result.get('matched'):
                    # Create speaker appearance record
                    create_speaker_appearance(
                        self.db,
                        clip_id=clip_id,
                        member_id=match_result['member_id'],
                        start_time=speaker.start_time,
                        end_time=speaker.end_time,
                        confidence=match_result['confidence'],
                        house_id=match_result.get('house_id')
                    )
                    
                    matched_count += 1
                else:
                    # Use default member for unmatched speakers
                    default_member_id = get_default_member_for_house(
                        speaker.house_id if speaker.house_id else "unknown"
                    )
                    
                    if default_member_id:
                        # Create speaker appearance with default member
                        create_speaker_appearance(
                            self.db,
                            clip_id=clip_id,
                            member_id=default_member_id,
                            start_time=speaker.start_time,
                            end_time=speaker.end_time,
                            confidence=0.0,
                            house_id=speaker.house_id
                        )
                    
                    unmatched_count += 1
            
            logger.info(f"Processed {len(unidentified_speakers)} unidentified speakers for clip {clip_id}")
            logger.info(f"Matched: {matched_count}, Unmatched: {unmatched_count}")
            
            return {
                "success": True,
                "matched": matched_count,
                "unmatched": unmatched_count,
                "total": len(unidentified_speakers)
            }
        except Exception as e:
            logger.error(f"Error matching unidentified speakers: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_default_member_for_house(self, house_id):
        """
        Alias for get_default_member_for_house for backward compatibility
        
        Args:
            house_id: ID of the house (commons, lords, or unknown)
            
        Returns:
            ID of the default member for the house
        """
        return get_default_member_for_house(house_id)
    
    def process_all_unidentified_videos(self) -> Dict[str, Any]:
        """
        Process all unidentified speaker videos
        
        Returns:
            Dictionary with results of the processing
        """
        # Ensure we have member data loaded
        if not self.member_embeddings:
            success = self.load_parliament_members()
            if not success:
                return {
                    "success": False,
                    "error": "Failed to load parliament members"
                }
        
        # Get all clips with unidentified speakers
        # Import locally to avoid circular imports
        try:
            from backend.models.unidentified_speaker import UnidentifiedSpeaker
            from backend.models.parliament_clip import ParliamentClip
        except ImportError:
            try:
                # Try alternative import path for Docker environment
                from models.unidentified_speaker import UnidentifiedSpeaker
                from models.parliament_clip import ParliamentClip
            except ImportError:
                # Try backend.db.models path
                from backend.db.models.unidentified_speaker import UnidentifiedSpeaker
                from backend.db.models.parliament_clip import ParliamentClip
        
        # Get distinct clip IDs with unidentified speakers
        if not UNIDENTIFIED_SPEAKER_AVAILABLE:
            logger.warning("UnidentifiedSpeaker model not available, skipping query")
            return []
            
        clip_ids = self.db.query(UnidentifiedSpeaker.clip_id).distinct().all()
        clip_ids = [c[0] for c in clip_ids]
        
        if not clip_ids:
            logger.info("No clips with unidentified speakers found")
            return {
                "success": True,
                "processed": 0,
                "total": 0
            }
        
        processed_count = 0
        
        # Process each clip
        for clip_id in clip_ids:
            result = self.match_unidentified_speakers(clip_id)
            if result.get('success'):
                processed_count += 1
        
        logger.info(f"Processed {processed_count} out of {len(clip_ids)} clips with unidentified speakers")
        
        return {
            "success": True,
            "processed": processed_count,
            "total": len(clip_ids)
        }
