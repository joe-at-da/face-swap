"""
Optimized face detection module for parliamentary videos
Implements several performance optimizations:
1. Scene change detection
2. Face tracking
3. Region of Interest (ROI) restriction
4. Reduced HOG upsampling
"""
import os
import cv2
import face_recognition
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class OptimizedFaceDetector:
    """
    Optimized face detector for parliamentary videos with significantly improved performance.
    Implements scene change detection, face tracking, and ROI restriction.
    """
    
    def __init__(self):
        """Initialize the optimized face detector"""
        # Initialize trackers list
        self.trackers = []
        self.previous_frame = None
        self.current_segment_faces = []
        self.segment_duration = 5  # seconds
    
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
        Detect faces only in the central region of the frame
        
        Args:
            frame: Input video frame
            roi_scale: Scale factor for ROI (0-1)
            
        Returns:
            tuple: (face_locations, face_encodings) - Adjusted to original frame coordinates
        """
        # Get ROI
        roi, x_start, y_start = self.get_frame_roi(frame, roi_scale)
        
        # Convert ROI to RGB
        rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        
        # Detect faces in ROI with reduced upsampling
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
        
        # Get face encodings if faces were found
        face_encodings = []
        if adjusted_locations:
            # Convert full frame to RGB for encodings
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_frame, adjusted_locations)
        
        return adjusted_locations, face_encodings
    
    def calculate_face_quality(self, frame, face_location, frame_center_x, frame_center_y, frame_width, frame_height):
        """
        Calculate quality metrics for a face to determine the best face to use.
        
        Factors considered:
        1. Size of face relative to minimum requirements
        2. Position in frame (centered faces score higher)
        3. Brightness and contrast
        4. Face angle (frontal faces score higher)
        
        Returns:
            Dictionary with quality metrics and overall score
        """
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        # Calculate face dimensions
        face_width = right - left
        face_height = bottom - top
        face_size = face_width * face_height
        
        # Calculate distance from center
        horizontal_distance = abs((left + right) / 2 - frame_center_x) / (frame_width / 2)
        vertical_distance = abs((top + bottom) / 2 - frame_center_y) / (frame_height / 2)
        
        # Overall distance (normalized 0-1, with higher penalty for horizontal offset)
        distance_from_center = np.sqrt(
            (horizontal_distance * 1.5) ** 2 +  # Apply higher weight to horizontal centering
            vertical_distance ** 2
        ) / np.sqrt(1.5**2 + 1)  # Normalize to 0-1 range
        
        # Calculate size score
        size_score = min(1.0, face_size / (frame_width * frame_height))
        
        # Calculate position score
        position_score = 1.0 - distance_from_center
        
        # Calculate sharpness
        gray_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        
        # Calculate brightness and contrast scores
        face_roi = frame[top:bottom, left:right]
        if face_roi.size > 0:
            # Convert to grayscale for brightness calculation
            if len(face_roi.shape) == 3 and face_roi.shape[2] == 3:
                gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            else:
                gray_roi = face_roi
                
            # Calculate brightness (mean pixel value)
            brightness = np.mean(gray_roi)
            brightness_score = min(1.0, brightness / 150.0)  # Normalize, optimal around 150
            
            # Calculate contrast (standard deviation of pixel values)
            contrast = np.std(gray_roi)
            contrast_score = min(1.0, contrast / 50.0)  # Normalize, optimal around 50
        else:
            brightness_score = 0.5
            contrast_score = 0.5
        
        # Calculate quality score based on all factors
        quality_score = (size_score * 0.4) + (position_score * 0.3) + (brightness_score * 0.15) + (contrast_score * 0.15)
        
        return {
            "face_width": face_width,
            "face_height": face_height,
            "face_size": face_size,
            "distance_from_center": distance_from_center,
            "sharpness": sharpness,
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
                                        
                                        # Save face image
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
