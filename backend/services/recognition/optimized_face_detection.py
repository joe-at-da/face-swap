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
    
    def calculate_face_quality(self, frame, face_location, frame_center_x, frame_center_y, 
                              frame_width, frame_height):
        """
        Calculate quality metrics for a detected face
        
        Args:
            frame: Video frame
            face_location: Face coordinates (top, right, bottom, left)
            frame_center_x, frame_center_y: Center coordinates of the frame
            frame_width, frame_height: Frame dimensions
            
        Returns:
            dict: Quality metrics for the face
        """
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        # Calculate face dimensions
        face_width = right - left
        face_height = bottom - top
        face_size = face_width * face_height
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        
        # Calculate distance from center
        horizontal_distance = abs(face_center_x - frame_center_x) / (frame_width / 2)
        vertical_distance = abs(face_center_y - frame_center_y) / (frame_height / 2)
        
        # Overall distance (normalized 0-1, with higher penalty for horizontal offset)
        distance_from_center = np.sqrt(
            (horizontal_distance * 1.5) ** 2 +  # Apply higher weight to horizontal centering
            vertical_distance ** 2
        ) / np.sqrt(1.5**2 + 1)  # Normalize to 0-1 range
        
        # Calculate sharpness
        gray_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray_face, cv2.CV_64F).var()
        
        # Calculate quality score (1.0 is best, 0.0 is worst)
        # Prioritize centered faces (70%) and sharpness (30%)
        centering_score = 1.0 - distance_from_center
        sharpness_score = min(sharpness / 500.0, 1.0)  # Normalize sharpness
        quality_score = (centering_score * 0.7) + (sharpness_score * 0.3)
        
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
                            
                            # Initialize tracker - handle different OpenCV versions
                            tracker = None
                            tracking_enabled = True
                            
                            try:
                                # OpenCV 4.5.1+ approach
                                tracker = cv2.TrackerKCF_create()
                            except AttributeError:
                                try:
                                    # OpenCV 4.x approach
                                    tracker = cv2.TrackerKCF.create()
                                except AttributeError:
                                    # OpenCV 3.x approach with contrib
                                    try:
                                        tracker = cv2.Tracker_create("KCF")
                                    except AttributeError:
                                        # Fallback to CSRT which is more widely available
                                        try:
                                            tracker = cv2.TrackerCSRT_create()
                                        except AttributeError:
                                            # Final fallback - use CSRT from newer API
                                            try:
                                                tracker = cv2.TrackerCSRT.create()
                                            except AttributeError:
                                                # If all trackers fail, disable tracking for this face
                                                logger.warning("No compatible tracker found in OpenCV installation - disabling tracking")
                                                tracking_enabled = False
                            
                            # Initialize the tracker with the bounding box if available
                            if tracking_enabled and tracker is not None:
                                try:
                                    success = tracker.init(frame, (left, top, right-left, bottom-top))
                                    if not success:
                                        logger.warning("Tracker initialization failed - disabling tracking")
                                        tracking_enabled = False
                                        tracker = None
                                except Exception as e:
                                    logger.warning(f"Tracker initialization error: {str(e)} - disabling tracking")
                                    tracking_enabled = False
                                    tracker = None
                            
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
                            
                            faces_found += 1
                    else:
                        # Update trackers
                        updated_trackers = []
                        for tracker_info in trackers:
                            # Handle tracker update with error handling for different OpenCV versions
                            try:
                                success, box = tracker_info["tracker"].update(frame)
                            except Exception as e:
                                logger.warning(f"Tracker update failed: {str(e)}")
                                success = False
                            if success:
                                x, y, w, h = [int(v) for v in box]
                                face_loc = (y, x+w, y+h, x)
                                
                                # Update tracker info
                                tracker_info["face_loc"] = face_loc
                                updated_trackers.append(tracker_info)
                        
                        # Replace trackers with updated ones
                        trackers = updated_trackers
                
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
