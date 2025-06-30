"""
Multimodal Recognition Service for combining voice and face recognition.

This service integrates voice and facial recognition to improve speaker identification
by combining evidence from both modalities.
"""

import os
import json
import logging
import numpy as np
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.db import models
from backend.db.session import get_db
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.recognition.timeline_service import TimelineService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class MultimodalRecognitionService:
    """Service for combining voice and face recognition for improved speaker identification."""
    
    def __init__(self):
        """Initialize the multimodal recognition service."""
        self.facial_recognition = FacialRecognitionService()
        self.face_profile_service = FaceProfileService()
        self.timeline_service = TimelineService()
        
        # Use Docker container paths as per user preference
        self.base_dir = Path("/app/data")
        self.output_dir = self.base_dir / "multimodal_recognition"
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def start_combined_recognition(self, video_id: int) -> Dict[str, Any]:
        """
        Start the combined recognition process for a Parliament TV video.
        This method handles separate audio and video streams as per user preference.
        
        Args:
            video_id: ID of the video to process
            
        Returns:
            Dictionary with recognition results and status
        """
        try:
            logger.info(f"Starting combined recognition for video {video_id}")
            
            # Get database session
            from backend.db.session import get_db
            from sqlalchemy.orm import Session
            
            db_generator = get_db()
            db: Session = next(db_generator)
            
            # Get the video from the database
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            if not video:
                logger.error(f"Video not found: {video_id}")
                return {"success": False, "error": f"Video not found: {video_id}"}
            
            # Check if the video has metadata with separate audio and video URLs
            metadata = {}
            if video.metadata:
                try:
                    # Use the make_json_serializable function to handle all metadata types
                    # including SQLAlchemy MetaData objects
                    metadata = make_json_serializable(video.metadata)
                    
                    # If metadata is still a string after serialization, parse it as JSON
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError as json_error:
                            logger.error(f"Error parsing metadata JSON string: {str(json_error)}")
                            # If it's not valid JSON, use it as a simple value
                            metadata = {"value": metadata}
                    
                    # Ensure metadata is a dictionary
                    if not isinstance(metadata, dict):
                        metadata = {"value": str(metadata)}
                        
                    logger.info(f"Successfully processed metadata for video {video_id}")
                except Exception as e:
                    logger.error(f"Error processing video metadata: {str(e)}")
                    return {"success": False, "error": f"Error processing video metadata: {str(e)}"}
            
            # Check if we have both audio and video files
            video_path = video.video_path
            audio_path = metadata.get("audio_path") or video.audio_path
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            
            # Create a recognition process record
            recognition_process = models.RecognitionProcess(
                video_id=video_id,
                status="processing",
                start_time=datetime.now(),
                process_metadata={"type": "multimodal"}
            )
            db.add(recognition_process)
            
            # Update the CaptureSession record with recognition status
            video.recognition_status = "processing"
            video.recognition_started_at = datetime.now()
            
            db.commit()
            db.refresh(recognition_process)
            
            # Process transcription first if not already done
            if not video.transcription_results:
                from backend.services.recognition.voice_recognition import VoiceRecognitionService
                voice_service = VoiceRecognitionService()
                
                # Transcribe the audio
                transcription_result = voice_service.transcribe_audio(audio_path)
                if not transcription_result.get("success", False):
                    error_msg = f"Transcription failed: {transcription_result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    recognition_process.status = "failed"
                    recognition_process.end_time = datetime.now()
                    recognition_process.error_message = error_msg
                    
                    # Update the CaptureSession record with failed status
                    video.recognition_status = "failed"
                    video.error_message = error_msg
                    
                    db.commit()
                    return {"success": False, "error": error_msg}
                
                # Save transcription results
                video.transcription_results = json.dumps(transcription_result.get("transcript", {}))
                db.commit()
                
                # Identify speakers in the audio
                speaker_result = voice_service.identify_speakers_in_audio(audio_path)
                if not speaker_result.get("success", False):
                    logger.error(f"Speaker identification failed: {speaker_result.get('error', 'Unknown error')}")
                    # Continue anyway, as we can still do face recognition
                
                # Combine transcription with speaker identification
                if speaker_result.get("success", True):
                    combined_result = voice_service.combine_transcription_with_speakers(
                        transcription_result.get("output_file", ""),
                        speaker_result.get("output_file", "")
                    )
                    if combined_result.get("success", False):
                        video.transcription_results = json.dumps(combined_result.get("combined_results", {}))
                        db.commit()
            
            # Process video with transcription to extract and identify faces
            multimodal_result = self.process_video_with_transcription(db, video_id)
            if not multimodal_result.get("success", False):
                error_msg = f"Multimodal processing failed: {multimodal_result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                recognition_process.status = "failed"
                recognition_process.end_time = datetime.now()
                recognition_process.error_message = error_msg
                
                # Update the CaptureSession record with failed status
                video.recognition_status = "failed"
                video.error_message = error_msg
                
                db.commit()
                return {"success": False, "error": error_msg}
            
            # Update recognition process record
            recognition_process.status = "completed"
            recognition_process.end_time = datetime.now()
            
            # Update the CaptureSession record with recognition status
            video.recognition_status = "completed"
            video.recognition_completed_at = datetime.now()
            
            # Serialize the results with our improved function that handles circular references
            try:
                serialized_results = make_json_serializable(multimodal_result)
                recognition_process.results = json.dumps(serialized_results)
                # Also save the results to the video record
                video.recognition_results = json.dumps(serialized_results)
            except Exception as serialize_error:
                logger.error(f"Error serializing multimodal results: {str(serialize_error)}")
                # Fallback to a simpler representation if serialization fails
                simplified_results = {
                    "message": "Results available but could not be fully serialized",
                    "summary": str(multimodal_result)[:1000]  # Include a truncated summary
                }
                recognition_process.results = json.dumps(simplified_results)
                video.recognition_results = json.dumps(simplified_results)
            
            db.commit()
            
            logger.info(f"Combined recognition completed for video {video_id}")
            return {"success": True, "recognition_id": recognition_process.id, "results": multimodal_result}
            
        except Exception as e:
            error_msg = f"Error in start_combined_recognition: {str(e)}"
            logger.exception(error_msg)
            
            try:
                # Try to update the database records if possible
                db_generator = get_db()
                db: Session = next(db_generator)
                
                # Get the video from the database
                video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
                if video:
                    video.recognition_status = "failed"
                    video.error_message = error_msg
                    
                    # Check if we have a recognition process record
                    recognition_process = db.query(models.RecognitionProcess).filter(
                        models.RecognitionProcess.video_id == video_id,
                        models.RecognitionProcess.status == "processing"
                    ).first()
                    
                    if recognition_process:
                        recognition_process.status = "failed"
                        recognition_process.end_time = datetime.now()
                        recognition_process.error_message = error_msg
                    
                    db.commit()
            except Exception as db_error:
                logger.exception(f"Failed to update database after recognition error: {str(db_error)}")
                
            return {"success": False, "error": error_msg}

    
