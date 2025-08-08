"""
Timeline-Based Face Selection Service

This service implements intelligent face selection within speech group timeline ranges
to reduce face borrowing and improve timeline-photo alignment.

Key features:
1. Groups faces by speech group timeline ranges
2. Selects the best face within each range using quality criteria
3. Maps selected faces to timeline segments
4. Reduces redundant face borrowing
"""

import logging
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class TimelineFaceSelector:
    """
    Intelligent face selection service for timeline-based face mapping.
    
    This service addresses the face borrowing problem by selecting the best face
    within each speech group timeline range and mapping it consistently across
    the entire timeline segment.
    """
    
    def __init__(self):
        """Initialize the timeline face selector."""
        self.quality_weights = {
            'mouth_open': 0.35,     # Higher priority for speaking indicator
            'center_frame': 0.25,   # Prioritize faces in center of frame
            'face_size': 0.2,       # Prioritize larger faces
            'sharpness': 0.12,      # Slightly reduced for speaking priority
            'frequency': 0.08       # Slightly reduced for speaking priority
        }
    
    def select_best_faces_for_timeline(self, 
                                     speech_groups: List[Dict], 
                                     all_faces: List[Dict],
                                     video_path: str = None) -> Dict[str, Dict]:
        """
        Select the best face for each speech group timeline range.
        
        Args:
            speech_groups: List of speech group dictionaries with start/end times
            all_faces: List of all detected faces with timestamps and quality data
            video_path: Optional path to video for additional analysis
            
        Returns:
            Dictionary mapping speech_group_id to selected face data
        """
        logger.info(f"Starting timeline-based face selection for {len(speech_groups)} speech groups")
        
        selected_faces = {}
        
        for speech_group in speech_groups:
            group_id = speech_group.get('speech_group_id', speech_group.get('id'))
            start_time = speech_group.get('start_time', speech_group.get('start', 0))
            end_time = speech_group.get('end_time', speech_group.get('end', 0))
            
            logger.debug(f"Processing speech group {group_id}: {start_time:.2f}s - {end_time:.2f}s")
            
            # Find all faces within this timeline range
            faces_in_range = self._get_faces_in_timeline_range(
                all_faces, start_time, end_time
            )
            
            if not faces_in_range:
                logger.warning(f"No faces found in timeline range {start_time:.2f}s - {end_time:.2f}s for group {group_id}")
                continue
            
            logger.info(f"Found {len(faces_in_range)} faces in timeline range for group {group_id}")
            
            # Select the best face from this range
            best_face = self._select_best_face_in_range(
                faces_in_range, start_time, end_time, video_path
            )
            
            if best_face:
                selected_faces[group_id] = {
                    'face_data': best_face,
                    'timeline_range': {
                        'start': start_time,
                        'end': end_time,
                        'duration': end_time - start_time
                    },
                    'total_faces_in_range': len(faces_in_range),
                    'selection_reason': best_face.get('selection_reason', 'quality_score')
                }
                
                logger.info(f"Selected best face for group {group_id}: {best_face.get('face_path', 'unknown')} "
                           f"(score: {best_face.get('quality_score', 0):.3f}, "
                           f"reason: {best_face.get('selection_reason', 'quality')})")
            else:
                logger.warning(f"Could not select best face for group {group_id}")
        
        logger.info(f"Timeline face selection completed: {len(selected_faces)} faces selected for {len(speech_groups)} groups")
        return selected_faces
    
    def _get_faces_in_timeline_range(self, 
                                   all_faces: List[Dict], 
                                   start_time: float, 
                                   end_time: float,
                                   tolerance: float = None) -> List[Dict]:
        """
        Get all faces within a specific timeline range.
        
        Args:
            all_faces: List of all detected faces
            start_time: Start time of the timeline range
            end_time: End time of the timeline range
            tolerance: Time tolerance for including faces slightly outside range
            
        Returns:
            List of faces within the timeline range
        """
        # Adaptive tolerance based on speech group duration
        if tolerance is None:
            duration = end_time - start_time
            # Shorter segments get smaller tolerance, longer segments get more
            tolerance = min(max(duration * 0.1, 0.5), 2.0)  # 10% of duration, min 0.5s, max 2s
        
        faces_in_range = []
        
        for face in all_faces:
            face_time = face.get('timestamp', face.get('face_time', 0))
            
            # Check if face is within the timeline range (with adaptive tolerance)
            if (start_time - tolerance) <= face_time <= (end_time + tolerance):
                faces_in_range.append(face)
        
        return faces_in_range
    
    def _select_best_face_in_range(self, 
                                 faces_in_range: List[Dict], 
                                 start_time: float, 
                                 end_time: float,
                                 video_path: str = None) -> Optional[Dict]:
        """
        Select the best face from faces within a timeline range.
        
        Args:
            faces_in_range: List of faces within the timeline range
            start_time: Start time of the timeline range
            end_time: End time of the timeline range
            video_path: Optional path to video for additional analysis
            
        Returns:
            Best face data or None if no suitable face found
        """
        if not faces_in_range:
            return None
        
        # Calculate enhanced quality scores for each face
        scored_faces = []
        
        for face in faces_in_range:
            enhanced_score = self._calculate_enhanced_quality_score(
                face, faces_in_range, start_time, end_time, video_path
            )
            
            face_copy = face.copy()
            face_copy['enhanced_quality_score'] = enhanced_score
            scored_faces.append(face_copy)
        
        # Sort by enhanced quality score and select the best
        scored_faces.sort(key=lambda x: x.get('enhanced_quality_score', 0), reverse=True)
        best_face = scored_faces[0]
        
        # Add selection reason
        best_face['selection_reason'] = self._get_selection_reason(best_face, faces_in_range)
        
        return best_face
    
    def _calculate_enhanced_quality_score(self, 
                                        face: Dict, 
                                        all_faces_in_range: List[Dict],
                                        start_time: float, 
                                        end_time: float,
                                        video_path: str = None) -> float:
        """
        Calculate enhanced quality score using multiple criteria.
        
        Args:
            face: Face data dictionary
            all_faces_in_range: All faces in the timeline range
            start_time: Start time of timeline range
            end_time: End time of timeline range
            video_path: Optional path to video for additional analysis
            
        Returns:
            Enhanced quality score
        """
        base_score = face.get('quality_score', 0)
        
        # Initialize component scores
        mouth_open_score = 0
        center_frame_score = 0
        face_size_score = 0
        sharpness_score = 0
        frequency_score = 0
        
        # 1. Mouth open detection (speaking indicator)
        mouth_open_score = self._detect_mouth_open(face, video_path)
        
        # 2. Center frame positioning
        center_frame_score = self._calculate_center_frame_score(face)
        
        # 3. Face size relative to frame
        face_size_score = self._calculate_face_size_score(face)
        
        # 4. Image sharpness
        sharpness_score = self._calculate_sharpness_score(face, video_path)
        
        # 5. Frequency of similar faces in range (consistency)
        frequency_score = self._calculate_frequency_score(face, all_faces_in_range)
        
        # Calculate weighted enhanced score
        enhanced_score = (
            base_score * 0.4 +  # Base quality score
            mouth_open_score * self.quality_weights['mouth_open'] +
            center_frame_score * self.quality_weights['center_frame'] +
            face_size_score * self.quality_weights['face_size'] +
            sharpness_score * self.quality_weights['sharpness'] +
            frequency_score * self.quality_weights['frequency']
        )
        
        return enhanced_score
    
    def _detect_mouth_open(self, face: Dict, video_path: str = None) -> float:
        """
        Detect if mouth is open (indicating speaking).
        
        Args:
            face: Face data dictionary
            video_path: Optional path to video
            
        Returns:
            Mouth open score (0.0 to 1.0)
        """
        # Check if mouth open data is already available
        if 'mouth_open' in face:
            return float(face['mouth_open'])
        
        # Try to analyze face image if available
        face_path = face.get('face_path', face.get('face_image_path', ''))
        if face_path and Path(face_path).exists():
            try:
                # Load face image
                face_img = cv2.imread(face_path)
                if face_img is not None:
                    # Simple mouth open detection based on face geometry
                    # This is a simplified implementation - could be enhanced with ML models
                    height, width = face_img.shape[:2]
                    
                    # Check if face has sufficient resolution for mouth analysis
                    if height >= 100 and width >= 100:
                        # Analyze lower third of face for mouth region (more precise)
                        mouth_region = face_img[int(height * 0.65):int(height * 0.85), 
                                              int(width * 0.3):int(width * 0.7)]
                        
                        # Enhanced mouth open detection
                        gray_mouth = cv2.cvtColor(mouth_region, cv2.COLOR_BGR2GRAY)
                        
                        # Apply Gaussian blur to reduce noise
                        blurred = cv2.GaussianBlur(gray_mouth, (5, 5), 0)
                        
                        # Use adaptive threshold for better dark region detection
                        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        dark_pixels = np.sum(thresh == 0)  # Count dark pixels (mouth cavity)
                        total_pixels = thresh.size
                        
                        # Enhanced scoring with better normalization
                        mouth_open_ratio = min(dark_pixels / total_pixels * 4, 1.0)
                        
                        # Bonus for significant dark regions (likely open mouth)
                        if mouth_open_ratio > 0.15:
                            mouth_open_ratio = min(mouth_open_ratio * 1.2, 1.0)
                        
                        return mouth_open_ratio
                        
            except Exception as e:
                logger.debug(f"Error analyzing mouth open for {face_path}: {e}")
        
        # Default: assume neutral (0.5)
        return 0.5
    
    def _calculate_center_frame_score(self, face: Dict) -> float:
        """
        Calculate score based on face position relative to frame center.
        
        Args:
            face: Face data dictionary
            
        Returns:
            Center frame score (0.0 to 1.0)
        """
        # Get face position data
        face_location = face.get('face_location', face.get('location', []))
        frame_width = face.get('frame_width', 1920)  # Default HD width
        frame_height = face.get('frame_height', 1080)  # Default HD height
        
        if not face_location or len(face_location) < 4:
            return 0.5  # Default neutral score
        
        # Face location format: [top, right, bottom, left]
        top, right, bottom, left = face_location
        
        # Calculate face center
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        
        # Calculate frame center
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # Calculate distance from center (normalized)
        distance_x = abs(face_center_x - frame_center_x) / (frame_width / 2)
        distance_y = abs(face_center_y - frame_center_y) / (frame_height / 2)
        
        # Calculate center score (closer to center = higher score)
        center_score = 1.0 - min(np.sqrt(distance_x**2 + distance_y**2), 1.0)
        
        return center_score
    
    def _calculate_face_size_score(self, face: Dict) -> float:
        """
        Calculate score based on face size relative to frame.
        
        Args:
            face: Face data dictionary
            
        Returns:
            Face size score (0.0 to 1.0)
        """
        face_location = face.get('face_location', face.get('location', []))
        
        if not face_location or len(face_location) < 4:
            return 0.5  # Default neutral score
        
        # Face location format: [top, right, bottom, left]
        top, right, bottom, left = face_location
        
        # Calculate face area
        face_width = right - left
        face_height = bottom - top
        face_area = face_width * face_height
        
        # Get frame dimensions for relative sizing
        frame_width = face.get('frame_width', 1920)
        frame_height = face.get('frame_height', 1080)
        frame_area = frame_width * frame_height
        
        # Calculate relative face size (percentage of frame)
        relative_size = face_area / frame_area
        
        # Optimal face size is 3-8% of frame area for good visibility
        if 0.03 <= relative_size <= 0.08:
            size_score = 1.0  # Perfect size range
        elif relative_size < 0.03:
            # Too small - scale linearly from 0 to 1
            size_score = relative_size / 0.03
        else:
            # Too large - diminishing returns but not penalized heavily
            size_score = min(0.08 / relative_size, 1.0)
        
        return size_score
    
    def _calculate_sharpness_score(self, face: Dict, video_path: str = None) -> float:
        """
        Calculate sharpness score for the face.
        
        Args:
            face: Face data dictionary
            video_path: Optional path to video
            
        Returns:
            Sharpness score (0.0 to 1.0)
        """
        # Check if sharpness data is already available
        if 'sharpness' in face:
            return min(float(face['sharpness']) / 100.0, 1.0)  # Normalize to 0-1
        
        # Try to analyze face image if available
        face_path = face.get('face_path', face.get('face_image_path', ''))
        if face_path and Path(face_path).exists():
            try:
                # Load face image
                face_img = cv2.imread(face_path, cv2.IMREAD_GRAYSCALE)
                if face_img is not None:
                    # Calculate Laplacian variance (sharpness measure)
                    laplacian_var = cv2.Laplacian(face_img, cv2.CV_64F).var()
                    
                    # Normalize to 0-1 range (typical sharp faces have variance > 100)
                    sharpness_score = min(laplacian_var / 200.0, 1.0)
                    return sharpness_score
                    
            except Exception as e:
                logger.debug(f"Error analyzing sharpness for {face_path}: {e}")
        
        # Default: assume moderate sharpness
        return 0.6
    
    def _calculate_frequency_score(self, face: Dict, all_faces_in_range: List[Dict]) -> float:
        """
        Calculate frequency score based on how often similar faces appear in range.
        
        Args:
            face: Face data dictionary
            all_faces_in_range: All faces in the timeline range
            
        Returns:
            Frequency score (0.0 to 1.0)
        """
        if len(all_faces_in_range) <= 1:
            return 1.0  # Single face gets max frequency score
        
        # Enhanced frequency calculation with adaptive tolerance
        face_location = face.get('face_location', face.get('location', []))
        if not face_location or len(face_location) < 4:
            return 0.5
        
        # Get frame dimensions for relative tolerance
        frame_width = face.get('frame_width', 1920)
        frame_height = face.get('frame_height', 1080)
        
        # Adaptive tolerance based on frame size (2% of frame dimensions)
        tolerance_x = frame_width * 0.02
        tolerance_y = frame_height * 0.02
        
        similar_faces = 0
        face_top, face_right, face_bottom, face_left = face_location
        face_center_x = (face_left + face_right) / 2
        face_center_y = (face_top + face_bottom) / 2
        
        for other_face in all_faces_in_range:
            if other_face == face:
                continue
                
            other_location = other_face.get('face_location', other_face.get('location', []))
            if not other_location or len(other_location) < 4:
                continue
            
            # Calculate center-to-center distance for better similarity detection
            other_top, other_right, other_bottom, other_left = other_location
            other_center_x = (other_left + other_right) / 2
            other_center_y = (other_top + other_bottom) / 2
            
            # Check if face centers are within tolerance
            distance_x = abs(face_center_x - other_center_x)
            distance_y = abs(face_center_y - other_center_y)
            
            if distance_x < tolerance_x and distance_y < tolerance_y:
                similar_faces += 1
        
        # Enhanced frequency score with better normalization
        if similar_faces > 0:
            frequency_score = min((similar_faces + 1) / len(all_faces_in_range), 1.0)
        else:
            frequency_score = 0.3  # Penalty for isolated faces
        
        return frequency_score
    
    def _get_selection_reason(self, best_face: Dict, all_faces: List[Dict]) -> str:
        """
        Determine the primary reason this face was selected.
        
        Args:
            best_face: The selected best face
            all_faces: All faces in the range
            
        Returns:
            String describing the selection reason
        """
        reasons = []
        
        # Check mouth open
        mouth_score = self._detect_mouth_open(best_face)
        if mouth_score > 0.7:
            reasons.append("mouth_open")
        
        # Check center frame
        center_score = self._calculate_center_frame_score(best_face)
        if center_score > 0.8:
            reasons.append("center_frame")
        
        # Check face size
        size_score = self._calculate_face_size_score(best_face)
        if size_score > 0.8:
            reasons.append("large_face")
        
        # Check quality score
        quality_score = best_face.get('quality_score', 0)
        if quality_score > 0.8:
            reasons.append("high_quality")
        
        if reasons:
            return "+".join(reasons)
        else:
            return "best_available"
    
    def map_faces_to_speech_groups(self, 
                                 selected_faces: Dict[str, Dict],
                                 speech_groups: List[Dict]) -> Dict[str, Dict]:
        """
        Map selected faces to all segments within their speech groups.
        
        Args:
            selected_faces: Dictionary of selected faces by speech_group_id
            speech_groups: List of speech group dictionaries
            
        Returns:
            Dictionary mapping segment_id to face data
        """
        segment_face_mapping = {}
        
        for speech_group in speech_groups:
            group_id = speech_group.get('speech_group_id', speech_group.get('id'))
            
            if group_id not in selected_faces:
                logger.warning(f"No selected face found for speech group {group_id}")
                continue
            
            selected_face = selected_faces[group_id]
            
            # Map this face to all segments in the speech group
            segments = speech_group.get('segments', [speech_group])  # Handle both grouped and individual segments
            
            for segment in segments:
                segment_id = segment.get('id', segment.get('segment_id'))
                if segment_id:
                    segment_face_mapping[segment_id] = {
                        'face_data': selected_face['face_data'],
                        'speech_group_id': group_id,
                        'timeline_range': selected_face['timeline_range'],
                        'mapping_reason': 'timeline_selection'
                    }
        
        logger.info(f"Mapped {len(selected_faces)} selected faces to {len(segment_face_mapping)} segments")
        return segment_face_mapping
