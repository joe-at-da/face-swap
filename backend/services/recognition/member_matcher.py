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
            
    def match_unidentified_speakers(self, video_id: int, save_unmatched: bool = True) -> Dict[str, Any]:
        """
        Match unidentified speakers from a video with parliament members
        
        Args:
            video_id: ID of the video with unidentified speakers
            save_unmatched: If True, save clips even when face matching fails
            
        Returns:
            Dictionary with results of the matching process
        """
        # Ensure we have member data loaded
        if not self.member_embeddings:
            success = self.load_parliament_members()
            if not success:
                return {
                    "success": False,
                    "error": "Failed to load parliament members"
                }
                
        # Load unidentified speaker metadata
        metadata_file = f"/app/data/temp/unidentified_speakers/unidentified_{video_id}.json"
        if not os.path.exists(metadata_file):
            return {
                "success": False,
                "error": f"Metadata file not found: {metadata_file}"
            }
            
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        except Exception as e:
            return {
                "success": False,
                "error": f"Error loading metadata file: {str(e)}"
            }
            
        # Get video metadata
        full_video_url = metadata.get('full_video_url', '')
        session_info = metadata.get('session_info', {})
        house = session_info.get('house', 'unknown')
        
        # Process each segment
        segments = metadata.get('segments', [])
        matched_clips = []
        unmatched_clips = []
        failed_clips = []
        
        for segment in segments:
            clip_id = segment.get('clip_id')
            face_data = segment.get('face_data', {})
            
            # Try to match the face to a member
            match_result = self._match_face_to_member(face_data, house)
            
            # Prepare base clip data regardless of match result
            clip_data = {
                'video_id': video_id,
                'start_time': segment.get('start_time'),
                'end_time': segment.get('end_time'),
                'start_timestamp': segment.get('start_timestamp'),
                'end_timestamp': segment.get('end_timestamp'),
                'duration': segment.get('duration'),
                'transcript': segment.get('transcript', ''),
                'clip_url': f"{full_video_url}#t={segment.get('start_time')},{segment.get('end_time')}",
                'created_at': datetime.now().isoformat()
            }
            
            if match_result['matched']:
                # Add matched member information
                clip_data['member_id'] = match_result['member_id']
                clip_data['match_confidence'] = match_result['confidence']
                
                try:
                    # Insert the clip into Supabase
                    response = self.supabase.client.table('parliament_member_clips').insert(clip_data).execute()
                    
                    if response.data:
                        matched_clips.append({
                            'clip_id': clip_id,
                            'member_id': match_result['member_id'],
                            'member_name': match_result['member_name'],
                            'confidence': match_result['confidence']
                        })
                    else:
                        failed_clips.append({
                            'clip_id': clip_id,
                            'reason': 'Failed to insert matched clip into Supabase'
                        })
                except Exception as e:
                    failed_clips.append({
                        'clip_id': clip_id,
                        'reason': f"Error inserting matched clip into Supabase: {str(e)}"
                    })
            elif save_unmatched:
                # For unmatched speakers, try to get a default member ID for unidentified speakers
                try:
                    # Get or create a default member for unidentified speakers
                    default_member = self._get_default_member_for_house(house)
                    
                    if default_member:
                        # Add default member information
                        clip_data['member_id'] = default_member['id']
                        clip_data['match_confidence'] = 0.0
                        clip_data['is_unidentified'] = True
                        
                        # Insert the clip into Supabase
                        response = self.supabase.client.table('parliament_member_clips').insert(clip_data).execute()
                        
                        if response.data:
                            unmatched_clips.append({
                                'clip_id': clip_id,
                                'member_id': default_member['id'],
                                'member_name': default_member['name'],
                                'reason': match_result['reason']
                            })
                        else:
                            failed_clips.append({
                                'clip_id': clip_id,
                                'reason': 'Failed to insert unmatched clip into Supabase'
                            })
                    else:
                        failed_clips.append({
                            'clip_id': clip_id,
                            'reason': f"No default member found for house: {house}"
                        })
                except Exception as e:
                    failed_clips.append({
                        'clip_id': clip_id,
                        'reason': f"Error inserting unmatched clip into Supabase: {str(e)}"
                    })
            else:
                # Skip saving unmatched clips if save_unmatched is False
                failed_clips.append({
                    'clip_id': clip_id,
                    'reason': match_result['reason']
                })
        
        # Return the results
        return {
            "success": True,
            "video_id": video_id,
            "matched_count": len(matched_clips),
            "unmatched_count": len(unmatched_clips),
            "failed_count": len(failed_clips),
            "matched_clips": matched_clips,
            "unmatched_clips": unmatched_clips,
            "failed_clips": failed_clips
        }
        
    def _match_face_to_member(self, face_data: Dict[str, Any], house: str = 'unknown', confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Match a face to a parliament member
        
        Args:
            face_data: Face data from recognition results
            house: House (commons or lords) to filter potential matches
            confidence_threshold: Minimum confidence score for a match (0.0-1.0)
            
        Returns:
            Dictionary with match results
        """
        # Check if we have face data
        if not face_data:
            return {
                "matched": False,
                "reason": "No face data available"
            }
            
        # Check if we have an embedding
        face_embedding = face_data.get('embedding')
        if not face_embedding:
            return {
                "matched": False,
                "reason": "No face embedding available"
            }
            
        # Find the best matching member
        best_match_id = None
        best_match_score = 0
        
        # If we don't have any member embeddings, we can't match
        if not self.member_embeddings:
            return {
                "matched": False,
                "reason": "No member embeddings available for matching"
            }
        
        # Normalize house name for comparison
        normalized_house = house.lower() if house else 'unknown'
        
        for member_id, member_embedding in self.member_embeddings.items():
            # Skip members from different house if house is known and not 'unknown'
            if normalized_house != 'unknown':
                member_house = self.member_data.get(member_id, {}).get('house', '')
                if member_house and member_house.lower() != normalized_house:
                    continue
                    
            # Convert member embedding to numpy array if it's not already
            if isinstance(member_embedding, list):
                member_embedding = np.array(member_embedding)
                
            # Calculate similarity score (cosine similarity)
            try:
                # Ensure both embeddings are normalized
                norm_face = np.linalg.norm(face_embedding)
                norm_member = np.linalg.norm(member_embedding)
                
                if norm_face > 0 and norm_member > 0:
                    similarity = np.dot(face_embedding, member_embedding) / (norm_face * norm_member)
                    
                    # Update best match if this is better
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_id = member_id
            except Exception as e:
                logger.error(f"Error calculating similarity for member {member_id}: {str(e)}")
                
        # Check if we found a good match
        if best_match_id and best_match_score > confidence_threshold:
            return {
                "matched": True,
                "member_id": best_match_id,
                "confidence": best_match_score,
                "member_name": self.member_data.get(best_match_id, {}).get('name', 'Unknown')
            }
        else:
            return {
                "matched": False,
                "reason": f"No match found with sufficient confidence (best: {best_match_score:.2f}, threshold: {confidence_threshold})"
            }
            
    def _get_default_member_for_house(self, house: str) -> Optional[Dict[str, Any]]:
        """
        Get or create a default member for unidentified speakers in a specific house
        
        Args:
            house: House (commons or lords) to get default member for
            
        Returns:
            Dictionary with default member data or None if not found/created
        """
        try:
            # Normalize house name
            normalized_house = house.lower() if house else 'unknown'
            
            # Define default member names based on house
            default_member_names = {
                'commons': 'Unidentified MP (Commons)',
                'lords': 'Unidentified Peer (Lords)',
                'unknown': 'Unidentified Speaker'
            }
            
            # Get the appropriate default member name
            default_name = default_member_names.get(normalized_house, default_member_names['unknown'])
            
            # Check if we already have a default member for this house
            response = self.supabase.client.table('parliament_members') \
                .select('*') \
                .eq('name', default_name) \
                .execute()
                
            if response.data and len(response.data) > 0:
                # Return existing default member
                return {
                    'id': response.data[0]['id'],
                    'name': response.data[0]['name'],
                    'house': normalized_house
                }
            
            # If no default member exists, create one
            new_member = {
                'name': default_name,
                'house_id': normalized_house if normalized_house in ['commons', 'lords'] else None,
                'is_default_member': True,
                'created_at': datetime.now().isoformat()
            }
            
            # Insert the new default member
            response = self.supabase.client.table('parliament_members').insert(new_member).execute()
            
            if response.data and len(response.data) > 0:
                return {
                    'id': response.data[0]['id'],
                    'name': response.data[0]['name'],
                    'house': normalized_house
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating default member for house {house}: {str(e)}")
            return None
            
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
            os.makedirs(unidentified_dir, exist_ok=True)
            logger.info(f"Created unidentified speakers directory: {unidentified_dir}")
            
        metadata_files = [f for f in os.listdir(unidentified_dir) if f.startswith("unidentified_") and f.endswith(".json")]
        
        if not metadata_files:
            logger.warning("No unidentified speaker metadata files found")
            return {
                "success": True,
                "processed_count": 0,
                "results": []
            }
            
        # Process each file
        results = []
        for file in metadata_files:
            try:
                video_id = int(file.replace("unidentified_", "").replace(".json", ""))
                logger.info(f"Processing unidentified speakers for video {video_id}")
                result = self.match_unidentified_speakers(video_id, save_unmatched=True)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing file {file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
        # Return overall results
        return {
            "success": True,
            "processed_count": len(results),
            "results": results
        }
