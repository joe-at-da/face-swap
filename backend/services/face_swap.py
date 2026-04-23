"""
Face Swapping Service using OpenCV and existing face recognition infrastructure.

This service provides face swapping functionality using OpenCV for image processing
and the existing face recognition system for face detection and landmark extraction.
"""

import os
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from backend.services.recognition.facial_recognition import FacialRecognitionService

logger = logging.getLogger(__name__)

class FaceSwapService:
    """
    Face swapping service that uses OpenCV and existing face recognition infrastructure.
    
    This service provides basic face swapping capabilities without requiring complex
    deep learning models like FaceFusion, making it more suitable for Docker environments.
    """
    
    def __init__(self):
        """Initialize the face swap service."""
        self.face_recognition = FacialRecognitionService()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def detect_faces_opencv(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using OpenCV's Haar cascade classifier.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of face bounding boxes (x, y, w, h)
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            return faces
        except Exception as e:
            logger.error(f"Error detecting faces with OpenCV: {str(e)}")
            return []
    
    def extract_face_region(self, image: np.ndarray, face_box: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Extract face region from image.
        
        Args:
            image: Input image as numpy array
            face_box: Face bounding box (x, y, w, h)
            
        Returns:
            Face region as numpy array or None if extraction fails
        """
        try:
            x, y, w, h = face_box
            # Add padding to include more of the face
            padding = 20
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.shape[1], x + w + padding)
            y2 = min(image.shape[0], y + h + padding)
            
            face_region = image[y1:y2, x1:x2]
            return face_region
        except Exception as e:
            logger.error(f"Error extracting face region: {str(e)}")
            return None
    
    def resize_face_to_target(self, source_face: np.ndarray, target_face: np.ndarray) -> np.ndarray:
        """
        Resize source face to match target face dimensions.
        
        Args:
            source_face: Source face image
            target_face: Target face image
            
        Returns:
            Resized source face
        """
        try:
            return cv2.resize(source_face, (target_face.shape[1], target_face.shape[0]))
        except Exception as e:
            logger.error(f"Error resizing face: {str(e)}")
            return source_face
    
    def blend_faces(self, target_image: np.ndarray, target_box: Tuple[int, int, int, int], 
                   source_face: np.ndarray, blend_factor: float = 0.7) -> np.ndarray:
        """
        Blend source face into target image at specified location.
        
        Args:
            target_image: Target image to modify
            target_box: Target face bounding box (x, y, w, h)
            source_face: Source face to blend
            blend_factor: Blending factor (0.0 = target, 1.0 = source)
            
        Returns:
            Modified image with blended face
        """
        try:
            result_image = target_image.copy()
            x, y, w, h = target_box
            
            # Resize source face to match target face size
            resized_source = cv2.resize(source_face, (w, h))
            
            # Create mask for seamless blending
            mask = np.zeros((h, w), dtype=np.uint8)
            center = (w // 2, h // 2)
            cv2.circle(mask, center, min(w, h) // 2, 255, -1)
            mask = cv2.GaussianBlur(mask, (15, 15), 0)
            
            # Apply mask to source face
            masked_source = cv2.bitwise_and(resized_source, resized_source, mask=mask)
            
            # Extract target face region
            target_face_region = result_image[y:y+h, x:x+w]
            
            # Blend faces
            blended = cv2.addWeighted(target_face_region, 1 - blend_factor, masked_source, blend_factor, 0)
            
            # Place blended face back into target image
            result_image[y:y+h, x:x+w] = blended
            
            return result_image
        except Exception as e:
            logger.error(f"Error blending faces: {str(e)}")
            return target_image
    
    def swap_face_in_image(self, image_path: str, target_member_id: str, 
                          output_path: str, blend_factor: float = 0.7) -> Dict[str, Any]:
        """
        Swap faces in an image with a target MP's face.
        
        Args:
            image_path: Path to source image
            target_member_id: Target MP member ID for face swapping
            output_path: Path to save output image
            blend_factor: Blending factor for face replacement
            
        Returns:
            Dictionary containing operation results
        """
        try:
            # Load source image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Failed to load image"}
            
            # Detect faces in source image
            faces = self.detect_faces_opencv(image)
            if len(faces) == 0:
                return {"success": False, "error": "No faces detected in image"}
            
            # Load target MP face from embeddings directory
            target_face_path = self.get_mp_face_path(target_member_id)
            if not target_face_path or not os.path.exists(target_face_path):
                return {"success": False, "error": f"Target MP face not found for member {target_member_id}"}
            
            target_face = cv2.imread(target_face_path)
            if target_face is None:
                return {"success": False, "error": "Failed to load target MP face"}
            
            # Process each detected face
            result_image = image.copy()
            faces_swapped = 0
            
            for face_box in faces:
                x, y, w, h = face_box
                
                # Skip very small faces
                if w < 50 or h < 50:
                    continue
                
                # Blend target face into source image
                result_image = self.blend_faces(result_image, face_box, target_face, blend_factor)
                faces_swapped += 1
            
            # Save result
            success = cv2.imwrite(output_path, result_image)
            if not success:
                return {"success": False, "error": "Failed to save output image"}
            
            return {
                "success": True,
                "faces_detected": len(faces),
                "faces_swapped": faces_swapped,
                "output_path": output_path,
                "target_member_id": target_member_id
            }
            
        except Exception as e:
            logger.error(f"Error in face swap: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_mp_face_path(self, member_id: str) -> Optional[str]:
        """
        Get the path to an MP's face image.
        
        Args:
            member_id: MP member ID
            
        Returns:
            Path to MP face image or None if not found
        """
        try:
            # Check both Docker and local paths
            docker_path = f"/app/data/mp_photos/{member_id}.jpg"
            local_path = f"/Users/joebradley/Veedoo/Development/the-mp/data/mp_photos/{member_id}.jpg"
            
            if os.path.exists(docker_path):
                return docker_path
            elif os.path.exists(local_path):
                return local_path
            else:
                # Check if there are any photo files with this member ID
                mp_photos_dir = "/app/data/mp_photos"
                if not os.path.exists(mp_photos_dir):
                    mp_photos_dir = "/Users/joebradley/Veedoo/Development/the-mp/data/mp_photos"
                
                if os.path.exists(mp_photos_dir):
                    for filename in os.listdir(mp_photos_dir):
                        if filename.startswith(member_id) and filename.endswith(('.jpg', '.jpeg', '.png')):
                            return os.path.join(mp_photos_dir, filename)
                
                return None
        except Exception as e:
            logger.error(f"Error getting MP face path: {str(e)}")
            return None
    
    def get_available_mp_faces(self) -> List[Dict[str, Any]]:
        """
        Get list of available MP faces for swapping.
        
        Returns:
            List of dictionaries with MP information
        """
        try:
            mp_photos_dir = "/app/data/mp_photos"
            if not os.path.exists(mp_photos_dir):
                mp_photos_dir = "/Users/joebradley/Veedoo/Development/the-mp/data/mp_photos"
            
            if not os.path.exists(mp_photos_dir):
                return []
            
            available_faces = []
            for filename in os.listdir(mp_photos_dir):
                if filename.endswith(('.jpg', '.jpeg', '.png')):
                    member_id = filename.split('.')[0]
                    face_path = os.path.join(mp_photos_dir, filename)
                    
                    # Try to get member name from embeddings
                    member_name = f"MP {member_id}"
                    embedding_path = f"/app/data/mp_embeddings/{member_id}.json"
                    if not os.path.exists(embedding_path):
                        embedding_path = f"/Users/joebradley/Veedoo/Development/the-mp/data/mp_embeddings/{member_id}.json"
                    
                    available_faces.append({
                        "member_id": member_id,
                        "name": member_name,
                        "face_path": face_path,
                        "embedding_path": embedding_path if os.path.exists(embedding_path) else None
                    })
            
            return available_faces
        except Exception as e:
            logger.error(f"Error getting available MP faces: {str(e)}")
            return []
