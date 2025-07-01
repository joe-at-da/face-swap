"""
Multimodal Recognition Service for combining voice and face recognition.

This service integrates voice and facial recognition to improve speaker identification
by combining evidence from both modalities.
"""

import os
import json
import logging
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
        
    def process_video_with_transcription(self, db: Session, video_id: int, transcription_file_path: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Get database session if not provided
            if db is None:
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
                                if ' - ' in timestamp_part:
                                    start_str, end_str = timestamp_part.split(' - ')
                                    start_time = self._parse_timestamp(start_str)
                                    end_time = self._parse_timestamp(end_str)
                                    
                                    # Extract speaker if available
                                    speaker = "Unknown"
                                    if ': ' in text_part:
                                        speaker_parts = text_part.split(': ', 1)
                                        speaker = speaker_parts[0].strip()
                                        text = speaker_parts[1].strip()
                                    else:
                                        text = text_part.strip()
                                    
                                    segment = {
                                        "start": start_time,
                                        "end": end_time,
                                        "text": text,
                                        "speaker": speaker
                                    }
                                    segments.append(segment)
                                    logger.debug(f"Added segment: {segment}")
                            except Exception as e:
                                logger.warning(f"Error parsing line '{line}': {str(e)}")
                    
                    # Create a transcription object with segments
                    transcription = {"segments": segments}
                    
                elif video.transcription_results.startswith('{') and video.transcription_results.endswith('}'):
                    # Try to parse as JSON
                    try:
                        transcription = json.loads(video.transcription_results)
                        logger.info("Successfully parsed transcription as JSON")
                        
                        # Extract segments from the JSON structure
                        if "segments" in transcription:
                            segments = transcription["segments"]
                            logger.info(f"Found {len(segments)} segments in JSON transcription")
                        else:
                            # Try to create segments from the JSON structure
                            segments = []
                            if "results" in transcription:
                                for result in transcription["results"]:
                                    if "alternatives" in result and result["alternatives"]:
                                        alt = result["alternatives"][0]
                                        if "words" in alt:
                                            for word in alt["words"]:
                                                start_time = float(word["start_time"].replace('s', ''))
                                                end_time = float(word["end_time"].replace('s', ''))
                                                segments.append({
                                                    "start": start_time,
                                                    "end": end_time,
                                                    "text": word["word"],
                                                    "speaker": "Unknown"
                                                })
                            transcription["segments"] = segments
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing transcription as JSON: {str(e)}")
                        # Fallback to plain text
                        transcription = {"segments": [], "text": video.transcription_results}
                else:
                    # Handle as plain text
                    logger.info("Processing as plain text transcription")
                    transcription = {"segments": [], "text": video.transcription_results}
            elif isinstance(video.transcription_results, dict):
                # Already a dictionary, just use it
                transcription = video.transcription_results
                if "segments" in transcription:
                    segments = transcription["segments"]
                    logger.info(f"Using {len(segments)} segments from dictionary transcription")
            else:
                # Handle unexpected type
                logger.warning(f"Unexpected transcription type: {type(video.transcription_results)}")
                transcription = {"segments": [], "text": str(video.transcription_results)}
            
            # Check if we have any segments with speakers
            has_speakers = False
            for segment in segments:
                if "speaker" in segment and segment["speaker"] != "Unknown":
                    has_speakers = True
                    break
            
            # Update the video with the processed transcription
            video.transcription_results = json.dumps(transcription)
            db.commit()
            
            # If there are no segments, return an error
            if not segments:
                logger.error("No segments found in transcription")
                return {"success": False, "error": "No segments found in transcription"}
            
            # Create output directory for frames
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
                
                # Skip segments without a valid time range
                if end_time <= start_time:
                    continue
                
                # Determine interval for frame extraction
                duration = end_time - start_time
                if duration < 3.0:
                    # For very short segments, extract just one frame
                    interval = duration
                elif duration < 10.0:
                    # For short segments, extract frames more frequently
                    interval = 2.0  # Frame every 2 seconds
                else:
                    interval = 4.0  # Frame every 3-5 seconds for long segments
                
                # Extract frames at regular intervals
                current_time = start_time
                while current_time < end_time:
                    # Extract frame at current time
                    frame_time = current_time
                    frame_path = os.path.join(output_dir, f"frame_{video_id}_{int(frame_time * 100):08d}.jpg")
                    
                    # Only extract if the frame doesn't already exist
                    if not os.path.exists(frame_path):
                        try:
                            # Use ffmpeg to extract the frame
                            cmd = [
                                "ffmpeg", "-y", "-ss", str(frame_time),
                                "-i", video_path, "-vframes", "1",
                                "-q:v", "2", frame_path
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            logger.info(f"Extracted frame at {frame_time:.2f}s to {frame_path}")
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
                                face_data["segment_speaker"] = speaker
                                face_data["segment_start"] = start_time
                                face_data["segment_end"] = end_time
                                face_data["segment_text"] = segment.get("text", "")
                                
                                # Store face data by time
                                faces_by_time[frame_time] = face_data
                                
                                # Store face data by speaker
                                if speaker not in faces_by_speaker:
                                    faces_by_speaker[speaker] = []
                                faces_by_speaker[speaker].append(face_data)
                                
                                # Create a recognition event
                                recognition_event = {
                                    "time": frame_time,
                                    "speaker": face_data.get("name", "Unknown"),
                                    "confidence": face_data.get("confidence", 0),
                                    "profile_id": face_data.get("profile_id"),
                                    "frame_path": frame_path,
                                    "segment_speaker": speaker,
                                    "segment_text": segment.get("text", "")
                                }
                                recognition_events.append(recognition_event)
                                
                                logger.info(f"Identified speaker in frame at {frame_time:.2f}s: {face_data.get('name', 'Unknown')}")
                        except Exception as e:
                            logger.error(f"Error identifying speaker in frame at {frame_time:.2f}s: {str(e)}")
                    
                    # Move to next interval
                    current_time += interval
            
            # Create correlations between speakers and face profiles
            for speaker, faces in faces_by_speaker.items():
                if not faces:
                    continue
                
                # Find the most common face profile for this speaker
                profile_counts = {}
                for face in faces:
                    profile_id = face.get("profile_id")
                    if profile_id:
                        profile_counts[profile_id] = profile_counts.get(profile_id, 0) + 1
                
                if profile_counts:
                    # Get the most common profile
                    most_common_profile_id = max(profile_counts.items(), key=lambda x: x[1])[0]
                    profile = self.face_profile_service.get_profile_by_id(db, most_common_profile_id)
                    
                    if profile:
                        correlation = {
                            "speaker": speaker,
                            "profile_id": most_common_profile_id,
                            "name": profile.get("name", "Unknown"),
                            "count": profile_counts[most_common_profile_id],
                            "total_frames": len(faces),
                            "confidence": profile_counts[most_common_profile_id] / len(faces)
                        }
                        correlations.append(correlation)
                        speaker_to_face_profile[speaker] = correlation
            
            # Store recognition events in the timeline
            for event in recognition_events:
                if event.get("type") == "face":
                    self.timeline_service.store_face_detection(db, video_id, event)
                elif event.get("type") == "speaker":
                    self.timeline_service.store_speaker_segment(db, video_id, event)
                    
            # Update the timeline data with correlations
            timeline = self.timeline_service.update_timeline_data(db, video_id)
            
            # Update the recognition process status
            recognition_process = db.query(models.RecognitionProcess).filter(
                models.RecognitionProcess.video_id == video_id,
                models.RecognitionProcess.process_type == "multimodal"
            ).first()
            
            if recognition_process:
                recognition_process.status = "completed"
                recognition_process.results = json.dumps({
                    "timeline": timeline,
                    "correlations": correlations,
                    "recognition_events": recognition_events
                })
                db.commit()
            
            return {
                "success": True,
                "video_id": video_id,
                "segments_count": len(segments),
                "recognition_events": len(recognition_events),
                "correlations": correlations,
                "timeline": timeline
            }
            
        except Exception as e:
            logger.exception(f"Error processing video with transcription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse a timestamp string into seconds."""
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
        """Identify speakers in a frame using facial recognition."""
        try:
            logger.info(f"Identifying speaker in frame: {frame_path}")
            
            # Use the facial recognition service to identify speakers
            face_results = self.facial_recognition.identify_speakers(
                image_path=frame_path,
                threshold=threshold
            )
            
            # Check if we got any results
            if not face_results["success"]:
                logger.warning(f"No faces identified in frame: {frame_path}")
                return {"success": False, "error": "No faces identified"}
            
            # Get the best detection (highest confidence)
            detections = face_results.get("detections", [])
            if not detections:
                logger.warning(f"No detections in frame: {frame_path}")
                return {"success": False, "error": "No detections"}
            
            # Sort by confidence (highest first)
            detections.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            best_detection = detections[0]
            
            # Get the profile information
            profile_id = best_detection.get("profile_id")
            if profile_id:
                profile = self.face_profile_service.get_profile_by_id(db, profile_id)
                if profile:
                    best_detection["name"] = profile.get("name", "Unknown")
                    best_detection["profile"] = profile
            
            return {"success": True, "data": best_detection}
            
        except Exception as e:
            logger.exception(f"Error identifying speaker in frame: {str(e)}")
            return {"success": False, "error": str(e)}
