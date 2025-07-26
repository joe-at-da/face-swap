"""
Optimized face detection module for parliamentary videos
Implements several performance optimizations:
1. Scene change detection
2. Face tracking
3. Region of Interest (ROI) restriction
4. Reduced HOG upsampling
5. YuNet face detector validation
"""
import os
import cv2
import face_recognition
import numpy as np
import logging
import time
import uuid
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants for YuNet face detector
YUNET_SCORE_THRESHOLD = 0.7  # Higher threshold for stricter filtering
YUNET_NMS_THRESHOLD = 0.3
YUNET_TOP_K = 5000

# Constants for face validation
MIN_FACE_CONFIDENCE = 0.6  # Minimum confidence for face detection
MIN_LANDMARK_CONFIDENCE = 0.8  # Minimum confidence for landmark detection
MIN_EYE_ASPECT_RATIO = 0.15  # Minimum eye aspect ratio for open eyes
MIN_FACE_ASPECT_RATIO = 1.0  # Minimum face aspect ratio (height/width)
MAX_FACE_ASPECT_RATIO = 1.8  # Maximum face aspect ratio (height/width)

class OptimizedFaceDetector:
    """
    Optimized face detector for parliamentary videos with significantly improved performance.
    Implements scene change detection, face tracking, and ROI restriction.
    """
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'extracted_faces')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize YuNet face detector for validation
        self.initialize_yunet_detector()
        
        # Initialize trackers list
        self.trackers = []
        self.previous_frame = None
        self.current_segment_faces = []
        self.segment_duration = 5  # seconds
    
    def initialize_yunet_detector(self):
        """Initialize the YuNet face detector from OpenCV"""
        try:
            # Try multiple possible locations for the YuNet model
            model_paths = [
                "/app/models/face_recognition/face_detection_yunet_2023mar.onnx",  # Docker container path
                "/app/models/face_detection_yunet_2023mar.onnx",  # Alternative path
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                             "../../../models/face_detection_yunet_2023mar.onnx"),  # Local development path
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                             "../../../models/face_recognition/face_detection_yunet_2023mar.onnx")  # Another local path
            ]
            
            # Find the first existing model path
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    logger.info(f"Found YuNet model at: {model_path}")
                    break
            
            if model_path is None:
                logger.warning("YuNet model file not found in any of the expected locations")
                self.yunet_detector = None
                return
                
            # Create face detector using YuNet model
            self.yunet_detector = cv2.FaceDetectorYN.create(
                model_path,
                "",  # Empty config path
                (320, 320),  # Default input size, will be resized for each frame
                YUNET_SCORE_THRESHOLD,
                YUNET_NMS_THRESHOLD,
                YUNET_TOP_K
            )
            logger.info("YuNet face detector initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize YuNet face detector: {e}")
            self.yunet_detector = None
    
    def validate_faces_with_yunet(self, frame, face_locations):
        """Validate detected faces using YuNet face detector
        
        Args:
            frame: The video frame
            face_locations: List of face locations as (top, right, bottom, left)
            
        Returns:
            List of indices of validated faces
        """
        validated_indices = []
        
        # Process each face location with YuNet
        for i, (top, right, bottom, left) in enumerate(face_locations):
            # First check face aspect ratio to filter out obvious non-faces
            face_width = right - left
            face_height = bottom - top
            if face_width == 0:
                logger.debug(f"Skipping face with zero width at {top}, {right}, {bottom}, {left}")
                continue
                
            aspect_ratio = face_height / face_width
            if aspect_ratio < MIN_FACE_ASPECT_RATIO or aspect_ratio > MAX_FACE_ASPECT_RATIO:
                logger.debug(f"Skipping face with invalid aspect ratio: {aspect_ratio:.2f}")
                continue
            
            # Extract the face region with padding
            height, width = frame.shape[:2]
            padding_x = int((right - left) * 0.2)
            padding_y = int((bottom - top) * 0.2)
            
            # Apply padding with boundary checks
            adj_left = max(0, left - padding_x)
            adj_top = max(0, top - padding_y)
            adj_right = min(width, right + padding_x)
            adj_bottom = min(height, bottom + padding_y)
            
            face_roi = frame[adj_top:adj_bottom, adj_left:adj_right]
            
            if face_roi.size == 0 or face_roi.shape[0] == 0 or face_roi.shape[1] == 0:
                logger.debug(f"Skipping empty face ROI at {top}, {right}, {bottom}, {left}")
                continue
            
            # Check for skin tone in the face region (basic heuristic)
            hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            
            # Skin tones typically have certain hue and saturation ranges
            # This is a very basic heuristic and can be improved
            skin_mask = cv2.inRange(hsv_roi, (0, 20, 70), (25, 170, 255))  # Typical skin tone range
            skin_pixels = cv2.countNonZero(skin_mask)
            total_pixels = face_roi.shape[0] * face_roi.shape[1]
            skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
            
            # Furniture and other objects typically have different color distributions
            if skin_ratio < 0.15:  # At least 15% of pixels should be in skin tone range
                logger.debug(f"Skipping face with low skin tone ratio: {skin_ratio:.2f}")
                continue
            
            # Detect faces in the ROI using YuNet
            try:
                self.yunet_detector.setInputSize((face_roi.shape[1], face_roi.shape[0]))
                faces = self.yunet_detector.detect(face_roi)
                
                # Check if any faces were detected by YuNet
                if faces[1] is not None and len(faces[1]) > 0:
                    # Get the highest confidence face
                    best_confidence = 0
                    for face in faces[1]:
                        confidence = face[14]
                        if confidence > best_confidence:
                            best_confidence = confidence
                    
                    logger.debug(f"YuNet validation: face {i} confidence {best_confidence:.2f}")
                    
                    # Validate if confidence is above threshold
                    if best_confidence >= YUNET_SCORE_THRESHOLD:
                        validated_indices.append(i)
                        logger.debug(f"YuNet validation passed for face {i} with confidence {best_confidence:.2f}")
                    else:
                        logger.debug(f"YuNet validation failed for face {i}: low confidence {best_confidence:.2f}")
                else:
                    logger.debug(f"YuNet validation failed for face {i}: no faces detected")
            except Exception as e:
                logger.warning(f"Error in YuNet validation for face {i}: {str(e)}")
        
        # If no faces were validated with the higher threshold, try with a lower threshold
        if not validated_indices and len(face_locations) > 0:
            logger.debug("No faces validated with higher threshold, trying with lower threshold")
            original_threshold = self.yunet_detector.getScoreThreshold()
            self.yunet_detector.setScoreThreshold(0.4)  # Lower threshold for retry
            
            try:
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    # Check face aspect ratio again
                    face_width = right - left
                    face_height = bottom - top
                    if face_width == 0:
                        continue
                        
                    aspect_ratio = face_height / face_width
                    if aspect_ratio < MIN_FACE_ASPECT_RATIO or aspect_ratio > MAX_FACE_ASPECT_RATIO:
                        continue
                    
                    # Extract the face region with padding
                    height, width = frame.shape[:2]
                    padding_x = int((right - left) * 0.2)
                    padding_y = int((bottom - top) * 0.2)
                    
                    # Apply padding with boundary checks
                    adj_left = max(0, left - padding_x)
                    adj_top = max(0, top - padding_y)
                    adj_right = min(width, right + padding_x)
                    adj_bottom = min(height, bottom + padding_y)
                    
                    face_roi = frame[adj_top:adj_bottom, adj_left:adj_right]
                    
                    if face_roi.size == 0 or face_roi.shape[0] == 0 or face_roi.shape[1] == 0:
                        continue
                    
                    # Check for skin tone
                    hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
                    skin_mask = cv2.inRange(hsv_roi, (0, 20, 70), (25, 170, 255))
                    skin_pixels = cv2.countNonZero(skin_mask)
                    total_pixels = face_roi.shape[0] * face_roi.shape[1]
                    skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
                    
                    if skin_ratio < 0.15:
                        continue
                    
                    # Detect faces in the ROI using YuNet with lower threshold
                    try:
                        self.yunet_detector.setInputSize((face_roi.shape[1], face_roi.shape[0]))
                        faces = self.yunet_detector.detect(face_roi)
                        
                        # Check if any faces were detected by YuNet
                        if faces[1] is not None and len(faces[1]) > 0:
                            # Get the highest confidence face
                            best_confidence = 0
                            for face in faces[1]:
                                confidence = face[14]
                                if confidence > best_confidence:
                                    best_confidence = confidence
                            
                            # Validate if confidence is above lower threshold
                            if best_confidence >= 0.4:  # Lower threshold for retry
                                validated_indices.append(i)
                                logger.debug(f"YuNet validation passed with lower threshold for face {i}: {best_confidence:.2f}")
                            else:
                                logger.debug(f"YuNet validation failed with lower threshold for face {i}: {best_confidence:.2f}")
                    except Exception as e:
                        logger.warning(f"Error in YuNet validation with lower threshold for face {i}: {str(e)}")
            finally:
                # Restore original threshold
                self.yunet_detector.setScoreThreshold(original_threshold)
                
        logger.debug(f"YuNet validation: {len(validated_indices)}/{len(face_locations)} faces validated")
        return validated_indices
    
    def detect_scene_change(self, current_frame, previous_frame, threshold=0.2):
        """
        Detect if there's been a major scene change between frames
        
        Args:
            current_frame: Current video frame
            previous_frame: Previous video frame
            threshold: Threshold for scene change detection (0-1)
            
        Returns:
            bool: True if scene change detected, False otherwise
        """
        if previous_frame is None:
            return True
            
        # Convert to grayscale and calculate histograms
        gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
        
        # Compare histograms
        hist_current = cv2.calcHist([gray_current], [0], None, [64], [0, 256])
        hist_previous = cv2.calcHist([gray_previous], [0], None, [64], [0, 256])
        
        # Normalize and compare
        cv2.normalize(hist_current, hist_current, 0, 1.0, cv2.NORM_MINMAX)
        cv2.normalize(hist_previous, hist_previous, 0, 1.0, cv2.NORM_MINMAX)
        
        difference = cv2.compareHist(hist_current, hist_previous, cv2.HISTCMP_BHATTACHARYYA)
        
        return difference > threshold
    
    def get_frame_roi(self, frame, roi_scale=0.6):
        """
        Extract region of interest (center portion of frame)
        
        Args:
            frame: Input video frame
            roi_scale: Scale factor for ROI (0-1)
            
        Returns:
            tuple: (roi, x_start, y_start) - ROI image and its coordinates
        """
        height, width = frame.shape[:2]
        
        # Calculate ROI dimensions (e.g., center 60% of the frame)
        roi_width = int(width * roi_scale)
        roi_height = int(height * roi_scale)
        
        # Calculate ROI coordinates
        x_start = (width - roi_width) // 2
        y_start = (height - roi_height) // 2
        
        # Extract ROI
        roi = frame[y_start:y_start+roi_height, x_start:x_start+roi_width]
        
        return roi, x_start, y_start
    
    def detect_faces_in_roi(self, frame, roi_scale=0.6):
        """
        Detect faces in a region of interest within a frame.
        Uses a two-stage approach: HOG detection followed by YuNet validation.
        """
        # Get ROI
        roi, x_start, y_start = self.get_frame_roi(frame, roi_scale)
        
        # Convert ROI to RGB
        rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        
        # STAGE 1: Detect faces in ROI with HOG (fast but can have false positives)
        face_locations = face_recognition.face_locations(
            rgb_roi, 
            model="hog",
            number_of_times_to_upsample=0  # Reduced from default 1 to 0
        )
        
        # Adjust face coordinates back to original frame
        adjusted_locations = []
        for top, right, bottom, left in face_locations:
            adjusted_locations.append(
                (top + y_start, right + x_start, bottom + y_start, left + x_start)
            )
        
        # If no faces found with HOG, return empty results
        if not adjusted_locations:
            return [], []
        
        # STAGE 2: Validate with YuNet detector if available
        validated_locations = []
        validated_indices = []
        
        # Convert full frame to RGB for encodings
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Try YuNet validation if available
        if self.yunet_detector is not None:
            try:
                # For each HOG detection, validate with YuNet
                validated_indices = self.validate_faces_with_yunet(frame, adjusted_locations)
            except Exception as e:
                logger.warning(f"YuNet validation failed: {e}, falling back to landmark validation")
                # If YuNet fails, fall back to landmark validation
                validated_indices = []
        
        # If YuNet validation failed or unavailable, fall back to landmark validation
        if not validated_indices:
            # Validate faces by checking for facial landmarks
            landmarks = face_recognition.face_landmarks(rgb_frame, adjusted_locations)
            
            # Only keep faces where landmarks were detected
            for i, landmark_dict in enumerate(landmarks):
                # First check face aspect ratio
                top, right, bottom, left = adjusted_locations[i]
                face_width = right - left
                face_height = bottom - top
                if face_width == 0:
                    logger.debug(f"Landmark validation: skipping face with zero width")
                    continue
                    
                aspect_ratio = face_height / face_width
                if aspect_ratio < MIN_FACE_ASPECT_RATIO or aspect_ratio > MAX_FACE_ASPECT_RATIO:
                    logger.debug(f"Landmark validation: skipping face with invalid aspect ratio: {aspect_ratio:.2f}")
                    continue
                
                # Check for skin tone in the face region
                face_roi = frame[top:bottom, left:right]
                if face_roi.size == 0 or face_roi.shape[0] == 0 or face_roi.shape[1] == 0:
                    logger.debug(f"Landmark validation: skipping empty face ROI")
                    continue
                    
                hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
                skin_mask = cv2.inRange(hsv_roi, (0, 20, 70), (25, 170, 255))
                skin_pixels = cv2.countNonZero(skin_mask)
                total_pixels = face_roi.shape[0] * face_roi.shape[1]
                skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
                
                if skin_ratio < 0.15:
                    logger.debug(f"Landmark validation: skipping face with low skin tone ratio: {skin_ratio:.2f}")
                    continue
                
                # Check if we found eyes and other key facial features
                if landmark_dict and ('left_eye' in landmark_dict and 'right_eye' in landmark_dict):
                    # Additional validation: check if this is really a face by verifying multiple facial features
                    required_features = ['left_eye', 'right_eye', 'nose_tip', 'top_lip', 'bottom_lip']
                    has_all_features = all(feature in landmark_dict for feature in required_features)
                    
                    # Calculate eye aspect ratio to check if eyes are open
                    eye_aspect_ratio = 0
                    if has_all_features:
                        left_eye = landmark_dict['left_eye']
                        right_eye = landmark_dict['right_eye']
                        
                        # Calculate eye aspect ratio
                        def calculate_eye_aspect_ratio(eye_points):
                            # Calculate height (average of two height measurements)
                            h1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
                            h2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
                            # Calculate width
                            w = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
                            # Return aspect ratio
                            return (h1 + h2) / (2.0 * w) if w > 0 else 0
                        
                        left_ear = calculate_eye_aspect_ratio(left_eye)
                        right_ear = calculate_eye_aspect_ratio(right_eye)
                        eye_aspect_ratio = (left_ear + right_ear) / 2.0
                    
                    # Check symmetry of facial features (asymmetric features often indicate false positives)
                    facial_symmetry = 1.0
                    if has_all_features:
                        # Calculate center points of eyes
                        left_eye_center = np.mean(left_eye, axis=0)
                        right_eye_center = np.mean(right_eye, axis=0)
                        
                        # Calculate distance between eyes
                        eye_distance = np.linalg.norm(left_eye_center - right_eye_center)
                        
                        # Calculate nose position relative to eye midpoint
                        nose_tip = np.mean(landmark_dict['nose_tip'], axis=0)
                        eye_midpoint = (left_eye_center + right_eye_center) / 2
                        
                        # Nose should be roughly below the midpoint between eyes
                        nose_offset = abs(nose_tip[0] - eye_midpoint[0]) / eye_distance if eye_distance > 0 else 1.0
                        
                        # Facial symmetry score (lower is better)
                        facial_symmetry = nose_offset
                    
                    # Verify face has all required features, reasonable eye aspect ratio, and good symmetry
                    if has_all_features and eye_aspect_ratio >= MIN_EYE_ASPECT_RATIO and facial_symmetry < 0.3:
                        validated_indices.append(i)
                        logger.debug(f"Landmark validation passed: face has all features, EAR={eye_aspect_ratio:.2f}, symmetry={facial_symmetry:.2f}, aspect ratio={aspect_ratio:.2f}")
                    else:
                        if not has_all_features:
                            logger.debug(f"Landmark validation failed: missing required facial features")
                        elif eye_aspect_ratio < MIN_EYE_ASPECT_RATIO:
                            logger.debug(f"Landmark validation failed: low eye aspect ratio {eye_aspect_ratio:.2f}")
                        else:
                            logger.debug(f"Landmark validation failed: poor facial symmetry {facial_symmetry:.2f}")
                else:
                    logger.debug("Landmark validation failed: missing eye landmarks")
        
        # Filter locations to only include validated faces
        validated_locations = [adjusted_locations[i] for i in validated_indices]
        
        # Get face encodings for validated faces
        face_encodings = []
        if validated_locations:
            face_encodings = face_recognition.face_encodings(rgb_frame, validated_locations)
        
        if len(validated_locations) < len(adjusted_locations):
            logger.debug(f"Filtered out {len(adjusted_locations) - len(validated_locations)} false positive face detections")
        
        return validated_locations, face_encodings
    
    def calculate_face_quality(self, frame, face_location, frame_center_x, frame_center_y, frame_width, frame_height):
        """
        Calculate quality metrics for a face to determine the best face to use.
        
        Factors considered:
        1. Size of face relative to minimum requirements
        2. Position in frame (centered faces score higher)
        3. Brightness and contrast
        4. Eye openness (faces with open eyes score higher)
        5. Sharpness
        
        Returns:
            Dictionary with quality metrics and overall score
        """
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        # Calculate face dimensions
        face_width = right - left
        face_height = bottom - top
        face_size = face_width * face_height
        
        # Calculate distance from center of frame
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        
        # Calculate horizontal and vertical distances separately
        horizontal_distance = abs(face_center_x - frame_center_x) / (frame_width / 2)
        vertical_distance = abs(face_center_y - frame_center_y) / (frame_height / 2)
        
        # Normalize distance to be in range [0, 1]
        distance_from_center = np.sqrt(
            ((face_center_x - frame_center_x) / frame_width) ** 2 + 
            ((face_center_y - frame_center_y) / frame_height) ** 2
        )
        
        # STRICT HORIZONTAL CENTERING CHECK
        # Reject faces that are too far from center horizontally (more than 40% from center)
        if horizontal_distance > 0.4:
            logger.debug(f"Rejecting face at position {horizontal_distance:.2f} from center (threshold: 0.4)")
            # Return very low quality score to ensure this face is not selected
            return {
                "face_width": face_width,
                "face_height": face_height,
                "face_size": face_size,
                "distance_from_center": distance_from_center,
                "horizontal_distance": horizontal_distance,
                "vertical_distance": vertical_distance,
                "sharpness": 0,
                "eyes_open_score": 0,
                "quality_score": -1.0  # Negative score ensures rejection
            }
        
        # Calculate size score (larger faces score higher)
        size_score = min(face_size / (frame_width * frame_height * 0.1), 1.0)
        
        # Calculate position scores
        horizontal_position_score = 1.0 - min(horizontal_distance * 2.5, 1.0)
        vertical_position_score = 1.0 - min(vertical_distance * 2.0, 1.0)
        
        # Calculate brightness and contrast
        if len(face_image.shape) == 3 and face_image.shape[2] == 3:
            # Convert to grayscale for brightness/contrast calculation
            gray_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray_face = face_image
            
        # Calculate brightness (mean pixel value)
        brightness = np.mean(gray_face)
        brightness_score = min(brightness / 200, 1.0)  # Normalize to [0, 1]
        
        # Calculate contrast (standard deviation of pixel values)
        contrast = np.std(gray_face)
        contrast_score = min(contrast / 80, 1.0)  # Normalize to [0, 1]
        
        # Calculate sharpness (Laplacian variance)
        sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        sharpness_score = min(sharpness / 1000, 1.0)
        
        # Detect facial landmarks to check if eyes are open
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        landmarks = face_recognition.face_landmarks(rgb_frame, [face_location])
        eyes_open_score = 0.0
        
        if landmarks and len(landmarks) > 0:
            face_landmarks = landmarks[0]
            if 'left_eye' in face_landmarks and 'right_eye' in face_landmarks:
                # Calculate eye aspect ratio (EAR) for both eyes
                # EAR = (height of eye) / (width of eye)
                # Higher values indicate more open eyes
                
                def calculate_eye_aspect_ratio(eye_points):
                    # Calculate height (average of two height measurements)
                    h1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
                    h2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
                    # Calculate width
                    w = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
                    # Return aspect ratio
                    return (h1 + h2) / (2.0 * w) if w > 0 else 0
                
                left_eye = face_landmarks['left_eye']
                right_eye = face_landmarks['right_eye']
                
                left_ear = calculate_eye_aspect_ratio(left_eye)
                right_ear = calculate_eye_aspect_ratio(right_eye)
                
                # Average EAR for both eyes
                avg_ear = (left_ear + right_ear) / 2.0
                
                # Convert to score (typical EAR for open eyes is around 0.2-0.3)
                # Values below 0.2 often indicate closed or partially closed eyes
                eyes_open_score = min(avg_ear / 0.25, 1.0)
        
        # Calculate quality score with two-tier approach
        # TIER 1: Horizontal position is most important (70%)
        # TIER 2: Other factors (30%)
        secondary_quality = (
            (size_score * 0.3) + 
            (vertical_position_score * 0.2) + 
            (sharpness_score * 0.15) + 
            (brightness_score * 0.1) + 
            (contrast_score * 0.05) + 
            (eyes_open_score * 0.2)
        )
        
        # Final quality score: horizontal position dominates, with secondary factors as tiebreakers
        quality_score = (horizontal_position_score * 0.7) + (secondary_quality * 0.3)
        
        return {
            "face_width": face_width,
            "face_height": face_height,
            "face_size": face_size,
            "distance_from_center": distance_from_center,
            "horizontal_distance": horizontal_distance,
            "vertical_distance": vertical_distance,
            "sharpness": sharpness,
            "eyes_open_score": eyes_open_score,
            "quality_score": quality_score
        }
    
    def extract_faces_from_video(self, video_path: str, output_dir: Optional[str] = None, 
                               interval: float = 3.0, min_confidence: float = 0.6,
                               prioritize_center: bool = True, select_best_frames: bool = True,
                               min_face_size: int = 200, min_face_area: int = 40000,
                               roi_scale: float = 0.6, detection_interval: int = 30) -> Dict[str, Any]:
        """
        Extract faces from a video file with optimized performance for parliamentary videos
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save extracted face images
            interval: Interval in seconds between frame processing (increased from default 1.0)
            min_confidence: Minimum confidence score for face detection
            prioritize_center: Whether to prioritize faces in the center of the frame
            select_best_frames: Whether to select the best quality frames
            min_face_size: Minimum width and height for detected faces (in pixels)
            min_face_area: Minimum area for detected faces (in square pixels)
            roi_scale: Scale factor for region of interest (0-1)
            detection_interval: Frame interval for forced detection when using tracking
            
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.info(f"Extracting faces from video with optimized detection: {video_path}")
            
            # Create output directory if not provided
            if not output_dir:
                output_dir = os.path.join(os.path.dirname(video_path), "extracted_faces")
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Using output directory: {output_dir}")
            
            # Open the video file
            video = cv2.VideoCapture(video_path)
            if not video.isOpened():
                logger.error(f"Could not open video file: {video_path}")
                return {"success": False, "error": "Could not open video file"}
            
            # Get video properties
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            logger.info(f"Video properties: FPS={fps}, Frames={frame_count}, Resolution={frame_width}x{frame_height}, Duration={duration:.2f}s")
            
            # Calculate frame interval
            frame_interval = int(fps * interval)
            if frame_interval < 1:
                frame_interval = 1
            
            # Calculate frame center for prioritization
            frame_center_x = frame_width / 2
            frame_center_y = frame_height / 2
            
            # Process frames
            faces_found = 0
            face_data = []  # Final output faces
            current_frame_idx = 0
            segment_faces = {}  # Faces grouped by time segment
            segment_size = int(fps * self.segment_duration)  # 5-second segments
            
            # Initialize trackers and previous frame
            trackers = []
            previous_frame = None
            
            # Track unique faces to avoid duplicates
            unique_face_encodings = []
            unique_face_ids = []
            
            while True:
                ret, frame = video.read()
                if not ret:
                    break
                
                # Calculate timestamp
                timestamp = current_frame_idx / fps
                segment_key = int(timestamp / self.segment_duration)
                
                # Process only every Nth frame
                if current_frame_idx % frame_interval == 0:
                    # Detect scene change
                    scene_changed = self.detect_scene_change(frame, previous_frame)
                    previous_frame = frame.copy()
                    
                    # On first frame, scene change, or at intervals, do full detection
                    if current_frame_idx == 0 or scene_changed or current_frame_idx % detection_interval == 0:
                        # Clear existing trackers
                        trackers = []
                        
                        # Detect faces in ROI
                        face_locations, face_encodings = self.detect_faces_in_roi(frame, roi_scale)
                        
                        # Initialize trackers for each face
                        for i, (face_loc, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                            top, right, bottom, left = face_loc
                            
                            # Skip faces that are too small
                            face_width = right - left
                            face_height = bottom - top
                            face_size = face_width * face_height
                            if face_width < min_face_size or face_height < min_face_size or face_size < min_face_area:
                                continue
                            
                            # Calculate quality metrics
                            quality_metrics = self.calculate_face_quality(
                                frame, face_loc, frame_center_x, frame_center_y, 
                                frame_width, frame_height
                            )
                            
                            # Use a simple custom tracking approach instead of OpenCV trackers
                            tracking_enabled = True
                            tracker = None
                            
                            # Extract face features for tracking
                            try:
                                # Convert bounding box to the format (x, y, width, height)
                                bbox = (int(left), int(top), int(right-left), int(bottom-top))
                                x, y, w, h = bbox
                                
                                # Ensure bbox is within frame boundaries
                                frame_h, frame_w = frame.shape[:2]
                                if x < 0 or y < 0 or x + w > frame_w or y + h > frame_h or w <= 0 or h <= 0:
                                    # Adjust bbox to fit within frame
                                    x = max(0, min(x, frame_w - 1))
                                    y = max(0, min(y, frame_h - 1))
                                    w = max(1, min(w, frame_w - x))
                                    h = max(1, min(h, frame_h - y))
                                    bbox = (x, y, w, h)
                                
                                # Extract the face region
                                face_roi = frame[y:y+h, x:x+w].copy()
                                
                                # Check if ROI is valid
                                if face_roi.size == 0 or face_roi.shape[0] == 0 or face_roi.shape[1] == 0:
                                    logger.warning(f"Invalid face ROI with shape {face_roi.shape if face_roi.size > 0 else 'empty'} - disabling tracking")
                                    tracking_enabled = False
                                else:
                                    # Create a simple custom tracker object
                                    # Store the template, bbox, and face encoding for matching in subsequent frames
                                    logger.info(f"Creating custom tracker with bbox: {bbox}")
                                    
                                    # Store the face template for template matching
                                    # Resize to a standard size for faster processing
                                    template_size = (64, 64)
                                    try:
                                        face_template = cv2.resize(face_roi, template_size)
                                        
                                        # Create custom tracker object with all necessary info
                                        tracker = {
                                            "bbox": bbox,
                                            "template": face_template,
                                            "template_size": template_size,
                                            "face_encoding": face_encoding,  # Use face encoding for better matching
                                            "search_region_scale": 1.5,  # Search region scale factor
                                            "last_frame_idx": current_frame_idx
                                        }
                                        logger.info(f"Custom tracker created successfully")
                                    except Exception as e:
                                        logger.warning(f"Error creating custom tracker: {str(e)} - disabling tracking")
                                        tracking_enabled = False
                            except Exception as e:
                                logger.warning(f"Custom tracker initialization error: {str(e)} - disabling tracking")
                                tracking_enabled = False
                            
                            # Check if this is a new unique face
                            is_new_face = True
                            if unique_face_encodings:
                                # Compare with existing faces
                                matches = face_recognition.compare_faces(unique_face_encodings, face_encoding, tolerance=0.6)
                                if True in matches:
                                    # This is an existing face
                                    face_id = unique_face_ids[matches.index(True)]
                                    is_new_face = False
                                    logger.debug(f"Recognized existing face ID: {face_id}")
                                else:
                                    # This is a new face
                                    face_id = len(unique_face_ids)
                                    unique_face_encodings.append(face_encoding)
                                    unique_face_ids.append(face_id)
                                    logger.debug(f"Found new face ID: {face_id}")
                            else:
                                # First face
                                face_id = 0
                                unique_face_encodings.append(face_encoding)
                                unique_face_ids.append(face_id)
                                logger.debug(f"Found first face ID: {face_id}")
                            
                            # Save face image
                            face_filename = f"face_{face_id}_{timestamp:.2f}.jpg"
                            face_path = os.path.join(output_dir, face_filename)
                            
                            try:
                                # Ensure the directory exists before writing
                                os.makedirs(os.path.dirname(face_path), exist_ok=True)
                                
                                # Save the face image
                                success = cv2.imwrite(face_path, frame[top:bottom, left:right])
                                
                                if not success:
                                    logger.warning(f"Failed to save face image to {face_path}")
                                    face_path = ""
                                else:
                                    logger.debug(f"Saved face image to {face_path}")
                            except Exception as e:
                                logger.warning(f"Error saving face image: {str(e)}")
                                face_path = ""
                            
                            # Store face data
                            face_info = {
                                "face_id": face_id,
                                "timestamp": timestamp,
                                "face_location": face_loc,
                                "face_encoding": face_encoding.tolist(),
                                "path": face_path,  # Use 'path' key for compatibility with existing system
                                "face_image_path": face_path,  # Keep this for backward compatibility
                                "segment_key": segment_key,
                                **quality_metrics
                            }
                            
                            # Add to segment faces
                            if segment_key not in segment_faces:
                                segment_faces[segment_key] = {}
                            
                            if face_id not in segment_faces[segment_key]:
                                segment_faces[segment_key][face_id] = face_info
                            elif quality_metrics["quality_score"] > segment_faces[segment_key][face_id]["quality_score"]:
                                # Replace with better quality face
                                segment_faces[segment_key][face_id] = face_info
                            
                            # Add to trackers if tracking is enabled
                            if tracking_enabled and tracker is not None:
                                trackers.append({
                                    "tracker": tracker,
                                    "face_loc": face_loc,
                                    "face_id": face_id,
                                    "last_detection_frame": current_frame_idx,
                                    "quality_score": quality_metrics["quality_score"]
                                })
                            
                    else:
                        # Update trackers using our custom tracking approach
                        updated_trackers = []
                        faces_found_by_tracking = 0
                        
                        for tracker_info in trackers:
                            try:
                                # Get the custom tracker data
                                custom_tracker = tracker_info["tracker"]
                                face_id = tracker_info["face_id"]
                                prev_face_loc = tracker_info["face_loc"]
                                
                                # Get the previous bounding box and template
                                prev_bbox = custom_tracker["bbox"]
                                template = custom_tracker["template"]
                                template_size = custom_tracker["template_size"]
                                search_scale = custom_tracker["search_region_scale"]
                                
                                # Extract previous coordinates
                                prev_x, prev_y, prev_w, prev_h = prev_bbox
                                
                                # Calculate search region with some margin
                                search_x = max(0, int(prev_x - prev_w * (search_scale - 1) / 2))
                                search_y = max(0, int(prev_y - prev_h * (search_scale - 1) / 2))
                                search_w = min(frame.shape[1] - search_x, int(prev_w * search_scale))
                                search_h = min(frame.shape[0] - search_y, int(prev_h * search_scale))
                                
                                # Check if search region is valid
                                if search_w <= 0 or search_h <= 0:
                                    logger.debug(f"Invalid search region: ({search_x}, {search_y}, {search_w}, {search_h})")
                                    continue
                                
                                # Extract search region
                                search_region = frame[search_y:search_y+search_h, search_x:search_x+search_w].copy()
                                
                                # Perform template matching
                                if search_region.shape[0] > template.shape[0] and search_region.shape[1] > template.shape[1]:
                                    # Use template matching to find the face in the search region
                                    result = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
                                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                                    
                                    # Check if the match is good enough
                                    if max_val > 0.5:  # Threshold for good match
                                        # Calculate new bounding box coordinates
                                        x = search_x + max_loc[0]
                                        y = search_y + max_loc[1]
                                        w = prev_w
                                        h = prev_h
                                        
                                        # Update tracker with new bbox
                                        bbox = (x, y, w, h)
                                        custom_tracker["bbox"] = bbox
                                        custom_tracker["last_frame_idx"] = current_frame_idx
                                        
                                        # Convert back to face_recognition format (top, right, bottom, left)
                                        face_loc = (y, x + w, y + h, x)
                                        
                                        # Log the updated face location
                                        logger.debug(f"Custom tracker updated successfully. New face_loc: {face_loc}, match score: {max_val:.2f}")
                                        
                                        # Update tracker info
                                        tracker_info["face_loc"] = face_loc
                                        updated_trackers.append(tracker_info)
                                        faces_found_by_tracking += 1
                                        
                                        # Extract and save face image for tracked faces too
                                        top, right, bottom, left = face_loc
                                        
                                        # Save face image for tracked face
                                        face_filename = f"face_{face_id}_{timestamp:.2f}.jpg"
                                        face_path = os.path.join(output_dir, face_filename)
                                        
                                        try:
                                            # Ensure the directory exists before writing
                                            os.makedirs(os.path.dirname(face_path), exist_ok=True)
                                            
                                            # Save the face image
                                            success = cv2.imwrite(face_path, frame[top:bottom, left:right])
                                            
                                            if not success:
                                                logger.warning(f"Failed to save tracked face image to {face_path}")
                                                face_path = ""
                                            else:
                                                logger.debug(f"Saved tracked face image to {face_path}")
                                                
                                                # Calculate quality metrics for the tracked face
                                                quality_metrics = self.calculate_face_quality(
                                                    frame, face_loc, frame_center_x, frame_center_y, 
                                                    frame_width, frame_height
                                                )
                                                
                                                # Store face data
                                                face_info = {
                                                    "face_id": face_id,
                                                    "timestamp": timestamp,
                                                    "face_location": face_loc,
                                                    "face_encoding": custom_tracker["face_encoding"].tolist(),
                                                    "path": face_path,
                                                    "face_image_path": face_path,
                                                    "segment_key": segment_key,
                                                    "tracked": True,
                                                    **quality_metrics
                                                }
                                                
                                                # Add to segment faces
                                                if segment_key not in segment_faces:
                                                    segment_faces[segment_key] = {}
                                                
                                                # Enhanced quality scoring - always keep the best face
                                                # If this is a new face or has better quality than existing one, update it
                                                if face_id not in segment_faces[segment_key]:
                                                    segment_faces[segment_key][face_id] = face_info
                                                    logger.debug(f"Added new tracked face for ID {face_id} with score {quality_metrics['quality_score']:.2f}")
                                                elif quality_metrics["quality_score"] > segment_faces[segment_key][face_id]["quality_score"]:
                                                    # Replace with better quality face
                                                    prev_score = segment_faces[segment_key][face_id]["quality_score"]
                                                    segment_faces[segment_key][face_id] = face_info
                                                    logger.debug(f"Replaced face for ID {face_id}: improved score from {prev_score:.2f} to {quality_metrics['quality_score']:.2f}")
                                                    
                                        except Exception as e:
                                            logger.warning(f"Error saving tracked face image: {str(e)}")
                                    else:
                                        logger.debug(f"Template matching score too low: {max_val:.2f} for face {face_id}")
                                else:
                                    logger.debug(f"Search region too small for template matching for face {face_id}")
                            except Exception as e:
                                logger.debug(f"Custom tracker update error: {str(e)}")
                        
                        # Replace trackers with updated ones
                        trackers = updated_trackers
                        logger.debug(f"Updated {faces_found_by_tracking} faces using custom tracking")
                        faces_found += faces_found_by_tracking
                
                # Increment frame counter
                current_frame_idx += 1
                
                # Log progress periodically
                if current_frame_idx % 1000 == 0:
                    logger.info(f"Processed {current_frame_idx}/{frame_count} frames, found {faces_found} faces")
            
            # Release video
            video.release()
            
            # Select best faces from each segment
            best_faces = []
            for segment_key, faces_by_id in segment_faces.items():
                for face_id, face_info in faces_by_id.items():
                    # Verify the face image exists before adding to results
                    face_image_path = face_info.get("path", "")
                    if face_image_path and not os.path.exists(face_image_path):
                        logger.warning(f"Face image file does not exist: {face_image_path}")
                        face_info["path"] = ""
                        face_info["face_image_path"] = ""
                    
                    best_faces.append(face_info)
            
            logger.info(f"Face extraction complete. Found {faces_found} faces, selected {len(best_faces)} best faces")
            
            return {
                "success": True,
                "faces_found": faces_found,
                "best_faces": len(best_faces),
                "face_data": best_faces,
                "video_info": {
                    "path": video_path,
                    "fps": fps,
                    "frame_count": frame_count,
                    "duration": duration,
                    "resolution": f"{frame_width}x{frame_height}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting faces: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
