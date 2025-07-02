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
    
    IMPORTANT: Before using this class, ensure that MP photos have been downloaded
    by running the download_mp_photos.py script. This script downloads photos from
    the UK Parliament website and generates face embeddings for all MPs.
    
    Example:
        # Run this first to download MP photos
        python download_mp_photos.py
        
        # Then use the matcher
        matcher = ParliamentMemberMatcher()
        matcher.load_parliament_members()
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
        Load parliament members from Supabase and manage local photo/embedding storage
        
        NOTE: This method expects MP photos to be pre-downloaded using the download_mp_photos.py script.
        Run this script before using the ParliamentMemberMatcher for best results.
        
        Returns:
            Boolean indicating success
        """
        logger.info("===== LOADING PARLIAMENT MEMBERS =====")
        try:
            import os
            import json
            
            # Get parliament members from Supabase
            try:
                response = self.supabase.client.table('parliament_members').select('*').execute()
                self.members = response.data
                logger.info(f"Retrieved {len(self.members)} parliament members from Supabase")
            except Exception as e:
                logger.warning(f"Error retrieving parliament members from Supabase: {str(e)}")
                # Try to load from cache if available
                cache_file = "/app/data/temp/parliament_members_cache.json"
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, 'r') as f:
                            self.members = json.load(f)
                        logger.info(f"Loaded {len(self.members)} parliament members from cache")
                    except Exception as cache_error:
                        logger.warning(f"Error loading cached parliament members: {str(cache_error)}")
                        self.members = []
                else:
                    self.members = []
        
            if not self.members:
                logger.warning("No parliament members found in Supabase or cache")
                return False
                
            # Count of members with embeddings
            members_with_embeddings = 0
            members_with_photos = 0
            members_missing_data = 0
            
            logger.info(f"Total members from Supabase/cache: {len(self.members)}")
            
            # Create directory for MP photos if it doesn't exist
            mp_photos_dir = "/app/data/mp_photos"
            os.makedirs(mp_photos_dir, exist_ok=True)
            
            # Check if photos directory is empty - warn if it is
            photo_files = [f for f in os.listdir(mp_photos_dir) if f.endswith('.jpg')]
            embedding_files = [f for f in os.listdir(mp_photos_dir) if f.endswith('.json')]
            if len(photo_files) == 0:
                logger.warning("No MP photos found in /app/data/mp_photos directory. ")
                logger.warning("Please run download_mp_photos.py script to download MP photos before using this service.")
            else:
                logger.info(f"Found {len(photo_files)} MP photos and {len(embedding_files)} embedding files in the photos directory")
            
            # Process each member
            for member in self.members:
                member_id = member.get('id')
                display_name = member.get('display_name')
                
                if not member_id:
                    logger.warning(f"Member has no ID: {member}")
                    continue
                
                # Check for local cached photo
                local_photo_path = f"/app/data/mp_photos/{member_id}.jpg"
                if os.path.exists(local_photo_path):
                    # Use local photo
                    members_with_photos += 1
                    
                    # Check for local cached embedding
                    local_embedding_path = f"/app/data/mp_photos/{member_id}.json"
                    if os.path.exists(local_embedding_path):
                        try:
                            with open(local_embedding_path, 'r') as f:
                                face_embedding = json.load(f)
                            
                            # Store the embedding for matching
                            self.member_embeddings[member_id] = face_embedding
                            members_with_embeddings += 1
                            logger.debug(f"Loaded embedding for member {member_id} ({display_name}): shape={np.array(face_embedding).shape if isinstance(face_embedding, list) else 'unknown'}, type={type(face_embedding).__name__}")
                            
                            # Store member data for reference
                            self.member_data[member_id] = {
                                'name': display_name,
                                'photo_path': local_photo_path
                            }
                        except Exception as e:
                            logger.warning(f"Failed to load local embedding for member {member_id}: {str(e)}")
                            members_missing_data += 1
                    else:
                        # Generate embedding from local photo
                        self._process_member_image(member_id, local_photo_path)
                        if member_id in self.member_embeddings:
                            members_with_embeddings += 1
                            
                            # Store member data for reference
                            self.member_data[member_id] = {
                                'name': display_name,
                                'photo_path': local_photo_path
                            }
                        else:
                            members_missing_data += 1
                else:
                    # No local photo - log a warning but don't try to download
                    # This is a change from previous behavior to rely on the download_mp_photos.py script
                    logger.warning(f"No photo found for member {display_name} (ID: {member_id}). ")
                    logger.warning(f"Please run download_mp_photos.py script to download all MP photos.")
                    members_missing_data += 1
            
            # Log summary statistics after processing all members
            logger.info(f"Loaded {len(self.members)} parliament members from Supabase")
            logger.info(f"Members with embeddings: {members_with_embeddings}")
            logger.info(f"Members with photos: {members_with_photos}")
            logger.info(f"Members missing data: {members_missing_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading parliament members: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def _download_mp_photo_from_parliament(self, member_id: str, name: str) -> bool:
        """
        Download a parliament member's photo from the UK Parliament website
        
        Args:
            member_id: ID of the parliament member
            name: Name of the parliament member
            
        Returns:
            Boolean indicating success
        """
        try:
            import requests
            import urllib.parse
            from io import BytesIO
            from PIL import Image
            
            # Search for the member by name
            encoded_name = urllib.parse.quote(name) if name else ""
            search_url = f"https://members-api.parliament.uk/api/Members/Search?Name={encoded_name}&skip=0&take=20"
            
            # Add proper headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://members.parliament.uk/',
                'Origin': 'https://members.parliament.uk'
            }
            
            # Search for the member
            search_response = requests.get(search_url, headers=headers)
            if search_response.status_code != 200:
                logger.warning(f"Failed to search for member {name}: {search_response.status_code}")
                
                # Try alternative search with just the first name if full name didn't work
                if ' ' in name:
                    first_name = name.split(' ')[0]
                    logger.info(f"Trying alternative search with just first name: {first_name}")
                    alt_search_url = f"https://members-api.parliament.uk/api/Members/Search?Name={urllib.parse.quote(first_name)}&skip=0&take=20"
                    alt_search_response = requests.get(alt_search_url, headers=headers)
                    if alt_search_response.status_code == 200:
                        search_response = alt_search_response
                    else:
                        return False
                else:
                    return False
            
            # Parse the search results
            member_data = search_response.json().get('items', [])
            if not member_data:
                logger.warning(f"No search results found for member {name}")
                return False
            
            # Get the first result
            member_id_uk = member_data[0].get('value', {}).get('id')
            if not member_id_uk:
                logger.warning(f"No UK Parliament ID found for member {name}")
                return False
            
            # Get member photo URL
            photo_url = f"https://members-api.parliament.uk/api/Members/{member_id_uk}/Portrait?CropType=FullSize"
            
            # Download the photo
            photo_response = requests.get(photo_url, headers=headers)
            if photo_response.status_code != 200:
                logger.warning(f"Failed to download photo for member {name}: {photo_response.status_code}")
                return False
            
            # Save the photo
            image = Image.open(BytesIO(photo_response.content))
            photo_path = f"/app/data/mp_photos/{member_id}.jpg"
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)
            image.save(photo_path)
            logger.info(f"Downloaded photo for member {name} to {photo_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading photo for member {name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _process_member_image(self, member_id: str, image_url: str) -> None:
        """
        Process a member's image to extract face embedding
        
        Args:
            member_id: ID of the parliament member
            image_url: URL or path to the member's image
        """
        try:
            # Get the image path
            image_path = image_url
            if image_url.startswith('http'):
                # Download the image
                import requests
                from io import BytesIO
                from PIL import Image
                
                response = requests.get(image_url)
                if response.status_code != 200:
                    logger.warning(f"Failed to download image for member {member_id}: {response.status_code}")
                    return
                
                # Save the image locally
                image = Image.open(BytesIO(response.content))
                image_path = f"/app/data/mp_photos/{member_id}.jpg"
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                logger.info(f"Downloaded image for member {member_id} to {image_path}")
            
            # Extract face embedding using the face recognition service
            face_data = self.face_recognition.extract_face_embedding(image_path)
            
            if face_data and 'embedding' in face_data:
                # Store the embedding for matching
                self.member_embeddings[member_id] = face_data['embedding']
                
                # Save the embedding locally for future use
                try:
                    import json
                    local_embedding_path = f"/app/data/mp_photos/{member_id}.json"
                    with open(local_embedding_path, 'w') as f:
                        json.dump(face_data['embedding'], f)
                    logger.info(f"Saved face embedding for member {member_id} to {local_embedding_path}")
                except Exception as e:
                    logger.warning(f"Failed to save face embedding locally: {str(e)}")
                    
                # No need to try updating Supabase since the columns don't exist
                # Just log that we're using local storage only
                logger.info(f"Using local storage for member {member_id} photo and embedding")
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
            speaker_identification = self.db.query(SpeakerIdentification).filter(SpeakerIdentification.id == video_id).first()
            if not speaker_identification:
                try:
                    # Get the capture session ID from the video clip
                    from backend.db.models import VideoClip
                    video_clip = self.db.query(VideoClip).filter(VideoClip.id == video_id).first()
                    capture_session_id = video_clip.capture_session_id if video_clip else None
                    
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
                    
                    # Create a new SpeakerIdentification record with explicit ID using raw SQL
                    # This ensures the ID is exactly what we need for the foreign key constraint
                    from sqlalchemy import text
                    self.db.execute(
                        text(f"INSERT INTO speaker_identifications (id, capture_session_id, status, created_by_id, created_at, updated_at) "
                        f"VALUES ({video_id}, {capture_session_id}, 'completed', 1, NOW(), NOW())")
                    )
                    self.db.commit()
                    logger.info(f"Created SpeakerIdentification record for video {video_id}")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Failed to create SpeakerIdentification record: {str(e)}")
                    # Return error since we can't proceed without this record
                    return {
                        "success": False,
                        "error": f"Failed to create SpeakerIdentification record: {str(e)}"
                    }
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
                
        # Check if we've already processed this video
        existing_appearances = self.db.query(SpeakerAppearance)\
            .filter(SpeakerAppearance.identification_id == video_id)\
            .count()
            
        if existing_appearances > 0:
            logger.info(f"Video {video_id} already has {existing_appearances} speaker appearances. Skipping processing.")
            # Return existing results
            return {
                "success": True,
                "video_id": video_id,
                "matched_count": existing_appearances,
                "unmatched_count": 0,
                "failed_count": 0,
                "message": f"Video already processed with {existing_appearances} speaker appearances"
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
        logger.info(f"Attempting to match face to member with confidence threshold {confidence_threshold}")
        # Check if we have face embedding
        if not face_data or 'embedding' not in face_data:
            logger.warning("No face embedding provided in face_data")
            logger.debug(f"Face data keys: {list(face_data.keys()) if face_data else 'None'}")
            return {
                "matched": False,
                "reason": "No face embedding provided"
            }
            
        # Get the face embedding
        face_embedding = face_data['embedding']
        logger.info(f"Got face embedding: shape={np.array(face_embedding).shape if isinstance(face_embedding, list) else 'unknown'}, type={type(face_embedding).__name__}")
        
        # Check for NaN or zero values in embedding
        if isinstance(face_embedding, list) or isinstance(face_embedding, np.ndarray):
            embedding_array = np.array(face_embedding)
            has_nan = np.isnan(embedding_array).any()
            has_zeros = (embedding_array == 0).all()
            logger.info(f"Embedding quality check: has_nan={has_nan}, all_zeros={has_zeros}")
            if has_nan or has_zeros:
                logger.warning("⚠️ Poor quality embedding detected (contains NaN or all zeros)")
        
        # Find the best match
        best_match_id = None
        best_match_score = 0.0
        
        # Track top matches for logging
        top_matches = []
        
        # Log the number of member embeddings we're comparing against
        logger.info(f"Comparing against {len(self.member_embeddings)} member embeddings")
        
        # Iterate through all member embeddings
        for member_id, member_embedding in self.member_embeddings.items():
            # Skip members from different houses if house is specified
            if house != 'unknown' and self.member_data.get(member_id, {}).get('house') != house:
                continue
                
            try:
                # Calculate similarity
                similarity = self._compute_similarity(face_embedding, member_embedding)
                
                # Add to top matches list
                member_name = self.member_data.get(member_id, {}).get('name', 'Unknown')
                top_matches.append((member_id, member_name, similarity))
                
                # Update best match if this is better
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_id = member_id
            except Exception as e:
                logger.error(f"Error calculating similarity for member {member_id}: {str(e)}")
        
        # Sort top matches by similarity score (descending)
        top_matches.sort(key=lambda x: x[2], reverse=True)
        
        # Log top 3 matches
        logger.info("Top 3 matching candidates:")
        for i, (member_id, member_name, score) in enumerate(top_matches[:3], 1):
            logger.info(f"  {i}. {member_name} (ID: {member_id}): score={score:.4f}")
                
        # Check if we found a good match
        if best_match_id and best_match_score > confidence_threshold:
            member_name = self.member_data.get(best_match_id, {}).get('name', 'Unknown')
            logger.info(f"✅ MATCH FOUND: {member_name} (ID: {best_match_id}) with confidence {best_match_score:.4f}")
            return {
                "matched": True,
                "member_id": best_match_id,
                "confidence": best_match_score,
                "member_name": member_name
            }
        else:
            logger.warning(f"❌ NO MATCH FOUND: Best score was {best_match_score:.4f}, threshold is {confidence_threshold}")
            if best_match_id:
                member_name = self.member_data.get(best_match_id, {}).get('name', 'Unknown')
                logger.info(f"Best non-matching candidate was {member_name} (ID: {best_match_id})")
            return {
                "matched": False,
                "reason": f"No match found with sufficient confidence (best: {best_match_score:.4f}, threshold: {confidence_threshold})"
            }
            
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
    
    def _compute_similarity(self, embedding1, embedding2) -> float:
        """
        Compute similarity between two face embeddings
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score (0.0-1.0)
        """
        try:
            # Convert to numpy arrays if needed
            if not isinstance(embedding1, np.ndarray):
                embedding1 = np.array(embedding1)
            if not isinstance(embedding2, np.ndarray):
                embedding2 = np.array(embedding2)
            
            # Ensure embeddings are flattened to 1D arrays
            embedding1 = embedding1.flatten()
            embedding2 = embedding2.flatten()
            
            # Check embedding dimensions
            if embedding1.size == 0 or embedding2.size == 0:
                logger.error(f"Empty embedding detected: embedding1 size={embedding1.size}, embedding2 size={embedding2.size}")
                return 0.0
            
            # Log embedding details for debugging
            logger.debug(f"Embedding1: shape={embedding1.shape}, min={np.min(embedding1):.4f}, max={np.max(embedding1):.4f}")
            logger.debug(f"Embedding2: shape={embedding2.shape}, min={np.min(embedding2):.4f}, max={np.max(embedding2):.4f}")
            
            # Handle embeddings from different sources (dlib vs OpenCV)
            # If sizes don't match, we need to adapt the comparison strategy
            if embedding1.size != embedding2.size:
                logger.warning(f"Embedding size mismatch: {embedding1.size} vs {embedding2.size}")
                
                # If one is 128 (dlib) and the other is different (likely OpenCV), 
                # we need to use a different comparison approach
                if embedding1.size == 128 or embedding2.size == 128:
                    logger.info("Detected potential dlib vs OpenCV embedding comparison")
                    
                    # For mismatched embedding types, we'll use a lower threshold
                    # and normalize each separately before computing similarity on the 
                    # first min(size1, size2) dimensions
                    min_size = min(embedding1.size, embedding2.size)
                    embedding1 = embedding1[:min_size]
                    embedding2 = embedding2[:min_size]
                    logger.info(f"Using first {min_size} dimensions for comparison")
                else:
                    logger.error(f"Cannot compare embeddings with incompatible sizes: {embedding1.size} vs {embedding2.size}")
                    return 0.0
            
            # Normalize the embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 < 1e-10 or norm2 < 1e-10:
                logger.warning("Near-zero norm detected in embedding")
                return 0.0
                
            embedding1 = embedding1 / norm1
            embedding2 = embedding2 / norm2
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2)
            
            # Adjust similarity score for cross-model comparisons
            # Empirically, dlib vs OpenCV comparisons tend to have lower similarity scores
            # even for the same face, so we apply a small boost to compensate
            if embedding1.size != embedding2.size:
                similarity = min(1.0, similarity * 1.2)  # Apply a 20% boost, capped at 1.0
                
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 0.0
            
    def _get_default_member_for_house(self, house_id: str) -> Optional[str]:
        """
        Get or create a default member for unidentified speakers in a specific house
        Uses local database models instead of Supabase
        
        Args:
            house_id: ID of the house (commons, lords, etc.)
            
        Returns:
            ID of the default member or None if failed
        """
        try:
            # Normalize house ID
            normalized_house = house_id.lower() if house_id else 'unknown'
            
            # Define default member names based on house
            if normalized_house == 'commons':
                default_name = 'Unidentified MP (Commons)'
            elif normalized_house == 'lords':
                default_name = 'Unidentified Peer (Lords)'
            else:
                default_name = 'Unidentified Speaker'
                
            # Check if default member already exists in local cache
            for member in self.members:
                member_id = member.get('id')
                member_display_name = member.get('display_name')
                member_house = member.get('house_id', '').lower() if member.get('house_id') else None
                
                if member_display_name and default_name in member_display_name and member_house == normalized_house:
                    logger.info(f"Found existing default member for house {house_id} with ID {member_id}")
                    return member_id
            
            # Create a new default member if not found
            import uuid
            import random
            
            # Generate a UUID for the member ID
            member_id = str(uuid.uuid4())
            
            # Generate a random integer for member_id (different from the UUID)
            random_member_id = random.randint(10000, 99999)
            
            # Create new member
            new_member = {
                'id': member_id,
                'member_id': random_member_id,
                'display_name': default_name,
                'house_id': normalized_house or None,
                'is_current_member': True,
                'created_at': datetime.now().isoformat()
            }
            
            # Add to local cache
            self.members.append(new_member)
            
            # Save updated cache
            try:
                import json
                import os
                os.makedirs("/app/data/temp", exist_ok=True)
                cache_file = "/app/data/temp/parliament_members_cache.json"
                with open(cache_file, 'w') as f:
                    json.dump(self.members, f)
                logger.info(f"Updated parliament members cache with new default member")
            except Exception as cache_error:
                logger.warning(f"Failed to update cache with default member: {str(cache_error)}")
            
            logger.info(f"Created default member for house {house_id} with ID {member_id}")
            return member_id
            
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
