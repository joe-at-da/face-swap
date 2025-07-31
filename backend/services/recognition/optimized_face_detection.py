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
import time
import math
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Import centralized configuration
try:
    from backend.core.recognition_config import FaceDetectionConfig
except ImportError:
    # Fallback values if config module is not available
    class FaceDetectionConfig:
        SEGMENT_DURATION = 5
        MAX_TIME_GAP = 1.5

from datetime import datetime
from scipy.spatial import distance as dist

logger = logging.getLogger(__name__)

# Constants for YuNet face detector
YUNET_SCORE_THRESHOLD = 0.3  # Exactly matching dev branch
YUNET_NMS_THRESHOLD = 0.3  # Same as dev branch
YUNET_TOP_K = 5000  # Same as dev branch

# Constants for face validation
MIN_FACE_WIDTH = 200
MIN_FACE_HEIGHT = 200
MIN_FACE_AREA = 40000
MIN_ASPECT_RATIO = 0.5
MAX_ASPECT_RATIO = 2.0
MIN_SKIN_RATIO = 0.3
YUNET_SCORE_THRESHOLD = 0.3
MIN_EYE_ASPECT_RATIO = 0.15  # Threshold for open eyes
MIN_SHARPNESS = 30.0  # Minimum variance of Laplacian for sharpness
MAX_HORIZONTAL_OFFSET = 0.4  # Maximum distance from center (40%)

# Constants for face size and position
MIN_FACE_WIDTH = 200  # Minimum width in pixels
MIN_FACE_HEIGHT = 200  # Minimum height in pixels
MIN_FACE_AREA = 40000  # Minimum area in square pixels
MAX_HORIZONTAL_OFFSET = 0.4  # Maximum allowed horizontal offset from center (as fraction of frame width)

