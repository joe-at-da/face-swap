"""
Module for matching unidentified speakers with parliament members based on facial recognition
"""
import os
import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from backend.services.integration.supabase_client import SupabaseService
from backend.services.recognition.face_recognition import FaceRecognitionService

logger = logging.getLogger(__name__)

class ParliamentMemberMatcher:
    """
    Class for matching unidentified speakers with parliament members
    based on facial recognition and other available data.
    """
    
    def __init__(self, db: Session, supabase_service: SupabaseService):
        """
        Initialize the matcher with database session and Supabase service
        
        Args:
            db: Database session
            supabase_service: Initialized Supabase service with appropriate permissions
        """
        self.db = db
        self.supabase = supabase_service
        self.face_recognition = FaceRecognitionService()
        self.member_embeddings = {}
        self.member_data = {}
        
    def load_parliament_members(self) -> bool:
        """
        Load parliament members data from Supabase and prepare for matching
        
        Returns:
            Boolean indicating success
        """
        try:
            # Fetch all parliament members from Supabase
            response = self.supabase.client.table('parliament_members').select('*').execute()
            
            if not response.data:
                logger.warning("No parliament members found in Supabase")
                return False
                
            logger.info(f"Loaded {len(response.data)} parliament members from Supabase")
            
            # Process each member
            for member in response.data:
                member_id = member.get('id')
                if not member_id:
                    continue
                    
                # Store member data for reference
                self.member_data[member_id] = {
                    'name': member.get('name'),
                    'party': member.get('party_id'),
                    'house': member.get('house_id'),
                    'image_url': member.get('image_url')
                }
                
                # If member has an image URL, process it for face embedding
                image_url = member.get('image_url')
                if image_url:
                    self._process_member_image(member_id, image_url)
            
            logger.info(f"Processed {len(self.member_embeddings)} member images for face matching")
            return True
            
        except Exception as e:
            logger.error(f"Error loading parliament members: {str(e)}")
            return False
            
    def _process_member_image(self, member_id: str, image_url: str) -> None:
        """
        Process a member's image to extract face embedding
        
        Args:
            member_id: ID of the parliament member
            image_url: URL to the member's image
        """
        try:
            # Download image if it's a remote URL
            if image_url.startswith('http'):
                import requests
                from io import BytesIO
                from PIL import Image
                
                response = requests.get(image_url)
                if response.status_code != 200:
                    logger.warning(f"Failed to download image for member {member_id}: {response.status_code}")
                    return
                    
                image = Image.open(BytesIO(response.content))
                image_path = f"/app/data/temp/member_images/{member_id}.jpg"
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
            else:
                # Use local path if it's not a remote URL
                image_path = image_url
                
            # Extract face embedding using the face recognition service
            face_data = self.face_recognition.extract_face_embedding(image_path)
            
            if face_data and 'embedding' in face_data:
                self.member_embeddings[member_id] = face_data['embedding']
                logger.info(f"Successfully extracted face embedding for member {member_id}")
            else:
                logger.warning(f"No face detected in image for member {member_id}")
                
        except Exception as e:
            logger.error(f"Error processing image for member {member_id}: {str(e)}")
            
    def match_unidentified_speakers(self, video_id: int) -> Dict[str, Any]:
        """
        Match unidentified speakers from a video with parliament members
        
        Args:
            video_id: ID of the video with unidentified speakers
            
        Returns:
            Dictionary with results of the matching process
        """
        # Load unidentified speaker metadata
        metadata_file = f"/app/data/temp/unidentified_speakers/unidentified_{video_id}.json"
        
        if not os.path.exists(metadata_file):
            logger.error(f"Unidentified speaker metadata file not found: {metadata_file}")
            return {
                "success": False,
                "error": "Metadata file not found"
            }
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Error loading unidentified speaker metadata: {str(e)}")
            return {
                "success": False,
                "error": f"Error loading metadata: {str(e)}"
            }
            
        # Get the house from session info to narrow down potential matches
        house = metadata.get('session_info', {}).get('house', 'unknown')
        full_video_url = metadata.get('full_video_url', '')
        
        # Initialize results
        matched_clips = []
        failed_matches = []
        
        # Process each segment
        for segment in metadata.get('segments', []):
            clip_id = segment.get('clip_id')
            face_data = segment.get('face_data', {})
            
            # Try to match the face with a parliament member
            match_result = self._match_face_to_member(face_data, house)
            
            if match_result and match_result.get('matched'):
                # We found a match! Create a clip in the parliament_member_clips table
                try:
                    member_id = match_result['member_id']
                    confidence = match_result['confidence']
                    
                    # Create clip data
                    clip_data = {
                        "id": clip_id,
                        "member_id": member_id,
                        "transcript": segment.get('transcript', 'No transcript available'),
                        "full_video_path": full_video_url,
                        "session_date": metadata.get('session_info', {}).get('date', datetime.now().date().isoformat()),
                        "session_type": "parliament_tv",
                        "debate_topic": metadata.get('session_info', {}).get('title', f"Parliament TV Session {video_id}"),
                        "status": "pending_review",
                        "confidence_score": float(confidence),
                        "start_timestamp": segment.get('start_timestamp', '00:00:00'),
                        "end_timestamp": segment.get('end_timestamp', '00:00:00'),
                        "duration_seconds": float(segment.get('duration', 0)),
                        "processing_notes": f"Matched with confidence {confidence:.2f}",
                        "is_deleted": False
                    }
                    
                    # Insert clip into parliament_member_clips table
                    response = self.supabase.client.table('parliament_member_clips').insert(clip_data).execute()
                    
                    if response and hasattr(response, 'data') and response.data:
                        matched_clips.append({
                            "clip_id": clip_id,
                            "member_id": member_id,
                            "confidence": confidence,
                            "member_name": self.member_data.get(member_id, {}).get('name', 'Unknown')
                        })
                        logger.info(f"Saved matched clip {clip_id} for member {member_id} to Supabase")
                    else:
                        failed_matches.append({
                            "clip_id": clip_id,
                            "reason": "Failed to insert clip into Supabase"
                        })
                        
                except Exception as e:
                    logger.error(f"Error saving matched clip {clip_id}: {str(e)}")
                    failed_matches.append({
                        "clip_id": clip_id,
                        "reason": f"Error: {str(e)}"
                    })
            else:
                # No match found
                failed_matches.append({
                    "clip_id": clip_id,
                    "reason": match_result.get('reason', 'No match found')
                })
                
        # Return results
        return {
            "success": True,
            "video_id": video_id,
            "matched_count": len(matched_clips),
            "failed_count": len(failed_matches),
            "matched_clips": matched_clips,
            "failed_matches": failed_matches
        }
        
    def _match_face_to_member(self, face_data: Dict[str, Any], house: str = 'unknown') -> Dict[str, Any]:
        """
        Match a face to a parliament member
        
        Args:
            face_data: Face data from recognition results
            house: House (commons or lords) to filter potential matches
            
        Returns:
            Dictionary with match results
        """
        if not face_data or not isinstance(face_data, dict):
            return {
                "matched": False,
                "reason": "No face data available"
            }
            
        # Extract face embedding from face data
        face_embedding = face_data.get('embedding')
        if not face_embedding:
            return {
                "matched": False,
                "reason": "No face embedding available"
            }
            
        # Convert embedding to numpy array if it's not already
        if isinstance(face_embedding, list):
            face_embedding = np.array(face_embedding)
            
        # Find the best matching member
        best_match_id = None
        best_match_score = 0
        
        for member_id, member_embedding in self.member_embeddings.items():
            # Skip members from different house if house is known
            if house != 'unknown':
                member_house = self.member_data.get(member_id, {}).get('house', '')
                if member_house and member_house.lower() != house.lower():
                    continue
                    
            # Convert member embedding to numpy array if it's not already
            if isinstance(member_embedding, list):
                member_embedding = np.array(member_embedding)
                
            # Calculate similarity score (cosine similarity)
            try:
                similarity = np.dot(face_embedding, member_embedding) / (
                    np.linalg.norm(face_embedding) * np.linalg.norm(member_embedding)
                )
                
                # Update best match if this is better
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_id = member_id
            except Exception as e:
                logger.error(f"Error calculating similarity for member {member_id}: {str(e)}")
                
        # Check if we found a good match
        if best_match_id and best_match_score > 0.7:  # Threshold for a good match
            return {
                "matched": True,
                "member_id": best_match_id,
                "confidence": best_match_score,
                "member_name": self.member_data.get(best_match_id, {}).get('name', 'Unknown')
            }
        else:
            return {
                "matched": False,
                "reason": f"No match found with sufficient confidence (best: {best_match_score:.2f})"
            }
            
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
                
        # Find all unidentified speaker metadata files
        unidentified_dir = "/app/data/temp/unidentified_speakers"
        if not os.path.exists(unidentified_dir):
            return {
                "success": False,
                "error": f"Unidentified speakers directory not found: {unidentified_dir}"
            }
            
        metadata_files = [f for f in os.listdir(unidentified_dir) if f.startswith("unidentified_") and f.endswith(".json")]
        
        if not metadata_files:
            return {
                "success": False,
                "error": "No unidentified speaker metadata files found"
            }
            
        # Process each file
        results = []
        for file in metadata_files:
            try:
                video_id = int(file.replace("unidentified_", "").replace(".json", ""))
                result = self.match_unidentified_speakers(video_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing file {file}: {str(e)}")
                
        # Return overall results
        return {
            "success": True,
            "processed_count": len(results),
            "results": results
        }
