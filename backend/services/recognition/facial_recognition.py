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
        
        # Prepare the command
        script_path = self.scripts_dir / "facial_recognition_capture.py"
        
        cmd = [
            "python",
            str(script_path),
            video_path
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
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
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"Face detection failed: {stderr}")
                return {
                    "success": False,
                    "error": stderr,
                    "output_file": None
                }
            
            # Parse the output to get the output file path
            output_path = None
            for line in stdout.splitlines():
                if line.startswith("Output file:"):
                    output_path = line.split(":", 1)[1].strip()
                    break
            
            return {
                "success": True,
                "output_file": output_path,
                "message": "Face detection completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in face detection: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None
            }
    
    def identify_speakers(self, video_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Identify speakers in a video file using facial recognition.
        
        Args:
            video_path: Path to the video file
            output_file: Optional path to save the output video with speaker identification
            
        Returns:
            Dict with identification results
        """
        logger.info(f"Identifying speakers in video: {video_path}")
        
        # Check if video file exists
        if not os.path.exists(video_path):
            error_msg = f"Video file not found: {video_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "results_file": None,
                "results": {"speakers": [], "total_speakers": 0}
            }
        
        # Prepare the command
        script_path = self.scripts_dir / "speaker_identification.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            error_msg = f"Speaker identification script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": True,  # Mark as success but with empty results
                "error": error_msg,
                "output_file": None,
                "results_file": None,
                "results": {"speakers": [], "total_speakers": 0},
                "message": "No speaker identification script found, but processing continues"
            }
        
        cmd = [
            "python",
            str(script_path),
            video_path,
            "--min-confidence", "0.4"  # Lower confidence threshold to detect more faces
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
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
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"Speaker identification failed: {stderr}")
                # Even if the process failed, we'll return a partial success with empty results
                # This allows the recognition process to continue rather than fail completely
                return {
                    "success": True,  # Mark as success but with empty results
                    "error": stderr,
                    "output_file": None,
                    "results_file": None,
                    "results": {"speakers": [], "total_speakers": 0},
                    "message": "Speaker identification failed but processing continues"
                }
            
            # Parse the output to get the output file path and results file path
            output_path = None
            results_path = None
            
            for line in stdout.splitlines():
                if "Results saved to:" in line:
                    results_path = line.split(":", 1)[1].strip()
                elif "Processed video saved to:" in line:
                    output_path = line.split(":", 1)[1].strip()
            
            # Load the results file if it exists
            results = {}
            if results_path and os.path.exists(results_path):
                try:
                    with open(results_path, 'r') as f:
                        results = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading results file: {str(e)}")
            
            return {
                "success": True,
                "output_file": output_path,
                "results_file": results_path,
                "results": make_json_serializable(results),
                "message": "Speaker identification completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in speaker identification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None,
                "results_file": None
            }
    
    def update_mp_database(self) -> Dict:
        """
        Update the MP database with the latest photos and face encodings.
        
        Returns:
            Dict with update results
        """
        logger.info("Updating MP database")
        
        # Prepare the command
        script_path = self.scripts_dir / "speaker_identification.py"
        
        cmd = [
            "python",
            str(script_path),
            "--update-db"
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
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"MP database update failed: {stderr}")
                return {
                    "success": False,
                    "error": stderr
                }
            
            return {
                "success": True,
                "message": "MP database updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating MP database: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
