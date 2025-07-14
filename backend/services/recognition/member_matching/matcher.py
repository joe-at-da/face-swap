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
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Import database functions from the existing module
from backend.services.recognition.member_matching.database import load_members_from_supabase

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
        self.members = []
        self.member_embeddings = {}
        
        # Matching parameters
        self.min_confidence_threshold = 0.5
        self.min_confidence_gap = 0.15
        
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
            self.members = load_members_from_supabase(self.supabase_service)
            if not self.members:
                logger.error("Failed to load parliament members")
                return False
            
            logger.info(f"Successfully loaded {len(self.members)} parliament members")
            
            # Extract embeddings from members
            self.member_embeddings = {}
            for member in self.members:
                member_id = member.get('id')
                embedding = member.get('embedding')
                if member_id and embedding:
                    self.member_embeddings[member_id] = {
                        'embedding': embedding,
                        'member_id': member.get('member_id'),
                        'name': member.get('name', 'Unknown')
                    }
            
            if not self.member_embeddings:
                logger.error("Failed to extract member embeddings")
                return False
            
            logger.info(f"Extracted {len(self.member_embeddings)} member embeddings")
            
            # Validate and normalize all stored embeddings
            self._validate_and_normalize_stored_embeddings()
            
            return True
        except Exception as e:
            logger.error(f"Error loading parliament members: {str(e)}")
            return False
    
    def _validate_and_normalize_stored_embeddings(self):
        """Validate and normalize all stored embeddings."""
        invalid_embeddings = []
        normalized_count = 0
        
        for member_id, data in self.member_embeddings.items():
            if not isinstance(data, dict) or "embedding" not in data:
                invalid_embeddings.append(member_id)
                continue
            
            embedding = np.array(data["embedding"])
            
            # Skip zero embeddings
            if np.all(np.abs(embedding) < 1e-10):
                invalid_embeddings.append(member_id)
                continue
            
            # Check if embedding needs normalization
            norm = np.linalg.norm(embedding)
            if abs(norm - 1.0) > 1e-5:  # If not already normalized
                # Normalize the embedding
                normalized_embedding = embedding / norm
                data["embedding"] = normalized_embedding.tolist()
                normalized_count += 1
        
        if normalized_count > 0:
            logger.info(f"Normalized {normalized_count} member embeddings")
        
        if invalid_embeddings:
            logger.warning(f"Found {len(invalid_embeddings)} invalid member embeddings")
    
    def _normalize_embedding(self, embedding: List[float]) -> np.ndarray:
        """Normalize an embedding to unit length."""
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        
        if norm < 1e-10:
            logger.warning("Received a zero or near-zero embedding")
            return np.zeros_like(embedding_array)
        
        return embedding_array / norm
    
    def _validate_similarity(self, similarity: float) -> Tuple[bool, float]:
        """
        Validate a similarity score and adjust if necessary.
        
        Returns:
            Tuple[bool, float]: (is_valid, adjusted_similarity)
        """
        # Check if similarity is within valid range
        if similarity > self.max_valid_similarity or similarity < self.min_valid_similarity:
            # Clamp to valid range and apply penalty for anomalous values
            adjusted = max(min(similarity, 1.0), -1.0)
            # Apply extra penalty for extremely anomalous values (like the 1.3+)
            if similarity > 1.2 or similarity < -1.2:
                adjusted *= 0.8  # Apply 20% reduction to highly suspicious matches
            return False, adjusted
        
        return True, similarity
    
    def _calculate_confidence(self, similarities: List[Tuple[str, float]]) -> Dict[str, float]:
        """
        Calculate confidence scores from similarities using a robust method.
        
        Args:
            similarities: List of (member_id, similarity) tuples
        
        Returns:
            Dict[str, float]: Mapping of member_id to confidence score
        """
        if not similarities:
            return {}
        
        # Extract valid similarities
        valid_similarities = []
        for member_id, similarity in similarities:
            is_valid = True
            adjusted_similarity = self._validate_similarity(similarity, member_id)
            if not is_valid:
                logger.warning(f"Anomalous similarity detected for member {member_id}: {similarity}, adjusted to {adjusted_similarity}")
            valid_similarities.append((member_id, adjusted_similarity))
        
        if not valid_similarities:
            logger.warning("No valid similarities found")
            return {}
        
        # Map similarities to confidence scores
        # Using a sigmoid-like transformation to map [-1,1] to [0,1]
        confidence_scores = {}
        for member_id, similarity in valid_similarities:
            # Transform similarity to confidence (0.5 * (similarity + 1))
            # This maps -1 to 0, 0 to 0.5, and 1 to 1.0
            confidence = 0.5 * (similarity + 1.0)
            confidence_scores[member_id] = confidence
        
        return confidence_scores
    
    def _apply_diversity_adjustments(self, 
                                    confidence_scores: Dict[str, float], 
                                    video_id: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Apply diversity-promoting adjustments to confidence scores.
        
        Args:
            confidence_scores: Mapping of member_id to confidence score
            video_id: Optional video ID for tracking matches within a video
        
        Returns:
            Dict[str, Dict[str, float]]: Mapping of member_id to adjustment details
        """
        now = time.time()
        adjustments = {}
        
        for member_id, confidence in confidence_scores.items():
            # Initialize adjustment details
            adjustments[member_id] = {
                "original_confidence": confidence,
                "adjusted_confidence": confidence,
                "cooldown_factor": 1.0,
                "diversity_boost": 0.0
            }
            
            # Apply cooldown based on recent matches
            last_match_time = self.last_match_times.get(member_id, 0)
            time_since_last_match = now - last_match_time
            
            if time_since_last_match < self.cooldown_period:
                # Linear cooldown factor (1.0 to 0.7) based on time since last match
                cooldown_factor = 0.7 + 0.3 * (time_since_last_match / self.cooldown_period)
                adjustments[member_id]["cooldown_factor"] = cooldown_factor
                
                # Apply cooldown to confidence
                adjustments[member_id]["adjusted_confidence"] *= cooldown_factor
            
            # Apply consecutive match penalty
            consecutive_matches = self.consecutive_matches.get(member_id, 0)
            if consecutive_matches >= self.max_consecutive_matches:
                # Apply stronger penalty for exceeding max consecutive matches
                consecutive_penalty = 0.2 * (consecutive_matches - self.max_consecutive_matches + 1)
                consecutive_penalty = min(consecutive_penalty, 0.6)  # Cap at 60% reduction
                adjustments[member_id]["adjusted_confidence"] -= consecutive_penalty
                adjustments[member_id]["consecutive_penalty"] = consecutive_penalty
            
            # Apply diversity boost for less frequently matched members
            if video_id:
                # Count matches for this member in this video
                member_matches_in_video = self.video_match_counts[video_id].get(member_id, 0)
                total_matches_in_video = sum(self.video_match_counts[video_id].values())
                
                if total_matches_in_video > 0:
                    # Calculate diversity boost (more boost for less frequently matched members)
                    if member_matches_in_video == 0:
                        # Extra boost for members never matched in this video
                        diversity_boost = self.diversity_boost_factor
                    else:
                        # Reduced boost for previously matched members
                        match_frequency = member_matches_in_video / total_matches_in_video
                        diversity_boost = self.diversity_boost_factor * (1.0 - match_frequency)
                    
                    adjustments[member_id]["diversity_boost"] = diversity_boost
                    adjustments[member_id]["adjusted_confidence"] += diversity_boost
            
            # Ensure confidence stays in valid range
            adjustments[member_id]["adjusted_confidence"] = max(0.0, min(1.0, adjustments[member_id]["adjusted_confidence"]))
        
        return adjustments
    
    def _match_face_to_member(self, 
                             face_embedding: List[float], 
                             confidence_threshold: float = 0.5,
                             house: Optional[str] = None,
                             video_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Match a face embedding to a parliament member.
        
        Args:
            face_embedding: Face embedding to match
            confidence_threshold: Minimum confidence threshold for a match
            house: Optional house filter (1=Commons, 2=Lords)
            video_id: Optional video ID for tracking matches within a video
        
        Returns:
            Dict[str, Any]: Match result
        """
        try:
            # Normalize the face embedding
            normalized_face_embedding = self._normalize_embedding(face_embedding)
            
            # Calculate similarity with all member embeddings
            similarities = []
            
            for member_id, data in self.member_embeddings.items():
                # Skip if not a dict or no embedding
                if not isinstance(data, dict) or "embedding" not in data:
                    continue
                
                # Skip if house filter is applied and member is not in the specified house
                if house is not None:
                    member = next((m for m in self.members if m["id"] == member_id), None)
                    if not member or str(member.get("house")) != str(house):
                        continue
                
                # Get member embedding
                member_embedding = np.array(data["embedding"])
                
                # Skip zero embeddings
                if np.all(np.abs(member_embedding) < 1e-10):
                    continue
                
                # Skip embeddings with different length
                if len(member_embedding) != len(normalized_face_embedding):
                    continue
                
                # Calculate similarity (dot product of normalized vectors)
                similarity = np.dot(normalized_face_embedding, member_embedding)
                
                # Check for anomalous high similarity scores
                if similarity > 0.95:
                    logger.debug(f"Very high similarity detected: {similarity:.4f} for member {member_id}")
                
                # Validate similarity
                is_valid, adjusted_similarity = self._validate_similarity(similarity)
                if not is_valid:
                    logger.warning(f"Anomalous similarity detected for member {member_id}: {similarity}, adjusted to {adjusted_similarity}")
                    similarity = adjusted_similarity
                
                similarities.append((member_id, similarity))
            
            # Sort similarities in descending order
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence(similarities)
            
            # Apply diversity adjustments
            adjustments = self._apply_diversity_adjustments(confidence_scores, video_id)
            
            # Sort members by adjusted confidence
            sorted_members = sorted(
                adjustments.items(),
                key=lambda x: x[1]["adjusted_confidence"],
                reverse=True
            )
            
            # Log top 5 matches with adjustment details
            logger.info("Top 5 matches (with diversity adjustments):")
            for i, (member_id, details) in enumerate(sorted_members[:5]):
                member = next((m for m in self.members if m["id"] == member_id), {"name": "Unknown"})
                name = member.get("name", "Unknown")
                orig_conf = details["original_confidence"]
                adj_conf = details["adjusted_confidence"]
                cooldown = details["cooldown_factor"]
                boost = details.get("diversity_boost", 0.0)
                logger.info(f"{i+1}. {name} (ID: {member_id}): orig={orig_conf:.4f}, adj={adj_conf:.4f}, cooldown={cooldown:.2f}, boost={boost:.2f}")
            
            # Check if we have any matches above threshold
            if not sorted_members:
                logger.info("No matches found")
                return {"matched": False}
            
            # Get best match
            best_match_id, best_match_details = sorted_members[0]
            best_match_confidence = best_match_details["original_confidence"]
            best_match_adjusted = best_match_details["adjusted_confidence"]
            
            # Get second best match for confidence gap calculation
            second_best_adjusted = 0.0
            if len(sorted_members) > 1:
                second_best_adjusted = sorted_members[1][1]["adjusted_confidence"]
            
            # Calculate confidence gap
            confidence_gap = best_match_adjusted - second_best_adjusted
            
            # Apply general threshold adjustment based on confidence gap between top matches
            if best_match_id and len(sorted_members) >= 2:
                top_confidence = sorted_members[0][1]["adjusted_confidence"]
                second_confidence = sorted_members[1][1]["adjusted_confidence"]
                confidence_gap = top_confidence - second_confidence
                
                if confidence_gap < 0.02:  # Very small gap between top matches
                    confidence_threshold = max(confidence_threshold, 0.92)
                    logger.info(f"Small confidence gap ({confidence_gap:.4f}), increasing threshold to {confidence_threshold:.4f}")
                elif confidence_gap < 0.05:  # Small gap between top matches
                    confidence_threshold = max(confidence_threshold, 0.90)
                    logger.info(f"Small confidence gap ({confidence_gap:.4f}), increasing threshold to {confidence_threshold:.4f}")
            
            # Check if best match meets threshold and confidence gap
            if best_match_adjusted >= confidence_threshold and confidence_gap >= self.min_confidence_gap:
                # Get member details
                member = next((m for m in self.members if m["id"] == best_match_id), None)
                
                if member:
                    # Update match history
                    self.last_match_times[best_match_id] = time.time()
                    self.consecutive_matches[best_match_id] = self.consecutive_matches.get(best_match_id, 0) + 1
                    
                    # Reset consecutive matches for other members
                    for other_id in self.consecutive_matches:
                        if other_id != best_match_id:
                            self.consecutive_matches[other_id] = 0
                    
                    # Update video match counts
                    if video_id:
                        self.video_match_counts[video_id][best_match_id] += 1
                    
                    # Log match details
                    logger.info(f"Consecutive match #{self.consecutive_matches[best_match_id]} for member {best_match_id}")
                    logger.info(f"Matched {member['name']} with original confidence {best_match_confidence:.4f}, adjusted to {best_match_adjusted:.4f} (threshold: {confidence_threshold:.4f}, gap: {confidence_gap:.4f})")
                    
                    # Log diversity stats
                    if video_id:
                        unique_members = len(self.video_match_counts[video_id])
                        total_matches = sum(self.video_match_counts[video_id].values())
                        logger.info(f"Diversity stats: {unique_members} unique members matched out of {total_matches} total matches")
                    
                    # Return match result
                    return {
                        "member_id": best_match_id,
                        "name": member["name"],
                        "confidence": best_match_confidence,
                        "adjusted_confidence": best_match_adjusted,
                        "matched": True,
                        "confidence_gap": confidence_gap
                    }
            
            # Log no match
            logger.info(f"Best match {next((m['name'] for m in self.members if m['id'] == best_match_id), 'Unknown')} with adjusted confidence {best_match_adjusted:.4f} below threshold {confidence_threshold}")
            return {"matched": False}
        
        except Exception as e:
            logger.error(f"Error matching face to member: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"matched": False, "error": str(e)}
    
    def match_face_to_member(self, 
                            face_embedding: List[float], 
                            confidence_threshold: float = 0.5,
                            house: Optional[str] = None,
                            video_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Public method to match a face embedding to a parliament member.
        
        Args:
            face_embedding: Face embedding to match
            confidence_threshold: Minimum confidence threshold for a match
            house: Optional house filter (1=Commons, 2=Lords)
            video_id: Optional video ID for tracking matches within a video
        
        Returns:
            Dict[str, Any]: Match result
        """
        return self._match_face_to_member(
            face_embedding, 
            confidence_threshold=confidence_threshold,
            house=house,
            video_id=video_id
        )
