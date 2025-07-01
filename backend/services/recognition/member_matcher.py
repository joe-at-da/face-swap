"""
Module for matching unidentified speakers with parliament members based on facial recognition
"""
import os
import logging
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
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
    
    def __init__(self, supabase_service: SupabaseService = None, db_session=None):
        """
        Initialize the parliament member matcher
        
        Args:
            supabase_service: Supabase service for database operations
            db_session: SQLAlchemy database session for local database operations
        """
        self.supabase = supabase_service or SupabaseService()
        self.face_recognition = FaceRecognitionService()
        
        # Get database session if not provided
        if db_session is None:
            from backend.db.session import get_db
            db_gen = get_db()
            self.db = next(db_gen)
            self._close_db = lambda: next(db_gen, None)
        else:
            self.db = db_session
            self._close_db = lambda: None
        
        # Import json for handling face embeddings
        import json
        
        # Store member data and embeddings
        self.member_data = {}
        self.member_embeddings = {}
        
        # Default confidence threshold for face matching
        self.confidence_threshold = 0.6
        
        # Load parliament members
        self.load_parliament_members()
        
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
            
            members_with_embeddings = 0
            members_with_photos = 0
            members_without_photos = 0
            
            # Process each member
            for member in response.data:
                member_id = member.get('id')
                if not member_id:
                    continue
                    
                # Skip default members (unidentified speakers)
                if member.get('is_default_member'):
                    continue
                    
                # Store member data for reference
                self.member_data[member_id] = {
                    'name': member.get('name'),
                    'party': member.get('party_id'),
                    'house': member.get('house_id'),
                    'image_url': member.get('image_url')
                }
                
                # Check if member already has face embedding
                face_embedding = member.get('face_embedding')
                if face_embedding:
                    # Store the embedding directly
                    self.member_embeddings[member_id] = face_embedding
                    members_with_embeddings += 1
                    continue
                
                # If no embedding but has image URL, process it
                image_url = member.get('image_url')
                if image_url:
                    members_with_photos += 1
                    self._process_member_image(member_id, image_url)
                else:
                    members_without_photos += 1
            
            logger.info(f"Members with embeddings: {members_with_embeddings}")
            logger.info(f"Members with photos but no embeddings: {members_with_photos}")
            logger.info(f"Members without photos: {members_without_photos}")
            logger.info(f"Total members with embeddings after processing: {len(self.member_embeddings)}")
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
            # Check if the image path exists
            if not image_url.startswith('http') and os.path.exists(image_url):
                # Use existing local path
                image_path = image_url
            elif image_url.startswith('http'):
                # Download image if it's a remote URL
                import requests
                from io import BytesIO
                from PIL import Image
                
                response = requests.get(image_url)
                if response.status_code != 200:
                    logger.warning(f"Failed to download image for member {member_id}: {response.status_code}")
                    return
                    
                image = Image.open(BytesIO(response.content))
                image_path = f"/app/data/mp_photos/{member_id}.jpg"
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
            else:
                # Path doesn't exist
                logger.warning(f"Image path does not exist for member {member_id}: {image_url}")
                return
                
            # Extract face embedding using the face recognition service
            face_data = self.face_recognition.extract_face_embedding(image_path)
            
            if face_data and 'embedding' in face_data:
                # Store the embedding for matching
                self.member_embeddings[member_id] = face_data['embedding']
                
                # Update the member in Supabase with the embedding if it's not already there
                try:
                    response = self.supabase.client.table('parliament_members').select('face_embedding').eq('id', member_id).execute()
                    if response.data and not response.data[0].get('face_embedding'):
                        update_data = {
                            'face_embedding': face_data['embedding'],
                            'image_url': image_path  # Ensure image_url is updated to the local path
                        }
                        self.supabase.client.table('parliament_members').update(update_data).eq('id', member_id).execute()
                        logger.info(f"Updated face embedding and image URL for member {member_id} in Supabase")
                except Exception as e:
                    logger.warning(f"Failed to update face embedding in Supabase: {str(e)}")
                    
                # Also update the local database if it exists
                try:
                    from sqlalchemy import text
                    # Check if speakers table exists
                    result = self.db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='speakers'")).fetchone()
                    if result:
                        # Get member name
                        member_name = self.member_data.get(member_id, {}).get('name', 'Unknown')
                        # Update or insert into speakers table
                        self.db.execute(
                            text("INSERT OR REPLACE INTO speakers (parliament_id, name, photo_url, face_encoding) VALUES (:parliament_id, :name, :photo_url, :face_encoding)"),
                            {
                                "parliament_id": member_id,
                                "name": member_name,
                                "photo_url": image_path,
                                "face_encoding": json.dumps(face_data['embedding'])
                            }
                        )
                        self.db.commit()
                        logger.info(f"Updated local database record for member {member_id}")
                except Exception as e:
                    logger.warning(f"Could not update local database: {str(e)}")
            else:
                logger.warning(f"No face detected in image for member {member_id}")
                
        except Exception as e:
            logger.error(f"Error processing image for member {member_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    def match_unidentified_speakers(self, video_id: int, save_unmatched: bool = True) -> Dict[str, Any]:
        """Match unidentified speakers from a video with parliament members
        
        Args:
            video_id: ID of the video with unidentified speakers
            save_unmatched: If True, save clips even when face matching fails
            
        Returns:
            Dictionary with results of the matching process
        """
        # Import models here to avoid circular imports
        from backend.db.models import SpeakerIdentification, SpeakerAppearance, Speaker
        from datetime import datetime
        
        # Create a SpeakerIdentification record for this video if it doesn't exist
        try:
            # First check if the record exists
            speaker_identification = self.db.query(SpeakerIdentification).filter(SpeakerIdentification.id == video_id).first()
            
            if not speaker_identification:
                # Get the capture session ID from the video clip
                from backend.db.models import VideoClip
                video_clip = self.db.query(VideoClip).filter(VideoClip.id == video_id).first()
                capture_session_id = video_clip.capture_session_id if video_clip else None
                
                # If we can't find a capture session, create one
                if not capture_session_id:
                    from backend.db.models import CaptureSession
                    capture_session = CaptureSession(
                        user_id=1,  # Default to user ID 1
                        status='completed',
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    self.db.add(capture_session)
                    self.db.commit()
                    self.db.refresh(capture_session)
                    capture_session_id = capture_session.id
                    logger.info(f"Created CaptureSession with ID {capture_session_id}")
                
                # Create a new SpeakerIdentification record with explicit ID
                self.db.execute(
                    f"INSERT INTO speaker_identifications (id, capture_session_id, status, created_by_id, created_at, updated_at) "
                    f"VALUES ({video_id}, {capture_session_id}, 'completed', 1, NOW(), NOW())"
                )
                self.db.commit()
                logger.info(f"Created SpeakerIdentification record for video {video_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create SpeakerIdentification record: {str(e)}")
            # Return an error since we can't proceed without this record
            return {
                "success": False,
                "error": f"Failed to create SpeakerIdentification record: {str(e)}"
            }
        
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
                member_id = match_result['member_id']
                confidence = match_result['confidence']
                
                try:
                    # Create a speaker appearance in the local database
                    from backend.db.models import SpeakerAppearance, Speaker
                    
                    # Check if we have a speaker for this member
                    speaker = self.db.query(Speaker).filter(Speaker.parliament_id == member_id).first()
                    
                    # If not, create one
                    if not speaker:
                        speaker = Speaker(
                            name=match_result['member_name'],
                            parliament_id=member_id,
                            is_active=True
                        )
                        self.db.add(speaker)
                        self.db.commit()
                        self.db.refresh(speaker)
                    
                    # Create the speaker appearance
                    appearance = SpeakerAppearance(
                        speaker_id=speaker.id,
                        identification_id=video_id,  # Using video_id as identification_id for now
                        start_time=float(segment.get('start_time', 0)),
                        end_time=float(segment.get('end_time', 0)),
                        duration=float(segment.get('duration', 0)),
                        confidence=confidence
                    )
                    
                    self.db.add(appearance)
                    self.db.commit()
                    
                    matched_clips.append({
                        'clip_id': clip_id,
                        'member_id': member_id,
                        'member_name': match_result['member_name'],
                        'confidence': confidence
                    })
                except Exception as e:
                    self.db.rollback()
                    failed_clips.append({
                        'clip_id': clip_id,
                        'reason': f"Error inserting matched clip into local database: {str(e)}"
                    })
            elif save_unmatched:
                try:
                    # Get or create a default member for unidentified speakers
                    default_member_id = self._get_default_member_for_house(house)
                    
                    if default_member_id:
                        # Add default member information
                        clip_data['member_id'] = default_member_id
                        clip_data['match_confidence'] = 0.0
                        clip_data['is_unidentified'] = True
                        
                        # Create a speaker appearance in the local database instead of using Supabase
                        from backend.db.models import SpeakerAppearance, Speaker
                        
                        # Check if we have a speaker for this default member
                        speaker = self.db.query(Speaker).filter(Speaker.parliament_id == default_member_id).first()
                        
                        # If not, create one
                        if not speaker:
                            speaker = Speaker(
                                name='Unidentified Speaker',
                                parliament_id=default_member_id,
                                is_active=True
                            )
                            self.db.add(speaker)
                            self.db.commit()
                            self.db.refresh(speaker)
                        
                        # Create the speaker appearance
                        appearance = SpeakerAppearance(
                            speaker_id=speaker.id,
                            identification_id=video_id,  # Using video_id as identification_id for now
                            start_time=float(segment.get('start_time', 0)),
                            end_time=float(segment.get('end_time', 0)),
                            duration=float(segment.get('duration', 0)),
                            confidence=0.0
                        )
                        
                        try:
                            self.db.add(appearance)
                            self.db.commit()
                            
                            unmatched_clips.append({
                                'clip_id': clip_id,
                                'member_id': default_member_id,
                                'member_name': 'Unidentified Speaker',
                                'reason': match_result['reason']
                            })
                        except Exception as e:
                            self.db.rollback()
                            failed_clips.append({
                                'clip_id': clip_id,
                                'reason': f'Failed to insert unmatched clip into local database: {str(e)}'
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
        # Check if we have face embedding
        if not face_data or 'embedding' not in face_data:
            return {
                "matched": False,
                "reason": "No face embedding provided"
            }
            
        # Get the face embedding
        face_embedding = face_data['embedding']
        
        # Find the best match
        best_match_id = None
        best_match_score = 0.0
        
        # Iterate through all member embeddings
        for member_id, member_embedding in self.member_embeddings.items():
            # Skip members from different houses if house is specified
            if house != 'unknown' and self.member_data.get(member_id, {}).get('house') != house:
                continue
                
            try:
                # Calculate similarity
                similarity = self._compute_similarity(face_embedding, member_embedding)
                
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
            
    def _compute_similarity(self, embedding1, embedding2):
        """
        Compute similarity between two face embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Convert to numpy arrays
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        # Normalize embeddings
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        # Compute cosine similarity
        similarity = np.dot(emb1, emb2)
        
        return float(similarity)
            
    def _get_default_member_for_house(self, house_id: str) -> Optional[str]:
        """
        Get or create a default member for unidentified speakers in a specific house
        
        Args:
            house_id: ID of the house (commons, lords, etc.)
            
        Returns:
            ID of the default member or None if failed
        """
        try:
            # Normalize house ID
            normalized_house = house_id.lower() if house_id else 'unknown'
            
            # Define default member names based on house
            default_member_names = {
                'commons': 'Unidentified MP (Commons)',
                'lords': 'Unidentified Peer (Lords)',
                'unknown': 'Unidentified Speaker'
            }
            
            # Get the appropriate default member name
            default_name = default_member_names.get(normalized_house, default_member_names['unknown'])
            
            # First, get all members and check if we have an unidentified member already
            # This is less efficient but avoids issues with UUID and LIKE operator
            response = self.supabase.client.table('parliament_members').select('*').execute()
            
            if response.data:
                # Check for existing unidentified members for this house
                for member in response.data:
                    member_id = member.get('id', '')
                    member_display_name = member.get('display_name', '')
                    member_house = member.get('house_id', '')
                    
                    # Check if this looks like an unidentified member for our house
                    if (member_display_name and default_name in member_display_name and 
                            member_house == normalized_house):
                        logger.info(f"Found existing default member for house {house_id}: {member_id}")
                        return member_id
            
            # If no default member exists for this house, create one with a UUID
            import uuid
            member_id = str(uuid.uuid4())
            
            # Create a new default member with available columns
            # First, let's check the available columns
            columns_response = self.supabase.client.table('parliament_members').select('*').limit(1).execute()
            
            if columns_response.data:
                # Get the column names from the first record
                sample_record = columns_response.data[0]
                column_names = list(sample_record.keys())
                logger.info(f"Available columns in parliament_members: {column_names}")
                
                # Create a new member with appropriate columns
                # Generate a random integer for member_id (since it's an integer type)
                import random
                random_member_id = random.randint(9000000, 9999999)  # Use a high range to avoid conflicts
                
                new_member = {
                    'id': member_id,
                    'member_id': random_member_id  # This must be an integer
                }
                
                # Add display_name if available
                if 'display_name' in column_names:
                    new_member['display_name'] = default_name
                elif 'full_name' in column_names:
                    new_member['full_name'] = default_name
                elif 'family_name' in column_names:
                    new_member['family_name'] = default_name
                
                # Add house_id if available
                if 'house_id' in column_names:
                    new_member['house_id'] = normalized_house if normalized_house in ['commons', 'lords'] else None
                
                # Add other required fields
                if 'is_current_member' in column_names:
                    new_member['is_current_member'] = True
                
                if 'created_at' in column_names:
                    new_member['created_at'] = datetime.now().isoformat()
                
                # Insert the new default member
                logger.info(f"Creating default member with data: {new_member}")
                response = self.supabase.client.table('parliament_members').insert(new_member).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"Created default member for house {house_id} with ID {member_id}")
                    return member_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating default member for house {house_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
