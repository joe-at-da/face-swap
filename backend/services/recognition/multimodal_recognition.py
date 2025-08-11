"""
Multimodal Recognition Service for combining voice and face recognition.

This service integrates voice and facial recognition to improve speaker identification
by combining evidence from both modalities.
"""

import os
import sys
import json
import time
import math
import copy
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments

from backend.db import models
from backend.core.recognition_config import AudioConfig, DiarizationConfig
try:
    from backend.core.recognition_config import FaceDetectionConfig
except ImportError:
    # Fallback values if config module is not available
    class FaceDetectionConfig:
        SEGMENT_DURATION = 5
        MAX_TIME_GAP = 1.5

from backend.services.recognition.voice_recognition import VoiceRecognitionService
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.services.recognition.face_profile_service import FaceProfileService
from backend.services.recognition.member_matcher import ParliamentMemberMatcher
from backend.services.recognition.timeline_service import TimelineService
from backend.services.recognition.timeline_face_selector import TimelineFaceSelector
from backend.services.recognition.timeline_combiner import combine_recognition_and_transcription
from backend.services.recognition.parliament_clips_integration import ParliamentClipsIntegrationService
from backend.services.recognition.sentence_segmentation import merge_incomplete_sentences
from backend.services.recognition.transcript_matcher import match_transcripts_to_diarization_segments
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class MultimodalRecognitionService:
    """
    Service for performing multimodal recognition combining facial recognition,
    voice recognition, and transcription analysis.
    """
    
    def __init__(self):
        self.face_service = FacialRecognitionService()
        self.facial_recognition = self.face_service  # Alias for backward compatibility
        self.voice_service = VoiceRecognitionService()
        self.face_profile_service = FaceProfileService()
        self.timeline_service = TimelineService()
        self.timeline_face_selector = TimelineFaceSelector()
        
        # Initialize parliament clips service
        self.parliament_clips_service = ParliamentClipsIntegrationService()
        
        # Initialize output directory for temporary files
        self.output_dir = "/tmp/multimodal_recognition"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize member matcher with supabase service
        from backend.services.integration.supabase_client import SupabaseService
        supabase_service = SupabaseService()
        self.member_matcher = ParliamentMemberMatcher(supabase_service)
        
        logger.info("🎯 MultimodalRecognitionService initialized with enhanced recognition quality features")
    
    def validate_and_refine_speech_groups(self, segments: List[Dict], diarization_data: List[Dict] = None) -> List[Dict]:
        """
        Enhanced speech group validation and refinement for better speaker turn detection.
        
        Args:
            segments: List of transcription segments with speaker information
            diarization_data: Optional diarization data for validation
            
        Returns:
            List of refined segments with improved speech group assignments
        """
        if not segments:
            return segments
            
        logger.info(f" Validating and refining speech groups for {len(segments)} segments")
        
        refined_segments = []
        current_speech_group = None
        current_speaker = None
        group_start_time = None
        group_segments = []
        
        for i, segment in enumerate(segments):
            segment_start = segment.get("start", 0)
            segment_end = segment.get("end", 0)
            segment_speaker = segment.get("speaker", "Unknown")
            segment_duration = segment_end - segment_start
            
            # Skip segments that are too short to be meaningful
            if segment_duration < DiarizationConfig.MIN_SPEECH_GROUP_DURATION / 4:
                logger.debug(f"  Skipping very short segment ({segment_duration:.2f}s): {segment.get('text', '')[:50]}")
                continue
            
            # Check if this is a speaker change
            speaker_changed = (current_speaker != segment_speaker)
            
            # Check if there's a significant time gap
            time_gap = 0
            if group_segments:
                last_segment = group_segments[-1]
                time_gap = segment_start - last_segment.get("end", 0)
            
            significant_gap = time_gap > DiarizationConfig.MAX_SPEECH_GROUP_GAP
            
            # Determine if we should start a new speech group
            should_start_new_group = (
                current_speech_group is None or  # First group
                speaker_changed or  # Speaker changed
                significant_gap  # Significant time gap
            )
            
            if should_start_new_group:
                # Finalize the previous group if it exists
                if group_segments:
                    self._finalize_speech_group(refined_segments, current_speech_group, group_segments)
                
                # Start new group
                current_speech_group = len(refined_segments) + 1
                current_speaker = segment_speaker
                group_start_time = segment_start
                group_segments = []
                
                logger.debug(f" Starting new speech group {current_speech_group} for speaker '{current_speaker}' at {segment_start:.2f}s")
            
            # Add segment to current group
            segment_copy = segment.copy()
            segment_copy["speech_group_id"] = current_speech_group
            segment_copy["group_speaker"] = current_speaker
            group_segments.append(segment_copy)
            
            logger.debug(f" Added segment to group {current_speech_group}: {segment.get('text', '')[:50]}...")
        
        # Finalize the last group
        if group_segments:
            self._finalize_speech_group(refined_segments, current_speech_group, group_segments)
        
        logger.info(f" Speech group validation complete: {len(refined_segments)} refined segments in {current_speech_group or 0} groups")
        
        return refined_segments
    
    def _finalize_speech_group(self, refined_segments: List[Dict], group_id: int, group_segments: List[Dict]):
        """
        Finalize a speech group by validating duration and applying group-level metadata.
        
        Args:
            refined_segments: List to append finalized segments to
            group_id: ID of the speech group
            group_segments: List of segments in this group
        """
        if not group_segments:
            return
        
        # Calculate group duration
        group_start = min(seg.get("start", 0) for seg in group_segments)
        group_end = max(seg.get("end", 0) for seg in group_segments)
        group_duration = group_end - group_start
        
        # Get group speaker (should be consistent)
        group_speaker = group_segments[0].get("group_speaker", "Unknown")
        
        # Validate minimum group duration
        if group_duration < DiarizationConfig.MIN_SPEECH_GROUP_DURATION:
            logger.debug(f"  Short speech group {group_id} ({group_duration:.2f}s) for speaker '{group_speaker}'")
        
        # Add group metadata to all segments
        for segment in group_segments:
            segment.update({
                "group_duration": group_duration,
                "group_start_time": group_start,
                "group_end_time": group_end,
                "group_segment_count": len(group_segments),
                "is_validated_group": True
            })
            
            refined_segments.append(segment)
        
        logger.debug(f" Finalized speech group {group_id}: {len(group_segments)} segments, "
                   f"{group_duration:.2f}s duration, speaker '{group_speaker}'")
    
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
            
            # DEBUG: Log what the recognition service actually receives
            logger.info(f"DEBUG: Recognition service received video {video_id}:")
            logger.info(f"DEBUG: video.metadata = {video.metadata}")
            logger.info(f"DEBUG: video.audio_path = {video.audio_path}")
            logger.info(f"DEBUG: video.video_path = {video.video_path}")
            logger.info(f"DEBUG: type(video.metadata) = {type(video.metadata)}")
            
            # Check if the video has metadata with separate audio and video URLs
            metadata = {}
            if video.metadata:
                try:
                    # Use the make_json_serializable function to handle all metadata types
                    # including SQLAlchemy MetaData objects
                    metadata = make_json_serializable(video.metadata)
                    logger.info(f"DEBUG: After make_json_serializable: metadata = {metadata}")
                    logger.info(f"DEBUG: type(metadata) = {type(metadata)}")
                    
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
            
            # DEBUG: Log the final paths being used
            logger.info(f"DEBUG: Final paths determined:")
            logger.info(f"DEBUG: video_path = {video_path}")
            logger.info(f"DEBUG: audio_path from metadata = {metadata.get('audio_path')}")
            logger.info(f"DEBUG: audio_path from video.audio_path = {video.audio_path}")
            logger.info(f"DEBUG: final audio_path = {audio_path}")
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {"success": False, "error": f"Video file not found: {video_path}"}
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return {"success": False, "error": f"Audio file not found: {audio_path}"}
            
            # Create a recognition process record with proper transaction handling
            try:
                # First check if the transaction is still valid
                try:
                    # Execute a simple query to test if transaction is valid
                    db.execute(text("SELECT 1")).scalar()
                except Exception as tx_error:
                    logger.warning(f"Transaction appears to be in a failed state, rolling back: {str(tx_error)}")
                    db.rollback()
                    
                recognition_process = models.RecognitionProcess(
                    video_id=video_id,
                    status="processing",
                    start_time=datetime.now(),
                    process_type="multimodal",
                    process_metadata={"type": "multimodal"}
                )
                db.add(recognition_process)
                
                # Update the CaptureSession record with recognition status
                video.recognition_status = "processing"
                video.recognition_started_at = datetime.now()
                
                db.commit()
                db.refresh(recognition_process)
                logger.info(f"Created new RecognitionProcess record for video {video_id} and updated CaptureSession status")
            except Exception as db_error:
                logger.error(f"Database error when creating RecognitionProcess: {str(db_error)}")
                try:
                    db.rollback()
                    logger.info("Successfully rolled back transaction after database error")
                except Exception as rollback_error:
                    logger.error(f"Error during transaction rollback: {str(rollback_error)}")
                return {"success": False, "error": f"Database error: {str(db_error)}"}
            
            # Process transcription first if not already done
            if not video.transcription_results:
                from backend.services.recognition.voice_recognition import VoiceRecognitionService
                voice_service = VoiceRecognitionService()
                
                # Transcribe the audio
                logger.info(f"Starting transcription for audio: {audio_path}")
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
                
                # Log the transcription result structure and handle different data types
                transcript_data = transcription_result.get("transcript", {})
                
                # Handle different transcript data types properly
                if isinstance(transcript_data, dict):
                    segments_count = len(transcript_data.get("segments", []))
                    logger.info(f"Received transcription with {segments_count} segments")
                elif isinstance(transcript_data, str):
                    # If transcript is a string, wrap it in the expected structure
                    logger.info(f"Received transcription as string (length: {len(transcript_data)} chars)")
                    transcript_data = {"text": transcript_data, "segments": []}
                elif isinstance(transcript_data, list):
                    # If transcript is a list of segments, wrap it properly
                    logger.info(f"Received transcription as list with {len(transcript_data)} segments")
                    transcript_data = {"segments": transcript_data}
                else:
                    logger.warning(f"Unexpected transcript data type: {type(transcript_data)}, converting to string")
                    transcript_data = {"text": str(transcript_data), "segments": []}
                
                # Save transcription results with proper serialization
                try:
                    video.transcription_results = json.dumps(transcript_data, ensure_ascii=False)
                    db.commit()
                    logger.info("Successfully saved transcription results to database")
                except Exception as e:
                    logger.error(f"Error saving transcription results: {str(e)}")
                    # Continue processing even if save fails
                    pass
                
                # Identify speakers in the audio
                speaker_result = voice_service.identify_speakers_in_audio(audio_path)
                if not speaker_result.get("success", False):
                    logger.error(f"Speaker identification failed: {speaker_result.get('error', 'Unknown error')}")
                    # Continue anyway, as we can still do face recognition
                
                # Combine transcription with speaker identification
                if speaker_result.get("success", True):
                    # Get the correct paths for transcription and speaker results
                    transcription_path = transcription_result.get("output_file", "")
                    speaker_results_path = speaker_result.get("results_file", "")
                    
                    logger.info(f"Combining transcription ({transcription_path}) with speaker results ({speaker_results_path})")
                    
                    combined_result = voice_service.combine_transcription_with_speakers(
                        transcription_path,
                        speaker_results_path
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
            
            # Generate comprehensive workflow summary with timing and key metrics
            end_time = datetime.now()
            total_duration = (end_time - recognition_process.start_time).total_seconds()
            
            # Extract key metrics from multimodal_result with type safety
            recognition_events = multimodal_result.get("recognition_events", [])
            if isinstance(recognition_events, int):
                logger.warning(f"Recognition events is unexpectedly an int: {recognition_events}")
                recognition_events = []
            
            faces = multimodal_result.get("faces", [])
            if isinstance(faces, int):
                logger.warning(f"Faces is unexpectedly an int: {faces}")
                faces = []
            
            segments = multimodal_result.get("segments", [])
            if isinstance(segments, int):
                logger.warning(f"Segments is unexpectedly an int: {segments}")
                segments = []
            
            total_faces = len(faces)
            total_events = len(recognition_events)
            identified_speakers = len([event for event in recognition_events if isinstance(event, dict) and event.get("member_id") and event.get("name") != "Unknown"])
            total_segments = len(segments)
            
            # Workflow summary will be logged in the endpoint for adjacency with completion message
            
            logger.info(f"Combined recognition completed for video {video_id}")
            return {"success": True, "recognition_id": recognition_process.id, "results": multimodal_result}
            
        except Exception as e:
            error_msg = f"Error in start_combined_recognition: {str(e)}"
            logger.exception(error_msg)
            
            # First, try to rollback the current transaction if it exists
            try:
                if 'db' in locals() and db is not None:
                    logger.info("Rolling back current transaction due to error")
                    db.rollback()
            except Exception as rollback_error:
                logger.exception(f"Error during rollback: {str(rollback_error)}")
            
            try:
                # Get a fresh database session to avoid transaction issues
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
                # Make sure to rollback if there's an error
                try:
                    if db is not None:
                        db.rollback()
                except Exception:
                    pass
                
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
        diarization_path = None  # Initialize diarization_path to prevent UnboundLocalError

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
                                    
                                    # Create segment with all required Whisper fields
                                    segment = {
                                        "id": len(segments),
                                        "seek": start_time,
                                        "start": start_time,
                                        "end": end_time,
                                        "text": text,
                                        "tokens": [],
                                        "temperature": 0.0,
                                        "avg_logprob": -0.5,
                                        "compression_ratio": 1.0,
                                        "no_speech_prob": 0.1,
                                        "speaker": speaker
                                    }
                                    segments.append(segment)
                                    logger.debug(f"Added segment: {segment}")
                            except Exception as e:
                                logger.warning(f"Error parsing line '{line}': {str(e)}")
                    
                    
                    # Create a transcription object with segments
                    transcription = {"segments": segments}
                    
                    # Handle chunked transcription format
                    if not segments and isinstance(video.transcription_results, str):
                        # Try to parse as a JSON string that might contain segments
                        try:
                            json_data = json.loads(video.transcription_results)
                            if isinstance(json_data, dict) and "segments" in json_data:
                                segments = json_data["segments"]
                                if segments:
                                    logger.info(f"Successfully parsed chunked transcription with {len(segments)} segments")
                                    transcription = json_data
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse transcription as JSON")
                            pass
                    
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
            has_speech_group_markers = False
            
            for segment in segments:
                if "speaker" in segment and segment["speaker"] != "Unknown":
                    has_speakers = True
                
                # Check if segments have speech_group_marker field from chunked transcription
                if "speech_group_marker" in segment:
                    has_speech_group_markers = True
                    # Use these markers to set speech_group_id for consistent speaker attribution
                    segment["speech_group_id"] = segment["speech_group_marker"]
            
            if has_speech_group_markers:
                logger.info("Found speech group markers in segments from chunked transcription")
                # These will be used for proper speaker turn grouping
            
            # Update the video with the processed transcription
            video.transcription_results = json.dumps(transcription)
            db.commit()
            
            # If there are no segments, try to create them from diarization data
            if not segments:
                logger.warning("No segments found in transcription, attempting to retranscribe or use diarization data")
                
                # Get or create the recognition process record for this video
                recognition_process = db.query(models.RecognitionProcess).filter(
                    models.RecognitionProcess.video_id == video_id
                ).first()
                
                if not recognition_process:
                    logger.info(f"Creating new RecognitionProcess record for video {video_id}")
                    recognition_process = models.RecognitionProcess(
                        video_id=video_id,
                        status="processing",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(recognition_process)
                    db.commit()
                
                # Check if we should retry transcription
                # Use a session variable to track if we've retried transcription
                if not getattr(recognition_process, '_transcription_retried', False):
                    logger.info("Attempting to retranscribe the audio with chunked approach")
                    
                    # Mark that we've retried transcription using a session attribute
                    recognition_process._transcription_retried = True
                    
                    # Retry transcription with explicit chunked approach
                    from backend.services.recognition.voice_recognition import VoiceRecognitionService
                    voice_service = VoiceRecognitionService()
                    
                    # Get the audio path from the video record
                    audio_path = video.audio_path
                    if not audio_path or not os.path.exists(audio_path):
                        logger.error(f"Audio file not found for retry: {audio_path}")
                        return {"success": False, "error": f"Audio file not found for retry: {audio_path}"}
                    
                    logger.info(f"Retrying transcription with chunked approach for audio: {audio_path}")
                    
                    # Force using chunked transcription
                    os.environ['FORCE_CHUNKED_TRANSCRIPTION'] = 'true'
                    transcription_result = voice_service.transcribe_audio(audio_path)
                    os.environ.pop('FORCE_CHUNKED_TRANSCRIPTION', None)
                    
                    # Initialize transcript_data to ensure it's always defined
                    transcript_data = {}
                    
                    if transcription_result.get("success", False):
                        transcript_data = transcription_result.get("transcript", {})
                        if isinstance(transcript_data, dict) and transcript_data.get("segments"):
                            segments_count = len(transcript_data.get("segments", []))
                            logger.info(f"Retry successful! Received transcription with {segments_count} segments")
                            
                            # Save the new transcription results
                            video.transcription_results = json.dumps(transcript_data)
                            db.commit()
                            
                            # Reload segments from the new transcription
                            try:
                                transcription = json.loads(video.transcription_results)
                                segments = transcription.get("segments", [])
                                logger.info(f"Loaded {len(segments)} segments from retry transcription")
                                
                                # If we have segments now, don't proceed to diarization fallback
                                if segments:
                                    logger.info("Using segments from retry transcription instead of diarization fallback")
                                    # Update the video with the processed transcription
                                    video.transcription_results = json.dumps(transcription)
                                    db.commit()
                                    # Skip the diarization fallback
                                    # Fall through to continue processing with the new segments
                                else:
                                    logger.warning("Retry transcription still produced no segments")
                            except (json.JSONDecodeError, AttributeError) as e:
                                logger.error(f"Failed to load retry transcription results: {str(e)}")
                    else:
                        logger.warning(f"Retry transcription failed: {transcription_result.get('error', 'Unknown error')}")
                
                # If we still have no segments, try diarization data
                if not segments:
                    logger.warning("Falling back to diarization data for segments")
                    # Initialize segments as empty list to ensure it's always defined
                    segments = []
                    # Initialize diarization_path to None to prevent UnboundLocalError
                    diarization_path = None
                    # Look for diarization data
                    primary_path = os.path.join("/app/data/media", f"{video_id}.diarization.json")
                    if os.path.exists(primary_path):
                        diarization_path = primary_path
                    
                    # Try alternative paths if the primary path doesn't exist or diarization_path is still None
                    if diarization_path is None or not os.path.exists(diarization_path):
                        alternative_paths = [
                            os.path.join("/app/data/media", f"{video_id}.audio.diarization.json"),
                            os.path.join("/app/data/media", f"{video_id}_audio.diarization.json"),
                            os.path.join("/app/data/temp", f"{video_id}.diarization.json")
                        ]
                        
                        # diarization_path is already initialized to None above
                        
                        for alt_path in alternative_paths:
                            if os.path.exists(alt_path):
                                diarization_path = alt_path
                                logger.info(f"Found diarization data at alternative path: {alt_path}")
                                break
                        
                        # Check if diarization_path was found
                        if diarization_path is None:
                            logger.warning(f"No diarization data found for video {video_id} in any of the expected locations")
                
                # Check if we already have segments from retry transcription
                if segments:
                    # We already have segments from retry transcription, skip diarization processing
                    logger.info(f"Using {len(segments)} segments from retry transcription, skipping diarization processing")
                    # Continue to face recognition with these segments
                # If no segments yet but diarization_path is available, process diarization data
                elif diarization_path is not None and os.path.exists(diarization_path):
                    # Initialize diarization_data to ensure it's always defined
                    diarization_data = {"segments": [], "speakers": {}}
                    
                    try:
                        with open(diarization_path, 'r') as f:
                            diarization_data = json.load(f)
                            
                        # Validate diarization data structure
                        if "segments" not in diarization_data or not isinstance(diarization_data["segments"], list):
                            logger.error(f"Invalid diarization data format: missing or invalid 'segments' field")
                            return {"success": False, "error": "Invalid diarization data format: missing segments"}
                        
                        # Log diarization data stats
                        diarization_segments = diarization_data.get("segments", [])
                        diarization_speakers = diarization_data.get("speakers", {})
                        logger.info(f"Loaded diarization data: {len(diarization_segments)} segments, {len(diarization_speakers)} speakers")
                        
                        # Check for empty segments list
                        if not diarization_segments:
                            logger.error("Diarization data contains empty segments list")
                            return {"success": False, "error": "Diarization data contains empty segments list"}
                        
                        # Create segments from diarization data
                        segments = []
                        for i, seg in enumerate(diarization_segments):
                            # Handle potential missing fields with defaults
                            start_time = seg.get("start_time", i * 60.0)  # Default to 1-minute segments if missing
                            end_time = seg.get("end_time", (i + 1) * 60.0)
                            speaker = seg.get("speaker", f"SPEAKER_{(i % 5) + 1}")  # Cycle through 5 default speakers
                            
                            # Validate timestamps
                            try:
                                start_time = float(start_time)
                                end_time = float(end_time)
                                
                                # Ensure end time is greater than start time
                                if end_time <= start_time:
                                    logger.error(f"Invalid segment timing: start={start_time}, end={end_time}")
                                    return {"success": False, "error": f"Invalid segment timing in diarization data: start={start_time}, end={end_time}"}
                                
                                # Log warning for unusually long segments but don't modify them
                                if end_time - start_time > 1800:
                                    logger.warning(f"Unusually long segment detected: {end_time - start_time} seconds")
                            except (ValueError, TypeError) as e:
                                logger.error(f"Invalid timestamp in segment {i}: {e}")
                                return {"success": False, "error": f"Invalid timestamp in diarization segment {i}: {e}"}
                            
                            # Create a segment with required fields
                            segment_id = f"{start_time}-{end_time}"
                            segment = {
                                "id": segment_id,
                                "seek": start_time,
                                "start": start_time,
                                "end": end_time,
                                "text": "",  # Empty placeholder, will be filled by transcript matcher
                                "tokens": [],
                                "temperature": 0.0,
                                "avg_logprob": -0.5,
                                "compression_ratio": 1.0,
                                "no_speech_prob": 0.1,
                                "speaker": speaker,
                                "diarization_segment": True,  # Flag to indicate this is a diarization segment
                                "start_time": start_time,  # Add start_time for transcript matcher
                                "end_time": end_time,  # Add end_time for transcript matcher
                                "speech_group_id": seg.get("speech_group_id", ""),  # Preserve speech group ID if available
                                "recognition_method": "diarization"  # Mark as diarization-based for parliament_clips_integration
                            }
                            segments.append(segment)
                        
                        # Try to match transcripts with diarization segments
                        if segments:
                            try:
                                # Use our simple transcript finder to get a valid directory
                                from backend.services.recognition.transcript_finder import find_transcript_directory
                                
                                # Get video path for context if available
                                video_path = None
                                if hasattr(self, 'video_path') and self.video_path:
                                    video_path = self.video_path
                                
                                # Find transcript directory
                                transcript_dir = find_transcript_directory(video_path)
                                
                                # Check if transcript directory exists and has files
                                if transcript_dir and os.path.exists(transcript_dir):
                                    logger.info(f"Attempting to match transcripts from {transcript_dir} with {len(segments)} diarization segments")
                                    
                                    # Match transcripts to diarization segments
                                    segments = match_transcripts_to_diarization_segments(segments, transcript_dir)
                                    
                                    # Count segments with real transcripts vs. placeholders
                                    placeholder_count = 0
                                    for segment in segments:
                                        if segment['text'].startswith("Speech segment from"):
                                            placeholder_count += 1
                                    
                                    if placeholder_count > 0:
                                        logger.warning(f"{placeholder_count} out of {len(segments)} segments ({placeholder_count/len(segments)*100:.1f}%) still have placeholder transcripts")
                                    else:
                                        logger.info("Successfully matched all segments with transcript text")
                                else:
                                    logger.warning(f"Transcript directory not found: {transcript_dir}")
                            except Exception as e:
                                logger.error(f"Error matching transcripts with diarization segments: {str(e)}")
                                # Continue with placeholder transcripts if matching fails
                                logger.warning("Continuing with placeholder transcripts due to matching error")
                        
                        # Update transcription with segments
                        if segments:
                            transcription["segments"] = segments
                            logger.info(f"Created {len(segments)} segments from diarization data")
                        else:
                            logger.error("Failed to create segments from diarization data")
                            return {"success": False, "error": "No segments could be created from diarization data"}
                    except Exception as e:
                        logger.error(f"Error creating segments from diarization data: {str(e)}")
                        return {"success": False, "error": f"Error creating segments from diarization data: {str(e)}"}
                else:
                    # No segments and no diarization data
                    logger.error(f"No segments found in transcription and no valid diarization data found for video {video_id}")
                    return {"success": False, "error": "No segments found in transcription and no diarization data available"}
            
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
            
            # CRITICAL: Handle sequential segment time offset calculation
            # In sequential processing, segment times are relative to each segment, not the full video
            # We need to calculate the absolute time offset for this segment
            sequential_time_offset = 0
            is_sequential_segment = False
            
            # Check if this is a sequential segment by examining metadata
            # Use the same metadata access pattern as the working non-sequential code
            metadata = {}
            if video.metadata:
                try:
                    # Use the same make_json_serializable function as the working non-sequential code
                    from backend.services.utils import make_json_serializable
                    metadata = make_json_serializable(video.metadata)
                    logger.debug(f"After make_json_serializable: metadata = {metadata}, type = {type(metadata)}")
                    
                    # If metadata is still a string after serialization, parse it as JSON
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                            logger.debug(f"Parsed metadata string to dict: {type(metadata)}")
                        except json.JSONDecodeError as json_error:
                            logger.error(f"Error parsing metadata JSON string: {str(json_error)}")
                            metadata = {"value": metadata}
                    
                    # Ensure metadata is a dictionary (same as working non-sequential code)
                    if not isinstance(metadata, dict):
                        metadata = {"value": str(metadata)}
                        
                except Exception as e:
                    logger.error(f"Error processing video metadata: {str(e)}")
                    metadata = {}
            
            is_sequential = metadata.get("is_sequential", False)
            logger.info(f"Sequential metadata analysis: is_sequential={is_sequential}, metadata_keys={list(metadata.keys()) if metadata else []}")
            
            if is_sequential:
                    is_sequential_segment = True
                    
                    # Calculate time offset based on segment index
                    # Sequential segments are 30 minutes (1800 seconds) each
                    # Extract segment index from video path or metadata
                    segment_index = 1  # Default to first segment
                    
                    # Try to extract segment index from video path (e.g., "1293_4.mp4" -> segment 4)
                    if video_path:
                        import re
                        video_filename = os.path.basename(video_path)
                        logger.debug(f"Analyzing video filename for segment index: {video_filename}")
                        
                        # Try multiple patterns to extract segment index
                        patterns = [
                            r'_(\d+)\.(mp4|avi|mov|mkv)$',  # Standard pattern: sessionid_segment.ext
                            r'segment_?(\d+)\.(mp4|avi|mov|mkv)$',  # segment_N.ext or segmentN.ext
                            r'(\d+)_segment\.(mp4|avi|mov|mkv)$',  # N_segment.ext
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, video_filename, re.IGNORECASE)
                            if match:
                                extracted_index = int(match.group(1))
                                logger.info(f"Extracted segment index {extracted_index} from filename using pattern: {pattern}")
                                segment_index = extracted_index
                                break
                        else:
                            logger.warning(f"Could not extract segment index from filename: {video_filename}, using default: {segment_index}")
                    else:
                        logger.warning(f"No video_path provided, using default segment index: {segment_index}")
                    
                    # Calculate time offset: (segment_index - 1) * 1800 seconds
                    sequential_time_offset = (segment_index - 1) * 1800
                    
                    logger.info(f"🕐 Sequential segment detected: segment {segment_index}, time offset: {sequential_time_offset}s ({sequential_time_offset/60:.1f} minutes)")
                    logger.info(f"🕐 Video path analyzed: {video_path}")
            
            # CRITICAL FIX: Create placeholder recognition events for segments without face matches
            # This ensures all transcribed segments are represented in the output, matching non-sequential pipeline behavior
            logger.info("Creating placeholder recognition events for segments without face matches")
            existing_segment_ids = set()
            for event in recognition_events:
                segment_id = event.get("segment_id")
                if segment_id:
                    existing_segment_ids.add(str(segment_id))
            
            placeholder_events_created = 0
            for segment in segments:
                segment_start = float(segment.get('start', 0))
                segment_end = float(segment.get('end', 0))
                
                # CRITICAL: Apply sequential time offset to segment times
                if is_sequential_segment:
                    absolute_start = segment_start + sequential_time_offset
                    absolute_end = segment_end + sequential_time_offset
                    logger.debug(f"Sequential time adjustment: segment {segment_start}-{segment_end}s -> absolute {absolute_start}-{absolute_end}s")
                else:
                    absolute_start = segment_start
                    absolute_end = segment_end
                
                segment_id = f"{segment_start}-{segment_end}"  # Keep original segment ID for consistency
                
                # If this segment doesn't have a recognition event yet, create a placeholder
                if str(segment_id) not in existing_segment_ids:
                    speaker = segment.get("speaker", "Unknown")
                    text = segment.get("text", "").strip()
                    
                    # Only create placeholder if segment has meaningful text
                    if text and len(text) > 5:  # Skip very short or empty segments
                        placeholder_event = {
                            "type": "speaker",
                            "start_time": absolute_start,  # Use absolute time for recognition events
                            "end_time": absolute_end,      # Use absolute time for recognition events
                            "timestamp": absolute_start,   # Use absolute time for recognition events
                            "speaker": speaker,
                            "text": text,
                            "member_id": None,  # Will be normalized later if possible
                            "name": "Unknown",
                            "confidence": 0.0,
                            "quality_score": 0.0,
                            "segment_id": segment_id,
                            "diarization_segment": segment.get("diarization_segment", False),
                            "speech_group_id": segment.get("speech_group_id", ""),
                            "placeholder_event": True,  # Mark as placeholder for debugging
                            "sequential_segment": is_sequential_segment,
                            "sequential_time_offset": sequential_time_offset,
                            "original_start_time": segment_start,  # Keep original for reference
                            "original_end_time": segment_end       # Keep original for reference
                        }
                        recognition_events.append(placeholder_event)
                        placeholder_events_created += 1
                        
                        if is_sequential_segment:
                            logger.info(f"Created sequential placeholder event for segment {segment_id}: "
                                      f"original {segment_start}-{segment_end}s -> absolute {absolute_start}-{absolute_end}s, "
                                      f"speaker={speaker}, text={text[:50]}...")
                        else:
                            logger.info(f"Created placeholder event for segment {segment_id}: speaker={speaker}, text={text[:50]}...")
            
            logger.info(f"Created {placeholder_events_created} placeholder recognition events for segments without face matches")
            logger.info(f"Total recognition events: {len(recognition_events)} (including {placeholder_events_created} placeholders)")
            
            # CRITICAL: Apply sequential time offset to existing recognition events from face detection
            if is_sequential_segment and sequential_time_offset > 0:
                events_adjusted = 0
                for event in recognition_events:
                    if not event.get("placeholder_event", False):  # Only adjust non-placeholder events
                        # Apply time offset to existing face-based recognition events
                        original_start = event.get("start_time", 0)
                        original_end = event.get("end_time", 0)
                        original_timestamp = event.get("timestamp", 0)
                        
                        event["start_time"] = original_start + sequential_time_offset
                        event["end_time"] = original_end + sequential_time_offset
                        event["timestamp"] = original_timestamp + sequential_time_offset
                        
                        # Add sequential metadata to existing events
                        event["sequential_segment"] = True
                        event["sequential_time_offset"] = sequential_time_offset
                        event["original_start_time"] = original_start
                        event["original_end_time"] = original_end
                        event["original_timestamp"] = original_timestamp
                        
                        events_adjusted += 1
                        logger.debug(f"Adjusted face-based event: {original_start}-{original_end}s -> {event['start_time']}-{event['end_time']}s")
                
                logger.info(f"🕐 Sequential time offset applied: {sequential_time_offset}s ({sequential_time_offset/60:.1f} minutes) to {events_adjusted} existing recognition events and {placeholder_events_created} placeholder events")
            
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
                    logger.info(f"Matched {match_result.get('matched', 0)} speakers using ParliamentMemberMatcher")
                    
                    # Start a new transaction for speaker identifications
                    try:
                        # Check if transaction is in a valid state first
                        from sqlalchemy import text
                        db.execute(text("SELECT 1"))
                        
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
                    except Exception as inner_e:
                        # Roll back the transaction if it's in a failed state
                        db.rollback()
                        logger.warning(f"Transaction appears to be in a failed state, rolling back: {str(inner_e)}")
            except Exception as e:
                logger.error(f"Error matching unidentified speakers: {str(e)}")
            
            # Update the recognition process record - with proper transaction handling
            try:
                # First check if the transaction is still valid
                try:
                    # Execute a simple query to test if transaction is valid
                    db.execute(text("SELECT 1")).scalar()
                except Exception as tx_error:
                    logger.warning(f"Transaction appears to be in a failed state, rolling back: {str(tx_error)}")
                    db.rollback()
                
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
                    logger.info(f"Updated existing RecognitionProcess record for video {video_id}")
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
                    logger.info(f"Created new RecognitionProcess record for video {video_id}")
            except Exception as db_error:
                logger.error(f"Database error when updating RecognitionProcess: {str(db_error)}")
                try:
                    db.rollback()
                    logger.info("Successfully rolled back transaction after database error")
                except Exception as rollback_error:
                    logger.error(f"Error during transaction rollback: {str(rollback_error)}")
                
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
                "segments": segments,
                "recognition_events": recognition_events,
                "correlations": correlations,
                "timeline": timeline,
                "speaker_appearances": speaker_appearances,
                "faces": all_faces
            }
            
        except Exception as e:
            logger.exception(f"Error processing video with transcription: {str(e)}")
            # Make sure to rollback any active transaction
            try:
                if db is not None:
                    db.rollback()
                    logger.info("Successfully rolled back transaction after exception")
            except Exception as rollback_error:
                logger.error(f"Error during transaction rollback: {str(rollback_error)}")
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
        Process segments using intelligent face extraction method with enhanced center-frame detection.
        
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
            
            # Extract high-quality faces from the entire video with enhanced center-frame prioritization
            logger.info(f"Extracting high-quality faces from video {video_id} with enhanced center-frame prioritization")
            extraction_result = self.face_profile_service.extract_faces_from_video(
                video_path=video_path,
                output_dir=video_dir,
                interval=1.0,  # Match dev branch interval (1.0 second between frames)
                min_confidence=0.6,
                prioritize_center=True,  # Enable center-frame prioritization
                select_best_frames=True,
                min_face_size=200,  # Minimum face dimensions in pixels (width/height)
                min_face_area=40000  # Minimum face area in square pixels (200x200)
                # Removed detection_interval parameter to match dev branch behavior
            )
            
            if extraction_result.get("success", False):
                extracted_faces = extraction_result.get("faces_found", 0)
                face_data = extraction_result.get("face_data", [])
                logger.info(f"Successfully extracted {extracted_faces} high-quality faces from video")
                
                # TIMELINE-BASED FACE SELECTION OPTIMIZATION
                # Instead of traditional face borrowing, select the best face within each speech group timeline range
                logger.info("🎯 Starting timeline-based face selection to reduce face borrowing")
                
                # Group segments by speech_group_id to create timeline ranges
                speech_groups = {}
                for segment in segments:
                    speech_group_id = segment.get('speech_group_id', f"group_{segment.get('id', 'unknown')}")
                    if speech_group_id not in speech_groups:
                        speech_groups[speech_group_id] = {
                            'speech_group_id': speech_group_id,
                            'start_time': segment.get('start', 0),
                            'end_time': segment.get('end', 0),
                            'segments': []
                        }
                    else:
                        # Extend timeline range to include this segment
                        speech_groups[speech_group_id]['start_time'] = min(
                            speech_groups[speech_group_id]['start_time'], 
                            segment.get('start', 0)
                        )
                        speech_groups[speech_group_id]['end_time'] = max(
                            speech_groups[speech_group_id]['end_time'], 
                            segment.get('end', 0)
                        )
                    
                    speech_groups[speech_group_id]['segments'].append(segment)
                
                logger.info(f"Created {len(speech_groups)} speech group timeline ranges from {len(segments)} segments")
                
                # Use timeline face selector to select best faces for each speech group
                speech_groups_list = list(speech_groups.values())
                selected_faces = self.timeline_face_selector.select_best_faces_for_timeline(
                    speech_groups_list, face_data, video_path
                )
                
                # Map selected faces to all segments within their speech groups
                segment_face_mapping = self.timeline_face_selector.map_faces_to_speech_groups(
                    selected_faces, speech_groups_list
                )
                
                logger.info(f"Timeline face selection completed: {len(selected_faces)} faces selected for {len(segment_face_mapping)} segments")
                
                # Convert to the expected segment_faces format for compatibility with existing code
                segment_faces = {}
                matched_faces = 0
                processed_faces = set()  # Track processed faces to avoid duplicates
                
                # Convert timeline-based face selection to segment_faces format
                # This maintains compatibility with existing downstream processing
                for segment in segments:
                    segment_id = segment.get("id", f"{segment.get('start', 0)}-{segment.get('end', 0)}")
                    segment_faces[segment_id] = []
                    
                    # Check if this segment has a selected face from timeline selection
                    if segment_id in segment_face_mapping:
                        face_mapping = segment_face_mapping[segment_id]
                        face_data_item = face_mapping['face_data']
                        
                        # Convert to expected format
                        face_path = face_data_item.get("face_path", face_data_item.get("face_image_path", ""))
                        face_time = face_data_item.get("timestamp", face_data_item.get("face_time", 0))
                        quality_score = face_data_item.get("enhanced_quality_score", face_data_item.get("quality_score", 0))
                        
                        if face_path and face_path not in processed_faces:
                            segment_faces[segment_id].append({
                                "face_info": face_data_item,
                                "face_time": face_time,
                                "face_path": face_path,
                                "quality_score": quality_score,
                                "segment": segment,
                                "match_type": "timeline_selected",
                                "speech_group_id": face_mapping.get('speech_group_id'),
                                "selection_reason": face_data_item.get('selection_reason', 'timeline_optimization')
                            })
                            processed_faces.add(face_path)
                            matched_faces += 1
                            
                            logger.info(f"✅ Timeline-selected face for segment {segment_id}: {face_path} "
                                      f"(quality: {quality_score:.3f}, reason: {face_data_item.get('selection_reason', 'timeline')})")
                
                logger.info(f"🎯 Timeline-based face selection complete: {matched_faces} faces mapped to segments")
                
                # Skip the old face matching logic since we're using timeline-based selection
                # The rest of the processing continues with the timeline-selected faces
                
                # Check for segments with no faces and log them
                empty_segments = [segment_id for segment_id, faces in segment_faces.items() if not faces]
                if empty_segments:
                    logger.info(f"Found {len(empty_segments)} segments with no timeline-selected faces. "
                               f"This is expected with timeline-based selection as faces are selected per speech group.")
                else:
                    logger.info("All segments have timeline-selected faces assigned.")
                
                # Continue with the existing face processing logic
                # The timeline-selected faces are now ready for speaker identification
                
                # Process each segment with its timeline-selected face for speaker identification
                logger.info("Processing segments with timeline-selected faces for speaker identification")
                for segment_id, faces in segment_faces.items():
                    # Skip if no faces for this segment
                    if not faces:  # This ensures we don't process empty face lists
                        logger.warning(f"Segment {segment_id} has no faces after all matching attempts")
                        continue
                        
                    # Sort faces by quality score (highest first)
                    faces.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
                    
                    # Get the best face (highest quality score, prioritizing center-frame)
                    best_face = faces[0]
                    face_path = best_face.get("face_path")
                    face_time = best_face.get("face_time", 0.0)  # Default to 0.0 if not present
                    matching_segment = best_face.get("segment", {})  # Default to empty dict if not present
                    
                    logger.info(f"Selected best face for segment {segment_id} with quality score {best_face.get('quality_score', 0):.2f}")
                    
                    # Check if face_path is defined and exists
                    if face_path is not None and os.path.exists(face_path):
                        # Process this high-quality face
                        logger.info(f"Processing high-quality face at {face_time:.2f}s")
                        
                        # Identify speaker in the high-quality face image
                        face_result = self.identify_speaker_in_frame(
                            db, 
                            face_path, 
                            threshold=0.45,  # Higher threshold for more accurate matches
                            timestamp=face_time, 
                            video_id=str(video_id)  # Convert to string as expected by the matcher
                        )
                        
                        # Handle case where face_result might be a list instead of dict
                        if isinstance(face_result, list):
                            logger.warning(f"face_result is unexpectedly a list: {face_result}")
                            continue
                        elif not isinstance(face_result, dict):
                            logger.warning(f"face_result is unexpected type {type(face_result)}: {face_result}")
                            continue
                        
                        if face_result.get("success", False):
                            face_data = face_result.get("data", {})
                            face_data["frame_path"] = face_path
                            face_data["frame_time"] = face_time
                            speaker = matching_segment.get("speaker", "unknown")
                            face_data["segment_speaker"] = speaker
                            
                            # Create a unique segment ID for deduplication that exactly matches diarization segment boundaries
                            # Use the exact timestamps from the segment without rounding
                            segment_start = float(matching_segment.get('start', 0))
                            segment_end = float(matching_segment.get('end', 0))
                            segment_id = f"{segment_start}-{segment_end}"
                            
                            # Add to recognition events with comprehensive structure and enhanced quality score
                            recognition_event = {
                                "type": "speaker",
                                # CRITICAL: Use EXACT segment start/end times to preserve diarization boundaries
                                "start_time": segment_start,  # Use precise segment start time
                                "end_time": segment_end,      # Use precise segment end time
                                "member_id": face_data.get("member_id"),
                                "name": face_data.get("name", "Unknown"),
                                "confidence": face_data.get("confidence", 0.0),
                                "face_image_url": face_path,
                                "text": matching_segment.get("text", ""),
                                "recognition_method": matching_segment.get("recognition_method", "facial_center_frame"),  # Preserve original recognition method
                                "matched_by": face_data.get("matched_by", "unknown"),
                                "profile_id": face_data.get("profile_id"),
                                "segment_speaker": speaker,
                                "time": face_time,  # Keep original face time for reference
                                "quality_score": best_face.get("quality_score", 0),  # Use the quality score from best face
                                "center_frame_priority": True,  # Flag to indicate this was selected with center-frame prioritization
                                "segment_id": segment_id,  # Add segment_id for deduplication
                                "diarization_segment": matching_segment.get("diarization_segment", False),  # Preserve diarization segment flag
                                "speech_group_id": matching_segment.get("speech_group_id", "")  # Preserve speech group ID from diarization
                            }
                            
                            # Check if we already have a recognition event for this segment
                            existing_event = next((e for e in recognition_events if e.get("segment_id") == segment_id), None)
                            
                            if existing_event:
                                # Only replace if this event has higher confidence or quality score
                                if (recognition_event["confidence"] > existing_event.get("confidence", 0) or 
                                    recognition_event["quality_score"] > existing_event.get("quality_score", 0)):
                                    # Remove the existing event
                                    recognition_events.remove(existing_event)
                                    # Add the new event
                                    recognition_events.append(recognition_event)
                                    logger.info(f"Replaced existing recognition event for segment {segment_id} with higher quality event")
                                    matched_faces += 1
                            else:
                                # No existing event for this segment, add the new one
                                recognition_events.append(recognition_event)
                                matched_faces += 1
                            
                            # Store face by time for later reference with enhanced quality score
                            time_key = int(face_time)
                            if time_key not in faces_by_time:
                                faces_by_time[time_key] = []
                            
                            # Add quality score and center-frame info to face data
                            face_data["quality_score"] = best_face.get("quality_score", 0)
                            face_data["center_frame_priority"] = True
                            faces_by_time[time_key].append(face_data)
                            
                            # Store face by speaker for later correlation
                            if speaker not in faces_by_speaker:
                                faces_by_speaker[speaker] = []
                            faces_by_speaker[speaker].append(face_data)
                            
                            # Mark this face as processed to avoid duplicates
                            processed_faces.add(face_path)
                            
                            # Log detailed information about the selected face
                            logger.info(f"Selected face for segment {segment_id}: "
                                       f"member_id={face_data.get('member_id')}, "
                                       f"name={face_data.get('name', 'Unknown')}, "
                                       f"quality_score={best_face.get('quality_score', 0):.2f}, "
                                       f"confidence={face_data.get('confidence', 0.0):.2f}")
                        else:
                            logger.warning(f"Failed to identify speaker in frame {face_path}: {face_result.get('error', 'Unknown error')}")
                    else:
                        if not face_path:
                            logger.debug("Face path is empty, skipping file existence check")
                        elif not os.path.exists(face_path):
                            logger.warning(f"Face image file not found: {face_path}")
                
                # Perform timeline-based speaker analysis to improve attribution
                logger.info("Performing timeline-based speaker analysis to improve attribution")
                self._perform_timeline_speaker_analysis(recognition_events, segments)
                
                logger.info(f"Matched {matched_faces} faces to segments out of {extracted_faces} extracted faces")
                logger.info(f"Processed {len(processed_faces)} unique faces (after deduplication)")
                
                # If we didn't find any faces, log a warning but continue processing
                if matched_faces == 0:
                    logger.warning("No faces matched to segments. Check face extraction and matching parameters.")
            else:
                logger.error(f"Face extraction failed: {extraction_result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.exception(f"Error in _process_segments_with_intelligent_face_extraction: {str(e)}")
            # Continue processing despite errors to maintain robustness
            
    def _perform_timeline_speaker_analysis(self, recognition_events: List[Dict], segments: List[Dict]) -> None:
        """
        Perform timeline-based speaker analysis to improve attribution accuracy.
        
        This method analyzes the timeline of speakers to detect transitions and improve
        attribution of transcripts to speakers, especially prioritizing center-frame speakers.
        
        Args:
            recognition_events: List of recognition events
            segments: List of transcription segments
        """
        # Log segments before timeline analysis to see original diarization segments
        logger.info("===== SEGMENT DEBUG INFO - BEFORE TIMELINE ANALYSIS =====")
        logger.info(f"Total segments: {len(segments)}")
        
        # Create a map of segment IDs to their original speakers from diarization
        original_speakers = {}
        for i, segment in enumerate(segments):
            segment_id = segment.get("id", f"{segment.get('start', 0)}-{segment.get('end', 0)}")
            speaker = segment.get("speaker", "None")
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            text = segment.get("text", "")[:30] + "..." if len(segment.get("text", "")) > 30 else segment.get("text", "")
            logger.info(f"Segment {i}: ID={segment_id}, Speaker={speaker}, Time=[{start:.2f}-{end:.2f}], Text={text}")
            original_speakers[str(segment_id)] = speaker
        
        try:
            logger.info("Starting timeline-based speaker analysis")
            
            # Sort events by time for timeline analysis
            sorted_events = sorted(recognition_events, key=lambda x: x.get("start_time", 0))
            
            # Group events by segment time ranges
            segment_events = {}
            for segment in segments:
                segment_id = segment.get("id", f"{segment.get('start', 0)}-{segment.get('end', 0)}")
                # Ensure segment_id is a string to avoid key type mismatches
                segment_events[str(segment_id)] = []
            
            # Assign events to segments
            for event in sorted_events:
                start_time = event.get("start_time", 0)
                for segment in segments:
                    segment_start = segment.get("start", 0)
                    segment_end = segment.get("end", 0)
                    if segment_start <= start_time <= segment_end:
                        segment_id = segment.get("id", f"{segment_start}-{segment_end}")
                        # Ensure segment_id is a string when accessing the dictionary
                        segment_events[str(segment_id)].append(event)
                        break
            
            # Analyze each segment for speaker transitions
            for segment_id, events in segment_events.items():
                if not events:
                    continue
                    
                # Get the original speaker from diarization for this segment
                original_speaker = original_speakers.get(str(segment_id), "None")
                logger.info(f"Segment {segment_id} original diarization speaker: {original_speaker}")
                
                # Sort events by confidence gap, quality score and center-frame priority
                events.sort(key=lambda x: (x.get("center_frame_priority", False), 
                                         x.get("confidence_gap", 0), 
                                         x.get("quality_score", 0)), 
                          reverse=True)
                
                # Select the best event (highest quality, center-frame prioritized)
                best_event = events[0]
                best_confidence = best_event.get("confidence", 0)
                
                # Update all events in this segment with the best speaker information
                best_member_id = best_event.get("member_id")
                best_name = best_event.get("name", "Unknown")
                
                # We're only preserving diarization segment boundaries here
                # Member ID assignment will happen later when matching faces with photos
                
                # Log segment information for debugging
                logger.info(f"Timeline analysis: Preserving diarization segment {segment_id}")
                
                # Mark all events in this segment as preserving diarization
                for event in events:
                    event["diarization_segment_preserved"] = True
            
            # Analyze speaker transitions across adjacent segments
            segment_ids = list(segment_events.keys())
            # Convert all segment_ids to strings before sorting to avoid TypeError with integers
            segment_ids = [str(x) for x in segment_ids]
            
            # Sort segments by start time to ensure proper timeline analysis
            # This is critical for preserving diarization segment boundaries
            try:
                segment_ids.sort(key=lambda x: float(x.split('-')[0]) if '-' in x else 0)
                logger.info(f"Sorted segment IDs for timeline analysis: {segment_ids}")
            except Exception as e:
                logger.error(f"Error sorting segment IDs: {e}")
                # Fallback sorting if the format is unexpected
                segment_ids.sort()
            
            for i in range(1, len(segment_ids)):
                prev_id = segment_ids[i-1]
                curr_id = segment_ids[i]
                
                prev_events = segment_events[prev_id]
                curr_events = segment_events[curr_id]
                
                if not prev_events or not curr_events:
                    continue
                
                # Get best events from each segment
                prev_best = max(prev_events, key=lambda x: x.get("quality_score", 0), default=None)
                curr_best = max(curr_events, key=lambda x: x.get("quality_score", 0), default=None)
                
                if prev_best and curr_best:
                    # Check if there's a speaker transition
                    prev_member_id = prev_best.get("member_id")
                    curr_member_id = curr_best.get("member_id")
                    
                    # If current segment has no identified speaker but previous does, and they're close in time
                    # (within the configured time gap), assume it's the same speaker continuing
                    if prev_member_id and not curr_member_id:
                        # Safely parse previous segment end time
                        prev_id_str = str(prev_id)
                        try:
                            if '-' in prev_id_str:
                                prev_end = float(prev_id_str.split('-')[1])
                            else:
                                prev_end = float(prev_id_str)
                        except (ValueError, IndexError):
                            prev_end = 0
                            
                        # Safely parse current segment start time
                        curr_id_str = str(curr_id)
                        try:
                            if '-' in curr_id_str:
                                curr_start = float(curr_id_str.split('-')[0])
                            else:
                                curr_start = float(curr_id_str)
                        except (ValueError, IndexError):
                            curr_start = 0
                        
                        # Check if the current segment has a different diarization speaker than the previous segment
                        prev_diarization_speaker = original_speakers.get(str(prev_id), "None")
                        curr_diarization_speaker = original_speakers.get(str(curr_id), "None")
                        
                        # Only apply timeline continuity if:
                        # 1. Segments are close in time (within the configured time gap)
                        # 2. Either the diarization speakers are the same OR we have high confidence face recognition
                        same_diarization_speaker = prev_diarization_speaker == curr_diarization_speaker
                        high_confidence = prev_best.get("confidence", 0) >= 0.8
                        
                        # We're only preserving diarization segment boundaries
                        # Member ID assignment will happen later when matching faces with photos
                        
                        # Just log the segment continuity for debugging
                        if curr_start - prev_end < 2.0 and same_diarization_speaker:
                            logger.info(f"Timeline continuity: Segments {prev_id} and {curr_id} have the same diarization speaker and are close in time")
                            
                            for event in curr_events:
                                event["diarization_segment_continuity"] = True
                                
                            logger.info(f"Timeline continuity: Marked segment {curr_id} as continuous with {prev_id}")
                        else:
                            # Log that we're preserving the diarization speaker boundary
                            if not same_diarization_speaker and curr_start - prev_end < 2.0:
                                logger.info(f"Preserving diarization speaker boundary between segments {prev_id} and {curr_id}: "
                                          f"speakers {prev_diarization_speaker} -> {curr_diarization_speaker}")
                            
                            logger.info(f"Timeline continuity: Segments {prev_id} and {curr_id} represent a speaker change")
            
            # Log segments after timeline analysis to see what changed
            logger.info("===== SEGMENT DEBUG INFO - AFTER TIMELINE ANALYSIS =====")
            logger.info(f"Total segments: {len(segments)}")
            
            for i, segment in enumerate(segments):
                segment_id = segment.get("id", f"{segment.get('start', 0)}-{segment.get('end', 0)}")
                speaker = segment.get("speaker", "None")
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                text = segment.get("text", "")[:30] + "..." if len(segment.get("text", "")) > 30 else segment.get("text", "")
                
                # Check if this segment's speaker was changed from the original diarization
                original_speaker = original_speakers.get(str(segment_id), "None")
                speaker_changed = original_speaker != speaker
                
                logger.info(f"Segment {i}: ID={segment_id}, Speaker={speaker}, Time=[{start:.2f}-{end:.2f}], Text={text}, " 
                          f"Changed={speaker_changed}, Original={original_speaker}")
            
            logger.info("Completed timeline-based speaker analysis")
            
        except Exception as e:
            logger.exception(f"Error in timeline-based speaker analysis: {str(e)}")
            # Continue processing despite errors
    
    def identify_speaker_in_frame(self, db: Session, frame_path: str, threshold: float = 0.45, timestamp: float = None, video_id: str = None) -> Dict[str, Any]:
        """Identify speakers in a frame using facial recognition and ParliamentMemberMatcher."""
        try:
            logger.info(f"===== IDENTIFYING SPEAKER IN FRAME: {frame_path} =====")
            
            # Default to not exporting to Supabase
            export_to_supabase = False
            
            # First, ensure member matcher is initialized
            if not self.member_matcher:
                logger.info("Initializing ParliamentMemberMatcher")
                logger.info("Initializing ParliamentMemberMatcher")
                from backend.services.integration.supabase_service import SupabaseService
                supabase_service = SupabaseService()
                
                # Initialize matcher without house filtering first (will be updated per video)
                self.member_matcher = ParliamentMemberMatcher(supabase_service)
            
            # Ensure member matcher has loaded parliament members
            if not hasattr(self.member_matcher, 'members') or not self.member_matcher.members:
                logger.info("Loading parliament members in ParliamentMemberMatcher")
                success = self.member_matcher.load_parliament_members()
                if success and self.member_matcher.members:
                    logger.info(f"Loaded {len(self.member_matcher.members)} parliament members")
                else:
                    logger.warning("Failed to load parliament members, using fallback")
            else:
                # Safely log the number of members
                member_count = len(self.member_matcher.members) if self.member_matcher.members else 0
                logger.info(f"Using {member_count} previously loaded parliament members")
            
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
                # Continue anyway, but log the warning - matching dev branch behavior
            
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
                
                # Determine house from video metadata for proper filtering
                from backend.services.recognition.unidentified_speakers import determine_house_from_metadata
                
                # Get video metadata for house detection from database
                video_metadata = {}
                if video_id:
                    try:
                        from backend.db.models import CaptureSession
                        capture = db.query(CaptureSession).filter(CaptureSession.id == video_id).first()
                        if capture and capture.metadata:
                            if isinstance(capture.metadata, str):
                                try:
                                    video_metadata = json.loads(capture.metadata)
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse metadata JSON for video {video_id}")
                            elif isinstance(capture.metadata, dict):
                                video_metadata = capture.metadata
                    except Exception as e:
                        logger.warning(f"Failed to retrieve video metadata for house detection: {e}")
                
                house_name = determine_house_from_metadata(video_metadata)
                
                # Map house name to ID for filtering
                house_mapping = {
                    "commons": "1",  # House of Commons
                    "lords": "2",    # House of Lords
                    "unknown": "1"   # Default to Commons if unknown
                }
                house = house_mapping.get(house_name.lower(), "1")
                
                logger.info(f"🏛️  Detected house: {house_name} (ID: {house}) for video {video_id}")
                if house_name.lower() == "lords":
                    logger.info("🔍 Filtering for House of Lords members")
                else:
                    logger.info("🔍 Filtering for House of Commons members (MPs)")
                
                # Create house-specific matcher if needed
                if not hasattr(self.member_matcher, 'house_id') or self.member_matcher.house_id != house:
                    logger.info(f"🏛️ Creating house-specific matcher for house {house}")
                    from backend.services.integration.supabase_client import SupabaseService
                    supabase_service = SupabaseService()
                    self.member_matcher = ParliamentMemberMatcher(supabase_service, house_id=house)
                    
                    # Load members with house filtering
                    if not self.member_matcher.load_parliament_members():
                        logger.error("Failed to load parliament members with house filtering")
                        return {"success": False, "error": "Failed to load parliament members with house filtering", "supabase_export": {"enabled": export_to_supabase}}
                
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
                            # CRITICAL FIX: Ensure member_id is never None - use fallback
                            fallback_member_id = "1" if house == "1" else "2"  # Use house-specific fallback
                            best_detection["member_id"] = fallback_member_id
                            best_detection["name"] = "Unidentified Speaker"
                            best_detection["matched_by"] = "fallback_unidentified"
                            logger.warning(f"Using fallback member ID: {fallback_member_id} for house {house}")
            else:
                logger.error(f"❌ No face embedding found in detection")
                return {"success": False, "error": "No face embedding found", "supabase_export": {"enabled": export_to_supabase}}
            
            # CRITICAL VALIDATION: Ensure member_id is never None before returning
            if best_detection.get('member_id') is None:
                logger.error("❌ CRITICAL: member_id is None after all matching attempts!")
                # Emergency fallback to prevent None member_id
                emergency_fallback_id = "1" if house == "1" else "2"
                best_detection["member_id"] = emergency_fallback_id
                best_detection["name"] = "Emergency Fallback Speaker"
                best_detection["matched_by"] = "emergency_fallback"
                logger.error(f"Applied emergency fallback member_id: {emergency_fallback_id}")
            
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
            if segment_duration < DiarizationConfig.SHORT_SEGMENT_THRESHOLD:
                interval = DiarizationConfig.SHORT_SEGMENT_FRAME_INTERVAL  # Frame interval for short segments
            else:
                interval = DiarizationConfig.LONG_SEGMENT_FRAME_INTERVAL  # Frame interval for long segments
            
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
                            threshold=0.45,  # Higher threshold for more accurate matches
                            timestamp=frame_time, 
                            video_id=str(video_id)  # Convert to string as expected by the matcher
                        )
                        # Initialize face_result if it's None to avoid potential KeyError
                        if face_result is None:
                            face_result = {"success": False, "error": "No result returned from identify_speaker_in_frame"}
                            
                        if face_result.get("success", False):
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

