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

    
    def process_video_with_transcription(self, db: Session, video_id: int) -> Dict[str, Any]:
        """
        Process a video with existing transcription to extract faces and link them to speakers.
        
        Args:
            db: Database session
            video_id: ID of the video to process
            
        Returns:
            Dictionary with processing results
        """
        # Initialize key variables at the beginning to ensure they're always defined
        recognition_events = []
        all_faces = []
        speaker_to_face_profile = {}
        segments = []
        correlations = []
        try:
            logger.info(f"Processing video with transcription: {video_id}")
            
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
            
            # Check if transcription with speaker diarization exists
            if not video.transcription_results:
                logger.error("Transcription results not found")
                return {"success": False, "error": "Transcription results not found"}
            
            # Parse transcription results
            try:
                # Add debug logging to see the raw transcription results
                logger.info(f"Processing transcription for video {video_id}")
                logger.info(f"Transcription type: {type(video.transcription_results)}")
                
                # Check if transcription results exists in a file
                transcript_path = None
                if hasattr(video, 'transcription_path') and video.transcription_path:
                    transcript_path = video.transcription_path
                    logger.info(f"Found transcription path: {transcript_path}")
                    if os.path.exists(transcript_path):
                        logger.info(f"Reading transcription from file: {transcript_path}")
                        with open(transcript_path, 'r') as f:
                            file_content = f.read()
                            logger.info(f"Transcription file content (first 200 chars): {file_content[:200]}...")
                
                # Handle different formats of transcription results
                if isinstance(video.transcription_results, str):
                    # Log a sample of the transcription string
                    sample = video.transcription_results[:200] + '...' if len(video.transcription_results) > 200 else video.transcription_results
                    logger.info(f"Transcription results (sample): {sample}")
                    
                    try:
                        # First try to parse as JSON
                        logger.info("Attempting to parse transcription as JSON")
                        
                        # Clean up the JSON string before parsing
                        # Remove any BOM characters or other potential issues
                        cleaned_json = video.transcription_results.strip()
                        if cleaned_json.startswith('\ufeff'):  # Remove BOM if present
                            cleaned_json = cleaned_json[1:]
                            
                        # Try to fix common JSON issues
                        if cleaned_json.startswith("'") and cleaned_json.endswith("'"):
                            cleaned_json = cleaned_json[1:-1]
                        if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
                            cleaned_json = cleaned_json[1:-1]
                            
                        # Log the cleaned JSON for debugging
                        logger.info(f"Cleaned JSON (first 100 chars): {cleaned_json[:100]}...")
                        
                        # Try parsing the cleaned JSON
                        transcription = json.loads(cleaned_json)
                        logger.info("Successfully parsed transcription as JSON")
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Error loading transcription: {str(json_err)}")
                        
                        # Try to fix common JSON issues and retry
                        try:
                            # Sometimes the JSON might have single quotes instead of double quotes
                            import ast
                            logger.info("Attempting to parse with ast.literal_eval")
                            transcription = ast.literal_eval(video.transcription_results)
                            logger.info("Successfully parsed transcription with ast.literal_eval")
                        except Exception as ast_err:
                            logger.error(f"Error parsing with ast: {str(ast_err)}")
                            # Continue with the fallback parsing
                        
                        # Check if it's a plain text format with timestamps [HH:MM:SS - HH:MM:SS]
                        if "[" in video.transcription_results and "]" in video.transcription_results:
                            logger.info("Detected plain text format with timestamps, parsing segments")
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
                            # If it's not timestamp format, create a simple structure with the text
                            logger.info("No timestamp format detected, using simple format")
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
                    # If it's already a dict or other object, use it directly
                    transcription = video.transcription_results
                
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
                
                if not has_speakers and segments:
                    # If no speaker information, add default speaker to all segments
                    logger.warning("No speaker information found in transcription, using default")
                    for segment in segments:
                        segment["speaker"] = "Unknown"
                        segment["speaker_id"] = "unknown"
                    has_speakers = True
                
                if not segments:
                    logger.error("No segments found in transcription")
                    return {"success": False, "error": "No segments found in transcription"}
                
            except Exception as e:
                logger.error(f"Error parsing transcription: {str(e)}")
                return {"success": False, "error": f"Error parsing transcription: {str(e)}"}
            
            # Create output directory for this video
            output_dir = str(self.output_dir / str(video_id))
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
                
                # Extract frames at calculated intervals within this segment
                for timestamp in np.arange(start_time, end_time, interval):
                    # Extract frame at this timestamp
                    frame_filename = f"frame_{video_id}_{timestamp:.2f}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    
                    # Extract the frame using ffmpeg if it doesn't exist
                    if not os.path.exists(frame_path):
                        try:
                            cmd = [
                                "ffmpeg",
                                "-ss", str(timestamp),
                                "-i", video_path,
                                "-vframes", "1",
                                "-q:v", "2",
                                frame_path,
                                "-y"
                            ]
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        except subprocess.CalledProcessError as e:
                            logger.error(f"Error extracting frame at {timestamp}: {str(e)}")
                            continue
                    
                    # Identify speaker in this frame
                    result = self.identify_speaker_in_frame(db, frame_path)
                    
                    if result.get("success", False):
                        # Store the face detection result
                        face_profile = result.get("face_profile", {})
                        confidence = result.get("confidence_score", 0.0)
                        
                        # Create face detection entry
                        face_detection = {
                            "timestamp": timestamp,
                            "frame_path": frame_path,
                            "frame_url": f"/api/v1/media/frames/{os.path.basename(frame_path)}",
                            "face_profile": face_profile,
                            "confidence": confidence,
                            "speaker": speaker,
                            "text": segment.get("text", ""),
                            "segment_id": segment.get("id"),
                            "segment_start": start_time,
                            "segment_end": end_time
                        }
                        
                        # Add to all faces list
                        all_faces.append(face_detection)
                        
                        # Add to faces by speaker
                        if speaker not in faces_by_speaker:
                            faces_by_speaker[speaker] = []
                        
                        faces_by_speaker[speaker].append(face_detection)
                        
                        # Add to faces by time
                        faces_by_time[timestamp] = face_detection
            
            # Create a timeline of speakers with face detections
            timeline = []
            for timestamp, data in sorted(faces_by_time.items()):
                timeline.append({
                    "timestamp": timestamp,
                    "speaker": data["speaker"],
                    "face_profile": data["face_profile"],
                    "confidence": data["confidence"],
                    "frame_path": data["frame_path"],
                    "frame_url": data["frame_url"],
                    "text": data["text"]
                })
            
            # Create a mapping of speakers to face profiles using a more sophisticated algorithm
            speaker_to_face_profile = {}
            for speaker, faces in faces_by_speaker.items():
                if not faces:
                    continue
                
                # Group faces by profile ID
                profiles = {}
                for face in faces:
                    profile_id = face.get("face_profile", {}).get("id")
                    if not profile_id:
                        continue
                    
                    if profile_id not in profiles:
                        profiles[profile_id] = {
                            "profile": face.get("face_profile", {}),
                            "count": 0,
                            "total_confidence": 0.0,
                            "frames": [],
                            "timestamps": []
                        }
                    
                    profiles[profile_id]["count"] += 1
                    profiles[profile_id]["total_confidence"] += face.get("confidence", 0.0)
                    profiles[profile_id]["frames"].append(face.get("frame_path"))
                    profiles[profile_id]["timestamps"].append(face.get("timestamp"))
                
                # Calculate weighted scores for each profile
                for profile_id, data in profiles.items():
                    # Calculate average confidence
                    avg_confidence = data["total_confidence"] / data["count"] if data["count"] > 0 else 0.0
                    
                    # Calculate temporal consistency (how well distributed the detections are)
                    timestamps = sorted(data["timestamps"])
                    if len(timestamps) > 1:
                        time_span = max(timestamps) - min(timestamps)
                        time_consistency = min(1.0, time_span / 60.0)  # Normalize to max of 1.0 for spans of 60s or more
                    else:
                        time_consistency = 0.0
                    
                    # Calculate final weighted score
                    # Weight: 60% count, 30% confidence, 10% temporal consistency
                    data["weighted_score"] = (
                        0.6 * (data["count"] / len(faces)) + 
                        0.3 * avg_confidence + 
                        0.1 * time_consistency
                    )
                    data["avg_confidence"] = avg_confidence
                    data["time_consistency"] = time_consistency
                
                # Find the profile with the highest weighted score
                best_profile_id = None
                best_score = 0.0
                
                for profile_id, data in profiles.items():
                    if data["weighted_score"] > best_score:
                        best_profile_id = profile_id
                        best_score = data["weighted_score"]
                
                if best_profile_id:
                    best_data = profiles[best_profile_id]
                    speaker_to_face_profile[speaker] = {
                        "profile": best_data["profile"],
                        "count": best_data["count"],
                        "confidence": best_data["avg_confidence"],
                        "time_consistency": best_data["time_consistency"],
                        "weighted_score": best_data["weighted_score"],
                        "best_frames": best_data["frames"][:5]  # Include up to 5 best frames
                    }
            
            # Create voice recognition data from transcription segments
            voice_segments = []
            for segment in segments:
                speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                voice_segment = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "speaker": speaker,
                    "text": segment.get("text", ""),
                    "confidence": segment.get("confidence", 0.5),
                    "segment_id": segment.get("id")
                }
                
                # Add face profile information if available
                if speaker in speaker_to_face_profile:
                    voice_segment["face_profile"] = speaker_to_face_profile[speaker]["profile"]
                    voice_segment["face_confidence"] = speaker_to_face_profile[speaker]["confidence"]
                
                voice_segments.append(voice_segment)
            
            # Update the transcription segments with face profile information
            for segment in segments:
                speaker = segment.get("speaker", segment.get("speaker_name", f"Speaker {segment.get('speaker_id', 'Unknown')}"))
                
                if speaker in speaker_to_face_profile:
                    segment["face_profile"] = speaker_to_face_profile[speaker]["profile"]
                    segment["face_confidence"] = speaker_to_face_profile[speaker]["confidence"]
                    segment["face_detection_count"] = speaker_to_face_profile[speaker]["count"]
            
            # Create integrated recognition results
            integrated_results = {
                "faces": all_faces,  # All individual face detections
                "voices": voice_segments,  # All voice segments with speaker info
                "speaker_face_mapping": speaker_to_face_profile,  # Mapping of speakers to their best face profile
                "timeline": timeline,  # Timeline of face detections
                "transcription": transcription,  # Original transcription with added face info
                "metadata": {
                    "video_id": video_id,
                    "processed_at": datetime.now().isoformat(),
                    "faces_count": len(all_faces),
                    "speakers_count": len(speaker_to_face_profile),
                    "segments_count": len(segments)
                }
            }
            
            # Store face detections in the timeline service
            for face in all_faces:
                face_detection = {
                    "timestamp": face["timestamp"],
                    "confidence": face["confidence"],
                    "name": face["face_profile"].get("name", "Unknown"),
                    "person_id": face["face_profile"].get("id"),
                    "frame_path": face["frame_path"],
                    "frame_url": face["frame_url"],
                    "speaker": face["speaker"],
                    "text": face["text"]
                }
                self.timeline_service.store_face_detection(db, video_id, face_detection)
            
            # Store speaker segments in the timeline service
            for voice in voice_segments:
                speaker_segment = {
                    "start": voice["start_time"],
                    "end": voice["end_time"],
                    "speaker": voice["speaker"],
                    "speaker_id": voice.get("face_profile", {}).get("id"),
                    "confidence": voice["confidence"],
                    "text": voice["text"],
                    "segment_id": voice["segment_id"]
                }
                self.timeline_service.store_speaker_segment(db, video_id, speaker_segment)
            
            # Update the timeline data using the timeline service
            timeline_result = self.timeline_service.update_timeline_data(db, video_id)
            
            # Find correlations between face and voice events
            # First get the timeline events
            timeline_events = self.timeline_service.get_timeline_events(db, video_id)
            
            # Prepare the recognition data structure expected by find_correlations
            # First check if timeline_events is successful
            if not timeline_events.get("success", False):
                logger.error(f"Failed to get timeline events: {timeline_events.get('error', 'Unknown error')}")
                recognition_data = {"face_events": [], "speaker_events": []}
            else:
                # Get the timeline data which is a list of events
                timeline_data = timeline_events.get("timeline", [])
                
                # Filter events by type and ensure they have the required fields
                face_events = []
                speaker_events = []
                
                for event in timeline_data:
                    # Check if event is a dictionary
                    if not isinstance(event, dict):
                        logger.warning(f"Skipping non-dictionary event: {event}")
                        continue
                        
                    event_type = event.get("type")
                    
                    # Make sure events have start_time and end_time fields
                    # The timeline_service.find_correlations method expects these fields
                    if event_type == "face":
                        # For face events, 'start' should be mapped to 'start_time'
                        face_event = event.copy()
                        if "start" in face_event and "start_time" not in face_event:
                            face_event["start_time"] = face_event["start"]
                        if "end" in face_event and "end_time" not in face_event:
                            face_event["end_time"] = face_event["end"]
                        # Ensure required fields exist
                        if "start_time" not in face_event:
                            face_event["start_time"] = 0
                        if "end_time" not in face_event:
                            face_event["end_time"] = face_event["start_time"] + 1
                        if "confidence" not in face_event:
                            face_event["confidence"] = 0.5
                        if "person_id" not in face_event and "id" in face_event:
                            face_event["person_id"] = face_event["id"]
                        if "person_name" not in face_event and "name" in face_event:
                            face_event["person_name"] = face_event["name"]
                        face_events.append(face_event)
                    elif event_type == "speaker":
                        # For speaker events, 'start' should be mapped to 'start_time'
                        speaker_event = event.copy()
                        if "start" in speaker_event and "start_time" not in speaker_event:
                            speaker_event["start_time"] = speaker_event["start"]
                        if "end" in speaker_event and "end_time" not in speaker_event:
                            speaker_event["end_time"] = speaker_event["end"]
                        # Ensure required fields exist
                        if "start_time" not in speaker_event:
                            speaker_event["start_time"] = 0
                        if "end_time" not in speaker_event:
                            speaker_event["end_time"] = speaker_event["start_time"] + 10
                        if "confidence" not in speaker_event:
                            speaker_event["confidence"] = 0.5
                        if "person_id" not in speaker_event and "id" in speaker_event:
                            speaker_event["person_id"] = speaker_event["id"]
                        if "person_name" not in speaker_event and "name" in speaker_event:
                            speaker_event["person_name"] = speaker_event["name"]
                        speaker_events.append(speaker_event)
                
                logger.info(f"Prepared {len(face_events)} face events and {len(speaker_events)} speaker events for correlation")
                
                recognition_data = {
                    "face_events": face_events,
                    "speaker_events": speaker_events
                }
            
            # Call find_correlations with the correct signature and proper error handling
            try:
                # Ensure recognition_data is properly formatted
                if not isinstance(recognition_data, dict):
                    logger.error(f"Recognition data is not a dictionary: {type(recognition_data)}")
                    recognition_data = {"face_events": [], "speaker_events": []}
                    
                # Ensure face_events and speaker_events are lists
                if not isinstance(recognition_data.get("face_events"), list):
                    logger.error(f"Face events is not a list: {type(recognition_data.get('face_events'))}")
                    recognition_data["face_events"] = []
                if not isinstance(recognition_data.get("speaker_events"), list):
                    logger.error(f"Speaker events is not a list: {type(recognition_data.get('speaker_events'))}")
                    recognition_data["speaker_events"] = []
                    
                # Validate all events have required fields
                for event_list in [recognition_data["face_events"], recognition_data["speaker_events"]]:
                    for i, event in enumerate(event_list):
                        if not isinstance(event, dict):
                            logger.warning(f"Event at index {i} is not a dictionary, removing")
                            event_list[i] = None
                            continue
                            
                        # Ensure required fields
                        for field in ["start_time", "end_time", "confidence"]:
                            if field not in event:
                                logger.warning(f"Event at index {i} missing {field}, adding default")
                                if field == "start_time":
                                    event[field] = event.get("start", 0)
                                elif field == "end_time":
                                    event[field] = event.get("end", event.get("start_time", 0) + 5)
                                else:  # confidence
                                    event[field] = 0.5
                                    
                        # Ensure person identification
                        if "person_id" not in event and "id" in event:
                            event["person_id"] = event["id"]
                        if "person_id" not in event:
                            event["person_id"] = "unknown"
                            
                        if "person_name" not in event and "name" in event:
                            event["person_name"] = event["name"]
                        if "person_name" not in event:
                            event["person_name"] = "Unknown"
                
                # Remove None events
                recognition_data["face_events"] = [e for e in recognition_data["face_events"] if e is not None]
                recognition_data["speaker_events"] = [e for e in recognition_data["speaker_events"] if e is not None]
                
                logger.info(f"Calling find_correlations with validated data: {len(recognition_data['face_events'])} face events, {len(recognition_data['speaker_events'])} speaker events")
                correlations_result = self.timeline_service.find_correlations(recognition_data)
                logger.info(f"Correlations found: {len(correlations_result) if isinstance(correlations_result, list) else 'non-list result'}")
            except Exception as e:
                logger.error(f"Error finding correlations: {str(e)}")
                correlations_result = []
            
            # Add timeline data to the integrated results with detailed type checking and logging
            logger.info(f"Timeline result type: {type(timeline_result)}")
            
            # Initialize recognition_events at the beginning to ensure it's always defined
            recognition_events = []
            
            # Handle different types of timeline_result safely
            if isinstance(timeline_result, dict):
                timeline_events_list = timeline_result.get("timeline", [])
                integrated_results["timeline"] = timeline_events_list
                recognition_events = timeline_events_list
                logger.info(f"Added timeline data from dictionary: {len(integrated_results['timeline'])} items")
            elif isinstance(timeline_result, list):
                integrated_results["timeline"] = timeline_result
                recognition_events = timeline_result
                logger.info(f"Added timeline data from list: {len(integrated_results['timeline'])} items")
            else:
                logger.warning(f"Unexpected timeline_result type: {type(timeline_result)}, using empty list")
                integrated_results["timeline"] = []
                # recognition_events already initialized as []
            
            # Handle correlations result safely
            logger.info(f"Correlations result type: {type(correlations_result)}")
            integrated_results["correlations"] = correlations_result
            logger.info(f"Added correlations data: {len(correlations_result) if isinstance(correlations_result, list) else 'non-list type'}")
            
            # Log the full integrated results structure
            logger.info(f"Integrated results keys: {integrated_results.keys()}")
            for key in integrated_results:
                if isinstance(integrated_results[key], list):
                    logger.info(f"Integrated results[{key}] has {len(integrated_results[key])} items")
                elif isinstance(integrated_results[key], dict):
                    logger.info(f"Integrated results[{key}] has {len(integrated_results[key].keys())} keys")
                else:
                    logger.info(f"Integrated results[{key}] has type {type(integrated_results[key])}")
                    
            # Make sure we have the variables needed for the return value
            if 'all_faces' not in locals():
                all_faces = []
            if 'speaker_to_face_profile' not in locals():
                speaker_to_face_profile = {}
            if 'segments' not in locals():
                segments = []
            if 'correlations' not in locals():
                correlations = []
            
            # Save the results to the database
            video.recognition_results = json.dumps(make_json_serializable(integrated_results))
            
            db.commit()
            
            logger.info(f"Completed multimodal processing for video {video_id}")
            
            # Create a safe return structure with proper defaults
            timeline_preview = []
            if recognition_events and isinstance(recognition_events, list):
                timeline_preview = recognition_events[:10]  # Return just the first 10 events to avoid large response
            
            return {
                "success": True,
                "video_id": video_id,
                "faces_count": len(all_faces) if isinstance(all_faces, list) else 0,
                "speakers_count": len(speaker_to_face_profile) if isinstance(speaker_to_face_profile, dict) else 0,
                "segments_count": len(segments) if isinstance(segments, list) else 0,
                "events_count": len(recognition_events) if isinstance(recognition_events, list) else 0,
                "correlations_count": len(correlations) if isinstance(correlations, list) else 0,
                "timeline": timeline_preview,
                "speaker_face_mapping": speaker_to_face_profile if isinstance(speaker_to_face_profile, dict) else {}
            }
            
        except Exception as e:
            logger.exception(f"Error in multimodal processing: {str(e)}")
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