def calculate_eye_aspect_ratio(eye_points):
    """
    Calculate the eye aspect ratio to determine if eyes are open.
    A higher ratio indicates more open eyes.
    """
    # Calculate height (average of two height measurements)
    h1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
    h2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
    # Calculate width
    w = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
    # Return aspect ratio
    return (h1 + h2) / (2.0 * w) if w > 0 else 0

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
        self.segment_duration = FaceDetectionConfig.SEGMENT_DURATION  # seconds
    
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
    
    def calculate_eye_aspect_ratio(self, eye_landmarks):
        # Compute the euclidean distances between the vertical eye landmarks
        A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
        B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
        
        # Compute the euclidean distance between the horizontal eye landmarks
        C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
        
        # Compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)
        return ear
    
    def calculate_sharpness(self, image):
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Calculate variance of Laplacian as a measure of sharpness
        return cv2.Laplacian(gray, cv2.CV_64F).var()
    
    def validate_face_geometry(self, frame, face_locations):
        validated_indices = []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        for idx, (top, right, bottom, left) in enumerate(face_locations):
            # Check face dimensions
            width = right - left
            height = bottom - top
            
            if width < MIN_FACE_WIDTH or height < MIN_FACE_HEIGHT or (width * height) < MIN_FACE_AREA:
                logger.debug(f"Face validation: face too small: {width}x{height}, area={width*height}")
                continue
                
            # Check aspect ratio
            aspect_ratio = width / height
            if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                logger.debug(f"Face validation: invalid aspect ratio: {aspect_ratio:.2f}")
                continue
                
            # Check horizontal centering
            face_center_x = left + width / 2
            frame_center_x = frame.shape[1] / 2
            distance_from_center = abs(face_center_x - frame_center_x) / frame_center_x
            if distance_from_center > MAX_HORIZONTAL_OFFSET:  # 40% threshold from center
                logger.debug(f"Face validation: face too far from center: {distance_from_center:.2f}")
                continue
            
            # Check skin tone
            face_roi = frame[top:bottom, left:right]
            total_pixels = width * height
            
            # Convert to HSV for better skin detection
            hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            
            # Detect skin pixels (relaxed range)
            # Wider HSV range to detect all skin tones including darker skin
            skin_mask = cv2.inRange(hsv_roi, (0, 5, 25), (50, 255, 255))  # This is correct, hsv_roi is defined on line 172
            skin_pixels = cv2.countNonZero(skin_mask)
            skin_ratio = skin_pixels / total_pixels
            
            if skin_ratio < MIN_SKIN_RATIO:
                logger.debug(f"Face validation: insufficient skin tone ratio: {skin_ratio:.2f}")
                continue
                
            # Check brightness to filter out dark clothing like suits
            avg_brightness = np.mean(hsv_roi[:,:,2])
            if avg_brightness < 50:  # Lower threshold for darker skin tones - Filter out very dark regions
                logger.debug(f"Face validation: low brightness: {avg_brightness:.2f}")
                continue
                
            # Check sharpness
            sharpness = self.calculate_sharpness(face_roi)
            if sharpness < MIN_SHARPNESS:
                logger.debug(f"Face validation: face too blurry: {sharpness:.2f}")
                continue
                
            # Check for open eyes using landmarks
            try:
                landmarks = face_recognition.face_landmarks(rgb_frame[top:bottom, left:right])
                if landmarks and len(landmarks) > 0:
                    landmark_dict = landmarks[0]
                    if 'left_eye' in landmark_dict and 'right_eye' in landmark_dict:
                        # Calculate eye aspect ratio for both eyes
                        left_ear = self.calculate_eye_aspect_ratio(landmark_dict['left_eye'])
                        right_ear = self.calculate_eye_aspect_ratio(landmark_dict['right_eye'])
                        avg_ear = (left_ear + right_ear) / 2.0
                        
                        if avg_ear < MIN_EYE_ASPECT_RATIO:
                            logger.debug(f"Face validation: eyes closed or squinting: {avg_ear:.2f}")
                            continue
            except Exception as e:
                logger.debug(f"Error checking eye landmarks: {str(e)}")
                # Continue even if landmark detection fails
                pass
                
            validated_indices.append(idx)
            
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
        Detect faces in a region of interest within a frame using YuNet detector.
        Falls back to landmark-based validation if YuNet is not available.
        """
        # Get ROI
        roi, x_start, y_start = self.get_frame_roi(frame, roi_scale)
        
        # Initialize empty results
        adjusted_locations = []
        
        # Check if YuNet detector is available
        if self.yunet_detector is None:
            logger.warning("YuNet detector not available, falling back to landmark detection")
            # Convert ROI to RGB for face_recognition library
            rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            
            # Detect faces with HOG as fallback
            face_locations = face_recognition.face_locations(
                rgb_roi, 
                model="hog",
                number_of_times_to_upsample=0
            )
            
            # Adjust face coordinates back to original frame
            for top, right, bottom, left in face_locations:
                adjusted_locations.append(
                    (top + y_start, right + x_start, bottom + y_start, left + x_start)
                )
            
            # If no faces found with HOG fallback, return empty results
            if not adjusted_locations:
                return [], []
        else:
            # Use YuNet as primary detector (more accurate than HOG)
            height, width = roi.shape[:2]
            self.yunet_detector.setInputSize((width, height))
            _, faces = self.yunet_detector.detect(roi)
            
            # If no faces detected, return empty results
            if faces is None:
                return [], []
            
            # Process YuNet detections
            for face in faces:
                # YuNet returns [x, y, w, h, score, ...]
                score = face[4]
                if score < YUNET_SCORE_THRESHOLD:
                    continue
                    
                # Convert to (top, right, bottom, left) format
                x, y, w, h = map(int, face[:4])
                
                # Apply minimal checks similar to original code
                # 1. Check minimum size (but more permissive)
                if w < MIN_FACE_WIDTH * 0.75 or h < MIN_FACE_HEIGHT * 0.75 or (w * h) < MIN_FACE_AREA * 0.5:
                    logger.debug(f"Initial detection: face too small: {w}x{h}, area={w*h}")
                    continue
                    
                # 2. Check if face is within reasonable bounds of the ROI
                if x < 0 or y < 0 or x + w > roi.shape[1] or y + h > roi.shape[0]:
                    logger.debug(f"Initial detection: face outside ROI bounds")
                    continue
                    
                # 3. Extract face crop for validation
                face_crop = roi[y:y+h, x:x+w]
                
                # Skip if face crop is invalid
                if face_crop.size == 0 or face_crop.shape[0] == 0 or face_crop.shape[1] == 0:
                    logger.debug(f"Initial detection: invalid face crop dimensions")
                    continue
                    
                # 4. Brightness check - reject very dark regions (likely clothing)
                hsv_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
                avg_brightness = np.mean(hsv_face[:,:,2])
                if avg_brightness < 50:  # Lower threshold for darker skin tones
                    logger.debug(f"Initial detection: too dark (brightness={avg_brightness:.2f})")
                    continue
                    
                # 5. Skin tone check - ensure minimum amount of skin tone pixels
                # Wider HSV range to detect all skin tones including darker skin
                skin_mask = cv2.inRange(hsv_face, (0, 5, 25), (50, 255, 255))
                skin_pixels = cv2.countNonZero(skin_mask)
                total_pixels = face_crop.shape[0] * face_crop.shape[1]
                skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
                
                if skin_ratio < 0.05:  # Lower threshold for darker skin tones - Minimum skin tone ratio
                    logger.debug(f"Initial detection: insufficient skin tone (ratio={skin_ratio:.2f})")
                    continue
                    
                # 6. Sharpness check - reject blurry detections
                gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
                if sharpness < 40:  # Slightly lower threshold than tracking for initial detection
                    logger.debug(f"Initial detection: too blurry (sharpness={sharpness:.2f})")
                    continue
                    
                # 7. Check horizontal centering (absolute threshold)
                face_center_x = x + w/2
                frame_center_x = roi.shape[1] / 2
                distance_from_center = abs(face_center_x - frame_center_x) / frame_center_x
                if distance_from_center > MAX_HORIZONTAL_OFFSET:  # Reject faces beyond 40% from horizontal center
                    logger.debug(f"Initial detection: face too far from center: {distance_from_center:.2f}")
                    continue
                
                left = x
                top = y
                right = x + w
                bottom = y + h
                
                # Adjust coordinates back to original frame
                adjusted_locations.append(
                    (top + y_start, right + x_start, bottom + y_start, left + x_start)
                )
            
            # If no faces found with YuNet, return empty results
            if not adjusted_locations:
                return [], []
        
        # Apply additional validation to the detected faces
        validated_locations = []
        validated_indices = []
        
        # Convert full frame to RGB for encodings
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply size, position, and aspect ratio validation
        validated_indices = self.validate_face_geometry(frame, adjusted_locations)
        
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
        sharpness = self.calculate_sharpness(face_image)
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
                        logger.debug(f"Updating {len(trackers)} trackers with custom tracking approach")
                        
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
                                        
                                        # Extract the potential face region for validation
                                        top, right, bottom, left = face_loc
                                        potential_face = frame[top:bottom, left:right]
                                        
                                        # Validate the tracked face with multiple checks
                                        is_valid_face = True
                                        
                                        # Check face brightness and skin tone
                                        if potential_face.size > 0 and potential_face.shape[0] > 0 and potential_face.shape[1] > 0:
                                            # Convert to HSV for brightness check
                                            hsv_face = cv2.cvtColor(potential_face, cv2.COLOR_BGR2HSV)
                                            avg_brightness = np.mean(hsv_face[:,:,2])
                                            
                                            # Check if face is too dark (likely clothing)
                                            if avg_brightness < 50:  # Lower threshold for darker skin tones
                                                logger.debug(f"Tracked face rejected: too dark (brightness={avg_brightness:.2f})")
                                                is_valid_face = False
                                            
                                            # Check skin tone ratio
                                            # Expanded HSV range to better detect diverse skin tones including darker skin
                                            # Wider HSV range to detect all skin tones including darker skin
                                            skin_mask = cv2.inRange(hsv_face, (0, 5, 25), (50, 255, 255))
                                            skin_pixels = cv2.countNonZero(skin_mask)
                                            total_pixels = potential_face.shape[0] * potential_face.shape[1]
                                            skin_ratio = skin_pixels / total_pixels if total_pixels > 0 else 0
                                            
                                            if skin_ratio < 0.05:  # Lower threshold for darker skin tones - Minimum skin tone ratio
                                                logger.debug(f"Tracked face rejected: insufficient skin tone (ratio={skin_ratio:.2f})")
                                                is_valid_face = False
                                                
                                            # Check face sharpness (blurry faces are often false positives)
                                            if is_valid_face:
                                                gray_face = cv2.cvtColor(potential_face, cv2.COLOR_BGR2GRAY)
                                                sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
                                                if sharpness < 50:  # Threshold for minimum sharpness
                                                    logger.debug(f"Tracked face rejected: too blurry (sharpness={sharpness:.2f})")
                                                    is_valid_face = False
                                            
                                            # Check for facial landmarks to confirm it's a face
                                            if is_valid_face:
                                                try:
                                                    # Convert to RGB for face_recognition library
                                                    rgb_face = cv2.cvtColor(potential_face, cv2.COLOR_BGR2RGB)
                                                    face_landmarks = face_recognition.face_landmarks(rgb_face)
                                                    
                                                    # Check if we detected landmarks and if eyes are present
                                                    if not face_landmarks or not all(key in face_landmarks[0] for key in ['left_eye', 'right_eye']):
                                                        logger.debug(f"Tracked face rejected: no valid facial landmarks detected")
                                                        is_valid_face = False
                                                    else:
                                                        # Calculate eye aspect ratio to check if eyes are open
                                                        left_eye = face_landmarks[0]['left_eye']
                                                        right_eye = face_landmarks[0]['right_eye']
                                                        left_ear = self.calculate_eye_aspect_ratio(left_eye)
                                                        right_ear = self.calculate_eye_aspect_ratio(right_eye)
                                                        eye_aspect_ratio = (left_ear + right_ear) / 2
                                                        
                                                        if eye_aspect_ratio < 0.15:  # Minimum eye aspect ratio
                                                            logger.debug(f"Tracked face rejected: eyes not clearly visible (EAR={eye_aspect_ratio:.2f})")
                                                            is_valid_face = False
                                                except Exception as e:
                                                    logger.debug(f"Error checking facial landmarks: {str(e)}")
                                        else:
                                            is_valid_face = False
                                        
                                        # Check horizontal centering
                                        face_center_x = (left + right) / 2
                                        frame_center_x = frame.shape[1] / 2
                                        distance_from_center = abs(face_center_x - frame_center_x) / frame_center_x
                                        if distance_from_center > 0.4:  # Same as detection threshold
                                            logger.debug(f"Tracked face rejected: too far from center (offset={distance_from_center:.2f})")
                                            is_valid_face = False
                                            
                                        # Only proceed if the face passes all validation checks
                                        if is_valid_face:
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
                                            logger.debug(f"Tracked face failed validation checks")
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
            
            # Select best faces from each segment using a two-phase approach
            # Phase 1: Group consecutive faces of the same person and select the best one from each group
            all_faces = []
            for segment_key, faces_by_id in segment_faces.items():
                for face_id, face_info in faces_by_id.items():
                    # Verify the face image exists before adding to results
                    face_image_path = face_info.get("path", "")
                    if face_image_path and not os.path.exists(face_image_path):
                        logger.warning(f"Face image file does not exist: {face_image_path}")
                        face_info["path"] = ""
                        face_info["face_image_path"] = ""
                        continue
                    
                    all_faces.append(face_info)
            
            # Sort by face_id and timestamp
            all_faces.sort(key=lambda x: (x["face_id"], x["timestamp"]))
            
            # Group consecutive faces (same face_id with timestamps close together)
            consecutive_groups = {}  # Dictionary to store groups by face_id
            max_time_gap = FaceDetectionConfig.MAX_TIME_GAP  # Maximum time gap in seconds to consider faces consecutive
            
            # First, organize all faces by face_id
            face_id_groups = {}
            for face_info in all_faces:
                face_id = face_info["face_id"]
                if face_id not in face_id_groups:
                    face_id_groups[face_id] = []
                face_id_groups[face_id].append(face_info)
            
            # Then, for each face_id, group consecutive appearances
            for face_id, faces in face_id_groups.items():
                # Sort by timestamp
                faces.sort(key=lambda x: x["timestamp"])
                
                current_group = []
                for face_info in faces:
                    timestamp = face_info["timestamp"]
                    
                    if not current_group or (timestamp - current_group[-1]["timestamp"] <= max_time_gap):
                        # Add to current group if within time gap
                        current_group.append(face_info)
                    else:
                        # Start a new group
                        if current_group:
                            group_id = f"{face_id}_{len(consecutive_groups)}"
                            consecutive_groups[group_id] = current_group
                        current_group = [face_info]
                
                # Don't forget the last group
                if current_group:
                    group_id = f"{face_id}_{len(consecutive_groups)}"
                    consecutive_groups[group_id] = current_group
            
            # Find the best face in each consecutive group
            best_faces_by_group = {}
            for group_id, group in consecutive_groups.items():
                best_face = max(group, key=lambda x: x["quality_score"])
                best_faces_by_group[group_id] = best_face
            
            # Phase 2: Rebuild the final face list by filtering original segment faces
            # This preserves the original segment structure expected by downstream code
            best_face_timestamps = {best_face["timestamp"] for best_face in best_faces_by_group.values()}
            
            # Build the final list of best faces while preserving the original structure
            best_faces = []
            for face_info in all_faces:
                if face_info["timestamp"] in best_face_timestamps:
                    best_faces.append(face_info)
            
            # Log statistics
            original_count = len(all_faces)
            final_count = len(best_faces)
            reduction_percent = ((original_count - final_count) / original_count * 100) if original_count > 0 else 0
            logger.info(f"Face reduction: {original_count} original faces → {final_count} best faces ({reduction_percent:.1f}% reduction)")
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
