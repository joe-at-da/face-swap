"""
Facial Recognition Service for Parliament TV Videos

This service provides facial recognition capabilities for Parliament TV videos,
integrating with the existing scripts for face detection and speaker identification.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings
from backend.services.utils import make_json_serializable

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
                    CaptureSession.output_file.like(f"%{video_name}%")
                ).first()
                
                if capture:
                    # Extract metadata from the capture session
                    metadata = {
                        "title": f"Parliament TV - {capture.title}" if capture.title else f"Parliament TV Capture {capture.id}",
                        "description": capture.description or "",
                        "capture_date": capture.start_time.isoformat() if capture.start_time else datetime.now().isoformat(),
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
                "capture_date": datetime.now().isoformat(),
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
                "capture_date": datetime.now().isoformat(),
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
    
    def identify_speakers(self, video_path: str, output_file: Optional[str] = None, store_unidentified: bool = True) -> Dict:
        """
        Identify speakers in a video file using facial recognition.
        Also stores unidentified faces for later identification if store_unidentified is True.
        
        Args:
            video_path: Path to the video file
            output_file: Optional path to save the output video with speaker identification
            store_unidentified: Whether to store unidentified faces for later identification
            
        Returns:
            Dict with identification results including both identified and unidentified faces
        """
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
                    "updated_at": datetime.now().isoformat()
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
        
        # Prepare the script path - use the new script that can store unidentified faces
        script_path = self.scripts_dir / "identify_and_store_faces.py"
        
        # If the new script doesn't exist, fall back to the old one
        if not script_path.exists():
            script_path = self.scripts_dir / "identify_speakers.py"
            logger.warning(f"New script not found, falling back to: {script_path}")
            store_unidentified = False  # Can't store unidentified faces with the old script
            
            if not script_path.exists():
                return {
                    "success": False,
                    "error": f"Speaker identification script not found: {script_path}",
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
        
        # Prepare the command
        cmd = [
            "python",
            str(script_path),
            "--input", video_path,
            "--encodings", str(self.mp_encodings_file),
            "--results", results_file
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        if store_unidentified and unidentified_dir and "identify_and_store_faces.py" in str(script_path):
            cmd.extend(["--unidentified-dir", unidentified_dir])
        
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
            
            # Export data for Supabase integration if results are successful
            supabase_export_info = None
            try:
                from backend.services.integration.supabase_export import export_recognition_results
                
                # Get video metadata
                video_metadata = self._get_video_metadata(video_path)
                
                # Create export directory
                video_dir = os.path.dirname(video_path)
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                export_dir = os.path.join(video_dir, f"{video_name}_supabase_export")
                os.makedirs(export_dir, exist_ok=True)
                
                # Export results for Supabase integration
                supabase_export_info = export_recognition_results(
                    video_path=video_path,
                    recognition_results=results,
                    video_metadata=video_metadata,
                    export_dir=export_dir
                )
                
                logger.info(f"Exported recognition results for Supabase integration: {supabase_export_info}")
            except Exception as e:
                logger.warning(f"Failed to export recognition results for Supabase integration: {str(e)}")
                supabase_export_info = {"error": str(e)}
            
            return {
                "success": True,
                "message": "Speaker identification completed successfully" + (" (with face detection only)" if not mp_encodings_exist else ""),
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
                    "updated_at": datetime.now().isoformat()
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
