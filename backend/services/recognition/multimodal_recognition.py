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
from backend.services.recognition.member_matcher import ParliamentMemberMatcher
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class MultimodalRecognitionService:
    """Service for combining voice and face recognition for improved speaker identification."""
    
    def __init__(self):
        """
        Initialize the multimodal recognition service
        """
        from backend.db.session import get_db
        
        self.facial_recognition = FacialRecognitionService()
        self.face_profile_service = FaceProfileService()
        self.timeline_service = TimelineService()
        self.member_matcher = None  # Will be initialized when needed with DB session
        
        # Set up directories using Docker container paths as per user preference
        self.output_dir = "/app/data/temp/recognition"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up MP photos directory
        self.mp_photos_dir = "/app/data/mp_photos"
        os.makedirs(self.mp_photos_dir, exist_ok=True)
        
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
            
            # Check if combined audio-video file exists and add to process metadata
            combined_av_path = os.path.join(os.path.dirname(video_path), f"combined_{video_id}.mp4")
            if os.path.exists(combined_av_path):
                logger.info(f"Found combined audio-video file: {combined_av_path}")
                # Get existing metadata or initialize empty dict
                process_metadata = recognition_process.process_metadata or {}
                if isinstance(process_metadata, str):
                    try:
                        process_metadata = json.loads(process_metadata)
                    except json.JSONDecodeError:
                        process_metadata = {}
                
                # Add combined_av_path to metadata
                process_metadata["combined_av_path"] = combined_av_path
                recognition_process.process_metadata = process_metadata
            
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
            
            # Ensure member matcher has loaded parliament members
            if not hasattr(self, 'member_matcher') or self.member_matcher is None:
                self.member_matcher = ParliamentMemberMatcher(db)
            
            # Initialize data structures for tracking faces and recognition events
            faces_by_speaker = {}
            faces_by_time = {}
            recognition_events = []
            correlations = []
            speaker_to_face_profile = {}
            
            # Process each segment
            for segment in segments:
                speaker = segment.get("speaker", "unknown")
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                # Skip segments that are too short
                if end_time - start_time < 1.0:
                    continue
                    
                # Determine frame extraction interval based on segment duration
                segment_duration = end_time - start_time
                if segment_duration < 10:
                    interval = 1.0  # Frame every second for short segments
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
                                
                                # Add to recognition events
                                recognition_event = {
                                    "type": "speaker",
                                    "start_time": frame_time,
                                    "end_time": min(frame_time + 5, end_time),  # Assume 5 seconds or until segment end
                                    "member_id": face_data.get("member_id"),
                                    "name": face_data.get("name", "Unknown"),
                                    "confidence": face_data.get("confidence", 0.0),
                                    "face_image_url": frame_path,
                                    "text": segment.get("text", ""),
                                    "recognition_method": "facial",
                                    "matched_by": face_data.get("matched_by", "unknown")
                                }
                                recognition_events.append(recognition_event)
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
            
            # Use ParliamentMemberMatcher to match unidentified speakers
            speaker_appearances = []
            try:
                if not hasattr(self, 'member_matcher') or self.member_matcher is None:
                    self.member_matcher = ParliamentMemberMatcher(db)
                
                # Match unidentified speakers using our improved matcher
                match_result = self.member_matcher.match_unidentified_speakers(video_id, save_unmatched=True)
                
                if match_result:
                    logger.info(f"Matched {match_result.get('matched_count', 0)} speakers using ParliamentMemberMatcher")
                    
                    # Get all speaker appearances for this video
                    speaker_identifications = db.query(models.SpeakerIdentification).filter(
                        models.SpeakerIdentification.capture_session_id == video_id
                    ).all()
                    
                    for identification in speaker_identifications:
                        # Get all appearances for this identification
                        appearances = db.query(models.SpeakerAppearance).filter(
                            models.SpeakerAppearance.identification_id == identification.id
                        ).all()
                        
                        for appearance in appearances:
                            # Convert to dict for JSON serialization
                            appearance_dict = {
                                "id": appearance.id,
                                "identification_id": appearance.identification_id,
                                "member_id": appearance.member_id,
                                "member_name": identification.member_name,
                                "start_time": appearance.start_time,
                                "end_time": appearance.end_time,
                                "confidence": appearance.confidence,
                                "matched_by": "parliament_member_matcher",
                                "face_image_url": appearance.face_image_url
                            }
                            speaker_appearances.append(appearance_dict)
            except Exception as e:
                logger.error(f"Error matching unidentified speakers: {str(e)}")
            
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
                    "recognition_events": recognition_events,
                    "speaker_appearances": speaker_appearances
                })
                db.commit()
            else:
                # Create a new recognition process record if one doesn't exist
                logger.info(f"Creating new RecognitionProcess record for video {video_id}")
                recognition_process = models.RecognitionProcess(
                    video_id=video_id,
                    process_type="multimodal",
                    status="completed",
                    results=json.dumps({
                        "timeline": timeline,
                        "correlations": correlations,
                        "recognition_events": recognition_events,
                        "speaker_appearances": speaker_appearances
                    }),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(recognition_process)
                db.commit()
            
            return {
                "success": True,
                "video_id": video_id,
                "segments_count": len(segments),
                "recognition_events": len(recognition_events),
                "correlations": correlations,
                "timeline": timeline,
                "speaker_appearances": speaker_appearances
            }
            
        except Exception as e:
            logger.exception(f"Error processing video with transcription: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse a timestamp string into seconds."""
        try:
            if ':' in timestamp:
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
        """Identify speakers in a frame using facial recognition and ParliamentMemberMatcher."""
        try:
            logger.info(f"Identifying speaker in frame: {frame_path}")
            
            # Default to not exporting to Supabase
            export_to_supabase = False
            
            # First, ensure member matcher has loaded parliament members
            if not hasattr(self.member_matcher, 'members') or not self.member_matcher.members:
                self.member_matcher.load_parliament_members()
            
            # Run facial recognition on the frame
            face_results = self.facial_recognition.detect_faces_in_image(frame_path)
            
            if not face_results.get("success", False):
                logger.warning(f"No faces detected in frame: {frame_path}")
                return {"success": False, "error": "No faces detected", "supabase_export": {"enabled": export_to_supabase}}
                
            detections = face_results.get("detections", [])
            if not detections:
                logger.warning(f"No detections in frame: {frame_path}")
                return {"success": False, "error": "No detections", "supabase_export": {"enabled": export_to_supabase}}
            
            # Sort by confidence (highest first)
            detections.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            best_detection = detections[0]
            
            # Try to match with our improved ParliamentMemberMatcher
            face_embedding = best_detection.get("embedding")
            if face_embedding is not None:
                # Get the house from the video metadata if available
                house = "unknown"  # Default house
                
                # Match the face to a parliament member
                match_result = self.member_matcher.match_face_to_member(face_embedding, threshold)
                
                if match_result and match_result.get("matched"):
                    # Use the matched member information
                    member_id = match_result.get("member_id")
                    member_name = match_result.get("member_name")
                    confidence = match_result.get("confidence")
                    
                    best_detection["member_id"] = member_id
                    best_detection["name"] = member_name
                    best_detection["confidence"] = confidence
                    best_detection["matched_by"] = "parliament_member_matcher"
                    
                    logger.info(f"Matched face to member {member_name} with confidence {confidence}")
                else:
                    # Fallback to the original method if no match found
                    profile_id = best_detection.get("profile_id")
                    if profile_id:
                        profile = self.face_profile_service.get_profile_by_id(db, profile_id)
                        if profile:
                            best_detection["name"] = profile.get("name", "Unknown")
                            best_detection["profile"] = profile
                            best_detection["matched_by"] = "face_profile_service"
                    else:
                        # If no match found, use default unidentified member
                        default_member_id = self.member_matcher._get_default_member_for_house(house)
                        if default_member_id:
                            best_detection["member_id"] = default_member_id
                            best_detection["name"] = "Unidentified Speaker"
                            best_detection["matched_by"] = "default_unidentified"
            
            return {
                "success": True, 
                "data": best_detection,
                "supabase_export": face_results.get("supabase_export", {"enabled": export_to_supabase})
            }
            
        except Exception as e:
            logger.exception(f"Error identifying speaker in frame: {str(e)}")
            return {"success": False, "error": str(e), "supabase_export": {"enabled": False, "error": str(e)}}
            
    def get_recognition_results(self, video_id: int) -> Dict[str, Any]:
        """Get recognition results for a video.
        
        Args:
            video_id: ID of the video to get results for
            
        Returns:
            Dictionary with recognition results
        """
        try:
            logger.info(f"Getting recognition results for video {video_id}")
            
            # Get database session
            from backend.db.session import get_db
            from sqlalchemy.orm import Session
            
            db_generator = get_db()
            db: Session = next(db_generator)
            
            # Get the recognition process from the database
            recognition_process = db.query(models.RecognitionProcess).filter(
                models.RecognitionProcess.video_id == video_id,
                models.RecognitionProcess.process_type == "multimodal"
            ).order_by(models.RecognitionProcess.created_at.desc()).first()
            
            if not recognition_process:
                logger.error(f"No recognition process found for video {video_id}")
                return {}
            
            # Get the recognition results
            results = {}
            if recognition_process.results:
                try:
                    # Use the make_json_serializable function to handle all result types
                    results = make_json_serializable(recognition_process.results)
                    
                    # If results is still a string after serialization, parse it as JSON
                    if isinstance(results, str):
                        try:
                            results = json.loads(results)
                        except json.JSONDecodeError as json_error:
                            logger.error(f"Error parsing results JSON string: {str(json_error)}")
                            # If it's not valid JSON, use it as a simple value
                            results = {"value": results}
                    
                    # Ensure results is a dictionary
                    if not isinstance(results, dict):
                        results = {"value": str(results)}
                        
                    logger.info(f"Successfully processed results for video {video_id}")
                except Exception as e:
                    logger.error(f"Error processing recognition results: {str(e)}")
                    return {}
            
            # Get the timeline data
            timeline_data = self.timeline_service.get_timeline_data(db, video_id)
            if timeline_data:
                results["timeline"] = timeline_data
            
            return results
            
        except Exception as e:
            logger.exception(f"Error getting recognition results: {str(e)}")
            return {}
