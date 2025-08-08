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
from typing import List, Dict, Tuple, Optional, Union, Any
from collections import defaultdict, Counter
from datetime import datetime, timedelta

# Import centralized configuration
try:
    from backend.core.recognition_config import MemberMatcherConfig
except ImportError:
    # Fallback values if config module is not available
    class MemberMatcherConfig:
        MIN_CONFIDENCE_THRESHOLD = 0.5
        MIN_CONFIDENCE_GAP = 0.15
        COOLDOWN_PERIOD = 60
        MAX_CONSECUTIVE_MATCHES = 3
        DIVERSITY_BOOST_FACTOR = 0.05
        MAX_VALID_SIMILARITY = 1.05
        MIN_VALID_SIMILARITY = -1.05
        SIMILARITY_ANOMALY_THRESHOLD = 3.0

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
        self.data_dir = '/app/data'
        photos_dir = os.path.join(self.data_dir, 'mp_photos')
        embeddings_dir = os.path.join(self.data_dir, 'mp_embeddings')  # Default embeddings directory
        
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
        
        # Store the path to the main encodings file and mapping file
        self.mp_encodings_file = os.path.join(self.data_dir, 'mp_encodings.json')
        self.uuid_to_member_id_file = os.path.join(photos_dir, 'uuid_to_member_id.json')
        
        # Matching parameters from centralized configuration
        self.min_confidence_threshold = MemberMatcherConfig.MIN_CONFIDENCE_THRESHOLD
        self.min_confidence_gap = MemberMatcherConfig.MIN_CONFIDENCE_GAP  # Minimum gap between top match and second match
        
        # Diversity promotion parameters from centralized configuration
        self.cooldown_period = MemberMatcherConfig.COOLDOWN_PERIOD  # seconds
        self.max_consecutive_matches = MemberMatcherConfig.MAX_CONSECUTIVE_MATCHES
        self.diversity_boost_factor = MemberMatcherConfig.DIVERSITY_BOOST_FACTOR
        
        # Match history for diversity promotion
        self.match_history = {}
        self.last_match_times = {}
        self.consecutive_matches = {}
        self.video_match_counts = defaultdict(Counter)
        
        # Statistical validation parameters from centralized configuration
        self.max_valid_similarity = MemberMatcherConfig.MAX_VALID_SIMILARITY  # Slightly above 1.0 to allow for floating point errors
        self.min_valid_similarity = MemberMatcherConfig.MIN_VALID_SIMILARITY  # Slightly below -1.0 to allow for floating point errors
        self.similarity_anomaly_threshold = MemberMatcherConfig.SIMILARITY_ANOMALY_THRESHOLD  # Standard deviations from mean
    
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
            
            # First, try to load the UUID to member ID mapping from the dedicated file
            try:
                if os.path.exists(self.uuid_to_member_id_file):
                    logger.info(f"Loading UUID to member ID mapping from {self.uuid_to_member_id_file}")
                    with open(self.uuid_to_member_id_file, 'r') as f:
                        mapping_data = json.load(f)
                        
                    # Process the mapping data
                    for uuid, info in mapping_data.items():
                        if isinstance(info, dict) and 'member_id' in info:
                            member_id = info['member_id']
                            uuid_to_member_id[uuid] = member_id
                            # Also store without dashes for compatibility
                            if '-' in uuid:
                                no_dash_uuid = uuid.replace('-', '')
                                uuid_to_member_id[no_dash_uuid] = member_id
                    
                    logger.info(f"Loaded {len(uuid_to_member_id)} UUID to member ID mappings from {self.uuid_to_member_id_file}")
                else:
                    logger.warning(f"UUID to member ID mapping file not found at {self.uuid_to_member_id_file}")
            except Exception as e:
                logger.error(f"Error loading UUID to member ID mapping: {str(e)}")
            
            # Now load embeddings from mp_encodings.json
            try:
                mp_encodings_data = {}
                if os.path.exists(self.mp_encodings_file):
                    logger.info(f"Loading embeddings from {self.mp_encodings_file}")
                    with open(self.mp_encodings_file, 'r') as f:
                        mp_encodings_data = json.load(f)
                
                    # Process the parallel arrays in mp_encodings.json
                    if all(k in mp_encodings_data for k in ['ids', 'encodings']):
                        ids = mp_encodings_data.get('ids', [])
                        encodings = mp_encodings_data.get('encodings', [])
                        names = mp_encodings_data.get('names', [])
                        
                        if len(ids) == len(encodings):
                            logger.info(f"Found {len(ids)} encodings in mp_encodings.json")
                            mp_encodings_loaded = len(ids)
                            
                            # Build a map from UUID/member_id to embedding
                            for i, id_value in enumerate(ids):
                                if i < len(encodings):
                                    mp_encodings_map[id_value] = encodings[i]
                                    
                                    # If this ID is in our UUID to member ID mapping, also store with the member ID
                                    if id_value in uuid_to_member_id:
                                        member_id = uuid_to_member_id[id_value]
                                        mp_encodings_map[member_id] = encodings[i]
                                        logger.debug(f"Mapped UUID {id_value} to member ID {member_id} for embeddings")
                        else:
                            logger.error(f"Mismatch in mp_encodings.json: {len(ids)} ids vs {len(encodings)} encodings")
                    else:
                        logger.error(f"Missing required keys in mp_encodings.json. Found keys: {list(mp_encodings_data.keys())}")
                else:
                    logger.warning(f"mp_encodings.json not found at {self.mp_encodings_file}")
                    logger.warning(f"Will attempt to load individual embedding files instead")
            except Exception as e:
                logger.error(f"Error loading mp_encodings.json: {str(e)}")
        
            # Build a map from UUID to member ID for reverse lookup
            # First use the mapping from the file, then supplement with in-memory data
            for member in self.members:
                member_id = member.get('id')
                photo_uuid = member.get('photo_uuid')
                if member_id and photo_uuid:
                    # Only add if not already in the mapping from the file
                    if photo_uuid not in uuid_to_member_id:
                        uuid_to_member_id[photo_uuid] = member_id
                        logger.debug(f"Added UUID {photo_uuid} to member ID {member_id} mapping from member data")
                    
                    # Also handle UUIDs without dashes
                    if '-' in photo_uuid:
                        no_dash_uuid = photo_uuid.replace('-', '')
                        if no_dash_uuid not in uuid_to_member_id:
                            uuid_to_member_id[no_dash_uuid] = member_id
                                
            # Now process the member embeddings
            for member in self.members:
                member_id = member.get('id')
                name = member.get('name', 'Unknown')
                photo_uuid = member.get('photo_uuid')
                
                # Skip members without ID
                if not member_id:
                    logger.warning(f"Skipping member without ID: {name}")
                    continue
                
                # Try to get embedding from member data
                embedding = member.get('embedding')
                if embedding:
                    # Validate embedding
                    if self._is_valid_embedding(embedding):
                        self.member_embeddings[member_id] = embedding
                        valid_embeddings += 1
                    else:
                        logger.warning(f"Invalid embedding format for member {name} (ID: {member_id})")
                        invalid_embeddings += 1
                        continue
                
                # Get the numeric member_id if available
                numeric_member_id = member.get('member_id')
                
                # Try to find embedding using member_id directly
                if member_id in mp_encodings_map:
                    # Use the embedding from mp_encodings.json with member_id
                    embedding = mp_encodings_map[member_id]
                    if self._is_valid_embedding(embedding):
                        self.member_embeddings[member_id] = embedding
                        valid_embeddings += 1
                        logger.info(f"Found embedding for member {name} using member_id {member_id} directly")
                        continue
                
                # Try using numeric member_id if available
                elif numeric_member_id and str(numeric_member_id) in mp_encodings_map:
                    embedding = mp_encodings_map[str(numeric_member_id)]
                    if self._is_valid_embedding(embedding):
                        self.member_embeddings[member_id] = embedding
                        valid_embeddings += 1
                        logger.info(f"Found embedding for member {name} using numeric member_id {numeric_member_id}")
                        continue
                
                # If no embedding in member data, try to find in mp_encodings_map using UUID
                elif photo_uuid and photo_uuid in mp_encodings_map:
                    # Use the embedding from mp_encodings.json
                    embedding = mp_encodings_map[photo_uuid]
                    if self._is_valid_embedding(embedding):
                        self.member_embeddings[member_id] = embedding
                        valid_embeddings += 1
                        logger.info(f"Found embedding for member {name} using UUID {photo_uuid}")
                    else:
                        logger.warning(f"Invalid embedding from mp_encodings.json for member {name} (ID: {member_id})")
                        invalid_embeddings += 1
                
                # Try without dashes in UUID
                elif photo_uuid and '-' in photo_uuid and photo_uuid.replace('-', '') in mp_encodings_map:
                    no_dash_uuid = photo_uuid.replace('-', '')
                    embedding = mp_encodings_map[no_dash_uuid]
                    if self._is_valid_embedding(embedding):
                        self.member_embeddings[member_id] = embedding
                        valid_embeddings += 1
                        logger.info(f"Found embedding for member {name} using no-dash UUID {no_dash_uuid}")
                    else:
                        logger.warning(f"Invalid embedding from mp_encodings.json (no-dash UUID) for member {name} (ID: {member_id})")
                        invalid_embeddings += 1
                
                # Try name-based matching as a last resort
                else:
                    # Try to match by name
                    found_match = False
                    if names and len(names) == len(ids):
                        for i, mp_name in enumerate(names):
                            if i < len(ids) and self._name_similarity(name, mp_name) > 0.8:
                                uuid_or_id = ids[i]
                                if uuid_or_id in mp_encodings_map:
                                    embedding = mp_encodings_map[uuid_or_id]
                                    if self._is_valid_embedding(embedding):
                                        self.member_embeddings[member_id] = embedding
                                        valid_embeddings += 1
                                        found_match = True
                                        logger.info(f"Matched member {name} to encoding for {mp_name} by name similarity")
                                        break
                    
                    if not found_match:
                        # Try to load from local file using PhotoManager
                        embedding = self.photo_manager.load_embedding(member_id)
                        if embedding is not None and self._is_valid_embedding(embedding):
                            self.member_embeddings[member_id] = embedding
                            valid_embeddings += 1
                            logger.info(f"Loaded embedding for member {name} (ID: {member_id}) from local file")
                        else:
                            # Try to load using photo_uuid as a last resort
                            if photo_uuid:
                                embedding = self.photo_manager.load_embedding(photo_uuid)
                                if embedding is not None and self._is_valid_embedding(embedding):
                                    self.member_embeddings[member_id] = embedding
                                    valid_embeddings += 1
                                    logger.info(f"Loaded embedding for member {name} (ID: {member_id}) using photo_uuid {photo_uuid}")
                                else:
                                    logger.debug(f"No embedding found for member {name} (ID: {member_id})")
                            else:
                                logger.debug(f"No embedding found for member {name} (ID: {member_id})")
            
            # Log summary
            # We're storing numpy arrays directly in member_embeddings, not dictionaries with source info
            # So we can't count by source type anymore
            
            logger.info(f"Loaded {valid_embeddings} valid embeddings and found {invalid_embeddings} invalid embeddings")
            logger.info(f"Loaded {mp_encodings_loaded} encodings from mp_encodings.json")
            logger.info(f"Loaded {len(self.member_embeddings)} total member embeddings")
            logger.info(f"UUID to member ID mapping contains {len(uuid_to_member_id)} entries")
            
            # Save the final UUID to member ID mapping for debugging purposes
            try:
                debug_mapping_file = os.path.join(self.data_dir, 'debug_uuid_to_member_id.json')
                with open(debug_mapping_file, 'w') as f:
                    json.dump(uuid_to_member_id, f, indent=2)
                logger.info(f"Saved debug UUID to member ID mapping to {debug_mapping_file}")
            except Exception as e:
                logger.error(f"Failed to save debug UUID to member ID mapping: {str(e)}")
            
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
        
        Args:
            similarity: The similarity score to validate
            
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
            Dict mapping member_id to confidence score (0.0 to 1.0)
        """
        confidence_scores = {}
        
        # If no similarities, return empty dict
        if not similarities:
            logger.warning("No similarities provided for confidence calculation")
            return confidence_scores
        
        # Extract similarity values
        similarity_values = [s[1] for s in similarities]
        
        # Get min and max similarity for normalization
        min_similarity = min(similarity_values)
        max_similarity = max(similarity_values)
        similarity_range = max_similarity - min_similarity
        
        # Calculate mean and standard deviation
        mean_similarity = np.mean(similarity_values)
        std_similarity = np.std(similarity_values) if len(similarity_values) > 1 else 0.1
        
        # Calculate confidence scores
        for member_id, similarity in similarities:
            # Method 1: Z-score based confidence (statistical approach)
            if std_similarity > 0:
                z_score = (similarity - mean_similarity) / std_similarity
                # Sigmoid function to map z-score to (0,1)
                z_confidence = 1.0 / (1.0 + np.exp(-z_score * 2))  # Steeper sigmoid for better separation
            else:
                # If all similarities are the same, use a default value
                z_confidence = 0.5
            
            # Method 2: Min-max normalization (linear scaling)
            if similarity_range > 0:
                linear_confidence = (similarity - min_similarity) / similarity_range
            else:
                # If all similarities are the same, use the raw similarity capped to [0,1]
                linear_confidence = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
            
            # Method 3: Absolute threshold (domain knowledge)
            # Similarity values are typically in [-1,1] for cosine similarity
            # Map to [0,1] with a bias toward higher values
            absolute_confidence = max(0.0, min(1.0, (similarity * 0.5) + 0.5))
            
            # Combine methods with weights favoring the most discriminative approach
            if len(similarities) > 5:  # If we have many candidates, statistical approach works better
                confidence = 0.5 * z_confidence + 0.3 * linear_confidence + 0.2 * absolute_confidence
            else:  # With few candidates, absolute values are more reliable
                confidence = 0.2 * z_confidence + 0.3 * linear_confidence + 0.5 * absolute_confidence
            
            # Ensure confidence is in [0,1]
            confidence = max(0.0, min(1.0, confidence))
            
            # Store the confidence score
            confidence_scores[member_id] = confidence
            
            # Log detailed confidence calculation for top matches
            if similarity >= max_similarity * 0.9:  # Only log for top matches
                logger.debug(f"Member {member_id}: similarity={similarity:.4f}, z_conf={z_confidence:.4f}, "
                           f"linear_conf={linear_confidence:.4f}, abs_conf={absolute_confidence:.4f}, "
                           f"final_conf={confidence:.4f}")
        
        return confidence_scores
    
    def _apply_diversity_promotion(self, similarity: float, member_id: str, video_id: Optional[str] = None) -> float:
        """
        Apply diversity promotion to reduce false positives.
        
        Args:
            similarity: The similarity score to adjust
            member_id: The member ID to apply diversity promotion for
            video_id: Optional video ID for tracking matches within a video
            
        Returns:
            Adjusted similarity score
        """
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
        if video_id and video_id in self.video_match_counts and member_id in self.video_match_counts[video_id]:
            # Get count of this member in this video
            member_count = self.video_match_counts[video_id][member_id]
            
            # Apply penalty based on frequency in this video - more aggressive
            if member_count > 3:
                frequency_penalty = self.diversity_boost_factor * (member_count / 10.0)  # Scales with frequency
                similarity -= frequency_penalty
                logger.debug(f"Applied frequency penalty of {frequency_penalty:.2f} for member {member_id} - count: {member_count}, new similarity: {similarity:.2f}")
        
        return similarity
    
    def _match_face_to_member(self, face_embedding: List[float], confidence_threshold: float = 0.5, house: Optional[str] = None, video_id: Optional[str] = None) -> Dict[str, Any]:
        """Match a face embedding to a parliament member.
        
        Args:
            face_embedding: The face embedding to match
            confidence_threshold: Minimum confidence threshold for a match
            house: House identifier ('1' for Commons, '2' for Lords)
            video_id: Optional video ID for diversity promotion
            
        Returns:
            Dict with member information or unidentified member if no match
        """
        start_time = time.time()
        
        if not self.member_embeddings:
            logger.warning("No member embeddings available for matching")
            return self._get_unidentified_member(house)
        
        logger.debug(f"Matching face embedding against {len(self.member_embeddings)} member embeddings")
        
        # Validate the input embedding first
        if not self._is_valid_embedding(face_embedding):
            logger.warning(f"Invalid input face embedding: shape={np.array(face_embedding).shape if face_embedding is not None else 'None'}")
            return self._get_unidentified_member(house)
        
        # Convert face embedding to numpy array and normalize
        try:
            normalized_face_embedding = self._normalize_embedding(face_embedding)
            if not self._is_valid_embedding(normalized_face_embedding):
                logger.warning("Face embedding invalid after normalization")
                return self._get_unidentified_member(house)
        except Exception as e:
            logger.error(f"Error normalizing face embedding: {str(e)}")
            return self._get_unidentified_member(house)
        
        # Calculate similarity scores for all members
        similarities = []
        skipped_embeddings = 0
        
        for member_id, embedding in self.member_embeddings.items():
            # Skip invalid embeddings
            if not self._is_valid_embedding(embedding):
                skipped_embeddings += 1
                continue
                
            # Calculate similarity
            try:
                similarity = compute_similarity(normalized_face_embedding, embedding)
            except Exception as e:
                logger.warning(f"Error computing similarity for member {member_id}: {str(e)}")
                continue
            
            # Validate similarity score
            is_valid, adjusted_similarity = self._validate_similarity(similarity)
            if not is_valid:
                logger.debug(f"Invalid similarity score {similarity} for member {member_id}")
                continue
            
            # Apply diversity promotion
            if video_id:
                adjusted_similarity = self._apply_diversity_promotion(adjusted_similarity, member_id, video_id)
            
            similarities.append((member_id, adjusted_similarity))
        
        if skipped_embeddings > 0:
            logger.warning(f"Skipped {skipped_embeddings} invalid member embeddings")
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Check if we have any matches
        if not similarities:
            logger.warning("No valid similarities found")
            return self._get_unidentified_member(house)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence(similarities)
        
        # Get the top match
        top_match_id, top_similarity = similarities[0]
        top_confidence = confidence_scores[top_match_id]
        
        # Check if the confidence is above the threshold
        if top_confidence < confidence_threshold:
            logger.debug(f"Top match confidence {top_confidence:.4f} below threshold {confidence_threshold:.4f}")
            return self._get_unidentified_member(house)
        
        # Get the second best match if available
        second_confidence = 0.0
        second_match_id = None
        if len(similarities) > 1:
            second_match_id = similarities[1][0]
            second_confidence = confidence_scores[second_match_id]
            
            # Check confidence gap
            confidence_gap = top_confidence - second_confidence
            if confidence_gap < self.min_confidence_gap:
                logger.warning(f"Small confidence gap: {confidence_gap:.4f} between {top_match_id} ({top_confidence:.4f}) and {second_match_id} ({second_confidence:.4f})")
        
        # Check for frequency warnings if video_id is provided
        if video_id and video_id in self.video_match_counts and top_match_id in self.video_match_counts[video_id]:
            match_count = self.video_match_counts[video_id][top_match_id]
            total_matches = sum(self.video_match_counts[video_id].values())
            if match_count > 10 and match_count / total_matches > 0.5:
                logger.warning(f"Member {top_match_id} appears very frequently: {match_count}/{total_matches} matches in video {video_id}")
        
        # Update match history
        self._update_match_history(top_match_id, video_id)
        
        # Get member info
        member_info = self._get_member_info(top_match_id)
        
        # Add confidence and similarity scores
        member_info['confidence'] = top_confidence
        member_info['raw_confidence'] = top_similarity
        member_info['matched'] = True
        
        # Add second best match info for debugging
        if second_match_id:
            member_info['second_best_match'] = {
                'id': second_match_id,
                'confidence': second_confidence,
                'gap': top_confidence - second_confidence
            }
        
        # Log successful match
        logger.info(f"Matched member {member_info['name']} (ID: {top_match_id}) with confidence {top_confidence:.4f}")
        processing_time = time.time() - start_time
        logger.debug(f"Matching completed in {processing_time:.3f}s")
        
        return member_info
    
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
        """Update match history for a member.
        
        Args:
            member_id: The ID of the matched member
            video_id: Optional video ID for tracking matches within a video
        """
        try:
            current_time = time.time()
            
            # Update last match time
            self.last_match_times[member_id] = current_time
            
            # Update consecutive matches
            self.consecutive_matches[member_id] = self.consecutive_matches.get(member_id, 0) + 1
            
            # Reset consecutive matches for other members
            for other_id in self.consecutive_matches:
                if other_id != member_id:
                    self.consecutive_matches[other_id] = 0
            
            # Update video match counts if video_id is provided
            if video_id:
                # Initialize video tracking if this is the first match for this video
                if video_id not in self.video_match_counts:
                    self.video_match_counts[video_id] = defaultdict(int)
                    logger.debug(f"Initialized match tracking for video {video_id}")
                
                # Increment match count for this member in this video
                self.video_match_counts[video_id][member_id] += 1
                
                # Calculate and log diversity statistics
                unique_members = len(self.video_match_counts[video_id])
                total_matches = sum(self.video_match_counts[video_id].values())
                
                # Log detailed stats for this video
                if total_matches % 10 == 0:  # Log every 10 matches to avoid excessive logging
                    logger.debug(f"Video {video_id} diversity stats: {unique_members} unique members, {total_matches} total matches")
                    
                    # Calculate diversity ratio (unique members / total matches)
                    diversity_ratio = unique_members / total_matches if total_matches > 0 else 0
                    
                    # Log warning if diversity is too low (many matches but few unique members)
                    if total_matches > 20 and diversity_ratio < 0.2:
                        logger.warning(f"Low diversity in video {video_id}: {unique_members} unique members in {total_matches} matches (ratio: {diversity_ratio:.2f})")
                        
                    # Log the top 3 most frequent members
                    sorted_counts = sorted(self.video_match_counts[video_id].items(), key=lambda x: x[1], reverse=True)
                    top_members = sorted_counts[:3]
                    logger.debug(f"Top members in video {video_id}: {', '.join([f'{m}({c})' for m, c in top_members])}")
        
        except Exception as e:
            logger.error(f"Error updating match history: {str(e)}")
            # Continue execution despite errors in match history tracking
    
    def _get_member_info(self, member_id: Union[str, int, None]) -> Dict[str, Any]:
        """Get member information from the members list.
        
        Args:
            member_id: The member ID (numeric preferred)
            
        Returns:
            Dict with member information, always containing at least 'id', 'member_id', 'name', and 'house' keys
        """
        if member_id is None:
            logger.warning("Received None member_id in _get_member_info")
            return {
                'id': None,
                'member_id': None,
                'name': 'Unknown (None)',
                'house': 'Unknown'
            }
        
        # Convert to string for comparison if it's not already
        member_id_str = str(member_id)
        
        # First try direct lookup by member_id (numeric ID preferred)
        for member in self.members:
            # Check if the member_id matches (prioritize numeric IDs)
            if str(member.get('member_id')) == member_id_str:
                # Return a copy with guaranteed keys
                member_info = member.copy()
                if 'name' not in member_info:
                    logger.warning(f"Member with ID {member_id} found but missing 'name' key")
                    member_info['name'] = f"Unknown Member ({member_id})"
                if 'house' not in member_info:
                    member_info['house'] = 'Unknown'
                if 'member_id' not in member_info:
                    member_info['member_id'] = member_id
                if 'id' not in member_info:
                    member_info['id'] = member_id
                return member_info
        
        # If not found by member_id, try by id as fallback
        for member in self.members:
            if str(member.get('id')) == member_id_str:
                # Return a copy with guaranteed keys
                member_info = member.copy()
                if 'name' not in member_info:
                    logger.warning(f"Member with ID {member_id} found but missing 'name' key")
                    member_info['name'] = f"Unknown Member ({member_id})"
                if 'house' not in member_info:
                    member_info['house'] = 'Unknown'
                if 'member_id' not in member_info:
                    member_info['member_id'] = member_id
                if 'id' not in member_info:
                    member_info['id'] = member_id
                return member_info
        
        # Log that we couldn't find member info
        logger.warning(f"Could not find member info for ID: {member_id}")
        
        # Return default info if not found
        member_id_display = str(member_id)[:8] if member_id is not None else 'None'
        return {
            'id': member_id,
            'member_id': member_id,
            'name': f"Unknown ({member_id_display})",
            'house': 'Unknown'
        }
    
    def _get_unidentified_member(self, house: Optional[str] = None) -> Dict[str, Any]:
        """Get an unidentified member placeholder for the specified house.
        
        Args:
            house: House identifier ('1' for Commons, '2' for Lords)
            
        Returns:
            Dict with placeholder information for an unidentified member
        """
        # Default member IDs for each house
        default_members = {
            "1": "-1",  # Commons unidentified speaker
            "2": "-2"   # Lords unidentified speaker
        }
        
        # If house is specified, use the default for that house
        member_id = default_members.get(str(house)) if house else default_members.get("1")
        
        # Determine house name for display
        house_name = "Lords" if house == "2" else "Commons"
        
        return {
            'member_id': member_id,
            'id': member_id,
            'name': f"Unidentified Speaker ({house_name})",
            'house': str(house) if house else "1",
            'confidence': 0.0,
            'raw_confidence': 0.0,
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
            
    def _is_valid_embedding(self, embedding: Optional[Union[List[float], np.ndarray]]) -> bool:
        """
        Check if an embedding is valid (not None, correct shape, no NaN or infinity values).
        
        Args:
            embedding: The embedding to validate
            
        Returns:
            bool: True if the embedding is valid, False otherwise
        """
        if embedding is None:
            logger.warning("Embedding is None")
            return False
            
        try:
            # Convert to numpy array if it's not already
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
                
            # Check shape (should be a 1D array with 128 elements for FaceNet)
            if embedding.ndim != 1 or embedding.shape[0] != 128:
                logger.warning(f"Invalid embedding shape: {embedding.shape}, expected (128,)")
                return False
                
            # Check for NaN or infinity values
            if np.isnan(embedding).any() or np.isinf(embedding).any():
                logger.warning("Embedding contains NaN or infinity values")
                return False
                
            # Check for zero norm (all zeros or very small values)
            norm = np.linalg.norm(embedding)
            if norm < 1e-6:
                logger.warning(f"Embedding has near-zero norm: {norm}")
                return False
                
            # Check for unreasonably large values
            max_abs_value = np.max(np.abs(embedding))
            if max_abs_value > 10.0:
                logger.warning(f"Embedding contains unusually large values: max abs = {max_abs_value}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating embedding: {str(e)}")
            return False
            
    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two member names using Jaccard similarity.
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        try:
            # Convert names to lowercase and split into words
            words1 = set(name1.lower().split())
            words2 = set(name2.lower().split())
            
            # Calculate Jaccard similarity: intersection / union
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            if union == 0:
                return 0.0
                
            return intersection / union
            
        except Exception as e:
            logger.error(f"Error calculating name similarity: {str(e)}")
            return 0.0
