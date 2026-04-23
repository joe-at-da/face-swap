"""
Intelligent Face Swapping Service

This service provides advanced face targeting and enhancement capabilities:
1. Face-specific targeting using face recognition
2. Face enhancement instead of replacement
3. AI-based filtering and alteration
4. Person-specific face matching
"""

import os
import cv2
import numpy as np
import logging
import json
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from scipy.spatial.distance import cosine
import face_recognition

from backend.services.recognition.facial_recognition import FacialRecognitionService

logger = logging.getLogger(__name__)

class IntelligentFaceSwapService:
    """
    Intelligent face swapping service that targets specific faces and enhances them
    rather than simple replacement.
    """
    
    def __init__(self):
        """Initialize the intelligent face swap service."""
        self.face_recognition = FacialRecognitionService()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.mp_encodings = self._load_mp_encodings()
        
    def _load_mp_encodings(self) -> Dict[str, Any]:
        """Load MP face encodings and metadata."""
        try:
            encodings_file = "/app/data/mp_embeddings/combined_encodings.json"
            if os.path.exists(encodings_file):
                with open(encodings_file, 'r') as f:
                    return json.load(f)
            else:
                # Fallback to individual encoding files
                mp_encodings = {}
                embeddings_dir = Path("/app/data/mp_embeddings")
                if embeddings_dir.exists():
                    for encoding_file in embeddings_dir.glob("*.json"):
                        member_id = encoding_file.stem
                        try:
                            with open(encoding_file, 'r') as f:
                                encoding = json.load(f)
                                mp_encodings[member_id] = encoding
                        except:
                            continue
                return mp_encodings
        except Exception as e:
            logger.error(f"Error loading MP encodings: {str(e)}")
            return {}
    
    def detect_and_identify_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces and identify them using face recognition.
        
        Returns:
            List of face dictionaries with detection and identification info
        """
        try:
            # Convert to RGB for face_recognition library
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_image, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            identified_faces = []
            
            for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                top, right, bottom, left = face_location
                face_box = (left, top, right - left, bottom - top)  # Convert to (x, y, w, h)
                
                # Identify face using MP database
                best_match = self._find_best_face_match(face_encoding)
                
                face_info = {
                    "face_id": i,
                    "location": face_location,
                    "box": face_box,
                    "encoding": face_encoding.tolist() if hasattr(face_encoding, 'tolist') else face_encoding,
                    "identified_mp": best_match,
                    "confidence": best_match.get("confidence", 0) if best_match else 0,
                    "width": right - left,
                    "height": bottom - top,
                    "center": ((left + right) // 2, (top + bottom) // 2)
                }
                
                identified_faces.append(face_info)
            
            logger.info(f"Detected and identified {len(identified_faces)} faces")
            return identified_faces
            
        except Exception as e:
            logger.error(f"Error in face detection and identification: {str(e)}")
            return []
    
    def _find_best_face_match(self, face_encoding: np.ndarray) -> Optional[Dict[str, Any]]:
        """Find the best matching MP for the given face encoding using the same method as the original system."""
        try:
            # Convert MP encodings to arrays for face_recognition library
            known_encodings = []
            known_member_ids = []
            
            for member_id, mp_data in self.mp_encodings.items():
                # Handle both list and dict formats
                if isinstance(mp_data, dict) and 'embedding' in mp_data:
                    encoding_data = mp_data['embedding']
                    if isinstance(encoding_data, list) and len(encoding_data) == 128:
                        mp_encoding = np.array(encoding_data)
                        known_encodings.append(mp_encoding)
                        known_member_ids.append(member_id)
                elif isinstance(mp_data, list) and len(mp_data) == 128:
                    mp_encoding = np.array(mp_data)
                    known_encodings.append(mp_encoding)
                    known_member_ids.append(member_id)
            
            if not known_encodings:
                logger.warning("No MP encodings available for comparison")
                return None
            
            # Use face_recognition.compare_faces like the original system with higher confidence threshold
            known_encodings_array = np.array(known_encodings)
            matches = face_recognition.compare_faces(known_encodings_array, face_encoding, tolerance=0.4)
            face_distances = face_recognition.face_distance(known_encodings_array, face_encoding)
            
            logger.debug(f"Face comparison: {sum(matches)} matches found, best distance: {min(face_distances) if face_distances.size > 0 else 'N/A'}")
            
            if any(matches):
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    member_id = known_member_ids[best_match_index]
                    confidence = 1.0 - face_distances[best_match_index]
                    distance = face_distances[best_match_index]
                    
                    return {
                        "member_id": member_id,
                        "confidence": confidence,
                        "distance": distance,
                        "name": f"MP {member_id}"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding face match: {str(e)}")
            return None
    
    def enhance_face_with_filters(self, image: np.ndarray, face_box: Tuple[int, int, int, int], 
                                 enhancement_type: str = "smooth") -> np.ndarray:
        """
        Apply face enhancement filters instead of replacement.
        
        Args:
            image: Input image
            face_box: Face bounding box (x, y, w, h)
            enhancement_type: Type of enhancement ("smooth", "sharpen", "cartoon", "age", "beautify")
            
        Returns:
            Enhanced image
        """
        try:
            result_image = image.copy()
            x, y, w, h = face_box
            
            # Extract face region with padding
            padding = 20
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.shape[1], x + w + padding)
            y2 = min(image.shape[0], y + h + padding)
            
            face_region = result_image[y1:y2, x1:x2]
            
            # Apply enhancement based on type
            if enhancement_type == "smooth":
                enhanced_face = self._apply_smoothing_filter(face_region)
            elif enhancement_type == "sharpen":
                enhanced_face = self._apply_sharpening_filter(face_region)
            elif enhancement_type == "cartoon":
                enhanced_face = self._apply_cartoon_filter(face_region)
            elif enhancement_type == "age":
                enhanced_face = self._apply_age_filter(face_region)
            elif enhancement_type == "beautify":
                enhanced_face = self._apply_beautify_filter(face_region)
            else:
                enhanced_face = face_region
            
            # Blend enhanced face back with original
            alpha = 0.7  # Enhancement strength
            result_image[y1:y2, x1:x2] = cv2.addWeighted(face_region, 1-alpha, enhanced_face, alpha, 0)
            
            return result_image
            
        except Exception as e:
            logger.error(f"Error in face enhancement: {str(e)}")
            return image
    
    def _apply_smoothing_filter(self, face_region: np.ndarray) -> np.ndarray:
        """Apply smoothing filter to face."""
        # Bilateral filter for skin smoothing
        smooth = cv2.bilateralFilter(face_region, 15, 80, 80)
        return smooth
    
    def _apply_sharpening_filter(self, face_region: np.ndarray) -> np.ndarray:
        """Apply sharpening filter to face."""
        kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(face_region, -1, kernel)
        return cv2.addWeighted(face_region, 0.7, sharpened, 0.3, 0)
    
    def _apply_cartoon_filter(self, face_region: np.ndarray) -> np.ndarray:
        """Apply cartoon effect to face."""
        # Bilateral filter for smoothing
        smooth = cv2.bilateralFilter(face_region, 15, 80, 80)
        # Create edge mask
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        # Combine
        cartoon = cv2.bitwise_and(smooth, edges)
        return cartoon
    
    def _apply_age_filter(self, face_region: np.ndarray) -> np.ndarray:
        """Apply aging effect to face."""
        # Add wrinkles and skin texture changes
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        # Add noise for texture
        noise = np.random.normal(0, 25, gray.shape)
        aged_gray = np.clip(gray + noise, 0, 255).astype(np.uint8)
        aged = cv2.cvtColor(aged_gray, cv2.COLOR_GRAY2BGR)
        # Blend with original
        return cv2.addWeighted(face_region, 0.6, aged, 0.4, 0)
    
    def _apply_beautify_filter(self, face_region: np.ndarray) -> np.ndarray:
        """Apply beautification filter to face."""
        # Skin smoothing + eye brightening
        smooth = cv2.bilateralFilter(face_region, 20, 100, 100)
        # Increase brightness slightly
        beautified = cv2.convertScaleAbs(smooth, alpha=1.1, beta=10)
        return beautified
    
    def swap_target_face_intelligently(self, image_path: str, target_member_id: str, 
                                     output_path: str, enhancement_type: str = "smooth",
                                     target_specific: bool = True) -> Dict[str, Any]:
        """
        Intelligently swap/enhance only the target member's face.
        
        Args:
            image_path: Path to source image
            target_member_id: Target MP member ID
            output_path: Path to save output image
            enhancement_type: Type of enhancement to apply
            target_specific: If True, only enhance the target MP's face
            
        Returns:
            Dictionary containing operation results
        """
        try:
            # Load source image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Failed to load image"}
            
            # Detect and identify all faces
            identified_faces = self.detect_and_identify_faces(image)
            if len(identified_faces) == 0:
                return {"success": False, "error": "No faces detected in image"}
            
            result_image = image.copy()
            faces_processed = 0
            target_faces_found = 0
            
            # Process each face
            for face_info in identified_faces:
                face_box = face_info["box"]
                x, y, w, h = face_box
                
                # Skip very small faces
                if w < 50 or h < 50:
                    continue
                
                # Check if this is our target face (if target_specific is True)
                should_process = False
                if target_specific:
                    if face_info["identified_mp"] and face_info["identified_mp"].get("member_id") == target_member_id:
                        should_process = True
                        target_faces_found += 1
                else:
                    # Process all faces
                    should_process = True
                
                if should_process:
                    # Apply enhancement instead of replacement
                    result_image = self.enhance_face_with_filters(result_image, face_box, enhancement_type)
                    faces_processed += 1
            
            # Save result
            success = cv2.imwrite(output_path, result_image)
            if not success:
                return {"success": False, "error": "Failed to save output image"}
            
            return {
                "success": True,
                "faces_detected": len(identified_faces),
                "target_faces_found": target_faces_found,
                "faces_processed": faces_processed,
                "enhancement_type": enhancement_type,
                "target_specific": target_specific,
                "output_path": output_path,
                "target_member_id": target_member_id,
                "face_details": identified_faces
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent face swapping: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_face_analysis_report(self, image_path: str) -> Dict[str, Any]:
        """Create a detailed analysis of faces in the image."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Failed to load image"}
            
            identified_faces = self.detect_and_identify_faces(image)
            
            # Create analysis report
            analysis = {
                "success": True,
                "total_faces": len(identified_faces),
                "identified_faces": 0,
                "unidentified_faces": 0,
                "face_details": []
            }
            
            for face_info in identified_faces:
                face_detail = {
                    "face_id": face_info["face_id"],
                    "location": face_info["location"],
                    "size": f"{face_info['width']}x{face_info['height']}",
                    "center": face_info["center"],
                    "identified_mp": None,
                    "confidence": 0
                }
                
                if face_info["identified_mp"]:
                    analysis["identified_faces"] += 1
                    face_detail["identified_mp"] = face_info["identified_mp"]
                    face_detail["confidence"] = face_info["confidence"]
                else:
                    analysis["unidentified_faces"] += 1
                
                analysis["face_details"].append(face_detail)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error creating face analysis: {str(e)}")
            return {"success": False, "error": str(e)}
