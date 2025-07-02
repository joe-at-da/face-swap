"""
Face recognition service for Parliament TV
"""
import os
import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    """
    Service for face recognition operations including:
    - Face detection
    - Face embedding extraction
    - Face matching
    """
    
    def __init__(self):
        """
        Initialize the face recognition service with necessary models
        """
        # Path to models within the Docker container
        models_dir = "/app/models/face_recognition"
        os.makedirs(models_dir, exist_ok=True)
        
        # Initialize face detector
        try:
            # Try to load OpenCV's DNN face detector
            self.face_detector_model = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
            
            # Download the model if it doesn't exist
            if not os.path.exists(self.face_detector_model):
                logger.info(f"Downloading face detector model to {self.face_detector_model}")
                self._download_face_detector_model()
            
            self.face_detector = cv2.FaceDetectorYN.create(
                self.face_detector_model,
                "",
                (320, 320),
                0.9,  # Score threshold
                0.3,  # NMS threshold
                5000  # Top K
            )
            logger.info("Face detector initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing face detector: {str(e)}")
            self.face_detector = None
        
        # Initialize face recognizer for embedding extraction
        try:
            # Try to load OpenCV's DNN face recognizer
            self.face_recognizer_model = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")
            
            # Download the model if it doesn't exist
            if not os.path.exists(self.face_recognizer_model):
                logger.info(f"Downloading face recognizer model to {self.face_recognizer_model}")
                self._download_face_recognizer_model()
            
            self.face_recognizer = cv2.FaceRecognizerSF.create(
                self.face_recognizer_model,
                ""
            )
            logger.info("Face recognizer initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing face recognizer: {str(e)}")
            self.face_recognizer = None
    
    def _download_face_detector_model(self):
        """
        Download the face detector model from OpenCV's GitHub repository
        """
        import urllib.request
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.face_detector_model), exist_ok=True)
        
        # URL for the face detector model
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        
        try:
            # Download the model
            urllib.request.urlretrieve(url, self.face_detector_model)
            logger.info(f"Downloaded face detector model to {self.face_detector_model}")
        except Exception as e:
            logger.error(f"Error downloading face detector model: {str(e)}")
    
    def _download_face_recognizer_model(self):
        """
        Download the face recognizer model from OpenCV's GitHub repository
        """
        import urllib.request
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.face_recognizer_model), exist_ok=True)
        
        # URL for the face recognizer model
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
        
        try:
            # Download the model
            urllib.request.urlretrieve(url, self.face_recognizer_model)
            logger.info(f"Downloaded face recognizer model to {self.face_recognizer_model}")
        except Exception as e:
            logger.error(f"Error downloading face recognizer model: {str(e)}")
    
    def detect_faces(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect faces in an image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of dictionaries containing face detection results
        """
        logger.info(f"Detecting faces in image: {image_path}")
        
        if not self.face_detector:
            logger.error("Face detector not initialized")
            return []
        
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return []
            
            # Log image properties
            height, width = image.shape[:2]
            logger.info(f"Image dimensions: {width}x{height}, channels: {image.shape[2] if len(image.shape) > 2 else 1}")
            
            # Resize image if it's too large
            max_size = 1280
            if height > max_size or width > max_size:
                scale = max_size / max(height, width)
                image = cv2.resize(image, (int(width * scale), int(height * scale)))
                height, width = image.shape[:2]
                logger.info(f"Resized image to {width}x{height}")
            
            # Set input size for the detector
            self.face_detector.setInputSize((width, height))
            logger.debug(f"Set face detector input size to {width}x{height}")
            
            # Detect faces
            logger.debug("Running face detection...")
            _, faces = self.face_detector.detect(image)
            
            if faces is None:
                logger.warning(f"❌ No faces detected in image: {image_path}")
                # Save a debug copy of the image
                debug_dir = "/app/data/temp/debug"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = f"{debug_dir}/no_face_{os.path.basename(image_path)}"
                cv2.imwrite(debug_path, image)
                logger.info(f"Saved debug image to {debug_path}")
                return []
            
            # Process detected faces
            face_results = []
            for i, face in enumerate(faces):
                x, y, w, h, score = face[:5]
                x, y, w, h = int(x), int(y), int(w), int(h)
                face_results.append({
                    "box": [x, y, w, h],
                    "confidence": float(score),
                    "landmarks": face[5:15].reshape(-1, 2).tolist() if len(face) > 5 else []
                })
                
                # Save face crop for debugging
                debug_dir = "/app/data/temp/debug/faces"
                os.makedirs(debug_dir, exist_ok=True)
                face_crop = image[y:y+h, x:x+w]
                face_path = f"{debug_dir}/face_{i}_{os.path.basename(image_path)}"
                cv2.imwrite(face_path, face_crop)
                logger.debug(f"Saved face crop {i} to {face_path}")
            
            logger.info(f"✅ Detected {len(face_results)} faces in image: {image_path} with confidences: {[f'{f["confidence"]:.2f}' for f in face_results]}")
            return face_results
            
        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}")
            return []
    
    def extract_face_embedding(self, image_path: str, face_box: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Extract face embedding from an image
        
        Args:
            image_path: Path to the image file
            face_box: Optional bounding box of the face [x, y, w, h]
            
        Returns:
            Dictionary containing face embedding and metadata
        """
        logger.info(f"Extracting face embedding from image: {image_path}")
        
        if not self.face_recognizer:
            logger.error("Face recognizer not initialized")
            return {}
        
        try:
            # Read the image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return {}
            
            # If face box is not provided, detect faces first
            if face_box is None:
                logger.info("No face box provided, detecting faces first")
                faces = self.detect_faces(image_path)
                if not faces:
                    logger.warning(f"❌ No faces detected in image: {image_path}")
                    return {}
                
                # Use the face with highest confidence
                faces.sort(key=lambda x: x["confidence"], reverse=True)
                face_box = faces[0]["box"]
                logger.info(f"Using face with highest confidence: {faces[0]['confidence']:.4f}")
            
            # Extract the face region
            x, y, w, h = face_box
            if y >= image.shape[0] or x >= image.shape[1] or y+h <= 0 or x+w <= 0:
                logger.error(f"❌ Face box outside image boundaries: box={face_box}, image={image.shape}")
                return {}
                
            # Ensure box is within image boundaries
            x = max(0, x)
            y = max(0, y)
            w = min(w, image.shape[1] - x)
            h = min(h, image.shape[0] - y)
            
            if w <= 0 or h <= 0:
                logger.error(f"❌ Invalid face box dimensions after boundary check: w={w}, h={h}")
                return {}
                
            face_image = image[y:y+h, x:x+w]
            logger.info(f"Extracted face region: {w}x{h} from position ({x},{y})")
            
            # Extract face embedding
            logger.debug(f"Extracting embedding from face image of size {face_image.shape}")
            try:
                face_embedding = self.face_recognizer.feature(face_image)
                logger.info(f"✅ Successfully extracted face embedding: shape={face_embedding.shape}, type={type(face_embedding).__name__}")
                
                # Save face image for debugging
                debug_dir = "/app/data/temp/debug/embeddings"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = f"{debug_dir}/face_{os.path.basename(image_path)}"
                cv2.imwrite(debug_path, face_image)
                logger.debug(f"Saved face image used for embedding to {debug_path}")
                
                # Check for NaN or zero values
                if np.isnan(face_embedding).any():
                    logger.warning("⚠️ NaN values detected in face embedding")
                if np.count_nonzero(face_embedding) == 0:
                    logger.warning("⚠️ All zeros in face embedding")
                
                # Normalize the embedding
                norm = np.linalg.norm(face_embedding)
                if norm > 0:
                    face_embedding = face_embedding / norm
                    logger.debug("Normalized face embedding")
                else:
                    logger.warning("⚠️ Zero norm in face embedding, cannot normalize")
                
                return {
                    "embedding": face_embedding.flatten().tolist(),
                    "box": face_box,
                    "image_path": image_path
                }
            except Exception as e:
                logger.error(f"❌ Error extracting face embedding: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return {}
            
        except Exception as e:
            logger.error(f"Error extracting face embedding: {str(e)}")
            return {}
    
    def match_faces(self, embedding1: Union[List[float], np.ndarray], embedding2: Union[List[float], np.ndarray]) -> float:
        """
        Match two face embeddings and return similarity score
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
        
        try:
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Error matching faces: {str(e)}")
            return 0.0
    
    def process_video_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Process a video frame to detect faces and extract embeddings
        
        Args:
            frame: Video frame as numpy array
            
        Returns:
            List of dictionaries containing face detection results and embeddings
        """
        if not self.face_detector or not self.face_recognizer:
            logger.error("Face detector or recognizer not initialized")
            return []
        
        try:
            # Set input size for the detector
            height, width = frame.shape[:2]
            self.face_detector.setInputSize((width, height))
            
            # Detect faces
            _, faces = self.face_detector.detect(frame)
            
            if faces is None:
                return []
            
            # Process detected faces
            face_results = []
            for face in faces:
                x, y, w, h, score = face[:5]
                x, y, w, h = int(x), int(y), int(w), int(h)
                
                # Extract face region
                face_image = frame[y:y+h, x:x+w]
                
                # Extract face embedding
                try:
                    face_embedding = self.face_recognizer.feature(face_image)
                    face_embedding = face_embedding / np.linalg.norm(face_embedding)
                    
                    face_results.append({
                        "box": [x, y, w, h],
                        "confidence": float(score),
                        "embedding": face_embedding.flatten().tolist(),
                        "landmarks": face[5:15].reshape(-1, 2).tolist() if len(face) > 5 else []
                    })
                except Exception as e:
                    logger.error(f"Error extracting face embedding from frame: {str(e)}")
            
            return face_results
            
        except Exception as e:
            logger.error(f"Error processing video frame: {str(e)}")
            return []
