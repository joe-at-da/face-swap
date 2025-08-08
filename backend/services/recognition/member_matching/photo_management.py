"""
Module for handling MP photo downloading and processing
"""
import os
import json
import logging
import requests
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import face_recognition
import cv2
from pathlib import Path

# Import centralized configuration
try:
    from backend.core.recognition_config import TimeoutConfig
except ImportError:
    # Fallback values if config module is not available
    class TimeoutConfig:
        REQUEST_TIMEOUT = 10

logger = logging.getLogger(__name__)

class PhotoManager:
    """
    Class for managing MP photos and embeddings
    """
    def __init__(self, photos_dir: str, embeddings_dir: str):
        """
        Initialize the photo manager
        
        Args:
            photos_dir: Directory for storing MP photos
            embeddings_dir: Directory for storing MP embeddings
        """
        self.photos_dir = photos_dir
        self.embeddings_dir = embeddings_dir
        
        # Create directories if they don't exist
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
        
        # Path to the UUID to member ID mapping file
        self.uuid_to_member_id_file = os.path.join(self.photos_dir, 'uuid_to_member_id.json')
        
        # Load UUID to member ID mapping if available
        self.uuid_to_member_id = {}
        self.load_uuid_mapping()
    
    def get_photo_path(self, member_id: str) -> str:
        """
        Get the path to an MP's photo
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            Path to the photo file
        """
        return os.path.join(self.photos_dir, f"{member_id}.jpg")
    
    def get_embedding_path(self, member_id: str) -> str:
        """
        Get the path to an MP's embedding file
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            Path to the embedding file
        """
        return os.path.join(self.embeddings_dir, f"{member_id}.json")
    
    def has_photo(self, member_id: str) -> bool:
        """
        Check if an MP has a photo
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            True if the MP has a photo, False otherwise
        """
        return os.path.exists(self.get_photo_path(member_id))
    
    def has_embedding(self, member_id: str) -> bool:
        """
        Check if an MP has an embedding
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            True if the MP has an embedding, False otherwise
        """
        return os.path.exists(self.get_embedding_path(member_id))
    
    def load_uuid_mapping(self):
        """
        Load the UUID to member ID mapping from file
        """
        if not os.path.exists(self.uuid_to_member_id_file):
            logger.warning(f"UUID to member ID mapping file not found at {self.uuid_to_member_id_file}")
            return
        
        try:
            with open(self.uuid_to_member_id_file, 'r') as f:
                mapping_data = json.load(f)
            
            # Process the mapping data
            for uuid, info in mapping_data.items():
                if isinstance(info, dict) and 'member_id' in info:
                    self.uuid_to_member_id[uuid] = info['member_id']
                    # Also store without dashes for compatibility
                    if '-' in uuid:
                        no_dash_uuid = uuid.replace('-', '')
                        self.uuid_to_member_id[no_dash_uuid] = info['member_id']
            
            logger.info(f"Loaded {len(self.uuid_to_member_id)} UUID to member ID mappings")
        except Exception as e:
            logger.error(f"Error loading UUID to member ID mapping: {str(e)}")
    
    def load_embedding(self, member_id: str) -> Optional[np.ndarray]:
        """
        Load an MP's embedding from file
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            Embedding as numpy array or None if not found
        """
        # First try with the direct member_id
        embedding_path = self.get_embedding_path(member_id)
        if os.path.exists(embedding_path):
            try:
                with open(embedding_path, 'r') as f:
                    embedding_data = json.load(f)
                
                if 'embedding' in embedding_data:
                    return np.array(embedding_data['embedding'])
            except Exception as e:
                logger.error(f"Error loading embedding for member {member_id}: {str(e)}")
        
        # If the member_id is a UUID, try to find the numeric member_id
        if member_id in self.uuid_to_member_id:
            numeric_member_id = self.uuid_to_member_id[member_id]
            logger.info(f"Found mapping from UUID {member_id} to numeric member_id {numeric_member_id}")
            
            # Try loading with the numeric member_id
            numeric_embedding_path = self.get_embedding_path(numeric_member_id)
            if os.path.exists(numeric_embedding_path):
                try:
                    with open(numeric_embedding_path, 'r') as f:
                        embedding_data = json.load(f)
                    
                    if 'embedding' in embedding_data:
                        return np.array(embedding_data['embedding'])
                except Exception as e:
                    logger.error(f"Error loading embedding for numeric member {numeric_member_id}: {str(e)}")
        
        logger.debug(f"No embedding found for member {member_id}")
        return None
    
    def generate_embedding(self, member_id: str) -> Optional[np.ndarray]:
        """
        Generate an embedding from an MP's photo
        
        Args:
            member_id: ID of the parliament member
            
        Returns:
            Embedding as numpy array or None if failed
        """
        photo_path = self.get_photo_path(member_id)
        if not os.path.exists(photo_path):
            logger.warning(f"No photo found for member {member_id}")
            return None
        
        try:
            # Load image
            image = face_recognition.load_image_file(photo_path)
            
            # Find faces in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                logger.warning(f"No faces found in photo for member {member_id}")
                return None
            
            # Use the first face found
            face_encoding = face_recognition.face_encodings(image, [face_locations[0]])[0]
            
            # Save the embedding
            embedding_path = self.get_embedding_path(member_id)
            with open(embedding_path, 'w') as f:
                json.dump({'embedding': face_encoding.tolist()}, f)
            
            logger.info(f"Generated and saved embedding for member {member_id}")
            return face_encoding
        except Exception as e:
            logger.error(f"Error generating embedding for member {member_id}: {str(e)}")
            return None
    
    def download_mp_photo_from_parliament(self, member_id: str, photo_url: str) -> bool:
        """
        Download an MP's photo from the UK Parliament website
        
        Args:
            member_id: ID of the parliament member
            photo_url: URL of the photo
            
        Returns:
            True if successful, False otherwise
        """
        if not photo_url:
            logger.warning(f"No photo URL provided for member {member_id}")
            return False
        
        photo_path = self.get_photo_path(member_id)
        
        try:
            # Set a user agent to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Download the photo using centralized timeout configuration
            response = requests.get(photo_url, headers=headers, timeout=TimeoutConfig.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Save the photo
            with open(photo_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded photo for member {member_id}")
            return True
        except Exception as e:
            logger.error(f"Error downloading photo for member {member_id}: {str(e)}")
            return False
