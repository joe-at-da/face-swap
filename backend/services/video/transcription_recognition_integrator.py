"""
Transcription and Recognition Integration Service.

This service integrates transcription data with face and voice recognition results
to create a unified timeline with accurate speaker identification.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from backend.core.config import settings
from backend.services.video.transcription import TranscriptionService
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
from backend.services.recognition.timeline_service import TimelineService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class TranscriptionRecognitionIntegrator:
    """Service for integrating transcription with face and voice recognition."""
    
    def __init__(self):
        """Initialize the integrator service."""
        self.transcription_service = TranscriptionService()
        self.facial_recognition = FacialRecognitionService()
        self.multimodal_service = MultimodalRecognitionService()
        self.timeline_service = TimelineService()
        
        self.output_dir = Path(settings.MEDIA_STORAGE_PATH) / "integrated_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_video(self, video_path: str, db_session=None, capture_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a video with transcription and recognition integration.
        
        Args:
            video_path: Path to the video file
            db_session: Optional database session for storing results
            capture_id: Optional capture session ID
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing video with transcription and recognition integration: {video_path}")
        
        try:
            # Check if the video file exists
            if not os.path.exists(video_path):
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            # Step 1: Run transcription with speaker diarization
            transcription_result = self.transcription_service.transcribe_video(video_path)
            
            # Step 2: Run face recognition
            face_result = self.facial_recognition.identify_speakers(video_path)
            
            if not face_result.get("success", False):
                logger.error(f"Face recognition failed: {face_result.get('error', 'Unknown error')}")
                return {
                    "success": False, 
                    "error": f"Face recognition failed: {face_result.get('error', 'Unknown error')}",
                    "transcription_result": transcription_result
                }
            
            # Step 3: Integrate transcription with face recognition
            integrated_result = self.integrate_results(transcription_result, face_result)
            
            # Step 4: Store results in the database if provided
            if db_session and capture_id:
                self.store_results(db_session, capture_id, transcription_result, face_result, integrated_result)
            
            # Step 5: Save integrated results to file
            output_file = self.output_dir / f"{Path(video_path).stem}_integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(make_json_serializable(integrated_result), f, indent=2)
            
            logger.info(f"Integrated results saved to {output_file}")
            
            return {
                "success": True,
                "message": "Video processed successfully with transcription and recognition integration",
                "integrated_result": integrated_result,
                "output_file": str(output_file)
            }
            
        except Exception as e:
            logger.exception(f"Error processing video: {str(e)}")
            return {"success": False, "error": f"Error processing video: {str(e)}"}
    
    def integrate_results(self, transcription_result: Dict[str, Any], face_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate transcription and face recognition results.
        
        Args:
            transcription_result: Transcription data
            face_result: Face recognition data
            
        Returns:
            Integrated results
        """
        logger.info("Integrating transcription and face recognition results")
        
        # Create a unified timeline
        timeline = []
        
        # Add face detections to timeline
        if "faces" in face_result:
            for face in face_result["faces"]:
                if "timestamp" in face and "name" in face:
                    timeline.append({
                        "type": "face",
                        "start": face["timestamp"],
                        "end": face["timestamp"] + 1.0,  # Assume 1 second duration
                        "person_name": face["name"],
                        "confidence": face.get("confidence", 0.0),
                        "data": {
                            "box": face.get("box", None),
                            "face_id": face.get("face_id"),
                            "person_id": face.get("person_id")
                        }
                    })
        
        # Add transcription segments to timeline
        if "segments" in transcription_result:
            for segment in transcription_result["segments"]:
                if "start" in segment and "end" in segment and "text" in segment:
                    # Try to find a face detection that matches this segment's time
                    matching_faces = []
                    for face in timeline:
                        if face["type"] == "face" and segment["start"] <= face["start"] <= segment["end"]:
                            matching_faces.append(face)
                    
                    # If we found matching faces, use the most confident one as the speaker
                    speaker = segment.get("speaker", "Unknown")
                    confidence = segment.get("confidence", 0.0)
                    person_id = None
                    
                    if matching_faces:
                        # Sort by confidence
                        matching_faces.sort(key=lambda x: x["confidence"], reverse=True)
                        best_match = matching_faces[0]
                        
                        # Update speaker information
                        speaker = best_match["person_name"]
                        confidence = best_match["confidence"]
                        person_id = best_match["data"].get("person_id")
                    
                    timeline.append({
                        "type": "transcript",
                        "start": segment["start"],
                        "end": segment["end"],
                        "person_name": speaker,
                        "confidence": confidence,
                        "data": {
                            "text": segment["text"],
                            "speaker_id": person_id,
                            "words": segment.get("words", [])
                        }
                    })
        
        # Sort the timeline by start time
        timeline.sort(key=lambda x: x.get("start", 0))
        
        # Find correlations between face detections and transcript segments
        correlations = []
        face_items = [item for item in timeline if item["type"] == "face"]
        transcript_items = [item for item in timeline if item["type"] == "transcript"]
        
        for face_item in face_items:
            for transcript_item in transcript_items:
                # Check for temporal overlap
                if (face_item["start"] <= transcript_item["end"] and 
                    face_item["end"] >= transcript_item["start"]):
                    
                    # Calculate overlap
                    overlap_start = max(face_item["start"], transcript_item["start"])
                    overlap_end = min(face_item["end"], transcript_item["end"])
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    # Only consider significant overlaps
                    if overlap_duration > 0.3:
                        # Check if they refer to the same person
                        same_person = face_item["person_name"] == transcript_item["person_name"]
                        
                        correlations.append({
                            "face_id": face_item["data"].get("face_id"),
                            "transcript_id": transcript_item["data"].get("speaker_id"),
                            "face_name": face_item["person_name"],
                            "transcript_name": transcript_item["person_name"],
                            "start": overlap_start,
                            "end": overlap_end,
                            "confidence": 0.8 if same_person else 0.5,
                            "same_person": same_person
                        })
        
        # Create the integrated result
        integrated_result = {
            "success": True,
            "timeline": timeline,
            "correlations": correlations,
            "transcription": {
                "text": transcription_result.get("text", ""),
                "language": transcription_result.get("language", "en"),
                "duration": transcription_result.get("duration", 0),
                "model": transcription_result.get("model", "")
            },
            "recognition": {
                "faces_count": len([item for item in timeline if item["type"] == "face"]),
                "transcripts_count": len([item for item in timeline if item["type"] == "transcript"]),
                "correlations_count": len(correlations)
            }
        }
        
        return integrated_result
    
    def store_results(self, db_session, capture_id: int, 
                     transcription_result: Dict[str, Any], 
                     face_result: Dict[str, Any], 
                     integrated_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store results in the database.
        
        Args:
            db_session: Database session
            capture_id: Capture session ID
            transcription_result: Transcription data
            face_result: Face recognition data
            integrated_result: Integrated results
            
        Returns:
            Dictionary with storage results
        """
        try:
            from backend.db import models
            
            # Get the capture session
            capture = db_session.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
            if not capture:
                return {"success": False, "error": f"Capture not found: {capture_id}"}
            
            # Store transcription results
            capture.transcription_results = json.dumps(make_json_serializable(transcription_result))
            
            # Store face recognition results
            capture.face_detection_results = json.dumps(make_json_serializable(face_result))
            
            # Store timeline data
            capture.timeline_data = json.dumps(make_json_serializable(integrated_result))
            
            # Store recognition events
            for item in integrated_result["timeline"]:
                event = models.RecognitionEvent(
                    capture_session_id=capture_id,
                    event_type=item["type"],
                    start_time=item["start"],
                    end_time=item["end"],
                    confidence=item["confidence"],
                    person_name=item["person_name"],
                    data=item
                )
                db_session.add(event)
            
            # Commit changes
            db_session.commit()
            
            return {
                "success": True,
                "message": f"Results stored successfully for capture {capture_id}"
            }
            
        except Exception as e:
            db_session.rollback()
            logger.exception(f"Error storing results: {str(e)}")
            return {"success": False, "error": f"Error storing results: {str(e)}"}
    
    def process_existing_data(self, db_session, capture_id: int) -> Dict[str, Any]:
        """
        Process existing transcription and recognition data for a capture session.
        
        Args:
            db_session: Database session
            capture_id: Capture session ID
            
        Returns:
            Dictionary with processing results
        """
        try:
            from backend.db import models
            
            # Get the capture session
            capture = db_session.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
            if not capture:
                return {"success": False, "error": f"Capture not found: {capture_id}"}
            
            # Check if both transcription and recognition results exist
            if not capture.transcription_results:
                return {"success": False, "error": "No transcription results found"}
            
            if not capture.face_detection_results and not capture.recognition_results:
                return {"success": False, "error": "No recognition results found"}
            
            # Parse transcription results
            try:
                transcription_result = json.loads(capture.transcription_results)
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid transcription results format"}
            
            # Parse face recognition results
            face_result = None
            if capture.face_detection_results:
                try:
                    face_result = json.loads(capture.face_detection_results)
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid face detection results format"}
            elif capture.recognition_results:
                try:
                    face_result = json.loads(capture.recognition_results)
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid recognition results format"}
            
            # Integrate results
            integrated_result = self.integrate_results(transcription_result, face_result)
            
            # Store results
            storage_result = self.store_results(
                db_session, capture_id, transcription_result, face_result, integrated_result
            )
            
            if not storage_result.get("success", False):
                return storage_result
            
            return {
                "success": True,
                "message": "Existing data processed successfully",
                "integrated_result": integrated_result
            }
            
        except Exception as e:
            logger.exception(f"Error processing existing data: {str(e)}")
            return {"success": False, "error": f"Error processing existing data: {str(e)}"}
