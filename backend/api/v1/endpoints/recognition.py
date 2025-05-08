"""
API endpoints for facial and voice recognition.
"""

import os
import logging
import json
import subprocess
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import sqlalchemy as sa
from pathlib import Path

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.schemas import recognition as schemas
from backend.services.recognition import FacialRecognitionService, VoiceRecognitionService
from backend.services.utils import make_json_serializable
from backend.core.security import has_permission

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
facial_recognition_service = FacialRecognitionService()
voice_recognition_service = VoiceRecognitionService()

@router.post("/combined-recognition")
async def process_combined_recognition(
    video_id: int = Body(..., description="ID of the video to process"),
    save_output: bool = Body(True, description="Whether to save output files"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process combined facial and voice recognition for a video.
    """
    try:
        logger.info(f"Processing combined recognition for video ID: {video_id}")
        logger.info(f"Current user: {current_user.email if current_user else 'None'}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"Video with ID {video_id} not found"}
            )
        
        # Check if the video file exists
        video_path = video.video_path
        file_path = video.file_path
        
        # Try different possible file paths
        possible_paths = []
        if video_path and os.path.exists(video_path):
            possible_paths.append(video_path)
        if file_path and os.path.exists(file_path):
            possible_paths.append(file_path)
            
        # Check for file in data/temp directory with specific pattern
        temp_path = f"/app/data/temp/capture_{video_id:04d}.mp4"
        if os.path.exists(temp_path):
            possible_paths.append(temp_path)
            
        # If we found any valid paths, use the first one
        if possible_paths:
            video_path = possible_paths[0]
            logger.info(f"Using video path: {video_path}")
        else:
            # Log all attempted paths for debugging
            logger.error(f"No valid video file found for ID {video_id}. Attempted paths:")
            if video_path:
                logger.error(f"  - video_path: {video_path} (exists: {os.path.exists(video_path)})")
            if file_path:
                logger.error(f"  - file_path: {file_path} (exists: {os.path.exists(file_path)})")
            logger.error(f"  - temp_path: {temp_path} (exists: {os.path.exists(temp_path)})")
                
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"Video file not found for video ID {video_id}"}
            )
        
        # Get the video and audio paths - Parliament TV has separate streams for each
        video_path = video.video_path
        logger.info(f"Initial video_path from database: {video_path}")
        
        # Check if we need to extract audio from the video file
        audio_path = video.audio_path
        audio_file_path = video.audio_file_path if hasattr(video, 'audio_file_path') else None
        
        logger.info(f"Database audio paths - audio_path: {audio_path}, audio_file_path: {audio_file_path}")
        
        # First try audio_file_path (newer captures)
        if audio_file_path and os.path.exists(audio_file_path):
            audio_path = audio_file_path
            logger.info(f"Using audio_file_path: {audio_path} (exists: {os.path.exists(audio_path)})")
        # Then try audio_path
        elif audio_path and os.path.exists(audio_path):
            logger.info(f"Using audio_path: {audio_path} (exists: {os.path.exists(audio_path)})")
        # If no audio path is found, check if we need to extract it from the video
        elif video_path and os.path.exists(video_path):
            # Extract audio from video if needed
            audio_extract_dir = os.path.join(os.path.dirname(video_path), "audio_extracts")
            os.makedirs(audio_extract_dir, exist_ok=True)
            
            audio_extract_path = os.path.join(audio_extract_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}.audio.mp3")
            
            if not os.path.exists(audio_extract_path):
                logger.info(f"Extracting audio from video to: {audio_extract_path}")
                try:
                    # Use ffmpeg to extract audio
                    cmd = [
                        "ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", audio_extract_path
                    ]
                    process = subprocess.run(cmd, capture_output=True, text=True)
                    if process.returncode != 0:
                        logger.error(f"Failed to extract audio: {process.stderr}")
                    else:
                        logger.info(f"Successfully extracted audio to: {audio_extract_path}")
                        # Update the database with the audio path
                        video.audio_file_path = audio_extract_path
                        db.commit()
                except Exception as e:
                    logger.error(f"Error extracting audio: {str(e)}")
            
            if os.path.exists(audio_extract_path):
                audio_path = audio_extract_path
                logger.info(f"Using extracted audio: {audio_path}")
            else:
                logger.warning(f"Failed to extract or find audio file")
                audio_path = None
        else:
            logger.warning(f"No audio file found and no video to extract from")
            audio_path = None
            
        # Log the final paths being used
        logger.info(f"Final paths - Video: {video_path} (exists: {os.path.exists(video_path) if video_path else False}), Audio: {audio_path} (exists: {os.path.exists(audio_path) if audio_path else False})")
        
        # Determine which processing modes are available based on file availability
        can_do_facial_recognition = video_path and os.path.exists(video_path)
        can_do_transcription = audio_path and os.path.exists(audio_path)
        
        logger.info(f"Processing capabilities - Facial recognition: {can_do_facial_recognition}, Transcription: {can_do_transcription}")
        
        # Log detailed file information for debugging
        if video_path and os.path.exists(video_path):
            try:
                video_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
                # Use ffprobe to get video duration and format
                probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name", "-of", "json", video_path]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if probe_result.returncode == 0:
                    video_info = json.loads(probe_result.stdout)
                    logger.info(f"Video file details - Size: {video_size:.2f} MB, Duration: {float(video_info['format']['duration']):.2f} seconds, Format: {video_info['format']['format_name']}")
                else:
                    logger.warning(f"Failed to get video details: {probe_result.stderr}")
            except Exception as e:
                logger.error(f"Error getting video file details: {str(e)}")
        
        if audio_path and os.path.exists(audio_path):
            try:
                audio_size = os.path.getsize(audio_path) / (1024 * 1024)  # Size in MB
                # Use ffprobe to get audio duration and format
                probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name", "-of", "json", audio_path]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if probe_result.returncode == 0:
                    audio_info = json.loads(probe_result.stdout)
                    logger.info(f"Audio file details - Size: {audio_size:.2f} MB, Duration: {float(audio_info['format']['duration']):.2f} seconds, Format: {audio_info['format']['format_name']}")
                else:
                    logger.warning(f"Failed to get audio details: {probe_result.stderr}")
            except Exception as e:
                logger.error(f"Error getting audio file details: {str(e)}")
        
        # Update the video record to indicate processing has started
        try:
            # Handle the case where recognition_progress might not exist yet
            try:
                if not video.recognition_progress:
                    video.recognition_progress = json.dumps({"steps": []})
            except AttributeError:
                # If the column doesn't exist in the database yet, use in-memory tracking
                logger.warning("recognition_progress column doesn't exist in the database yet")
                # We'll still track progress in memory
                video.recognition_progress = json.dumps({"steps": []})
            
            # Update video record with processing status
            video.recognition_status = "processing"
            video.recognition_started_at = datetime.now()
            
            # Initialize progress tracking
            progress = {
                "status": "processing",
                "started_at": datetime.now().isoformat(),
                "steps": [{
                    "name": "initialization",
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                }]
            }
            video.recognition_progress = json.dumps(progress)
            
            db.commit()
            logger.info(f"Database updated with processing status for video ID: {video_id}")
        except Exception as e:
            logger.error(f"Failed to update database with processing status: {str(e)}")
        
        # We need at least one of the two to proceed
        if not can_do_facial_recognition and not can_do_transcription:
            logger.error(f"Both video and audio files not found. Video path: {video_path}, Audio path: {audio_path}")
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": f"Both video and audio files not found"}
            )
        
        # Step 1: Process speaker identification (only if video is available)
        speaker_result = None
        if can_do_facial_recognition:
            # Update progress with speaker identification started status
            try:
                # Check if recognition_progress column exists
                if not hasattr(video, 'recognition_progress'):
                    # Add the column if it doesn't exist
                    try:
                        engine = db.get_bind()
                        if not sa.inspect(engine).has_column(video.__table__.name, 'recognition_progress'):
                            logger.warning(f"recognition_progress column doesn't exist, adding it")
                            sa.Table(video.__table__.name, sa.MetaData(),
                                sa.Column('recognition_progress', sa.Text),
                                extend_existing=True)
                            engine.execute(f"ALTER TABLE {video.__table__.name} ADD COLUMN IF NOT EXISTS recognition_progress TEXT")
                        # Set default value
                        video.recognition_progress = json.dumps({"steps": []})
                    except Exception as schema_error:
                        logger.error(f"Failed to add recognition_progress column: {str(schema_error)}")
                        # Continue with in-memory progress tracking
                        video.recognition_progress = json.dumps({"steps": []})
                
                progress = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
                progress["status"] = "processing"
                progress["steps"].append({
                    "name": "speaker_identification",
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                })
                video.recognition_progress = json.dumps(progress)
                db.commit()
                logger.info(f"Updated progress for speaker identification start: {video_id}")
            except Exception as e:
                logger.error(f"Failed to update progress for speaker identification: {str(e)}")
            
            logger.info(f"Processing speaker identification for video: {video_path}")
            
            # Define output file paths
            speaker_output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_speakers.json"
            speaker_output_dir = os.path.dirname(video_path)
            speaker_output_file = os.path.join(speaker_output_dir, speaker_output_filename) if save_output else None
            
            try:
                # Call the facial recognition service with the video file
                logger.info(f"Starting facial recognition using video file: {video_path}")
                speaker_result = facial_recognition_service.identify_speakers(
                    video_path, 
                    speaker_output_file
                )
                logger.info(f"Facial recognition completed with result: {speaker_result['success']}")
                
                if not speaker_result.get("success"):
                    logger.error(f"Speaker identification failed: {speaker_result.get('error')}")
                    # Continue with transcription even if facial recognition fails
                    speaker_result = {
                        "success": False,
                        "error": f"Speaker identification failed: {speaker_result.get('error')}",
                        "message": "Speaker identification failed but continuing with transcription",
                        "results": {"speakers": [], "total_speakers": 0},
                        "output_file": None
                    }
            except Exception as e:
                logger.exception(f"Exception in facial recognition service: {str(e)}")
                # Continue with transcription even if facial recognition fails
                speaker_result = {
                    "success": False,
                    "error": f"Exception in facial recognition service: {str(e)}",
                    "message": "Speaker identification failed but continuing with transcription",
                    "results": {"speakers": [], "total_speakers": 0},
                    "output_file": None
                }
        else:
            logger.info(f"Skipping speaker identification as no video file is available")
            speaker_result = {
                "success": True,
                "message": "Speaker identification skipped as no video file is available",
                "results": {"speakers": [], "total_speakers": 0},
                "output_file": None
            }
        
        # Step 2: Process transcription (only if audio is available)
        transcript_result = None
        if can_do_transcription:
            # Update progress with transcription started status
            try:
                # Check if recognition_progress column exists
                if not hasattr(video, 'recognition_progress'):
                    # Add the column if it doesn't exist
                    try:
                        engine = db.get_bind()
                        if not sa.inspect(engine).has_column(video.__table__.name, 'recognition_progress'):
                            logger.warning(f"recognition_progress column doesn't exist, adding it")
                            sa.Table(video.__table__.name, sa.MetaData(),
                                sa.Column('recognition_progress', sa.Text),
                                extend_existing=True)
                            engine.execute(f"ALTER TABLE {video.__table__.name} ADD COLUMN IF NOT EXISTS recognition_progress TEXT")
                        # Set default value
                        video.recognition_progress = json.dumps({"steps": []})
                    except Exception as schema_error:
                        logger.error(f"Failed to add recognition_progress column: {str(schema_error)}")
                        # Continue with in-memory progress tracking
                        video.recognition_progress = json.dumps({"steps": []})
                
                progress = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
                progress["status"] = "processing"
                progress["steps"].append({
                    "name": "transcription",
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                })
                video.recognition_progress = json.dumps(progress)
                db.commit()
                logger.info(f"Updated progress for transcription start: {video_id}")
            except Exception as e:
                logger.error(f"Failed to update progress for transcription: {str(e)}")
            
            logger.info(f"Processing transcription for audio: {audio_path}")
            
            # Create output file path for transcription
            transcript_output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_transcript.txt"
            output_dir = os.path.dirname(audio_path)
            transcript_output_file = os.path.join(output_dir, transcript_output_filename) if save_output else None
            
            # Process transcription with proper error handling using the audio file
            try:
                logger.info(f"Starting audio transcription using audio file: {audio_path}")
                transcript_result = voice_recognition_service.transcribe_audio(audio_path, transcript_output_file)
                logger.info(f"Audio transcription completed with result: {transcript_result['success']}")
                
                if not transcript_result.get("success"):
                    logger.error(f"Transcription failed: {transcript_result.get('error')}")
                    # If facial recognition succeeded but transcription failed, return a partial success
                    if speaker_result and speaker_result.get("success"):
                        transcript_result = {
                            "success": False,
                            "error": f"Transcription failed: {transcript_result.get('error')}",
                            "message": "Transcription failed but speaker identification succeeded",
                            "output_file": None,
                            "transcript": ""
                        }
                    else:
                        transcript_result = {
                            "success": False,
                            "error": f"Transcription failed: {transcript_result.get('error')}",
                            "message": "Transcription failed",
                            "output_file": None,
                            "transcript": ""
                        }
            except Exception as e:
                logger.exception(f"Exception in transcription service: {str(e)}")
                transcript_result = {
                    "success": False,
                    "error": f"Exception in transcription service: {str(e)}",
                    "message": "Transcription failed due to exception",
                    "output_file": None,
                    "transcript": ""
                }
            
            # Process speaker identification in audio if transcription succeeded
            speaker_audio_result = None
            if transcript_result and transcript_result.get("success"):
                # Define output file path for speaker identification in audio
                speaker_audio_output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_speakers_audio.json"
                speaker_audio_output_file = os.path.join(output_dir, speaker_audio_output_filename) if save_output else None
                
                # Process speaker identification in audio using the audio file
                try:
                    logger.info(f"Starting speaker identification in audio using audio file: {audio_path}")
                    speaker_audio_result = voice_recognition_service.identify_speakers_in_audio(
                        audio_path, 
                        speaker_audio_output_file
                    )
                    logger.info(f"Speaker identification in audio completed with result: {speaker_audio_result['success']}")
                    
                    if not speaker_audio_result.get("success"):
                        logger.error(f"Speaker identification in audio failed: {speaker_audio_result.get('error')}")
                        speaker_audio_result = {
                            "success": False,
                            "error": f"Speaker identification in audio failed: {speaker_audio_result.get('error')}",
                            "message": "Speaker identification in audio failed but transcription succeeded",
                            "output_file": None
                        }
                except Exception as e:
                    logger.exception(f"Exception in speaker identification in audio: {str(e)}")
                    speaker_audio_result = {
                        "success": False,
                        "error": f"Exception in speaker identification in audio: {str(e)}",
                        "message": "Speaker identification in audio failed due to exception",
                        "output_file": None
                    }
        else:
            logger.info(f"Skipping transcription as no audio file is available")
            transcript_result = {
                "success": True,
                "message": "Transcription skipped as no audio file is available",
                "output_file": None,
                "transcript": ""
            }
        
        # Step 3: Combine the results
        combined_result = {
            "success": True,
            "video_id": video_id,
            "speaker_identification": speaker_result or {
                "success": False,
                "message": "Speaker identification not performed",
                "results": {"speakers": [], "total_speakers": 0}
            },
            "transcription": transcript_result or {
                "success": False,
                "message": "Transcription not performed",
                "transcript": ""
            },
            "processing_details": {
                "video_available": can_do_facial_recognition,
                "audio_available": can_do_transcription,
                "video_path": video_path,
                "audio_path": audio_path,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Add combined output file if saving output
        if save_output:
            # Create combined output file
            combined_output_filename = f"{os.path.splitext(os.path.basename(video_path if video_path else audio_path))[0]}_combined_recognition.json"
            output_dir = os.path.dirname(video_path if video_path else audio_path)
            combined_output_file = os.path.join(output_dir, combined_output_filename)
            
            try:
                with open(combined_output_file, 'w') as f:
                    json.dump(combined_result, f, indent=2, default=str)
                logger.info(f"Combined recognition results saved to: {combined_output_file}")
                combined_result["combined_output_file"] = combined_output_file
            except Exception as e:
                logger.warning(f"Failed to save combined results to file: {str(e)}")
        
        # Update the database with the results and final progress
        try:
            # Update progress with completion status
            try:
                progress = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
                progress["status"] = "completed"
                progress["completed_at"] = datetime.now().isoformat()
                progress["steps"].append({
                    "name": "completion",
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                video.recognition_progress = json.dumps(progress)
            except Exception as e:
                logger.error(f"Failed to update progress with completion status: {str(e)}")
            
            # Update video record with recognition results
            video.recognition_results = json.dumps(combined_result)
            video.recognition_status = "completed"
            video.recognition_completed_at = datetime.now()
            
            db.commit()
            logger.info(f"Database updated with recognition results for video ID: {video_id}")
        except Exception as e:
            logger.error(f"Failed to update database with recognition results: {str(e)}")
        
        # Add a message to the combined result
        combined_result["message"] = "Recognition completed with available data"
        
        return combined_result
    except Exception as e:
        logger.exception(f"Error in combined recognition: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Error in combined recognition: {str(e)}"}
        )
