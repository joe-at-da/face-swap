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
        # Look for embeddings in both the standard location and the download_mp_photos.py location
        self.mp_photos_dir = "/app/data/mp_photos"
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
                    logger.debug(f"No embedding found for member {member.get('display_name')} (ID: {member_key})")


            
            logger.info(f"Loaded {len(self.member_embeddings)} member embeddings")
            
            if len(self.member_embeddings) == 0:
                logger.warning("No member embeddings loaded. Make sure MP photos have been downloaded.")
                logger.warning("Run the download_mp_photos.py script to download MP photos and generate embeddings.")
        except Exception as e:
            logger.error(f"Error loading member embeddings: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def match_face_to_member(self, face_embedding, confidence_threshold=0.1, house="unknown", timestamp=None, video_id=None):
        """Match a face embedding to a parliament member.
        
        Args:
            face_embedding: Face embedding vector
            confidence_threshold: Confidence threshold for matching
            house: House ID to filter members by
            timestamp: Optional timestamp of the current frame (for temporal consistency)
            video_id: Optional video ID for tracking speaker history
            
        Returns:
            Dict with match information or None if no match
        """
        try:
            # Initialize speaker history tracking if not already done
            if not hasattr(self, '_speaker_history'):
                self._speaker_history = {}
                logger.info("Initialized speaker history tracking")
                
            # Initialize confidence adjustment tracking if not already done
            if not hasattr(self, '_confidence_adjustments'):
                self._confidence_adjustments = {}
                logger.info("Initialized confidence adjustment tracking")
                
            # Get the match result
            match_result = self._match_face_to_member({'embedding': face_embedding}, house, confidence_threshold)
            
            # Apply temporal consistency if we have timestamp and video_id
            if timestamp is not None and video_id is not None and match_result:
                match_result = self._apply_temporal_consistency(match_result, timestamp, video_id)
                
            return match_result
        except Exception as e:
            logger.error(f"Error matching face to member: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _match_face_to_member(self, face_data: Dict[str, Any], house: str = "unknown", 
                              confidence_threshold: float = 0.1) -> Dict[str, Any]:
        """
        Internal method to match a face to a parliament member
        
        Args:
            face_data: Dictionary with face data including embedding
            house: House ID to filter members by
            confidence_threshold: Confidence threshold for matching
            
        Returns:
            Dictionary with match information
        """
        try:
            # Check if we have member embeddings loaded
            if not self.member_embeddings:
                logger.error("No member embeddings loaded. Call load_parliament_members() first.")
                return {'matched': False, 'error': 'No member embeddings loaded'}
                
            # Get face embedding
            if 'embedding' not in face_data:
                logger.error("No embedding found in face data")
                return {'matched': False, 'error': 'No embedding in face data'}
                
            face_embedding = face_data['embedding']
            
            # Calculate similarity with all members
            similarities = []
            
            for member_id, member_data in self.member_embeddings.items():
                # Skip if no embedding
                if 'embedding' not in member_data:
                    continue
                    
                # Calculate similarity
                similarity = compute_similarity(face_embedding, member_data['embedding'])
                
                # Convert member_id to int if possible for consistent comparison
                try:
                    numeric_id = int(member_id)
                except (ValueError, TypeError):
                    numeric_id = -1  # Use -1 as fallback for non-numeric IDs
                
                # Get member name
                member_name = member_data['member'].get('display_name', 'Unknown')
                if not member_name:
                    member_name = member_data['member'].get('name', 'Unknown')
                
                # Add to similarities list
                similarities.append({
                    'member_id': numeric_id,  # Always use numeric ID
                    'name': member_name,
                    'confidence': float(similarity),
                    'house_id': member_data['member'].get('house_id', house)
                })
            
            # Sort by confidence (highest first)
            similarities.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Get top 5 matches
            top_5 = similarities[:5] if similarities else []
            
            # Get best match
            best_match = top_5[0] if top_5 else None
            best_confidence = best_match['confidence'] if best_match else 0.0
            
            # Calculate confidence gap between top two matches
            confidence_gap = 0.0
            if len(top_5) >= 2:
                confidence_gap = best_confidence - top_5[1]['confidence']
            
            # IMPROVED: Only return a match if confidence is significantly above threshold
            # This helps reduce false positives
            if best_match and best_confidence >= confidence_threshold:
                # Add more metadata to the match for better tracking
                best_match['matched'] = True
                best_match['confidence_gap'] = confidence_gap if len(top_5) >= 2 else 1.0
                best_match['top_alternatives'] = [(m['name'], m['confidence']) for m in top_5[1:3]] if len(top_5) > 1 else []
                best_match['original_threshold'] = confidence_threshold
                
                logger.info(f"Matched {best_match['name']} with confidence {best_confidence:.4f} (threshold: {confidence_threshold:.4f})")
                return best_match
            else:
                return {
                    'matched': False,
                    'confidence': best_confidence if best_match else 0.0,
                    'best_match_id': best_match['member_id'] if best_match else None,
                    'best_match_name': best_match['name'] if best_match else None,
                    'best_match_confidence': best_confidence if best_match else 0.0
                }
        except Exception as e:
            logger.error(f"Error matching face to member: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'matched': False,
                'error': str(e)
            }
            
    def _apply_temporal_consistency(self, match_result: Dict[str, Any], timestamp: float, video_id: str) -> Dict[str, Any]:
        """
        Apply temporal consistency checks to improve speaker differentiation.
        
        This method tracks speaker appearances over time and can adjust confidence
        based on temporal proximity to reduce the likelihood of misattributing
        multiple clips to the same speaker when multiple speakers are present.
        
        Args:
            match_result: The current match result from _match_face_to_member
            timestamp: Current frame timestamp in seconds
            video_id: ID of the current video
            
        Returns:
            Potentially adjusted match result
        """
        # Initialize video history if not already done
        if not hasattr(self, '_video_speaker_history'):
            self._video_speaker_history = {}
            
        # Initialize history for this video
        if video_id not in self._video_speaker_history:
            self._video_speaker_history[video_id] = {
                'speakers': {},
                'last_timestamp': None,
                'speaker_transitions': 0
            }
            
        video_history = self._video_speaker_history[video_id]
        
        # If this is not a match, just record the timestamp and return
        if not match_result.get('matched', False):
            video_history['last_timestamp'] = timestamp
            return match_result
            
        member_id = match_result.get('member_id')
        confidence = match_result.get('confidence', 0.0)
        
        # Initialize speaker history if this is a new speaker
        if member_id not in video_history['speakers']:
            video_history['speakers'][member_id] = {
                'appearances': [],
                'total_duration': 0.0,
                'last_seen': None
            }
            
        speaker_history = video_history['speakers'][member_id]
        
        # Record this appearance
        speaker_history['appearances'].append({
            'timestamp': timestamp,
            'confidence': confidence
        })
        
        # Calculate time since last seen for this speaker
        if speaker_history['last_seen'] is not None:
            time_since_last_seen = timestamp - speaker_history['last_seen']
            speaker_history['total_duration'] += time_since_last_seen
        
        speaker_history['last_seen'] = timestamp
        
        # Check for speaker transition
        if video_history['last_timestamp'] is not None:
            last_speaker_id = None
            
            # Find who was the last speaker
            for spk_id, spk_data in video_history['speakers'].items():
                if spk_data['last_seen'] == video_history['last_timestamp']:
                    last_speaker_id = spk_id
                    break
            
            # If we have a different speaker than last time, it's a transition
            if last_speaker_id is not None and last_speaker_id != member_id:
                video_history['speaker_transitions'] += 1
                logger.info(f"Speaker transition detected: {last_speaker_id} -> {member_id} at {timestamp:.2f}s")
                
                # Check if this transition happened too quickly (potential false positive)
                time_since_last = timestamp - video_history['last_timestamp']
                if time_since_last < 5.0:  # Less than 5 seconds between speakers is suspicious
                    logger.warning(f"Rapid speaker transition detected ({time_since_last:.2f}s). Possible false positive.")
                    
                    # Get the total speaking time for both speakers
                    current_speaker_time = speaker_history['total_duration']
                    last_speaker_time = video_history['speakers'][last_speaker_id]['total_duration'] 
                    
                    # If the last speaker has spoken much more than the current one,
                    # and the confidence is close to the threshold, this might be a false positive
                    if last_speaker_time > (current_speaker_time * 3) and confidence < (match_result['original_threshold'] + 0.15):
                        logger.warning(f"Possible false positive match. Last speaker ({last_speaker_id}) has spoken {last_speaker_time:.2f}s vs current ({member_id}) {current_speaker_time:.2f}s")
                        
                        # Check confidence gap
                        if match_result.get('confidence_gap', 1.0) < 0.2:
                            logger.warning(f"Small confidence gap ({match_result['confidence_gap']:.4f}) detected during rapid speaker transition")
                            
                            # Get the alternatives
                            alternatives = match_result.get('top_alternatives', [])
                            
                            # If the last speaker is among the alternatives, prefer continuity
                            for alt_name, alt_conf in alternatives:
                                alt_id = next((id for id, data in self.member_embeddings.items() 
                                              if data.get('member', {}).get('name') == alt_name), None)
                                
                                if alt_id == last_speaker_id and alt_conf > (confidence - 0.1):
                                    logger.info(f"Maintaining speaker continuity: {alt_name} ({alt_conf:.4f}) instead of {match_result['name']} ({confidence:.4f})")
                                    
                                    # Update the match result to maintain continuity
                                    match_result['member_id'] = last_speaker_id
                                    match_result['name'] = alt_name
                                    match_result['confidence'] = alt_conf
                                    match_result['continuity_adjusted'] = True
                                    break
        
        # Update the last timestamp
        video_history['last_timestamp'] = timestamp
        
        # Add temporal consistency metadata to the match result
        match_result['temporal_metadata'] = {
            'speaker_transitions': video_history['speaker_transitions'],
            'speaker_history_count': len(speaker_history['appearances']),
            'total_speaker_duration': speaker_history['total_duration']
        }
        
        return match_result
        
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
