"""
Facial Recognition Service for Parliament TV Videos

This service provides facial recognition capabilities for Parliament TV videos,
integrating with the existing scripts for face detection and speaker identification.
"""

import os
import json
import logging
import cv2
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import datetime
import numpy as np
import face_recognition

from backend.core.config import settings
from backend.services.utils import make_json_serializable
from backend.services.recognition.supabase_export import export_recognition_results
from backend.db.session import SessionLocal
from backend.db.models import Speaker, CaptureSession
from sqlalchemy import or_

# Set up logging
logger = logging.getLogger(__name__)

class FacialRecognitionService:
    """Service for facial recognition in Parliament TV videos."""
    
    def __init__(self):
        """Initialize the facial recognition service."""
        self.base_dir = Path(os.environ.get('DATA_DIR', '/app/data'))
        self.mp_photos_dir = self.base_dir / "mp_photos"
        self.mp_encodings_file = self.base_dir / "mp_encodings.json"
        self.scripts_dir = Path("/app/scripts")
        
        # Create directories if they don't exist
        self.mp_photos_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenCV YuNet face detector
        try:
            model_paths = [
                "/app/models/face_recognition/face_detection_yunet_2023mar.onnx",  # Docker container path
                "/app/models/face_detection_yunet_2023mar.onnx",  # Alternative path
                str(Path("/app/models/face_detection_yunet_2023mar.onnx")),  # Path object
                str(Path(__file__).parent.parent.parent.parent / "models" / "face_recognition" / "face_detection_yunet_2023mar.onnx")  # Relative to this file
            ]
            
            # Try each path until we find one that exists
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    logger.info(f"Found YuNet model at: {model_path}")
                    break
            
            if model_path is None:
                logger.error("YuNet model file not found in any of the expected locations")
                logger.info("Falling back to face_recognition library for face detection")
                self.use_yunet = False
            else:
                self.face_detector = cv2.FaceDetectorYN.create(
                    model=model_path,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.3,  # Lower threshold for better detection
                    nms_threshold=0.3,
                    top_k=5000
                )
                self.use_yunet = True
        except Exception as e:
            logger.exception(f"Error initializing YuNet face detector: {str(e)}")
            logger.info("Falling back to face_recognition library for face detection")
            self.use_yunet = False
        
    def detect_faces_in_image(self, image_path: str) -> Dict[str, Any]:
        """
        Detect faces in an image file using OpenCV YuNet detector.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with detection results including faces found and their embeddings
        """
        try:
            logger.info(f"Detecting faces in image: {image_path}")
            
            # Check if the image file exists
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}",
                    "detections": []
                }
            
            # Use our improved detect_faces method which uses OpenCV YuNet detector
            face_results = self.detect_faces(image_path)
            
            if not face_results:
                logger.warning(f"No faces detected in {image_path}")
                logger.info(f"No faces detected in image")
                
                return {
                    "success": False,
                    "error": "No faces detected in the image",
                    "detections": []
                }
            
            # Process the face results from detect_faces method
            detections = []
            
            logger.info(f"Detected {len(face_results)} faces in image {image_path}")
            
            for i, face in enumerate(face_results):
                # Extract face information
                box = face.get('box', [])
                confidence = face.get('confidence', 0.0)
                landmarks = face.get('landmarks', [])
                
                # Get face embedding using the face region
                x, y, w, h = box
                
                # Load the image
                image = cv2.imread(image_path)
                if image is None:
                    logger.error(f"Failed to load image: {image_path}")
                    continue
                    
                # Extract face region with some margin
                margin = 0.2  # 20% margin
                x_margin = int(w * margin)
                y_margin = int(h * margin)
                
                # Ensure coordinates are within image bounds
                height, width = image.shape[:2]
                x1 = max(0, x - x_margin)
                y1 = max(0, y - y_margin)
                x2 = min(width, x + w + x_margin)
                y2 = min(height, y + h + y_margin)
                
                face_img = image[y1:y2, x1:x2]
                
                # Skip if face region is empty
                if face_img.size == 0:
                    logger.warning(f"Empty face region for face {i}")
                    continue
                
                # Get face embedding using face_recognition on the extracted face region
                face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                
                # Try with different face detection parameters
                # First attempt with default parameters
                face_locations = face_recognition.face_locations(face_rgb)
                
                # If that fails, try with a more lenient model (HOG instead of CNN)
                if not face_locations:
                    try:
                        face_locations = face_recognition.face_locations(face_rgb, model="hog")
                    except Exception as e:
                        logger.debug(f"HOG model fallback failed: {str(e)}")
                
                # If still no face detected, try with the original box coordinates directly
                if not face_locations:
                    logger.info(f"Using original detection box as face location for face {i}")
                    # Create a face location in (top, right, bottom, left) format from the box
                    face_locations = [(y, x + w, y + h, x)]  # Convert from (x,y,w,h) to (top,right,bottom,left)
                
                # Try to generate face encodings
                try:
                    face_encodings = face_recognition.face_encodings(face_rgb, face_locations)
                    
                    if not face_encodings:
                        logger.warning(f"Failed to extract embedding for face {i} despite multiple attempts")
                        continue
                except Exception as encoding_error:
                    logger.warning(f"Error extracting face embedding: {str(encoding_error)}")
                    continue
                    
                face_embedding = np.array(face_encodings[0])
                
                # Ensure the embedding is properly normalized
                norm = np.linalg.norm(face_embedding)
                if norm > 0:
                    face_embedding = face_embedding / norm
                
                # Check for NaN values
                if np.isnan(face_embedding).any():
                    logger.warning(f"NaN values detected in face embedding for face {i}")
                    continue
                    
                # Convert to list for JSON serialization
                embedding_list = face_embedding.tolist()
                
                # Log embedding stats for debugging
                logger.debug(f"Face {i} embedding stats: length={len(embedding_list)}, min={min(embedding_list):.4f}, max={max(embedding_list):.4f}")
                
                # Get the face location from face_locations (top, right, bottom, left format)
                face_top, face_right, face_bottom, face_left = face_locations[0] if face_locations else (0, 0, 0, 0)
                
                detections.append({
                    "id": f"face_{i}",
                    "confidence": 1.0,  # Default confidence
                    "box": box,  # [x, y, width, height] format
                    "embedding": embedding_list,  # Use the normalized embedding list
                    "source": "dlib_face_recognition",  # Add source information for debugging
                    "face_location": {
                        "top": face_top,
                        "right": face_right,
                        "bottom": face_bottom,
                        "left": face_left
                    },
                })
                
            return {
                "success": True,
                "message": f"Detected {len(detections)} faces",
                "detections": detections
            }
            
        except Exception as e:
            logger.exception(f"Error detecting faces in image: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "detections": []
            }
    
    def detect_faces(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect faces in an image using OpenCV YuNet detector with fallback to face_recognition.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of dictionaries with face detection results
        """
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return []
            
            # If YuNet initialization failed, use face_recognition library
            if not hasattr(self, 'use_yunet') or not self.use_yunet:
                logger.info(f"Using face_recognition library for face detection in {image_path}")
                # Convert to RGB for face_recognition
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Try multiple detection models in sequence for better results
                face_locations = []
                
                # First try with default model (usually CNN if available)
                try:
                    face_locations = face_recognition.face_locations(rgb_image)
                except Exception as e:
                    logger.warning(f"Default face detection failed: {str(e)}")
                
                # If that fails, try with HOG model which is faster but less accurate
                if not face_locations:
                    try:
                        logger.info(f"Trying HOG model for face detection in {image_path}")
                        face_locations = face_recognition.face_locations(rgb_image, model="hog")
                    except Exception as e:
                        logger.warning(f"HOG face detection failed: {str(e)}")
                
                if not face_locations:
                    logger.warning(f"No faces detected with any method in {image_path}")
                    return []
                
                face_results = []
                for face_location in face_locations:
                    top, right, bottom, left = face_location
                    face_result = {
                        "box": [left, top, right - left, bottom - top],
                        "confidence": 1.0,  # face_recognition doesn't provide confidence scores
                        "landmarks": []  # face_recognition doesn't provide landmarks in this function
                    }
                    face_results.append(face_result)
                
                logger.info(f"Detected {len(face_results)} faces with face_recognition in {image_path}")
                return face_results
            
            # Get original image dimensions
            height, width = image.shape[:2]
            
            # Set detector input size to original image dimensions
            # This is crucial for accurate face detection
            self.face_detector.setInputSize((width, height))
            
            # Try YuNet detection with different parameters if needed
            try:
                # First attempt with default parameters
                _, faces = self.face_detector.detect(image)
                
                # Check if faces were detected
                if faces is None or len(faces) == 0:
                    logger.warning(f"No faces detected with YuNet in {image_path} using default parameters")
                    
                    # Try with lower score threshold for better detection
                    original_threshold = self.face_detector.getScoreThreshold()
                    self.face_detector.setScoreThreshold(0.2)  # Lower threshold to detect more faces
                    
                    try:
                        _, faces = self.face_detector.detect(image)
                        logger.info(f"Retried YuNet detection with lower threshold: {0.2}")
                    finally:
                        # Restore original threshold
                        self.face_detector.setScoreThreshold(original_threshold)
                    
                    if faces is None or len(faces) == 0:
                        logger.warning(f"No faces detected with YuNet in {image_path} even with lower threshold")
                        # Fall back to face_recognition library
                        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_image)
                        
                        if not face_locations:
                            return []
                        
                        # Convert face_locations to YuNet-like format
                        faces = []
                        for top, right, bottom, left in face_locations:
                            w = right - left
                            h = bottom - top
                            faces.append([left, top, w, h, 1.0])  # Confidence set to 1.0
            except Exception as e:
                logger.error(f"Error in YuNet face detection: {str(e)}")
                return []
                
            face_results = []
            
            for face in faces:
                x, y, w, h, confidence = face[:5]
                x, y, w, h = int(x), int(y), int(w), int(h)
                
                # Skip faces with very low confidence
                if confidence < 0.3:
                    continue
                    
                # Extract landmarks if available (points 5-14 in the face array)
                landmarks = []
                if len(face) > 5:
                    for i in range(5, min(15, len(face)), 2):
                        if i+1 < len(face):
                            landmarks.append((int(face[i]), int(face[i+1])))
                
                face_result = {
                    "box": [x, y, w, h],
                    "confidence": float(confidence),
                    "landmarks": landmarks
                }
                
                face_results.append(face_result)
            
            logger.info(f"Detected {len(face_results)} faces with YuNet in {image_path}")
            return face_results
            
        except Exception as e:
            logger.exception(f"Error detecting faces: {str(e)}")
            # Attempt fallback to face_recognition on exception
            try:
                logger.info(f"Attempting fallback to face_recognition after YuNet error")
                rgb_image = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_image)
                
                face_results = []
                for face_location in face_locations:
                    top, right, bottom, left = face_location
                    face_result = {
                        "box": [left, top, right - left, bottom - top],
                        "confidence": 1.0,
                        "landmarks": []
                    }
                    face_results.append(face_result)
                
                logger.info(f"Fallback detected {len(face_results)} faces with face_recognition")
                return face_results
            except Exception as fallback_error:
                logger.exception(f"Fallback face detection also failed: {str(fallback_error)}")
                return []
            
    def _extract_video_id_from_path(self, video_path: str) -> Optional[int]:
        """
        Extract video ID from the video file path.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video ID as an integer, or None if extraction fails
        """
        try:
            # Try to extract video ID from the path
            filename = os.path.basename(video_path)
            if filename.startswith("capture_"):
                # Format: capture_XXXX.mp4
                video_id_str = filename.replace("capture_", "").split(".")[0]
                try:
                    return int(video_id_str)
                except ValueError:
                    pass
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID from path: {str(e)}")
            return None
    
    def _get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Get metadata for a video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dict with video metadata
        """
        try:
            # Try to get metadata from the database
            from sqlalchemy.orm import Session
            from backend.db.session import SessionLocal
            from backend.db.models import CaptureSession
            
            video_name = os.path.basename(video_path)
            
            db = SessionLocal()
            try:
                # Find the capture session for this video
                capture = db.query(CaptureSession).filter(
                    or_(
                        CaptureSession.video_path.like(f"%{video_name}%"),
                        CaptureSession.file_path.like(f"%{video_name}%")
                    )
                ).first()
                
                if capture:
                    # Extract metadata from the capture session
                    metadata = {
                        "title": f"Parliament TV - {capture.title}" if capture.title else f"Parliament TV Capture {capture.id}",
                        "description": capture.description or "",
                        "capture_date": capture.start_time.isoformat() if capture.start_time else datetime.datetime.now().isoformat(),
                        "duration": capture.duration or 0,
                        "source_url": capture.url or "",
                    }
                    
                    # Extract audio and video URLs from metadata if available
                    if capture.metadata:
                        if isinstance(capture.metadata, dict):
                            metadata["audio_url"] = capture.metadata.get("audio_url", "")
                            metadata["video_url"] = capture.metadata.get("video_url", "")
                        elif isinstance(capture.metadata, str):
                            try:
                                meta_dict = json.loads(capture.metadata)
                                metadata["audio_url"] = meta_dict.get("audio_url", "")
                                metadata["video_url"] = meta_dict.get("video_url", "")
                            except:
                                pass
                    
                    return metadata
            finally:
                db.close()
                
            # If we couldn't get metadata from the database, return basic info
            return {
                "title": f"Parliament TV Video - {os.path.basename(video_path)}",
                "description": "Parliament TV video capture",
                "capture_date": datetime.datetime.now().isoformat(),
                "duration": 0,
                "source_url": "",
                "audio_url": "",
                "video_url": ""
            }
        except Exception as e:
            logger.error(f"Error getting video metadata: {str(e)}")
            return {
                "title": f"Parliament TV Video - {os.path.basename(video_path)}",
                "description": "Parliament TV video capture",
                "capture_date": datetime.datetime.now().isoformat(),
                "duration": 0,
                "source_url": "",
                "audio_url": "",
                "video_url": ""
            }
        
    def _generate_face_encoding(self, image_path: Path) -> Dict:
        """Generate a face encoding from an image file."""
        try:
            import face_recognition
            
            # Load the image
            image = face_recognition.load_image_file(str(image_path))
            
            # Find all faces in the image
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                return {
                    "success": False,
                    "error": "No faces detected in the image"
                }
            
            # If multiple faces are detected, use the largest one
            if len(face_locations) > 1:
                logger.warning(f"Multiple faces detected in {image_path}, using the largest one")
                
                # Find the largest face by area
                largest_area = 0
                largest_face_idx = 0
                
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    area = (bottom - top) * (right - left)
                    if area > largest_area:
                        largest_area = area
                        largest_face_idx = i
                
                # Get encoding for the largest face
                face_encodings = face_recognition.face_encodings(image, [face_locations[largest_face_idx]])
            else:
                # Get encoding for the single face
                face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if not face_encodings:
                return {
                    "success": False,
                    "error": "Failed to generate face encoding"
                }
            
            # Return the first face encoding
            return {
                "success": True,
                "encoding": face_encodings[0].tolist(),
                "face_location": face_locations[0]
            }
            
        except Exception as e:
            logger.error(f"Error generating face encoding: {str(e)}")
            return {
                "success": False,
                "error": f"Error generating face encoding: {str(e)}"
            }
    
    def _generate_face_encoding_from_url(self, url: str) -> Dict:
        """Generate a face encoding from a URL."""
        try:
            import requests
            import tempfile
            
            # Download the image
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to download image: HTTP {response.status_code}"
                }
            
            # Save the image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            # Generate face encoding from the temporary file
            result = self._generate_face_encoding(Path(temp_file_path))
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating face encoding from URL: {str(e)}")
            return {
                "success": False,
                "error": f"Error generating face encoding from URL: {str(e)}"
            }
    
    def detect_faces_in_video(self, video_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Detect faces in a video file using facial recognition.
        
        Args:
            video_path: Path to the video file
            output_file: Optional path to save the output video with face detection
            
        Returns:
            Dict with detection results
        """
        logger.info(f"Detecting faces in video: {video_path}")
        
        # Check if the video file exists
        if not os.path.exists(video_path):
            return {
                "success": False,
                "error": f"Video file not found: {video_path}",
                "output_file": None
            }
        
        # Prepare the script path
        script_path = self.scripts_dir / "detect_faces.py"
        
        if not os.path.exists(script_path):
            return {
                "success": False,
                "error": f"Face detection script not found: {script_path}",
                "output_file": None
            }
        
        # Prepare the output file if not provided
        if not output_file:
            output_file = f"{os.path.splitext(video_path)[0]}_faces.mp4"
        
        # Prepare the command
        cmd = [
            "python",
            str(script_path),
            "--input", video_path,
            "--output", output_file
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Face detection failed: {stderr}")
                return {
                    "success": False,
                    "error": f"Face detection failed: {stderr}",
                    "output_file": None
                }
            
            logger.info(f"Face detection completed successfully")
            
            # Check if the output file exists
            if not os.path.exists(output_file):
                return {
                    "success": False,
                    "error": f"Output file not found: {output_file}",
                    "output_file": None
                }
            
            return {
                "success": True,
                "message": "Face detection completed successfully",
                "output_file": output_file
            }
            
        except Exception as e:
            logger.exception(f"Error detecting faces: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None
            }
    
    def identify_speakers(self, video_path: str, db_session=None, output_file: Optional[str] = None, store_unidentified: bool = True, export_to_supabase: bool = True) -> Dict:
        """
        Identify speakers in a video file using facial recognition.
        Also stores unidentified faces for later identification if store_unidentified is True.
        Can export results to Supabase format with combined audio-video if requested.
        
        Args:
            video_path: Path to the video file
            output_file: Optional path to save the output video with speaker identification
            store_unidentified: Whether to store unidentified faces for later identification
            export_to_supabase: Whether to export results to Supabase format
            
        Returns:
            Dict with identification results including both identified and unidentified faces
        """
        # Track problematic frames to avoid repeated processing
        problematic_frames_cache_file = f"{os.path.splitext(video_path)[0]}_problematic_frames.json"
        problematic_frames = set()
        
        # Load previously identified problematic frames if the cache file exists
        if os.path.exists(problematic_frames_cache_file):
            try:
                with open(problematic_frames_cache_file, 'r') as f:
                    problematic_frames = set(json.load(f))
                logger.info(f"Loaded {len(problematic_frames)} problematic frames from cache")
            except Exception as e:
                logger.warning(f"Failed to load problematic frames cache: {str(e)}")
        
        logger.info(f"Identifying speakers in video: {video_path}")
        
        # Check if the video file exists
        if not os.path.exists(video_path):
            return {
                "success": False,
                "error": f"Video file not found: {video_path}",
                "output_file": None,
                "results_file": None
            }
        
        # Check if the MP encodings file exists
        mp_encodings_exist = os.path.exists(self.mp_encodings_file)
        if not mp_encodings_exist:
            logger.warning(f"MP encodings file not found: {self.mp_encodings_file}. Will proceed with face detection only.")
            # Create an empty MP encodings file with the required structure
            try:
                # Create an empty MP encodings file with the required structure
                empty_encodings = {
                    "names": [],
                    "encodings": [],
                    "parliament_ids": [],
                    "updated_at": datetime.datetime.now().isoformat()
                }
                os.makedirs(os.path.dirname(self.mp_encodings_file), exist_ok=True)
                with open(self.mp_encodings_file, 'w') as f:
                    json.dump(empty_encodings, f, indent=2)
                logger.info(f"Created empty MP encodings file for face detection: {self.mp_encodings_file}")
            except Exception as e:
                logger.error(f"Failed to create empty MP encodings file: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to create empty MP encodings file: {str(e)}",
                    "output_file": None,
                    "results_file": None
                }
        
        # Use the optimized face detector instead of inefficient scripts
        try:
            from .optimized_face_detection import OptimizedFaceDetector
            logger.info(f"Using OptimizedFaceDetector for efficient face identification: {video_path}")
        except ImportError as e:
            logger.error(f"Failed to import OptimizedFaceDetector: {str(e)}")
            return {
                "success": False,
                "error": f"OptimizedFaceDetector not available: {str(e)}",
                "output_file": None,
                "results_file": None
            }
        
        # Prepare the results file
        results_file = f"{os.path.splitext(video_path)[0]}_speaker_identification_results.json"
        
        # Prepare the directory for unidentified faces
        unidentified_dir = None
        if store_unidentified:
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            unidentified_dir = os.path.join(video_dir, f"{video_name}_unidentified_faces")
            os.makedirs(unidentified_dir, exist_ok=True)
        
        # Create a temporary file with problematic frames information if needed
        problematic_frames_temp_file = None
        if problematic_frames:
            problematic_frames_temp_file = f"{os.path.splitext(video_path)[0]}_problematic_frames_temp.json"
            try:
                with open(problematic_frames_temp_file, 'w') as f:
                    json.dump(list(problematic_frames), f)
                logger.info(f"Saved {len(problematic_frames)} problematic frames to temp file for script")
            except Exception as e:
                logger.warning(f"Failed to save problematic frames temp file: {str(e)}")
                problematic_frames_temp_file = None
        
        # Use OptimizedFaceDetector for efficient processing
        try:
            # Initialize the optimized detector
            detector = OptimizedFaceDetector(output_dir=unidentified_dir)
            
            # Load known face encodings
            import json
            import numpy as np
            from datetime import datetime
            
            known_encodings = []
            known_names = []
            known_parliament_ids = []
            
            if os.path.exists(self.mp_encodings_file):
                with open(self.mp_encodings_file, 'r') as f:
                    encodings_data = json.load(f)
                    
                if encodings_data.get("names") and encodings_data.get("encodings"):
                    known_names = encodings_data["names"]
                    known_encodings = [np.array(enc) for enc in encodings_data["encodings"]]
                    known_parliament_ids = encodings_data.get("parliament_ids", [])
                    
                    logger.info(f"Loaded {len(known_names)} known face encodings")
                else:
                    logger.warning("MP encodings file exists but contains no encodings")
            else:
                logger.warning(f"MP encodings file not found: {self.mp_encodings_file}")
            
            # Process video with optimized detector (much faster!)
            # Use optimized frame sampling: 1 frame every 3-5 seconds instead of every 2nd frame
            detection_results = detector.extract_faces_from_video(
                video_path=video_path,
                output_dir=unidentified_dir if store_unidentified else None,
                interval=4.0,  # Process 1 frame every 4 seconds (vs every 0.08 seconds in old script!)
                min_confidence=0.6,
                prioritize_center=True,
                select_best_frames=True,
                roi_scale=0.7  # Focus on center 70% of frame
            )
            
            # Convert results to expected format
            speaker_results = {
                "video_path": video_path,
                "total_frames": detection_results.get("total_frames", 0),
                "processed_frames": detection_results.get("processed_frames", 0),
                "identified_speakers": {},
                "speaker_segments": [],
                "unidentified_faces": detection_results.get("unidentified_faces", []),
                "processing_time": detection_results.get("processing_time", 0)
            }
            
            # Process detected faces and match with known encodings
            if detection_results.get("faces") and known_encodings:
                import face_recognition
                
                for face_data in detection_results["faces"]:
                    face_encoding = face_data.get("encoding")
                    if face_encoding is not None:
                        # Compare with known encodings
                        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
                        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                        
                        if any(matches):
                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                speaker_name = known_names[best_match_index]
                                parliament_id = known_parliament_ids[best_match_index] if best_match_index < len(known_parliament_ids) else None
                                confidence = 1.0 - face_distances[best_match_index]
                                
                                # Add to speaker segments
                                speaker_results["speaker_segments"].append({
                                    "start_time": face_data.get("timestamp", 0),
                                    "end_time": face_data.get("timestamp", 0) + 1.0,  # 1 second segment
                                    "speaker_name": speaker_name,
                                    "member_id": parliament_id,
                                    "confidence": confidence,
                                    "transcript": ""  # Will be filled by transcription
                                })
                                
                                # Track identified speakers
                                if speaker_name not in speaker_results["identified_speakers"]:
                                    speaker_results["identified_speakers"][speaker_name] = {
                                        "parliament_id": parliament_id,
                                        "appearances": 0,
                                        "total_confidence": 0
                                    }
                                
                                speaker_results["identified_speakers"][speaker_name]["appearances"] += 1
                                speaker_results["identified_speakers"][speaker_name]["total_confidence"] += confidence
            
            # Save results to JSON file
            with open(results_file, 'w') as f:
                json.dump(speaker_results, f, indent=2, default=str)
            
            logger.info(f"OptimizedFaceDetector completed: {len(speaker_results['speaker_segments'])} segments identified")
            
        except Exception as e:
            logger.error(f"Error with OptimizedFaceDetector: {str(e)}")
            import traceback
            logger.error(f"OptimizedFaceDetector error traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"OptimizedFaceDetector failed: {str(e)}",
                "output_file": None,
                "results_file": None
            }
            
        # Update problematic frames from results if available
        try:
            with open(results_file, 'r') as f:
                results_data = json.load(f)
                if 'problematic_frames' in results_data:
                    new_problematic_frames = set(results_data['problematic_frames'])
                    problematic_frames.update(new_problematic_frames)
                    logger.info(f"Updated problematic frames with {len(new_problematic_frames)} new entries")
                    
                    # Save updated problematic frames cache
                    with open(problematic_frames_cache_file, 'w') as cache_f:
                        json.dump(list(problematic_frames), cache_f)
                    logger.info(f"Saved {len(problematic_frames)} problematic frames to cache")
        except Exception as e:
            logger.warning(f"Failed to update problematic frames from results: {str(e)}")
            
        # Clean up temporary file
        if problematic_frames_temp_file and os.path.exists(problematic_frames_temp_file):
            try:
                os.remove(problematic_frames_temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temporary problematic frames file: {str(e)}")
        
        logger.info(f"Speaker identification completed successfully")
            
        # Check if the results file exists
        if not os.path.exists(results_file):
            return {
                "success": False,
                "error": f"Results file not found: {results_file}",
                "output_file": output_file if output_file and os.path.exists(output_file) else None,
                "results_file": None
            }
        
        # Load the results
        with open(results_file, "r") as f:
            results = json.load(f)
        
        # Add information about unidentified faces if available
        if store_unidentified and unidentified_dir:
            results["unidentified_dir"] = unidentified_dir
        
        # Add a note if we were using an empty MP encodings file
        if not mp_encodings_exist:
            results["note"] = "Used empty MP encodings file. All faces detected are unidentified."
        
        # Export results to Supabase format if requested
        supabase_export_info = None
        if export_to_supabase:
            try:
                # Get video metadata including separate audio and video URLs
                video_metadata = self._get_video_metadata(video_path)
                
                # Get the video ID from the path
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                video_id = None
                if video_name.startswith("capture_"):
                    try:
                        video_id = int(video_name.replace("capture_", ""))
                    except ValueError:
                        logger.warning(f"Could not extract video ID from filename: {video_name}")
                
                # Find corresponding audio file if it exists
                audio_path = None
                video_dir = os.path.dirname(video_path)
                potential_audio_path = os.path.join(video_dir, f"{video_name}.audio.mp3")
                if os.path.exists(potential_audio_path):
                    audio_path = potential_audio_path
                    logger.info(f"Found corresponding audio file: {audio_path}")
                
                # Export results with combined audio-video creation
                # Ensure we have a proper SQLAlchemy session
                local_db_session = None
                if db_session is None or not hasattr(db_session, 'query'):
                    # Create a new session if none provided or if it's not a valid SQLAlchemy session
                    local_db_session = SessionLocal()
                    use_session = local_db_session
                else:
                    use_session = db_session
                
                try:
                    supabase_export_info = export_recognition_results(
                        video_id=video_id or 0,  # Use 0 if we couldn't extract a valid ID
                        recognition_results=results,
                        video_path=video_path,
                        audio_path=audio_path,
                        metadata=video_metadata,
                        db_session=use_session  # Pass the proper SQLAlchemy session
                    )
                finally:
                    # Close the local session if we created one
                    if local_db_session:
                        local_db_session.close()
                
                logger.info(f"Exported recognition results to Supabase format: {supabase_export_info}")
            except Exception as e:
                logger.error(f"Error exporting results to Supabase format: {str(e)}")
                supabase_export_info = {"error": str(e)}
        
        return {
            "success": True,
            "message": "Speaker identification completed successfully",
            "output_file": output_file if output_file and os.path.exists(output_file) else None,
            "results_file": results_file,
            "unidentified_dir": unidentified_dir if store_unidentified else None,
            "supabase_export": supabase_export_info,
            "results": results
        }
    

        
        try:
            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Speaker identification failed: {stderr}")
                return {
                    "success": False,
                    "error": f"Speaker identification failed: {stderr}",
                    "output_file": None,
                    "results_file": None
                }
            
            logger.info(f"Speaker identification completed successfully")
            
            # Check if the results file exists
            if not os.path.exists(results_file):
                return {
                    "success": False,
                    "error": f"Results file not found: {results_file}",
                    "output_file": output_file if output_file and os.path.exists(output_file) else None,
                    "results_file": None
                }
            
            # Load the results
            with open(results_file, "r") as f:
                results = json.load(f)
            
            # Add information about unidentified faces if available
            if store_unidentified and unidentified_dir:
                results["unidentified_dir"] = unidentified_dir
            
            # Add a note if we were using an empty MP encodings file
            if not mp_encodings_exist:
                results["note"] = "Used empty MP encodings file. All faces detected are unidentified."
            
            # Export results to Supabase format if requested
            supabase_export_info = None
            if export_to_supabase:
                try:
                    # Get video metadata including separate audio and video URLs
                    video_metadata = self._get_video_metadata(video_path)
                    
                    # Set up export directory
                    export_dir = os.path.join(os.path.dirname(video_path), "supabase_export")
                    os.makedirs(export_dir, exist_ok=True)
                    
                    # Export results with combined audio-video creation
                    # Ensure we have a proper SQLAlchemy session
                    local_db_session = None
                    if db_session is None or not hasattr(db_session, 'query'):
                        # Create a new session if none provided or if it's not a valid SQLAlchemy session
                        local_db_session = SessionLocal()
                        use_session = local_db_session
                    else:
                        use_session = db_session
                    
                    try:
                        # Extract video ID from the path if possible
                        video_id = self._extract_video_id_from_path(video_path)
                        
                        supabase_export_info = export_recognition_results(
                            video_id=video_id or 0,  # Use 0 if we couldn't extract a valid ID
                            recognition_results=results,
                            video_path=video_path,
                            metadata=video_metadata,
                            db_session=use_session  # Pass the proper SQLAlchemy session
                        )
                    finally:
                        # Close the local session if we created one
                        if local_db_session:
                            local_db_session.close()
                    
                    logger.info(f"Exported recognition results to Supabase format: {supabase_export_info}")
                except Exception as e:
                    logger.error(f"Error exporting results to Supabase format: {str(e)}")
                    supabase_export_info = {"error": str(e)}
            
            return {
                "success": True,
                "message": "Speaker identification completed successfully",
                "output_file": output_file if output_file and os.path.exists(output_file) else None,
                "results_file": results_file,
                "unidentified_dir": unidentified_dir if store_unidentified else None,
                "supabase_export": supabase_export_info,
                "results": results
            }
        except Exception as e:
            logger.exception(f"Error identifying speakers: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None,
                "results_file": None
            }
    
    def load_mp_database(self) -> Dict:
        """
        Load the MP database with face encodings.
        
        Returns:
            Dict with load results
        """
        try:
            if not os.path.exists(self.mp_encodings_file):
                logger.warning(f"MP encodings file not found: {self.mp_encodings_file}")
                return {
                    "success": False,
                    "error": f"MP encodings file not found: {self.mp_encodings_file}"
                }
            
            # Load the MP encodings from the JSON file
            with open(self.mp_encodings_file, "r") as f:
                data = json.load(f)
            
            # Check if the data has the required fields
            if not all(key in data for key in ["names", "encodings"]):
                logger.error(f"Invalid MP encodings file format: {self.mp_encodings_file}")
                return {
                    "success": False,
                    "error": f"Invalid MP encodings file format: {self.mp_encodings_file}"
                }
            
            logger.info(f"MP database loaded successfully with {len(data['names'])} speakers")
            
            return {
                "success": True,
                "message": f"MP database loaded successfully with {len(data['names'])} speakers",
                "data": data
            }
        except Exception as e:
            logger.exception(f"Error loading MP database: {str(e)}")
            return {
                "success": False,
                "error": f"Error loading MP database: {str(e)}"
            }
    
    def update_mp_database(self) -> Dict:
        """
        Update the MP database with the latest photos and face encodings.
        
        Returns:
            Dict with update results
        """
        logger.info("Updating MP database")
        
        try:
            # Get all speakers from the database
            from sqlalchemy.orm import Session
            from backend.db.session import SessionLocal
            from backend.db.models import Speaker
            
            db = SessionLocal()
            try:
                speakers = db.query(Speaker).filter(Speaker.face_encoding.isnot(None)).all()
                
                if not speakers:
                    return {
                        "success": False,
                        "error": "No speakers with face encodings found in the database"
                    }
                
                # Create the MP encodings data
                mp_data = {
                    "names": [],
                    "encodings": [],
                    "parliament_ids": [],
                    "updated_at": datetime.datetime.now().isoformat()
                }
                
                for speaker in speakers:
                    if speaker.face_encoding:
                        mp_data["names"].append(speaker.name)
                        mp_data["encodings"].append(speaker.face_encoding)
                        mp_data["parliament_ids"].append(speaker.parliament_id or "")
                
                # Save the MP encodings to a JSON file
                with open(self.mp_encodings_file, "w") as f:
                    json.dump(mp_data, f)
                
                logger.info(f"MP database updated successfully with {len(speakers)} speakers")
                
                # Load the updated database
                self.load_mp_database()
                
                return {
                    "success": True,
                    "message": f"MP database updated successfully with {len(speakers)} speakers"
                }
            finally:
                db.close()
        except Exception as e:
            logger.exception(f"Error updating MP database: {str(e)}")
            return {
                "success": False,
                "error": f"Error updating MP database: {str(e)}"
            }