def process_video_with_transcription(self, video_id: int, transcription_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a video with transcription results
    """
    # Initialize key variables at the beginning to ensure they're always defined
    recognition_events = []
    all_faces = []
    speaker_to_face_profile = {}
    segments = []
    correlations = []
    
    try:
        logger.info(f"Processing video with transcription: {video_id}")
        
        # Get database session
        db_generator = get_db()
        db: Session = next(db_generator)
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return {"success": False, "error": f"Video not found: {video_id}"}
        
        # Check if the video file exists
        video_path = video.video_path
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": f"Video file not found: {video_path}"}
        
        # Check if we have transcription results
        if not video.transcription_results and not transcription_file_path:
            logger.error("Transcription results not found")
            return {"success": False, "error": f"No transcription results found for video {video_id}"}
        
        # If a transcription file path is provided, read from it
        transcription_content = None
        if transcription_file_path:
            try:
                with open(transcription_file_path, 'r') as f:
                    transcription_content = f.read()
                    logger.info(f"Read transcription from file: {transcription_file_path}")
            except Exception as e:
                logger.error(f"Error reading transcription file: {str(e)}")
        
        # If we couldn't find a transcription file, look for the latest transcript in the audio_extracts folder
        if not transcription_content:
            # Look for transcript files matching the pattern transcript_{video_id}_*.txt
            audio_extracts_dir = Path("/app/data/temp/audio_extracts")
            if audio_extracts_dir.exists():
                transcript_files = list(audio_extracts_dir.glob(f"transcript_{video_id}_*.txt"))
                if transcript_files:
                    # Sort by modification time to get the latest
                    latest_transcript = max(transcript_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"Found latest transcript file: {latest_transcript}")
                    try:
                        with open(latest_transcript, 'r') as f:
                            transcription_content = f.read()
                            logger.info(f"Latest transcript content (first 200 chars): {transcription_content[:200]}...")
                    except Exception as e:
                        logger.error(f"Error reading latest transcript file: {str(e)}")
        
        # If we found transcription content in a file, use it instead of the database content
        if transcription_content:
            video.transcription_results = transcription_content
        
        # Handle different formats of transcription results
        transcription = None
        if isinstance(video.transcription_results, str):
            # Log a sample of the transcription string
            sample = video.transcription_results[:200] + '...' if len(video.transcription_results) > 200 else video.transcription_results
            logger.info(f"Transcription results (sample): {sample}")
            
            # First check if the transcription looks like a timestamp format [HH:MM:SS - HH:MM:SS]
            is_timestamp_format = "[" in video.transcription_results and "]" in video.transcription_results
            
            if is_timestamp_format:
                # Process timestamp format
                logger.info("Processing as timestamp format transcription")
                segments = []
                
                # Split by lines
                lines = video.transcription_results.strip().split('\n')
                logger.info(f"Found {len(lines)} lines in transcription")
                
                for i, line in enumerate(lines[:10]):  # Log first 10 lines for debugging
                    logger.info(f"Line {i}: {line}")
                
                for line in lines:
                    # Try to parse timestamp format [HH:MM:SS - HH:MM:SS] Text
                    if line.startswith('[') and ']' in line:
                        try:
                            timestamp_part = line[1:line.index(']')]
                            text_part = line[line.index(']')+1:].strip()
                            
                            # Parse timestamps
                            times = timestamp_part.split(' - ')
                            if len(times) == 2:
                                start_time = self._parse_timestamp(times[0])
                                end_time = self._parse_timestamp(times[1])
                                
                                logger.info(f"Parsed times: start={start_time}, end={end_time}")
                                
                                segments.append({
                                    "start": start_time,
                                    "end": end_time,
                                    "text": text_part,
                                    "speaker": "Unknown",
                                    "speaker_id": "unknown"
                                })
                        except Exception as e:
                            logger.warning(f"Error parsing timestamp line: {line}, error: {str(e)}")
                
                logger.info(f"Parsed {len(segments)} segments from transcription")
                
                if segments:
                    transcription = {"segments": segments}
                    logger.info("Created transcription with parsed segments")
                else:
                    # If parsing failed, fall back to simple format
                    logger.warning("No segments parsed, falling back to simple format")
                    transcription = {
                        "segments": [{
                            "start": 0,
                            "end": 60,  # Assume 60 seconds for the whole content
                            "text": video.transcription_results,
                            "speaker": "Unknown",
                            "speaker_id": "unknown"
                        }]
                    }
            else:
                # Try to parse as JSON
                try:
                    logger.info("Attempting to parse transcription as JSON")
                    
                    # Clean up the JSON string before parsing
                    cleaned_json = video.transcription_results.strip()
                    if cleaned_json.startswith('\ufeff'):  # Remove BOM if present
                        cleaned_json = cleaned_json[1:]
                        
                    # Try to fix common JSON issues
                    if cleaned_json.startswith("'") and cleaned_json.endswith("'"):
                        cleaned_json = cleaned_json[1:-1]
                    if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
                        cleaned_json = cleaned_json[1:-1]
                        
                    # Try parsing the cleaned JSON
                    transcription = json.loads(cleaned_json)
                    logger.info("Successfully parsed transcription as JSON")
                except json.JSONDecodeError as json_err:
                    logger.error(f"Error loading transcription: {str(json_err)}")
                    
                    # Create a simple structure with the text
                    logger.info("JSON parsing failed, using simple format")
                    transcription = {
                        "segments": [{
                            "start": 0,
                            "end": 60,  # Assume 60 seconds for the whole content
                            "text": video.transcription_results,
                            "speaker": "Unknown",
                            "speaker_id": "unknown"
                        }]
                    }
        elif isinstance(video.transcription_results, dict):
            # If it's already a dict, use it directly
            transcription = video.transcription_results
        else:
            # Handle unexpected type
            logger.warning(f"Unexpected transcription type: {type(video.transcription_results)}")
            transcription = {"segments": [], "text": str(video.transcription_results)}
        
        # Ensure transcription is a dictionary
        if not isinstance(transcription, dict):
            transcription = {"segments": [], "text": str(transcription)}
        
        # Get segments or create an empty list
        segments = transcription.get("segments", [])
        if not segments and isinstance(transcription.get("text"), str):
            # If there are no segments but there is text, create a simple segment
            segments = [{
                "start": 0,
                "end": 60,  # Assume 60 seconds for the whole content
                "text": transcription.get("text"),
                "speaker": "Unknown",
                "speaker_id": "unknown"
            }]
        
        # Check if segments have speaker information
        has_speakers = False
        for segment in segments:
            if segment.get("speaker") or segment.get("speaker_id") or segment.get("speaker_name"):
                has_speakers = True
                break
        
        # Update the video with the processed transcription
        video.transcription_results = json.dumps(transcription)
        db.commit()
        
        # If there are no segments, return an error
        if not segments:
            logger.error("No segments found in transcription")
            return {"success": False, "error": "No segments found in transcription"}
        
        # Extract frames for each segment
        output_dir = os.path.join(self.output_dir, f"video_{video_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract faces from speaker segments
        faces_by_speaker = {}
        faces_by_time = {}
        all_faces = []
        
        # Process each segment to extract faces
        for segment in segments:
            speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            
            if end_time <= start_time:
                continue
            
            # Calculate segment duration and adjust sampling rate based on duration
            duration = end_time - start_time
            
            # For short segments (< 5s), extract 1-2 frames
            # For medium segments (5-15s), extract a frame every 2-3 seconds
            # For long segments (> 15s), extract a frame every 3-5 seconds
            if duration < 5:
                interval = max(1.0, duration / 2)  # 1-2 frames for short segments
            elif duration < 15:
                interval = 2.5  # Frame every 2-3 seconds for medium segments
            else:
                interval = 4.0  # Frame every 3-5 seconds for long segments
            
            # Extract frames at regular intervals
            current_time = start_time
            while current_time < end_time:
                # Extract frame at current time
                frame_time = current_time
                frame_path = os.path.join(output_dir, f"frame_{video_id}_{int(frame_time * 100):08d}.jpg")
                
                # Skip if frame already exists
                if not os.path.exists(frame_path):
                    try:
                        # Use ffmpeg to extract the frame
                        ffmpeg_cmd = [
                            "ffmpeg", "-y", "-ss", str(frame_time), "-i", video_path,
                            "-vframes", "1", "-q:v", "2", frame_path
                        ]
                        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        logger.info(f"Extracted frame at {frame_time:.2f}s: {frame_path}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Error extracting frame at {frame_time:.2f}s: {str(e)}")
                        continue
                
                # Identify speaker in the frame
                if os.path.exists(frame_path):
                    try:
                        face_result = self.identify_speaker_in_frame(db, frame_path)
                        if face_result["success"]:
                            face_data = face_result["data"]
                            face_data["frame_path"] = frame_path
                            face_data["frame_time"] = frame_time
                            face_data["segment_text"] = segment.get("text", "")
                            face_data["segment_speaker"] = speaker
                            
                            # Add to all faces list
                            all_faces.append(face_data)
                            
                            # Add to faces by time
                            time_key = int(frame_time)
                            if time_key not in faces_by_time:
                                faces_by_time[time_key] = []
                            faces_by_time[time_key].append(face_data)
                            
                            # Add to faces by speaker
                            if speaker not in faces_by_speaker:
                                faces_by_speaker[speaker] = []
                            faces_by_speaker[speaker].append(face_data)
                            
                            # Create a recognition event
                            recognition_event = {
                                "time": frame_time,
                                "speaker": face_data.get("name", "Unknown"),
                                "confidence": face_data.get("confidence", 0),
                                "text": segment.get("text", ""),
                                "face_profile_id": face_data.get("face_profile_id"),
                                "frame_path": frame_path
                            }
                            recognition_events.append(recognition_event)
                            
                            logger.info(f"Identified speaker in frame at {frame_time:.2f}s: {face_data.get('name', 'Unknown')}")
                    except Exception as e:
                        logger.error(f"Error identifying speaker in frame at {frame_time:.2f}s: {str(e)}")
                
                # Move to next interval
                current_time += interval
        
        # Create correlations between speakers and face profiles
        for speaker, faces in faces_by_speaker.items():
            # Count occurrences of each face profile
            profile_counts = {}
            for face in faces:
                profile_id = face.get("face_profile_id")
                if profile_id:
                    if profile_id not in profile_counts:
                        profile_counts[profile_id] = 0
                    profile_counts[profile_id] += 1
            
            # Find the most common face profile for this speaker
            if profile_counts:
                most_common_profile_id = max(profile_counts.items(), key=lambda x: x[1])[0]
                most_common_count = profile_counts[most_common_profile_id]
                total_faces = len(faces)
                confidence = most_common_count / total_faces if total_faces > 0 else 0
                
                # Get the face profile
                face_profile = self.face_profile_service.get_face_profile(db, most_common_profile_id)
                if face_profile:
                    speaker_to_face_profile[speaker] = {
                        "face_profile_id": most_common_profile_id,
                        "name": face_profile.get("name", "Unknown"),
                        "confidence": confidence,
                        "count": most_common_count,
                        "total": total_faces
                    }
                    
                    # Add to correlations
                    correlations.append({
                        "speaker": speaker,
                        "face_profile_id": most_common_profile_id,
                        "name": face_profile.get("name", "Unknown"),
                        "confidence": confidence,
                        "count": most_common_count,
                        "total": total_faces
                    })
        
        # Create a timeline of recognition events
        timeline = self.timeline_service.create_timeline(recognition_events)
        
        # Update the video with recognition results
        recognition_results = {
            "timeline": timeline,
            "correlations": correlations,
            "speaker_to_face_profile": speaker_to_face_profile,
            "faces_count": len(all_faces),
            "segments_count": len(segments),
            "has_speakers": has_speakers
        }
        
        # Update the video in the database
        video.recognition_results = json.dumps(recognition_results)
        video.recognition_completed_at = datetime.now()
        video.recognition_status = "completed"
        db.commit()
        
        return {
            "success": True,
            "video_id": video_id,
            "timeline": timeline,
            "correlations": correlations,
            "faces_count": len(all_faces),
            "segments_count": len(segments)
        }
    
    except Exception as e:
        logger.exception(f"Error processing video with transcription: {str(e)}")
        
        # Update the video with error status
        try:
            db_generator = get_db()
            db: Session = next(db_generator)
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            if video:
                video.recognition_status = "error"
                video.error_message = str(e)
                db.commit()
        except Exception as db_err:
            logger.error(f"Error updating video status: {str(db_err)}")
        
        return {"success": False, "error": str(e)}


    def _parse_timestamp(self, timestamp: str) -> float:
        """
        Parse a timestamp in HH:MM:SS format to seconds.
        
        Args:
            timestamp: String in HH:MM:SS format
            
        Returns:
            Float representing seconds
        """
        try:
            parts = timestamp.split(':') 
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(float, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS
                minutes, seconds = map(float, parts)
                return minutes * 60 + seconds
            else:  # Just seconds
                return float(timestamp)
        except Exception as e:
            logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
            return 0.0
    
    def identify_speaker_in_frame(self, db: Session, frame_path: str, threshold: float = 0.6) -> Dict[str, Any]:
        """
        Identify a speaker in a video frame using facial recognition.
        
        Args:
            db: Database session
            frame_path: Path to the frame image
            threshold: Confidence threshold for face recognition
            
        Returns:
            Dictionary with identification results
        """
        try:
            logger.info(f"Identifying speaker in frame: {frame_path}")
            
            # Check if the frame file exists
            if not os.path.exists(frame_path):
                logger.error(f"Frame file not found: {frame_path}")
                return {"success": False, "error": f"Frame file not found: {frame_path}"}
            
            # Detect and identify faces in the frame using identify_speakers method
            face_results = self.facial_recognition.identify_speakers(
                video_path=frame_path,  # Using the frame path as the video path
                db_session=db,
                output_file=None,  # No output file needed
                store_unidentified=False,  # Don't store unidentified faces
                export_to_supabase=False  # Don't export to Supabase
            )
            
            if not face_results.get("success", False):
                logger.error(f"Error identifying faces: {face_results.get('error', 'Unknown error')}")
                return {"success": False, "error": f"Error identifying faces: {face_results.get('error', 'Unknown error')}"}
            
            # The identify_speakers method returns results in the 'results' key
            # Let's extract the detections from the results
            results_data = face_results.get("results", {})
            
            # Check if results_data is a dictionary or a list
            if isinstance(results_data, dict):
                # If it's a dictionary, look for detections key
                detections = results_data.get("detections", [])
            elif isinstance(results_data, list):
                # If it's a list, it might be the detections directly
                detections = results_data
            else:
                # If it's neither, use an empty list
                detections = []
            
            # If no detections found, return empty result
            if len(detections) == 0:
                logger.info("No faces detected in the frame")
                return {"success": True, "faces_found": 0}
            
            # Get the detection with the highest confidence
            best_detection = None
            best_confidence = 0.0
            
            for detection in detections:
                confidence = detection.get("confidence", 0.0)
                if confidence > best_confidence:
                    best_detection = detection
                    best_confidence = confidence
            
            # Get the speaker information from the detection
            speaker_id = best_detection.get("person_id", "unknown")
            speaker_name = best_detection.get("name", "Unknown")
            
            # Create a simplified face profile structure
            face_profile = {
                "id": speaker_id,
                "name": speaker_name,
                "confidence": best_confidence
            }
            
            # Check if there's a linked voice profile in the database
            voice_profile = None
            if speaker_id and speaker_id != "unknown":
                # Try to find a face profile in the database
                face_profile_obj = db.query(models.FaceProfile).filter(
                    models.FaceProfile.id == speaker_id
                ).first()
                
                if face_profile_obj and face_profile_obj.voice_profile_id:
                    voice_profile = db.query(models.VoiceProfile).filter(
                        models.VoiceProfile.id == face_profile_obj.voice_profile_id
                    ).first()
            
            return {
                "success": True,
                "faces_found": len(detections),
                "face_profile": face_profile,
                "voice_profile": voice_profile.to_dict() if voice_profile else None,
                "confidence_score": best_confidence
            }
            
        except Exception as e:
            logger.exception(f"Error identifying speaker in frame: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def calculate_speaker_confidence(self, face_data: Dict[str, Any], voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence score for speaker identification based on both face and voice recognition.
        
        Args:
            face_data: Face recognition data including confidence scores
            voice_data: Voice recognition data including confidence scores
            
        Returns:
            Dictionary with combined confidence scores and metadata
        """
        try:
            # Extract basic confidence scores
            face_confidence = face_data.get("confidence", 0.0)
            voice_confidence = voice_data.get("confidence", 0.0)
            
            # Extract profile information
            face_profile = face_data.get("face_profile", {})
            voice_profile = voice_data.get("voice_profile", {})
            
            # Extract names for comparison
            face_name = face_profile.get("name", "").lower() if face_profile else ""
            voice_name = voice_profile.get("name", "").lower() if voice_profile else ""
            
            # Calculate base confidence scores
            base_confidence = {
                "face": face_confidence,
                "voice": voice_confidence,
                "combined": 0.0  # Will be calculated below
            }
            
            # Calculate name similarity score (0-1)
            name_similarity = 0.0
            if face_name and voice_name:
                # Simple string similarity
                if face_name == voice_name:
                    name_similarity = 1.0
                elif face_name in voice_name or voice_name in face_name:
                    name_similarity = 0.8
                else:
                    # Simple character overlap similarity
                    common_chars = sum(1 for c in face_name if c in voice_name)
                    name_similarity = common_chars / max(len(face_name), len(voice_name)) if max(len(face_name), len(voice_name)) > 0 else 0.0
            
            # Check for explicit links between profiles
            face_profile_id = face_profile.get("id") if face_profile else None
            voice_profile_id = voice_profile.get("id") if voice_profile else None
            
            face_linked_voice_id = face_profile.get("voice_profile_id") if face_profile else None
            voice_linked_face_id = voice_profile.get("face_profile_id") if voice_profile else None
            
            explicit_link = (face_linked_voice_id == voice_profile_id) or (voice_linked_face_id == face_profile_id)
            
            # Calculate confidence boosters/penalties
            boosters = {
                "explicit_link": 0.2 if explicit_link else 0.0,
                "name_match": 0.15 * name_similarity,
                "high_individual_confidence": 0.1 if (face_confidence > 0.8 and voice_confidence > 0.8) else 0.0
            }
            
            # Calculate penalties
            penalties = {
                "name_mismatch": 0.2 if (face_name and voice_name and name_similarity < 0.3) else 0.0,
                "low_face_confidence": 0.1 if face_confidence < 0.5 else 0.0,
                "low_voice_confidence": 0.1 if voice_confidence < 0.5 else 0.0
            }
            
            # Calculate total boosters and penalties
            total_boosters = sum(boosters.values())
            total_penalties = sum(penalties.values())
            
            # Calculate base combined confidence (weighted average)
            if face_confidence > 0 or voice_confidence > 0:
                # If we have both face and voice, weight them 60/40
                if face_confidence > 0 and voice_confidence > 0:
                    base_combined = 0.6 * face_confidence + 0.4 * voice_confidence
                # If we only have one, use that one
                else:
                    base_combined = face_confidence if face_confidence > 0 else voice_confidence
            else:
                base_combined = 0.0
            
            # Apply boosters and penalties to get final confidence
            final_confidence = min(1.0, max(0.0, base_combined + total_boosters - total_penalties))
            
            # Determine confidence level category
            confidence_level = "unknown"
            if final_confidence >= 0.9:
                confidence_level = "very_high"
            elif final_confidence >= 0.75:
                confidence_level = "high"
            elif final_confidence >= 0.6:
                confidence_level = "medium"
            elif final_confidence >= 0.4:
                confidence_level = "low"
            else:
                confidence_level = "very_low"
            
            # Create detailed result
            result = {
                "success": True,
                "confidence": {
                    "face": face_confidence,
                    "voice": voice_confidence,
                    "base_combined": base_combined,
                    "final": final_confidence,
                    "level": confidence_level
                },
                "factors": {
                    "boosters": boosters,
                    "penalties": penalties
                },
                "metadata": {
                    "name_similarity": name_similarity,
                    "explicit_link": explicit_link,
                    "face_name": face_name,
                    "voice_name": voice_name
                }
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Error calculating speaker confidence: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "confidence": {
                    "face": face_data.get("confidence", 0.0),
                    "voice": voice_data.get("confidence", 0.0),
                    "final": max(face_data.get("confidence", 0.0), voice_data.get("confidence", 0.0))
                }
            }
    def get_recognition_status(self, video_id: int) -> Dict[str, Any]:
        """
        Get the status of the recognition process for a video.
        
        Args:
            video_id: ID of the video to check
            
        Returns:
            Dictionary with recognition status information
        """
        # Added comment to trigger file reload
        try:
            # Get database session
            from backend.db.session import get_db
            from sqlalchemy.orm import Session
            
            db_generator = get_db()
            db: Session = next(db_generator)
            
            # Get the video from the database
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            
            if not video:
                logger.error(f"Video not found: {video_id}")
                return {"success": False, "error": f"Video not found: {video_id}"}
            
            return {
                "success": True,
                "status": {
                    "status": video.recognition_status or "not_started",
                    "video_id": video_id,
                    "started_at": video.recognition_started_at,
                    "completed_at": video.recognition_completed_at,
                    "has_results": bool(video.recognition_results),
                    "error_message": video.error_message if hasattr(video, 'error_message') else None
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting recognition status: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def get_recognition_results(self, video_id: int) -> Dict[str, Any]:
        """
        Get the recognition results for a video.
        
        Args:
            video_id: ID of the video to get results for
            
        Returns:
            Dictionary with recognition results
        """
        try:
            # Get database session
            from backend.db.session import get_db
            from sqlalchemy.orm import Session
            
            db_generator = get_db()
            db: Session = next(db_generator)
            
            # Get the video from the database
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            
            if not video:
                logger.error(f"Video not found: {video_id}")
                return {"success": False, "error": f"Video not found: {video_id}"}
                
            # Check if recognition is completed
            if video.recognition_status != "completed":
                return {
                    "success": False, 
                    "error": f"Recognition not completed for video {video_id}. Current status: {video.recognition_status or 'not_started'}"
                }
                
            # Get recognition results
            results = {}
            if video.recognition_results:
                try:
                    if isinstance(video.recognition_results, str):
                        results = json.loads(video.recognition_results)
                    else:
                        results = video.recognition_results
                except json.JSONDecodeError:
                    return {"success": False, "error": f"Invalid recognition results format for video {video_id}"}
                    
            # Get recognition process records
            recognition_processes = db.query(models.RecognitionProcess).filter(
                models.RecognitionProcess.video_id == video_id
            ).all()
            
            # Combine all results
            combined_results = {
                "video_id": video_id,
                "recognition_status": video.recognition_status,
                "started_at": video.recognition_started_at,
                "completed_at": video.recognition_completed_at,
                "results": results,
                "processes": [
                    {
                        "id": process.id,
                        "status": process.status,
                        "start_time": process.start_time,
                        "end_time": process.end_time,
                        "process_type": process.process_metadata.get("type", "unknown") if process.process_metadata else "unknown",
                        "error_message": process.error_message if hasattr(process, 'error_message') else None
                    } for process in recognition_processes
                ]
            }
            
            return {"success": True, "results": combined_results}
        except Exception as e:
            logger.exception(f"Error in get_recognition_results: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def combine_recognition_results(self, voice_results: Dict[str, Any], face_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine voice and face recognition results for improved speaker identification.
        
        Args:
            voice_results: Results from voice recognition
            face_results: Results from face recognition
            
        Returns:
            Combined recognition results
        """
        try:
            logger.info("Combining voice and face recognition results")
            
            # Check if both results are valid
            if not voice_results.get("success", False) or not face_results.get("success", False):
                logger.warning("One or both recognition results are invalid")
                
                # Return the successful result if only one failed
                if voice_results.get("success", False):
                    return {
                        "success": True,
                        "source": "voice",
                        "confidence": voice_results.get("confidence_score", 0.0),
                        "profile": voice_results.get("profile", {}),
                        "message": "Face recognition failed, using voice recognition only"
                    }
                elif face_results.get("success", False):
                    return {
                        "success": True,
                        "source": "face",
                        "confidence": face_results.get("confidence_score", 0.0),
                        "profile": face_results.get("face_profile", {}),
                        "message": "Voice recognition failed, using face recognition only"
                    }
                else:
                    return {"success": False, "error": "Both recognition methods failed"}
            
            # Extract profile information
            voice_profile = voice_results.get("profile", {})
            face_profile = face_results.get("face_profile", {})
            voice_profile_id = voice_profile.get("id")
            face_profile_id = face_profile.get("id")
            
            # Extract linked profile IDs
            voice_linked_face_id = voice_profile.get("face_profile_id")
            face_linked_voice_id = face_results.get("voice_profile", {}).get("id") if face_results.get("voice_profile") else None
            
            # Extract names for comparison
            voice_name = voice_profile.get("name", "").lower()
            face_name = face_profile.get("name", "").lower()
            
            # Extract confidence scores
            voice_confidence = voice_results.get("confidence_score", 0.0)
            face_confidence = face_results.get("confidence_score", 0.0)
            
            # Calculate name similarity score (0-1)
            name_similarity = 0.0
            if voice_name and face_name:
                # Simple string similarity
                if voice_name == face_name:
                    name_similarity = 1.0
                elif voice_name in face_name or face_name in voice_name:
                    name_similarity = 0.8
                else:
                    # Calculate Levenshtein distance-based similarity
                    try:
                        import Levenshtein
                        distance = Levenshtein.distance(voice_name, face_name)
                        max_len = max(len(voice_name), len(face_name))
                        name_similarity = 1.0 - (distance / max_len) if max_len > 0 else 0.0
                    except ImportError:
                        # Fallback if Levenshtein is not available
                        common_chars = sum(1 for c in voice_name if c in face_name)
                        name_similarity = common_chars / max(len(voice_name), len(face_name)) if max(len(voice_name), len(face_name)) > 0 else 0.0
            
            # Check if profiles are explicitly linked
            explicit_link = (voice_linked_face_id == face_profile_id) or (face_linked_voice_id == voice_profile_id)
            
            # Determine if they are the same person based on multiple factors
            same_person = False
            combined_confidence = 0.0
            reason = ""
            
            if explicit_link:
                # Explicit link between profiles
                same_person = True
                combined_confidence = 0.7 * max(voice_confidence, face_confidence) + 0.3 * min(voice_confidence, face_confidence)
                reason = "Explicit link between voice and face profiles"
            elif name_similarity > 0.8:
                # High name similarity
                same_person = True
                combined_confidence = 0.6 * max(voice_confidence, face_confidence) + 0.4 * min(voice_confidence, face_confidence)
                reason = f"High name similarity ({name_similarity:.2f})"
            elif name_similarity > 0.5 and (voice_confidence > 0.7 and face_confidence > 0.7):
                # Moderate name similarity but high confidence in both
                same_person = True
                combined_confidence = 0.5 * voice_confidence + 0.5 * face_confidence
                reason = f"Moderate name similarity ({name_similarity:.2f}) with high confidence in both"
            else:
                # Different people or uncertain
                same_person = False
                combined_confidence = max(voice_confidence, face_confidence)
                reason = "Different people identified by voice and face recognition"
            
            if same_person:
                logger.info(f"Voice and face recognition agree on the speaker: {reason}")
                
                # Merge profile information
                merged_profile = {}
                
                # Start with the profile that has higher confidence
                if voice_confidence >= face_confidence:
                    merged_profile.update(voice_profile)
                    # Add face information if available
                    if face_profile:
                        merged_profile["face_profile_id"] = face_profile_id
                        merged_profile["face_image_url"] = face_profile.get("image_url")
                        merged_profile["face_confidence"] = face_confidence
                else:
                    merged_profile.update(face_profile)
                    # Add voice information if available
                    if voice_profile:
                        merged_profile["voice_profile_id"] = voice_profile_id
                        merged_profile["voice_confidence"] = voice_confidence
                
                return {
                    "success": True,
                    "source": "multimodal",
                    "confidence": combined_confidence,
                    "profile": merged_profile,
                    "voice_confidence": voice_confidence,
                    "face_confidence": face_confidence,
                    "name_similarity": name_similarity,
                    "reason": reason
                }
            
            # If they identified different people, use the one with higher confidence
            if voice_confidence > face_confidence:
                logger.info(f"Using voice recognition result (higher confidence): {voice_confidence:.2f} vs {face_confidence:.2f}")
                return {
                    "success": True,
                    "source": "voice",
                    "confidence": voice_confidence,
                    "profile": voice_profile,
                    "alternative_profile": face_profile,
                    "name_similarity": name_similarity,
                    "reason": "Voice recognition has higher confidence"
                }
            else:
                logger.info(f"Using face recognition result (higher confidence): {face_confidence:.2f} vs {voice_confidence:.2f}")
                return {
                    "success": True,
                    "source": "face",
                    "confidence": face_confidence,
                    "profile": face_profile,
                    "alternative_profile": voice_profile,
                    "name_similarity": name_similarity,
                    "reason": "Face recognition has higher confidence"
                }
            
        except Exception as e:
            logger.exception(f"Error combining recognition results: {str(e)}")
            return {"success": False, "error": str(e)}
