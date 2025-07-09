"""
Multimodal Recognition Service for combining voice and face recognition.

This service integrates voice and facial recognition to improve speaker identification
by combining evidence from both modalities.
"""

import os
import json
import logging
import subprocess
import math
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
from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
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
        self.parliament_clips_service = ParliamentClipsIntegrationService()
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
            
            # Use intelligent face extraction method instead of frame-by-frame extraction
            logger.info("Using intelligent face extraction method for better speaker recognition")
            self._process_segments_with_intelligent_face_extraction(
                segments, video_path, output_dir, video_id, db,
                faces_by_time, faces_by_speaker, recognition_events
            )
            
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
            
            # Store recognition events in the timeline with enhanced logging
            face_events_count = 0
            speaker_events_count = 0
            member_id_types = {}
            
            for event in recognition_events:
                if event.get("type") == "face":
                    # Log member ID information for face events
                    member_id = event.get("member_id")
                    if member_id is not None:
                        member_id_type = type(member_id).__name__
                        member_id_types[member_id_type] = member_id_types.get(member_id_type, 0) + 1
                        logger.info(f"Face event at {event.get('timestamp', 0):.2f}s: member_id={member_id} (type: {member_id_type}), name={event.get('name', 'Unknown')}")
                    
                    self.timeline_service.store_face_detection(db, video_id, event)
                    face_events_count += 1
                    
                elif event.get("type") == "speaker":
                    # Log member ID information for speaker events
                    member_id = event.get("member_id")
                    if member_id is not None:
                        member_id_type = type(member_id).__name__
                        member_id_types[member_id_type] = member_id_types.get(member_id_type, 0) + 1
                        logger.info(f"Speaker event {event.get('start_time', 0):.2f}s-{event.get('end_time', 0):.2f}s: member_id={member_id} (type: {member_id_type}), name={event.get('name', 'Unknown')}")
                    
                    self.timeline_service.store_speaker_segment(db, video_id, event)
                    speaker_events_count += 1
            
            # Log summary of member ID types
            logger.info(f"Recognition events summary: {face_events_count} face events, {speaker_events_count} speaker events")
            logger.info(f"Member ID types encountered: {member_id_types}")
                    
            # Update the timeline data with correlations
            timeline = self.timeline_service.update_timeline_data(db, video_id)
            
            # Use ParliamentMemberMatcher to match unidentified speakers
            speaker_appearances = []
            try:
                if not hasattr(self, 'member_matcher') or self.member_matcher is None:
                    self.member_matcher = ParliamentMemberMatcher(db)
                
                # Match unidentified speakers using our improved matcher
                # Note: match_unidentified_speakers only accepts clip_id parameter
                match_result = self.member_matcher.match_unidentified_speakers(str(video_id))
                
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
                
            # Save recognition events to the local SQLite parliament_clips database
            try:
                logger.info(f"Saving recognition events to local SQLite parliament_clips database for video {video_id}")
                clips_result = self.parliament_clips_service.save_recognition_events_to_parliament_clips(
                    video_id=video_id,
                    recognition_events=recognition_events,
                    video_path=video_path
                )
                
                if clips_result.get("success"):
                    logger.info(f"Successfully saved {clips_result.get('clips_saved')} clips to parliament_clips database")
                else:
                    logger.error(f"Failed to save clips to parliament_clips database: {clips_result.get('error')}")
            except Exception as e:
                logger.exception(f"Error saving to parliament_clips database: {str(e)}")
            
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
            
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """
        Parse a timestamp string in format HH:MM:SS or MM:SS into seconds
        """
        parts = timestamp_str.strip().split(':')
        if len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + float(parts[1])
        else:
            # Try to parse as a float directly
            try:
                return float(timestamp_str)
            except ValueError:
                logger.error(f"Could not parse timestamp: {timestamp_str}")
                return 0.0
                
    def _process_segments_with_intelligent_face_extraction(self, segments: List[Dict], video_path: str, 
                                            output_dir: str, video_id: int, db: Session,
                                            faces_by_time: Dict, faces_by_speaker: Dict, 
                                            recognition_events: List) -> None:
        """
        Process segments using intelligent face extraction method.
        
        Args:
            segments: List of transcription segments
            video_path: Path to the video file
            output_dir: Directory to save output files
            video_id: ID of the video in the database
            db: Database session
            faces_by_time: Dictionary to store faces by timestamp
            faces_by_speaker: Dictionary to store faces by speaker
            recognition_events: List to store recognition events
        """
        try:
            # Create output directory for this video
            video_dir = os.path.join(output_dir, f"video_{video_id}")
            os.makedirs(video_dir, exist_ok=True)
            
            # Extract high-quality faces from the entire video
            logger.info(f"Extracting high-quality faces from video {video_id}")
            extraction_result = self.face_profile_service.extract_faces_from_video(
                video_path=video_path,
                output_dir=video_dir,
                interval=1.0,  # Base interval, but our method will select best frames
                min_confidence=0.6,
                prioritize_center=True,
                select_best_frames=True
            )
            
            if extraction_result.get("success", False):
                extracted_faces = extraction_result.get("faces_found", 0)
                face_data = extraction_result.get("face_data", [])
                logger.info(f"Successfully extracted {extracted_faces} high-quality faces from video")
                
                # Map extracted faces to segments based on timestamp
                matched_faces = 0
                processed_faces = set()  # Track processed faces to avoid duplicates
                
                for face_info in face_data:
                    face_time = face_info.get("timestamp", 0)
                    face_path = face_info.get("path", "")
                    
                    # Skip if we've already processed this face (deduplication)
                    if face_path in processed_faces:
                        logger.debug(f"Skipping duplicate face at {face_time:.2f}s with path {face_path}")
                        continue
                    
                    # Find the segment that contains this timestamp
                    matching_segment = None
                    for segment in segments:
                        start_time = segment.get("start", 0)
                        end_time = segment.get("end", 0)
                        if start_time <= face_time <= end_time:
                            matching_segment = segment
                            break
                    
                    if matching_segment and os.path.exists(face_path):
                        # Process this high-quality face
                        logger.info(f"Processing high-quality face at {face_time:.2f}s")
                        
                        # Identify speaker in the high-quality face image
                        # Pass timestamp and video_id for temporal consistency checks
                        # Using very low threshold as requested to ensure we capture all potential matches
                        face_result = self.identify_speaker_in_frame(
                            db, 
                            face_path, 
                            threshold=0.1,  # Lower threshold to match more faces
                            timestamp=face_time, 
                            video_id=str(video_id)  # Convert to string as expected by the matcher
                        )
                        
                        if face_result["success"]:
                            face_data = face_result["data"]
                            face_data["frame_path"] = face_path
                            face_data["frame_time"] = face_time
                            speaker = matching_segment.get("speaker", "unknown")
                            face_data["segment_speaker"] = speaker
                            
                            # Add to recognition events with comprehensive structure
                            recognition_event = {
                                "type": "speaker",
                                "start_time": face_time,
                                "end_time": min(face_time + 5, matching_segment.get("end", face_time + 5)),
                                "member_id": face_data.get("member_id"),
                                "name": face_data.get("name", "Unknown"),
                                "confidence": face_data.get("confidence", 0.0),
                                "face_image_url": face_path,
                                "text": matching_segment.get("text", ""),
                                "recognition_method": "facial",
                                "matched_by": face_data.get("matched_by", "unknown"),
                                "profile_id": face_data.get("profile_id"),
                                "segment_speaker": speaker,
                                "time": face_time,  # Add time field for backward compatibility
                                "quality_score": face_info.get("quality_score", 0)
                            }
                            
                            recognition_events.append(recognition_event)
                            matched_faces += 1
                            
                            # Store face by time for later reference
                            time_key = int(face_time)
                            if time_key not in faces_by_time:
                                faces_by_time[time_key] = []
                            faces_by_time[time_key].append(face_data)
                            
                            # Store face by speaker for later correlation
                            if speaker not in faces_by_speaker:
                                faces_by_speaker[speaker] = []
                            faces_by_speaker[speaker].append(face_data)
                            
                            # Mark this face as processed to avoid duplicates
                            processed_faces.add(face_path)
                        else:
                            logger.warning(f"Failed to identify speaker in frame {face_path}: {face_result.get('error', 'Unknown error')}")
                    else:
                        if not matching_segment:
                            logger.debug(f"No matching segment found for face at {face_time:.2f}s")
                        if not os.path.exists(face_path):
                            logger.warning(f"Face image file not found: {face_path}")
                
                logger.info(f"Matched {matched_faces} faces to segments out of {extracted_faces} extracted faces")
                logger.info(f"Processed {len(processed_faces)} unique faces (after deduplication)")
                
                # If we didn't find any faces, log a warning
                if matched_faces == 0:
                    logger.warning("No faces matched to segments. Check face extraction and matching parameters.")
            else:
                logger.error(f"Face extraction failed: {extraction_result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.exception(f"Error in _process_segments_with_intelligent_face_extraction: {str(e)}")
            # Continue processing despite errors to maintain robustness
            
    def identify_speaker_in_frame(self, db: Session, frame_path: str, threshold: float = 0.1, timestamp: float = None, video_id: str = None) -> Dict[str, Any]:
        """Identify speakers in a frame using facial recognition and ParliamentMemberMatcher."""
        try:
            logger.info(f"===== IDENTIFYING SPEAKER IN FRAME: {frame_path} =====")
            
            # Default to not exporting to Supabase
            export_to_supabase = False
            
            # First, ensure member matcher is initialized
            if not self.member_matcher:
                logger.info("Initializing ParliamentMemberMatcher")
                self.member_matcher = ParliamentMemberMatcher(db)
            
            # Ensure member matcher has loaded parliament members
            if not hasattr(self.member_matcher, 'members') or not self.member_matcher.members:
                logger.info("Loading parliament members in ParliamentMemberMatcher")
                self.member_matcher.load_parliament_members()
                logger.info(f"Loaded {len(self.member_matcher.members)} parliament members")
            else:
                logger.info(f"Using {len(self.member_matcher.members)} previously loaded parliament members")
            
            # Run facial recognition on the frame
            logger.info(f"Running facial recognition on frame: {frame_path}")
            face_results = self.facial_recognition.detect_faces_in_image(frame_path)
            
            if not face_results.get("success", False):
                logger.warning(f"❌ No faces detected in frame: {frame_path}")
                return {"success": False, "error": "No faces detected", "supabase_export": {"enabled": export_to_supabase}}
                
            detections = face_results.get("detections", [])
            if not detections:
                logger.warning(f"❌ No detections in frame: {frame_path}")
                return {"success": False, "error": "No detections", "supabase_export": {"enabled": export_to_supabase}}
            
            logger.info(f"Found {len(detections)} face detections in frame")
            
            # Sort by confidence (highest first)
            detections.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            
            # IMPROVED: Consider multiple face detections instead of just the best one
            # This helps when there are multiple speakers in the frame
            best_detection = detections[0]
            
            # Log information about all detections for debugging
            for i, detection in enumerate(detections[:3]):  # Log top 3 detections
                logger.info(f"Detection #{i+1}: confidence={detection.get('confidence', 0):.4f}, "
                           f"box={detection.get('box', [])}")
            
            logger.info(f"Using best detection with confidence: {best_detection.get('confidence', 0):.4f}")
            
            # IMPROVED: Skip low-confidence detections
            if best_detection.get('confidence', 0) < 0.7:  # Minimum face detection confidence
                logger.warning(f"⚠️ Best face detection has low confidence: {best_detection.get('confidence', 0):.4f}")
                # Continue anyway, but log the warning
            
            # Try to match with our improved ParliamentMemberMatcher
            face_embedding = best_detection.get("embedding")
            if face_embedding is not None:
                # Log embedding information
                if isinstance(face_embedding, list):
                    embedding_len = len(face_embedding)
                    has_nan = any(isinstance(x, float) and (math.isnan(x) or math.isinf(x)) for x in face_embedding)
                    has_zeros = all(x == 0 for x in face_embedding)
                    logger.info(f"Face embedding: length={embedding_len}, has_nan={has_nan}, all_zeros={has_zeros}")
                else:
                    logger.warning(f"Face embedding is not a list but {type(face_embedding).__name__}")
                
                # Get the house from the video metadata if available
                house = "unknown"  # Default house
                logger.info(f"Using house: {house} for matching")
                
                # Match the face to a parliament member
                logger.info(f"Matching face to parliament member with threshold: {threshold}")
                
                # Pass timestamp and video_id for temporal consistency checks if available
                if timestamp is not None and video_id is not None:
                    logger.info(f"Using temporal consistency with timestamp {timestamp:.2f}s for video {video_id}")
                
                match_result = self.member_matcher.match_face_to_member(
                    face_embedding, 
                    threshold, 
                    house=house,
                    timestamp=timestamp, 
                    video_id=video_id
                )
                
                if match_result:
                    # Log if temporal consistency was applied
                    if match_result.get('continuity_adjusted'):
                        logger.info(f"Match was adjusted for temporal consistency")
                    logger.info(f"Match result: {json.dumps(match_result)}")
                
                if match_result and match_result.get("matched"):
                    # Use the matched member information
                    member_id = match_result.get("member_id")
                    member_name = match_result.get("name")  # Use 'name' instead of 'member_name'
                    confidence = match_result.get("confidence")
                    confidence_gap = match_result.get("confidence_gap", 0)
                    alternatives = match_result.get("alternatives", [])
                    
                    best_detection["member_id"] = member_id
                    best_detection["name"] = member_name
                    best_detection["confidence"] = confidence
                    best_detection["confidence_gap"] = confidence_gap
                    best_detection["matched_by"] = "parliament_member_matcher"
                    best_detection["alternatives"] = alternatives
                    
                    # Enhanced logging with member ID type and alternatives
                    logger.info(f"✅ Successfully matched face to member {member_name} (ID: {member_id}, type: {type(member_id).__name__}) with confidence {confidence:.4f}, gap: {confidence_gap:.4f}")
                    if alternatives and len(alternatives) > 0:
                        alt_info = ", ".join([f"{name} ({conf:.4f})" for name, conf in alternatives[:3]])
                        logger.info(f"   Alternative matches: {alt_info}")
                else:
                    logger.warning(f"⚠️ Failed to match face with ParliamentMemberMatcher")
                    if match_result:
                        logger.info(f"Best match details: member_id={match_result.get('best_match_id')}, confidence={match_result.get('best_match_confidence', 0):.4f}, threshold={threshold}")
                    
                    # Fallback to the original method if no match found
                    profile_id = best_detection.get("profile_id")
                    if profile_id:
                        logger.info(f"Trying fallback to face_profile_service with profile_id: {profile_id}")
                        profile = self.face_profile_service.get_profile_by_id(db, profile_id)
                        if profile:
                            best_detection["name"] = profile.get("name", "Unknown")
                            best_detection["profile"] = profile
                            best_detection["matched_by"] = "face_profile_service"
                            logger.info(f"Matched to profile: {profile.get('name', 'Unknown')}")
                        else:
                            logger.warning(f"No profile found for profile_id: {profile_id}")
                    else:
                        logger.warning("No profile_id available for fallback matching")
                        
                        # If no match found, use default unidentified member
                        logger.info(f"Using default unidentified member for house: {house}")
                        default_member_id = self.member_matcher._get_default_member_for_house(house)
                        if default_member_id:
                            best_detection["member_id"] = default_member_id
                            best_detection["name"] = "Unidentified Speaker"
                            best_detection["matched_by"] = "default_unidentified"
                            logger.info(f"Using default unidentified member ID: {default_member_id}")
                        else:
                            logger.warning(f"No default member found for house: {house}")
            else:
                logger.error(f"❌ No face embedding found in detection")
            
            # Log the final detection result
            logger.info(f"Final detection result: member_id={best_detection.get('member_id')}, name={best_detection.get('name', 'Unknown')}, matched_by={best_detection.get('matched_by', 'unknown')}")
            
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
                return {"success": False, "error": f"No recognition process found for video {video_id}"}
            
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
                    return {"success": False, "error": f"Error processing recognition results: {str(e)}"}
            
            # Get the timeline data
            timeline_result = self.timeline_service.get_timeline_events(db, video_id)
            if timeline_result and "timeline" in timeline_result:
                results["timeline"] = timeline_result["timeline"]
                logger.info(f"Added timeline data with {len(timeline_result['timeline'])} events")
            
            # Add success flag to results
            results["success"] = True
            
            return results
            
        except Exception as e:
            logger.exception(f"Error getting recognition results: {str(e)}")
            return {"success": False, "error": f"Error getting recognition results: {str(e)}"}
            
    def _process_segments_with_frame_extraction(self, segments: List[Dict], video_path: str, 
                                         output_dir: str, video_id: int, db: Session,
                                         faces_by_time: Dict, faces_by_speaker: Dict, 
                                         recognition_events: List) -> None:
        """
        Process segments by extracting frames at regular intervals (fallback method).
        
        Args:
            segments: List of transcription segments
            video_path: Path to the video file
            output_dir: Directory to save output files
            video_id: ID of the video in the database
            db: Database session
            faces_by_time: Dictionary to store faces by timestamp
            faces_by_speaker: Dictionary to store faces by speaker
            recognition_events: List to store recognition events
        """
        logger.info("Using standard frame extraction method as fallback")
        
        # Track processed frames to avoid duplicates
        processed_frames = set()
        
        for segment in segments:
            speaker = segment.get("speaker", "unknown")
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            
            # Skip segments that are too short
            if end_time - start_time < 1.0:
                logger.debug(f"Skipping segment that is too short: {start_time:.2f}s - {end_time:.2f}s")
                continue
                
            # Determine frame extraction interval based on segment duration
            segment_duration = end_time - start_time
            if segment_duration < 10:
                interval = 1.0  # Frame every second for short segments
            else:
                interval = 4.0  # Frame every 3-5 seconds for long segments
            
            logger.info(f"Processing segment {start_time:.2f}s - {end_time:.2f}s with interval {interval:.1f}s")
            
            # Extract frames at regular intervals
            current_time = start_time
            while current_time < end_time:
                # Extract frame at current time
                frame_time = current_time
                frame_path = os.path.join(output_dir, f"frame_{video_id}_{int(frame_time * 100):08d}.jpg")
                
                # Skip if we've already processed this frame (deduplication)
                if frame_path in processed_frames:
                    logger.debug(f"Skipping duplicate frame at {frame_time:.2f}s with path {frame_path}")
                    current_time += interval
                    continue
                
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
                        current_time += interval
                        continue
                
                # Identify speaker in the frame
                if os.path.exists(frame_path):
                    try:
                        # Pass timestamp and video_id for temporal consistency checks
                        # Using very low threshold as requested to ensure we capture all potential matches
                        face_result = self.identify_speaker_in_frame(
                            db, 
                            frame_path, 
                            threshold=0.1,  # Lower threshold to match more faces
                            timestamp=frame_time, 
                            video_id=str(video_id)  # Convert to string as expected by the matcher
                        )
                        if face_result["success"]:
                            face_data = face_result["data"]
                            face_data["frame_path"] = frame_path
                            face_data["frame_time"] = frame_time
                            face_data["segment_speaker"] = speaker
                            
                            # Add to recognition events with comprehensive structure
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
                                "matched_by": face_data.get("matched_by", "unknown"),
                                "profile_id": face_data.get("profile_id"),
                                "segment_speaker": speaker,
                                "time": frame_time  # Add time field for backward compatibility
                            }
                            recognition_events.append(recognition_event)
                            
                            # Store additional segment information
                            face_data["segment_start"] = start_time
                            face_data["segment_end"] = end_time
                            face_data["segment_text"] = segment.get("text", "")
                            
                            # Store face by time for later reference
                            time_key = int(frame_time)
                            if time_key not in faces_by_time:
                                faces_by_time[time_key] = []
                            faces_by_time[time_key].append(face_data)
                            
                            # Store face by speaker for later correlation
                            if speaker not in faces_by_speaker:
                                faces_by_speaker[speaker] = []
                            faces_by_speaker[speaker].append(face_data)
                            
                            # Mark this frame as processed to avoid duplicates
                            processed_frames.add(frame_path)
                        else:
                            logger.warning(f"Failed to identify speaker in frame {frame_path}: {face_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"Error processing frame {frame_path}: {str(e)}")
                
                # Move to next frame time
                current_time += interval
        
        logger.info(f"Processed {len(processed_frames)} unique frames using frame extraction method")
        
        # If we didn't find any faces, log a warning
        if not processed_frames:
            logger.warning("No frames processed. Check frame extraction parameters.")

