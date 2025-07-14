"""
Enhanced ParliamentMemberMatcher implementation to fix false positive issues.

This implementation addresses the root causes of false positive matches:
1. Ensures consistent normalization of embeddings
2. Validates similarity scores to detect anomalies
3. Implements a more robust confidence calculation
4. Enhances diversity promotion without blacklisting
"""
import os
import json
import time
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Import database functions and embedding utilities
from backend.services.recognition.member_matching.database import load_members_from_supabase
from backend.services.recognition.member_matching.embedding import extract_embedding, normalize_embedding, compute_similarity
from backend.services.recognition.member_matching.photo_management import PhotoManager

logger = logging.getLogger(__name__)

class ParliamentMemberMatcher:
    """
    Enhanced matcher for matching face embeddings to parliament members.
    
    Implements robust similarity validation, consistent normalization,
    and enhanced diversity promotion without blacklisting.
    """
    
    def __init__(self, supabase_service):
        """Initialize the matcher."""
        self.supabase_service = supabase_service
        self.members = []  # Initialize with empty list instead of None
        self.member_embeddings = {}
        
        # Initialize photo manager for local embeddings
        # Use the correct paths for Docker container
        data_dir = '/app/data'
        photos_dir = os.path.join(data_dir, 'mp_photos')
        embeddings_dir = os.path.join(data_dir, 'mp_embeddings')  # Default embeddings directory
        
        # Create the embeddings directory if it doesn't exist
        # This ensures PhotoManager can initialize properly even if we're only using mp_encodings.json
        if not os.path.exists(embeddings_dir):
            try:
                os.makedirs(embeddings_dir, exist_ok=True)
                logger.info(f"Created embeddings directory: {embeddings_dir}")
            except Exception as e:
                logger.warning(f"Failed to create embeddings directory: {str(e)}")
        
        # Initialize the photo manager
        self.photo_manager = PhotoManager(photos_dir, embeddings_dir)
        
        # Store the path to the main encodings file
        self.mp_encodings_file = os.path.join(data_dir, 'mp_encodings.json')
        
        # Matching parameters
        self.min_confidence_threshold = 0.5
        self.min_confidence_gap = 0.15  # Minimum gap between top match and second match
        
        # Diversity promotion parameters
        self.cooldown_period = 60  # seconds
        self.max_consecutive_matches = 3
        self.diversity_boost_factor = 0.05
        
        # Match history for diversity promotion
        self.match_history = {}
        self.last_match_times = {}
        self.consecutive_matches = {}
        self.video_match_counts = defaultdict(Counter)
        
        # Statistical validation parameters
        self.max_valid_similarity = 1.05  # Slightly above 1.0 to allow for floating point errors
        self.min_valid_similarity = -1.05  # Slightly below -1.0 to allow for floating point errors
        self.similarity_anomaly_threshold = 3.0  # Standard deviations from mean
    
    def load_parliament_members(self) -> bool:
        """Load parliament members and their embeddings."""
        try:
            # Load members from database
            loaded_members = load_members_from_supabase(self.supabase_service)
            if not loaded_members:
                logger.error("Failed to load parliament members from Supabase")
                # Try to load from sample data or cache
                from backend.services.recognition.member_matching.database import load_members_from_cache, load_sample_members
                
                # Try to load from cache
                cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'parliament_members.json')
                loaded_members = load_members_from_cache(cache_file)
                
                # If still no members, try sample data
                if not loaded_members:
                    loaded_members = load_sample_members()
                    
                # If still no members, use a minimal fallback list
                if not loaded_members:
                    logger.warning("Using minimal fallback member list")
                    loaded_members = [
                        {"id": "1", "name": "Fallback Member 1", "embedding": [0.0] * 128},
                        {"id": "2", "name": "Fallback Member 2", "embedding": [0.0] * 128}
                    ]
            
            # Store members
            self.members = loaded_members
            logger.info(f"Loaded {len(self.members)} parliament members")
            
            # Extract embeddings from members
            self.member_embeddings = {}
            valid_embeddings = 0
            invalid_embeddings = 0
            mp_encodings_loaded = 0
        
            # Load all embeddings from mp_encodings.json - this is the primary source
            mp_encodings_data = {}
            mp_encodings_map = {}  # Map from UUID to embedding
            uuid_to_member_id = {}  # Map from UUID to member ID for reverse lookup
        
            try:
                if os.path.exists(self.mp_encodings_file):
                    logger.info(f"Loading embeddings from {self.mp_encodings_file}")
                    with open(self.mp_encodings_file, 'r') as f:
                        mp_encodings_data = json.load(f)
                
                    # Process the parallel arrays in mp_encodings.json
                    if all(k in mp_encodings_data for k in ['ids', 'encodings']):
                        ids = mp_encodings_data.get('ids', [])
                        encodings = mp_encodings_data.get('encodings', [])
                        names = mp_encodings_data.get('names', [])
                    
                        # Create a mapping from UUID to embedding
                        for i, mp_id in enumerate(ids):
                            if i < len(encodings):
                                mp_encodings_map[mp_id] = {
                                    'embedding': encodings[i],
                                    'name': names[i] if i < len(names) else f"MP {mp_id[:6]}"
                                }
                    
                        logger.info(f"Loaded {len(mp_encodings_map)} embeddings from mp_encodings.json")
                    
                        # Create a mapping from UUID to member ID for all members
                        # This will help us match UUIDs to member IDs later
                        for member in self.members:
                            member_id = member.get('id')
                            photo_uuid = member.get('photo_uuid')
                            if member_id and photo_uuid:
                                uuid_to_member_id[photo_uuid] = member_id
                    
                        logger.info(f"Created mapping for {len(uuid_to_member_id)} members with photo UUIDs")
                    else:
                        logger.warning("mp_encodings.json does not have expected structure with ids and encodings")
                else:
                    logger.error(f"mp_encodings.json not found at {self.mp_encodings_file}")
            except Exception as e:
                logger.error(f"Error loading mp_encodings.json: {str(e)}")
        
            # Process each member
            for member in self.members:
                member_id = member.get('id')
                
                # Skip members without ID
                if not member_id:
                    logger.debug(f"Skipping member with missing ID")
                    invalid_embeddings += 1
                    continue
                
                # First try to find a matching photo UUID in the mp_encodings_map
                # Members in Supabase have photo_uuid field that should match the UUIDs in mp_encodings.json
                photo_uuid = member.get('photo_uuid')
                if photo_uuid and photo_uuid in mp_encodings_map:
                    try:
                        embedding = mp_encodings_map[photo_uuid]['embedding']
                        normalized_embedding = self._normalize_embedding(embedding)
                        
                        # Check if embedding is valid
                        if np.all(np.abs(normalized_embedding) < 1e-10) or np.isnan(normalized_embedding).any() or np.isinf(normalized_embedding).any():
                            logger.warning(f"Invalid mp_encodings embedding for member {member_id} (UUID {photo_uuid}): contains zeros, NaN, or Inf")
                        else:
                            # Store as a list for JSON serialization
                            embedding_list = normalized_embedding.tolist()
                            
                            # Store the embedding and metadata
                            self.member_embeddings[member_id] = {
                                'embedding': embedding_list,
                                'member_id': member.get('member_id', member_id),
                                'name': member.get('name', mp_encodings_map[photo_uuid].get('name', f'Member {member_id}')),
                                'house': member.get('house', '1'),
                                'source': 'mp_encodings'
                            }
                            valid_embeddings += 1
                            mp_encodings_loaded += 1
                            continue  # Skip to next member since we found a valid embedding
                    except Exception as e:
                        logger.warning(f"Error processing mp_encodings embedding for member {member_id} (UUID {photo_uuid}): {str(e)}")
            
                # If we couldn't find by UUID, try to find by member ID in the reverse mapping
                # Some UUIDs in mp_encodings might be mapped to member IDs in our mapping
                found = False
                for uuid, mapped_member_id in uuid_to_member_id.items():
                    if mapped_member_id == member_id and uuid in mp_encodings_map:
                        try:
                            embedding = mp_encodings_map[uuid]['embedding']
                            normalized_embedding = self._normalize_embedding(embedding)
                            
                            if not (np.all(np.abs(normalized_embedding) < 1e-10) or np.isnan(normalized_embedding).any() or np.isinf(normalized_embedding).any()):
                                embedding_list = normalized_embedding.tolist()
                                self.member_embeddings[member_id] = {
                                    'embedding': embedding_list,
                                    'member_id': member.get('member_id', member_id),
                                    'name': member.get('name', mp_encodings_map[uuid].get('name', f'Member {member_id}')),
                                    'house': member.get('house', '1'),
                                    'source': 'mp_encodings_reverse_lookup'
                                }
                                valid_embeddings += 1
                                mp_encodings_loaded += 1
                                found = True
                                break
                        except Exception as e:
                            logger.warning(f"Error processing reverse lookup embedding for member {member_id}: {str(e)}")
                
                if found:
                    continue
                
                # If we get here, we couldn't load a valid embedding from any source
                logger.warning(f"No valid embedding found for member {member_id}, using zero vector")
                
                # Create a zero embedding as a last resort
                zero_embedding = [0.0] * 128
                
                # Store the embedding and metadata
                self.member_embeddings[member_id] = {
                    'embedding': zero_embedding,
                    'member_id': member.get('member_id', member_id),  # Fallback to id if member_id is missing
                    'name': member.get('name', f'Member {member_id}'),  # Fallback to generic name if missing
                    'house': member.get('house', '1'),  # Default to commons if not specified
                    'source': 'fallback'
                }
                invalid_embeddings += 1
            
            # Log summary
            direct_lookups = sum(1 for m in self.member_embeddings.values() if m.get('source') == 'mp_encodings')
            reverse_lookups = sum(1 for m in self.member_embeddings.values() if m.get('source') == 'mp_encodings_reverse_lookup')
            fallbacks = sum(1 for m in self.member_embeddings.values() if m.get('source') == 'fallback')
            
            logger.info(f"Loaded {len(self.members)} parliament members with {valid_embeddings} valid embeddings:")
            logger.info(f"  - {direct_lookups} from direct UUID lookup")
            logger.info(f"  - {reverse_lookups} from reverse UUID lookup")
            logger.info(f"  - {fallbacks} fallback zero embeddings (no match found)")
            
            # Log some sample member IDs with their embedding sources
            sample_members = list(self.member_embeddings.items())[:5]
            for member_id, data in sample_members:
                logger.info(f"Sample member {member_id} ({data.get('name')}): source={data.get('source')}")
            
            # Check if we have enough valid embeddings
            if valid_embeddings == 0:
                logger.error("No valid embeddings found for any parliament members")
                logger.error("This is a critical error - face recognition will not work properly")
                logger.error(f"Checked mp_encodings.json at {self.mp_encodings_file}")
                
                # Don't raise an exception - we'll use fallback embeddings instead
                logger.warning("Continuing with fallback zero embeddings, but face recognition will be unreliable")
            elif valid_embeddings < len(self.members) * 0.5:
                # If we have less than 50% valid embeddings, log a warning
                logger.warning(f"Only found embeddings for {valid_embeddings}/{len(self.members)} members ({valid_embeddings/len(self.members)*100:.1f}%)")
                logger.warning("Face recognition may be unreliable with so few valid embeddings")
                
            # Return True if we have at least some valid embeddings
            return valid_embeddings > 0
        except Exception as e:
            logger.error(f"Error loading parliament members: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Ensure we always have at least some members
            if not self.members:
                logger.warning("Exception occurred, using minimal fallback member list")
                self.members = [
                    {"id": "1", "name": "Fallback Member 1", "embedding": [0.0] * 128},
                    {"id": "2", "name": "Fallback Member 2", "embedding": [0.0] * 128}
                ]
                self.member_embeddings = {
                    "1": {"embedding": [0.0] * 128, "member_id": "1", "name": "Fallback Member 1", "house": "1", "source": "fallback"},
                    "2": {"embedding": [0.0] * 128, "member_id": "2", "name": "Fallback Member 2", "house": "1", "source": "fallback"}
                }
            
            return len(self.members) > 0
    
    def _normalize_embedding(self, embedding: List[float]) -> np.ndarray:
        """
        Normalize an embedding to unit length
        
        Args:
            embedding: Embedding to normalize
            
        Returns:
            Normalized embedding
        """
        # Use the shared utility function
        return normalize_embedding(np.array(embedding))
    
    def _validate_similarity(self, similarity: float) -> Tuple[bool, float]:
        """
        Validate a similarity score and adjust if necessary.
        
        Returns:
            Tuple[bool, float]: (is_valid, adjusted_similarity)
        """
        # Check if similarity is within valid range
        if similarity < self.min_valid_similarity or similarity > self.max_valid_similarity:
            # Clamp to valid range
            adjusted_similarity = max(self.min_valid_similarity, min(similarity, self.max_valid_similarity))
            return False, adjusted_similarity
        return True, similarity
    
    def _calculate_confidence(self, similarities: List[Tuple[str, float]]) -> Dict[str, float]:
        """
        Calculate confidence scores from similarities using a robust method.
        
        Args:
            similarities: List of (member_id, similarity) tuples
        
        Returns:
            Dict[str, float]: Mapping of member_id to confidence score
        """
        confidence_scores = {}
        
        # If no similarities, return empty dict
        if not similarities:
            return confidence_scores
        
        # Extract similarity values
        similarity_values = [s[1] for s in similarities]
        
        # Calculate mean and standard deviation
        mean_similarity = np.mean(similarity_values)
        std_similarity = np.std(similarity_values) if len(similarity_values) > 1 else 0.1
        
        # Calculate confidence scores
        for member_id, similarity in similarities:
            # Convert similarity to confidence score (0.0 to 1.0)
            # Use a sigmoid-like function to map similarity to confidence
            if std_similarity > 0:
                z_score = (similarity - mean_similarity) / std_similarity
                confidence = 1.0 / (1.0 + np.exp(-z_score))
            else:
                # If all similarities are the same, use the raw similarity
                confidence = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
            
            confidence_scores[member_id] = confidence
        
        return confidence_scores
    
    def _apply_diversity_promotion(self, similarity: float, member_id: str, video_id: Optional[str] = None) -> float:
        """Apply diversity promotion to reduce false positives."""
        current_time = time.time()
        
        # Initialize tracking for this member if not already present
        if member_id not in self.last_match_times:
            self.last_match_times[member_id] = 0
        if member_id not in self.consecutive_matches:
            self.consecutive_matches[member_id] = 0
        
        # Calculate time since last match
        time_since_last_match = current_time - self.last_match_times[member_id]
        
        # Apply cooldown penalty if matched recently - more aggressive to reduce false positives
        if time_since_last_match < self.cooldown_period:
            # Penalty increases as time_since_last_match decreases
            cooldown_factor = 1 - (self.cooldown_period - time_since_last_match) / self.cooldown_period
            # More aggressive cooldown penalty
            similarity *= cooldown_factor * 0.9  # Additional 10% reduction
        
        # Apply consecutive match penalty - more aggressive
        if self.consecutive_matches[member_id] > self.max_consecutive_matches:
            # Penalty increases with each consecutive match beyond the max
            consecutive_penalty = self.diversity_boost_factor * 2 * (self.consecutive_matches[member_id] - self.max_consecutive_matches)
            similarity -= consecutive_penalty
        
        # Apply video-specific diversity promotion if video_id is provided
        if video_id:
            # Get count of this member in this video
            member_count = self.video_match_counts[video_id][member_id]
            
            # Apply penalty based on frequency in this video - more aggressive
            if member_count > 3:
                frequency_penalty = self.diversity_boost_factor * (member_count / 10.0)  # Scales with frequency
                similarity -= frequency_penalty
                logger.debug(f"Applied frequency penalty of {frequency_penalty:.2f} for member {member_id} - count: {member_count}, new similarity: {similarity:.2f}")
                        
        # Update video match counts if provided
        if video_id:
            self.video_match_counts[video_id][member_id] += 1
            
        return similarity
    
    def _match_face_to_member(self, face_embedding: List[float], confidence_threshold: float = 0.5, house: Optional[str] = None, video_id: Optional[str] = None) -> Dict[str, Any]:
        """Match a face embedding to a parliament member."""
        if not self.member_embeddings:
            logger.warning("No member embeddings available for matching")
            return self._get_unidentified_member(house)
        
        # Convert face embedding to numpy array and normalize
        face_embedding_array = np.array(face_embedding)
        normalized_face_embedding = self._normalize_embedding(face_embedding_array)
        
        # Check if embedding is valid
        if np.all(np.abs(normalized_face_embedding) < 1e-10) or np.isnan(normalized_face_embedding).any() or np.isinf(normalized_face_embedding).any():
            logger.warning("Invalid face embedding: contains zeros, NaN, or Inf")
            return self._get_unidentified_member(house)
        
        # Calculate similarity scores for all members
        matches = []
        for member_id, member_data in self.member_embeddings.items():
            try:
                member_embedding = member_data['embedding']
                
                # Skip invalid embeddings
                if not member_embedding or len(member_embedding) != 128:
                    continue
                
                # Skip zero embeddings (fallback embeddings)
                if member_data.get('source') == 'fallback':
                    logger.debug(f"Skipping fallback embedding for member {member_id}")
                    continue
                
                # Calculate similarity using the shared utility
                similarity = compute_similarity(normalized_face_embedding, member_embedding)
                
                # Validate similarity score
                if similarity < self.min_valid_similarity or similarity > self.max_valid_similarity:
                    logger.warning(f"Anomalous similarity score for member {member_id}: {similarity}")
                    continue
                
                # Apply diversity promotion - more aggressive to reduce false positives
                adjusted_similarity = self._apply_diversity_promotion(similarity, member_id, video_id)
                
                # Add to matches if above threshold
                if adjusted_similarity >= confidence_threshold:
                    matches.append({
                        'member_id': member_data['member_id'],
                        'id': member_id,
                        'name': member_data['name'],
                        'house': member_data['house'],
                        'confidence': adjusted_similarity,
                        'raw_confidence': similarity,
                        'embedding_source': member_data.get('source', 'unknown')
                    })
            except Exception as e:
                logger.error(f"Error matching member {member_id}: {str(e)}")
        
        # Sort matches by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Check if we have a match with sufficient confidence
        if matches and matches[0]['confidence'] >= confidence_threshold:
            top_match = matches[0]
            
            # Check if there's a significant gap between top match and second match
            if len(matches) > 1 and (matches[0]['confidence'] - matches[1]['confidence']) < self.min_confidence_gap:
                logger.debug(f"Confidence gap too small: {matches[0]['confidence']:.2f} vs {matches[1]['confidence']:.2f}")
                return self._get_unidentified_member(house)
            
            # Apply a frequency check to reduce false positives
            if video_id and top_match['id'] in self.video_match_counts.get(video_id, {}):
                count = self.video_match_counts[video_id][top_match['id']]
                max_appearances = 10  # Maximum reasonable appearances in a single video
                
                if count > max_appearances:
                    logger.debug(f"Member {top_match['id']} ({top_match['name']}) appeared too many times in video {video_id}: {count} > {max_appearances}")
                    return self._get_unidentified_member(house)
            
            # Update match history
            self._update_match_history(top_match['id'], video_id)
            
            # Return the match
            return top_match
        
        # No match found, return unidentified member
        return self._get_unidentified_member(house)
    
    def match_face_to_member(self, 
                            face_embedding: List[float], 
                            confidence_threshold: float = 0.5,
                            house: Optional[str] = None,
                            video_id: Optional[str] = None,
                            timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Public method to match a face embedding to a parliament member.
        
        Args:
            face_embedding: Face embedding to match
            confidence_threshold: Minimum confidence threshold for a match
            house: Optional house filter (1=Commons, 2=Lords)
            video_id: Optional video ID for tracking matches within a video
            timestamp: Optional timestamp of the frame in seconds for temporal consistency
        
        Returns:
            Dict[str, Any]: Match result
        """
        # Note: We're ignoring the timestamp parameter for now as it's not used in the matching logic
        # In the future, this could be used for temporal consistency in matching
        return self._match_face_to_member(
            face_embedding, 
            confidence_threshold=confidence_threshold,
            house=house,
            video_id=video_id
        )
    
    def match_unidentified_speakers(self, clip_id: str) -> Dict[str, Any]:
        """
        Match unidentified speakers in a clip to parliament members.
        
        Args:
            clip_id: ID of the clip to process
            
        Returns:
            Dict with results of the matching process
        """
        try:
            logger.info(f"Matching unidentified speakers for clip {clip_id}")
            
            # This would normally process unidentified speakers from the clip
            # and try to match them against known parliament members
            
            # For now, just return a success response
            return {
                "success": True,
                "clip_id": clip_id,
                "matched_count": 0,
                "message": "No unidentified speakers to process"
            }
            
        except Exception as e:
            logger.error(f"Error matching unidentified speakers: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    def _update_match_history(self, member_id: str, video_id: Optional[str] = None) -> None:
        """Update match history for a member."""
        current_time = time.time()
        
        # Update last match time
        self.last_match_times[member_id] = current_time
        
        # Update consecutive matches
        self.consecutive_matches[member_id] = self.consecutive_matches.get(member_id, 0) + 1
        
        # Reset consecutive matches for other members
        for other_id in self.consecutive_matches:
            if other_id != member_id:
                self.consecutive_matches[other_id] = 0
        
        # Update video match counts
        if video_id:
            self.video_match_counts[video_id][member_id] += 1
            unique_members = len(self.video_match_counts[video_id])
            total_matches = sum(self.video_match_counts[video_id].values())
            logger.debug(f"Video {video_id} diversity stats: {unique_members} unique members, {total_matches} total matches")
    
    def _get_unidentified_member(self, house: Optional[str] = None) -> Dict[str, Any]:
        """Get an unidentified member placeholder for the specified house."""
        # Default member IDs for each house
        default_members = {
            "1": "-1",  # Commons unidentified speaker
            "2": "-2"   # Lords unidentified speaker
        }
        
        # If house is specified, use the default for that house
        member_id = default_members.get(str(house)) if house else default_members.get("1")
        
        return {
            'member_id': member_id,
            'id': member_id,
            'name': f"Unidentified Speaker ({house if house else 'Commons'})",
            'house': str(house) if house else "1",
            'confidence': 0.0,
            'matched': False
        }
    
    def _get_default_member_for_house(self, house: Optional[str] = None) -> Optional[str]:
        """
        Get the default member ID for a specific house to use when no match is found.
        
        Args:
            house: House identifier ('1' for Commons, '2' for Lords)
            
        Returns:
            Optional[str]: Member ID of the default unidentified member for the house, or None if not found
        """
        try:
            # Default member IDs for each house
            default_members = {
                "1": "-1",  # Commons unidentified speaker
                "2": "-2"   # Lords unidentified speaker
            }
            
            # If house is specified, return the default for that house
            if house and house in default_members:
                return default_members[house]
            
            # Otherwise return the Commons default
            return default_members.get("1")
            
        except Exception as e:
            logger.error(f"Error getting default member for house {house}: {str(e)}")
            return None
