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
    
    def __init__(self, db: Session, cache_dir: str = "/app/data/cache"):
        """
        Initialize the matcher
        
        Args:
            db: Database session
            cache_dir: Directory for caching data
        """
        self.db = db
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize Supabase service
        self.supabase = SupabaseService()
        
        # Initialize face recognition service
        self.face_recognition = FaceRecognitionService()
        
        # Initialize photo manager
        self.photo_manager = PhotoManager(
            photos_dir=os.path.join(self.cache_dir, "mp_photos"),
            embeddings_dir=os.path.join(self.cache_dir, "mp_embeddings")
        )
        
        # Initialize member data
        self.members = []
        self.member_embeddings = {}
        self.member_cache_file = os.path.join(self.cache_dir, "parliament_members.json")
    
    def load_parliament_members(self) -> bool:
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
    
    def _load_member_embeddings(self) -> None:
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
                member_id = member.get('id')
                
                if not member_id:
                    logger.warning("Member has no ID, skipping")
                    continue
                
                # Try to load embedding from file
                embedding_file = os.path.join(
                    self.photo_manager.embeddings_dir, 
                    f"{member_id}.json"
                )
                
                if os.path.exists(embedding_file):
                    try:
                        with open(embedding_file, 'r') as f:
                            embedding_data = json.load(f)
                            
                        if 'embedding' in embedding_data:
                            # Convert embedding to numpy array if needed
                            embedding = embedding_data['embedding']
                            if isinstance(embedding, list):
                                embedding = np.array(embedding)
                                
                            self.member_embeddings[member_id] = {
                                'embedding': embedding,
                                'member': member
                            }
                    except Exception as e:
                        logger.warning(f"Error loading embedding for member {member_id}: {str(e)}")
            
            logger.info(f"Loaded {len(self.member_embeddings)} member embeddings")
            
            if len(self.member_embeddings) == 0:
                logger.warning("No member embeddings loaded. Make sure MP photos have been downloaded.")
                logger.warning("Run the download_mp_photos.py script to download MP photos and generate embeddings.")
        except Exception as e:
            logger.error(f"Error loading member embeddings: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def match_face_to_member(self, face_embedding, threshold: float = 0.6) -> Dict[str, Any]:
        """
        Match a face embedding to a parliament member
        
        Args:
            face_embedding: Face embedding vector to match
            threshold: Minimum confidence score for a match (0.0-1.0)
            
        Returns:
            Dictionary with match results
        """
        if not self.member_embeddings:
            logger.error("No member embeddings loaded. Call load_parliament_members() first.")
            return {
                'matched': False,
                'error': "No member embeddings loaded"
            }
        
        return self._match_face_to_member({'embedding': face_embedding}, confidence_threshold=threshold)
    
    def _match_face_to_member(self, face_data: Dict[str, Any], house: str = "unknown", 
                             confidence_threshold: float = 0.6) -> Dict[str, Any]:
        """
        Internal method to match a face to a parliament member
        
        Args:
            face_data: Dictionary with face data including embedding
            house: House ID to filter members by (commons, lords, etc.)
            confidence_threshold: Minimum confidence score for a match (0.0-1.0)
            
        Returns:
            Dictionary with match results
        """
        try:
            # Get face embedding
            face_embedding = face_data.get('embedding')
            if face_embedding is None:
                return {
                    'matched': False,
                    'error': "No face embedding provided"
                }
            
            # Convert to numpy array if needed
            if isinstance(face_embedding, list):
                face_embedding = np.array(face_embedding)
            
            # Check embedding dimensions
            embedding_dim = len(face_embedding) if isinstance(face_embedding, np.ndarray) else -1
            
            # Detect if this is a dlib-based embedding (128 dimensions)
            is_dlib = embedding_dim == 128
            if is_dlib:
                logger.info("Detected dlib-based face embedding (128 dimensions)")
                
                # Adjust confidence threshold for cross-model comparison
                # Dlib and other models may have different similarity distributions
                if confidence_threshold > 0.5:
                    adjusted_threshold = confidence_threshold - 0.2
                    logger.info(f"Adjusting confidence threshold from {confidence_threshold} to {adjusted_threshold} for cross-model comparison")
                    confidence_threshold = adjusted_threshold
            
            # Find best match
            best_match = None
            best_confidence = 0.0
            
            for member_id, data in self.member_embeddings.items():
                member = data.get('member', {})
                member_embedding = data.get('embedding')
                
                if member_embedding is None:
                    continue
                
                # Skip members from different houses if house is specified
                member_house = member.get('house_id', '').lower()
                if house != "unknown" and member_house != house.lower():
                    continue
                
                # Compute similarity
                confidence = compute_similarity(face_embedding, member_embedding)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'member_id': member_id,
                        'name': member.get('name', 'Unknown'),
                        'house_id': member.get('house_id'),
                        'confidence': confidence
                    }
            
            # Return best match if confidence is above threshold
            if best_match and best_confidence >= confidence_threshold:
                best_match['matched'] = True
                return best_match
            else:
                return {
                    'matched': False,
                    'confidence': best_confidence if best_match else 0.0
                }
        except Exception as e:
            logger.error(f"Error matching face to member: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'matched': False,
                'error': str(e)
            }
    
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
            from backend.models.unidentified_speaker import UnidentifiedSpeaker
            
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
                    confidence_threshold=0.5
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
        from backend.models.unidentified_speaker import UnidentifiedSpeaker
        from backend.models.parliament_clip import ParliamentClip
        
        # Get distinct clip IDs with unidentified speakers
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
    
    def __init__(self, db: Session, cache_dir: str = "/app/data/cache"):
        """
        Initialize the matcher
        
        Args:
            db: Database session
            cache_dir: Directory for caching data
        """
        self.db = db
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize Supabase service
        self.supabase = SupabaseService()
        
        # Initialize face recognition service
        self.face_recognition = FaceRecognitionService()
        
        # Initialize photo manager
        self.photo_manager = PhotoManager(
            photos_dir=os.path.join(self.cache_dir, "mp_photos"),
            embeddings_dir=os.path.join(self.cache_dir, "mp_embeddings")
        )
        
        # Initialize member data
        self.members = []
        self.member_embeddings = {}
        self.member_cache_file = os.path.join(self.cache_dir, "parliament_members.json")
    
    def load_parliament_members(self) -> bool:
        """
        Load parliament members from Supabase, cache, or sample data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load members from Supabase, cache, or sample data
            from backend.services.recognition.member_matching.database import load_members
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
    
    def _load_member_embeddings(self) -> None:
        """
        Load embeddings for all members
        """
        self.member_embeddings = {}
        members_with_embeddings = 0
        members_with_photos = 0
        members_missing_data = 0
        
        for member in self.members:
            member_id = member.get('id')
            if not member_id:
                continue
            
            # Check if member has a photo
            has_photo = self.photo_manager.has_photo(member_id)
            if has_photo:
                members_with_photos += 1
            
            # Check if member has an embedding
            has_embedding = self.photo_manager.has_embedding(member_id)
            
            if has_embedding:
                # Load embedding from file
                embedding = self.photo_manager.load_embedding(member_id)
                if embedding is not None:
                    self.member_embeddings[member_id] = embedding
                    members_with_embeddings += 1
                    continue
            
            # If member has a photo but no embedding, generate one
            if has_photo and not has_embedding:
                embedding = self.photo_manager.generate_embedding(member_id)
                if embedding is not None:
                    self.member_embeddings[member_id] = embedding
                    members_with_embeddings += 1
                    continue
            
            # If we get here, the member is missing data
            if not has_photo:
                logger.warning(f"No photo found for member {member.get('display_name')} (ID: {member_id}).")
                logger.warning("Please run download_mp_photos.py script to download all MP photos.")
            
            members_missing_data += 1
        
        logger.info(f"Loaded {len(self.members)} parliament members from Supabase")
        logger.info(f"Members with embeddings: {members_with_embeddings}")
        logger.info(f"Members with photos: {members_with_photos}")
        logger.info(f"Members missing data: {members_missing_data}")
    
    def match_face_to_member(self, face_embedding, threshold: float = 0.6) -> Dict[str, Any]:
        """
        Match a face embedding to a parliament member
        
        Args:
            face_embedding: Face embedding vector to match
            threshold: Minimum confidence score for a match (0.0-1.0)
            
        Returns:
            Dictionary with match results
        """
        # Create a face_data dict with the embedding
        face_data = {"embedding": face_embedding}
        
        # Check if this is likely a dlib embedding (from face_recognition library)
        is_dlib_embedding = False
        if isinstance(face_embedding, list) and len(face_embedding) == 128:
            is_dlib_embedding = True
            logger.info("Detected dlib-based face embedding (128 dimensions)")
            # Use a lower threshold for dlib embeddings as they may not match perfectly with OpenCV embeddings
            adjusted_threshold = 0.4
            logger.info(f"Adjusting confidence threshold from {threshold} to {adjusted_threshold} for cross-model comparison")
        else:
            adjusted_threshold = threshold
        
        # Call the internal method with the face data
        return self._match_face_to_member(face_data, house="unknown", confidence_threshold=adjusted_threshold)
    
    def _match_face_to_member(self, face_data: Dict[str, Any], house: str = "unknown", 
                             confidence_threshold: float = 0.6) -> Dict[str, Any]:
        """
        Internal method to match a face to a parliament member
        
        Args:
            face_data: Dictionary with face data including embedding
            house: House ID to filter members by (commons, lords, etc.)
            confidence_threshold: Minimum confidence score for a match
            
        Returns:
            Dictionary with match results
        """
        if not self.member_embeddings:
            logger.error("No member embeddings loaded. Call load_parliament_members() first.")
            return {
                "success": False,
                "error": "No member embeddings loaded"
            }
        
        # Extract face embedding
        if 'embedding' not in face_data:
            logger.error("No embedding found in face data")
            return {
                "success": False,
                "error": "No embedding found in face data"
            }
        
        face_embedding = face_data['embedding']
        
        # Find the best match
        best_match_id = None
        best_match_score = 0
        best_match_name = None
        best_match_house = None
        
        for member_id, member_embedding in self.member_embeddings.items():
            # Get member details
            member_details = next((m for m in self.members if m.get('id') == member_id), None)
            if not member_details:
                continue
            
            # Check if member is in the specified house
            member_house = member_details.get('house_id')
            if house != "unknown" and member_house and member_house.lower() != house.lower():
                continue
            
            # Compute similarity
            similarity = compute_similarity(face_embedding, member_embedding)
            
            # Update best match if this is better
            if similarity > best_match_score:
                best_match_id = member_id
                best_match_score = similarity
                best_match_name = member_details.get('display_name')
                best_match_house = member_details.get('house_id')
        
        # Check if the best match exceeds the confidence threshold
        if best_match_score >= confidence_threshold:
            logger.info(f"Matched face to member {best_match_name} (ID: {best_match_id}) with confidence {best_match_score:.4f}")
            return {
                "success": True,
                "matched": True,
                "member_id": best_match_id,
                "display_name": best_match_name,
                "house_id": best_match_house,
                "confidence": best_match_score
            }
        else:
            logger.info(f"No match found for face (best score: {best_match_score:.4f}, threshold: {confidence_threshold})")
            return {
                "success": True,
                "matched": False,
                "best_score": best_match_score,
                "threshold": confidence_threshold
            }
    
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
            from backend.models.unidentified_speaker import UnidentifiedSpeaker
            
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
                    confidence_threshold=0.5
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
        from backend.models.unidentified_speaker import UnidentifiedSpeaker
        from backend.models.parliament_clip import ParliamentClip
        
        # Get distinct clip IDs with unidentified speakers
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
