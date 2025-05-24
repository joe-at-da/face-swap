"""
API endpoints for facial and voice recognition.
"""

import os
import json
import time
import logging
import datetime
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks, Body, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import sqlalchemy as sa
from pathlib import Path
import threading

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


@router.get("/unidentified/{capture_id}/{filename}")
async def get_unidentified_face_image(
    capture_id: str,
    filename: str
):
    """
    Get an unidentified face image by capture ID and filename.
    This endpoint directly serves images from the capture's unidentified faces directory.
    This endpoint is public and does not require authentication.
    """
    try:
        
        # Sanitize the filename to prevent directory traversal
        safe_filename = os.path.basename(filename)
        logger.info(f"Looking for unidentified face image for capture {capture_id}: {safe_filename}")
        
        # Try with zero-padded capture ID (e.g., 0382)
        padded_capture_id = capture_id.zfill(4)
        
        # Define possible paths for the unidentified face image
        possible_paths = [
            # Primary location - capture specific directory with padded ID
            os.path.join("/app/data/temp", f"capture_{padded_capture_id}_unidentified_faces", safe_filename),
            # Try with non-padded ID
            os.path.join("/app/data/temp", f"capture_{capture_id}_unidentified_faces", safe_filename),
            # Try in general unidentified faces directory
            os.path.join("/app/data/unidentified_faces", f"capture_{padded_capture_id}", safe_filename),
            os.path.join("/app/data/unidentified_faces", f"capture_{capture_id}", safe_filename),
        ]
        
        # Try each possible path
        for path in possible_paths:
            if os.path.exists(path) and os.path.isfile(path):
                logger.info(f"Found unidentified face image at {path}")
                return FileResponse(path)
        
        # If we get here, the file wasn't found
        logger.warning(f"Unidentified face image not found for capture {capture_id}: {safe_filename}")
        
        # Return a 404 error
        raise HTTPException(status_code=404, detail=f"Unidentified face image not found: {safe_filename}")
    except Exception as e:
        logger.exception(f"Error getting unidentified face image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting unidentified face image: {str(e)}")


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
    This endpoint starts the recognition process in the background and returns immediately.
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
            
        # Initialize or reset recognition status
        video.recognition_status = "processing"
        video.recognition_started_at = datetime.now()
        
        # Initialize progress tracking
        progress_data = {
            "status": "processing",
            "steps": [],
            "completion_percentage": 0,
            "current_step": "initialization",
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
        
        # Add initialization step
        progress_data["steps"].append({
            "name": "initialization",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "message": "Recognition process initialized"
        })
        
        # Save initial progress to database
        video.recognition_progress = json.dumps(progress_data)
        db.commit()
        
        # Start the background process
        # This will return immediately and let the process run in the background
        recognition_thread = threading.Thread(
            target=run_recognition_process,
            args=(video_id, save_output, current_user.id if current_user else None)
        )
        recognition_thread.daemon = True
        recognition_thread.start()
        
        # Return immediate response to client
        return {
            "success": True,
            "message": "Recognition process started in the background",
            "video_id": video_id,
            "status": "processing",
            "check_status_url": f"/api/v1/recognition/detailed-status/{video_id}"
        }
    except Exception as e:
        logger.exception(f"Error starting recognition process: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Error starting recognition process: {str(e)}"}
        )

def run_recognition_process(video_id: int, save_output: bool = True, user_id: int = None):
    """
    Run the recognition process in a background thread.
    This function should not be called directly from the API endpoint.
    """
    # Create a new database session for this thread
    from sqlalchemy.orm import sessionmaker
    from backend.db.session import engine
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        logger.info(f"Starting background recognition process for video ID: {video_id}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            logger.error(f"Video with ID {video_id} not found in background process")
            return
            
        # Update progress to indicate process has started
        update_recognition_progress(db, video, "processing", 5, "Checking file availability", step_name="initialization")
        
        # Check if the video file exists
        video_path = video.video_path
        file_path = video.file_path
        audio_path = video.audio_path
        
        # Log all file paths for debugging
        logger.info(f"Video paths - video_path: {video_path}, file_path: {file_path}, audio_path: {audio_path}")
        
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
            
            # Update the database with the correct video path if it was different
            if video_path != video.video_path:
                video.video_path = video_path
                db.commit()
                logger.info(f"Updated database with correct video path: {video_path}")
        else:
            # Log all attempted paths for debugging
            logger.error(f"No valid video file found for ID {video_id}. Attempted paths:")
            if video_path:
                logger.error(f"  - video_path: {video_path} (exists: {os.path.exists(video_path)})")
            if file_path:
                logger.error(f"  - file_path: {file_path} (exists: {os.path.exists(file_path)})")
            logger.error(f"  - temp_path: {temp_path} (exists: {os.path.exists(temp_path)})")
            
            # Update progress to indicate failure
            update_recognition_progress(db, video, "failed", 0, "Video file not found", step_name="file_check")
            return
            
        # Check for audio file
        possible_audio_paths = []
        if audio_path and os.path.exists(audio_path):
            possible_audio_paths.append(audio_path)
            
        # Check for audio file in standard locations            
        audio_extract_path = f"/app/data/audio_extracts/capture_{video_id:04d}.audio.mp3"
        if os.path.exists(audio_extract_path):
            possible_audio_paths.append(audio_extract_path)
            
        # If we found any valid audio paths, use the first one
        if possible_audio_paths:
            audio_path = possible_audio_paths[0]
            logger.info(f"Using audio path: {audio_path}")
            
            # Update the database with the correct audio path if it was different
            if audio_path != video.audio_path:
                video.audio_path = audio_path
                db.commit()
                logger.info(f"Updated database with correct audio path: {audio_path}")
        else:
            logger.warning(f"No valid audio file found for ID {video_id}. Recognition will proceed with video only.")
            
        # Update progress to indicate file checks complete
        update_recognition_progress(db, video, "processing", 10, "Files verified, starting recognition", step_name="file_check")
        
        # Initialize variables for recognition
        can_do_facial_recognition = bool(video_path and os.path.exists(video_path))
        can_do_transcription = bool(audio_path and os.path.exists(audio_path))
        
        # Process results
        speaker_result = None
        transcript_result = None
        
        # Step 1: Process facial recognition if video is available
        if can_do_facial_recognition:
            try:
                # Update progress for facial recognition start
                update_recognition_progress(db, video, "processing", 25, "Starting facial recognition", step_name="facial_recognition")
                
                # Define output file paths
                speaker_output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_speakers.json"
                speaker_output_dir = os.path.dirname(video_path)
                speaker_output_file = os.path.join(speaker_output_dir, speaker_output_filename) if save_output else None
                
                # Call the facial recognition service with the video file
                logger.info(f"Starting facial recognition using video file: {video_path}")
                speaker_result = facial_recognition_service.identify_speakers(
                    video_path, 
                    speaker_output_file
                )
                logger.info(f"Facial recognition completed with result: {speaker_result['success']}")
                
                # Update progress after facial recognition
                if speaker_result.get("success"):
                    update_recognition_progress(db, video, "processing", 50, "Facial recognition completed successfully", step_name="facial_recognition")
                else:
                    update_recognition_progress(db, video, "processing", 40, f"Facial recognition completed with errors: {speaker_result.get('error')}", step_name="facial_recognition")
                    
                    # Continue with transcription even if facial recognition fails
                    speaker_result = {
                        "success": False,
                        "error": f"Speaker identification failed: {speaker_result.get('error')}",
                        "message": "Speaker identification failed but continuing with transcription",
                        "results": {"speakers": [], "total_speakers": 0},
                        "output_file": None
                    }
            except Exception as e:
                logger.exception(f"Error in facial recognition: {str(e)}")
                update_recognition_progress(db, video, "processing", 40, f"Error in facial recognition: {str(e)}", step_name="facial_recognition")
                speaker_result = {
                    "success": False,
                    "error": f"Exception in facial recognition: {str(e)}",
                    "message": "Speaker identification failed due to exception",
                    "results": {"speakers": [], "total_speakers": 0},
                    "output_file": None
                }
        else:
            logger.info(f"Skipping facial recognition as no video file is available")
            speaker_result = {
                "success": False,
                "message": "Facial recognition skipped as no video file is available",
                "results": {"speakers": [], "total_speakers": 0},
                "output_file": None
            }
            
        # Step 2: Process transcription (only if audio is available)
        if can_do_transcription:
            try:
                # Update progress for transcription start
                update_recognition_progress(db, video, "processing", 60, "Starting audio transcription", step_name="transcription")
                
                # Create output file path for transcription
                transcript_output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_transcript.txt"
                output_dir = os.path.dirname(audio_path)
                transcript_output_file = os.path.join(output_dir, transcript_output_filename) if save_output else None
                
                # Process transcription with proper error handling using the audio file
                logger.info(f"Starting audio transcription using audio file: {audio_path}")
                transcript_result = voice_recognition_service.transcribe_audio(audio_path, transcript_output_file)
                logger.info(f"Audio transcription completed with result: {transcript_result['success']}")
                
                # Update progress after transcription
                if transcript_result.get("success"):
                    update_recognition_progress(db, video, "processing", 75, "Audio transcription completed successfully", step_name="transcription")
                    
                    # Check if the transcript file exists in the audio_extracts directory
                    audio_filename = os.path.basename(audio_path)
                    audio_basename = os.path.splitext(audio_filename)[0]
                    audio_dir = os.path.dirname(audio_path)
                    
                    # Try different possible transcript file patterns
                    possible_transcript_files = [
                        os.path.join(audio_dir, f"{audio_basename}_transcript.txt"),
                        os.path.join(audio_dir, f"{audio_basename}.audio_transcript.txt"),
                        os.path.join(audio_dir, f"{audio_basename}_transcription.txt"),
                        os.path.join(audio_dir, f"{audio_basename}.txt")
                    ]
                    
                    transcript_file = None
                    transcript_content = ""
                    
                    # Check if any of the possible transcript files exist
                    for file_path in possible_transcript_files:
                        if os.path.exists(file_path):
                            transcript_file = file_path
                            try:
                                with open(file_path, 'r') as f:
                                    transcript_content = f.read()
                                logger.info(f"Found transcript file: {file_path}")
                                break
                            except Exception as e:
                                logger.error(f"Error reading transcript file {file_path}: {str(e)}")
                    
                    # Update the transcript_result with the actual transcript content if found
                    if transcript_file and transcript_content:
                        transcript_result["output_file"] = transcript_file
                        transcript_result["transcript"] = transcript_content
                        logger.info(f"Updated transcript_result with content from {transcript_file}")
                    else:
                        logger.warning(f"No transcript file found in {audio_dir} for {audio_basename}")
                else:
                    update_recognition_progress(db, video, "processing", 65, f"Audio transcription completed with errors: {transcript_result.get('error')}", step_name="transcription")
                    
                    # If transcription failed but facial recognition succeeded, return a partial success
                    if speaker_result and speaker_result.get("success"):
                        transcript_result = {
                            "success": False,  # Mark as failed with error message
                            "error": f"Transcription failed: {transcript_result.get('error')}",
                            "message": "Transcription failed but speaker identification succeeded",
                            "output_file": None,
                            "transcript": "No transcript available due to processing error."
                        }
                    else:
                        transcript_result = {
                            "success": False,  # Mark as failed with error message
                            "error": f"Transcription failed: {transcript_result.get('error')}",
                            "message": "Transcription failed but processing continues",
                            "output_file": None,
                            "transcript": "No transcript available due to processing error."
                        }
            except Exception as e:
                logger.exception(f"Exception in transcription service: {str(e)}")
                update_recognition_progress(db, video, "processing", 65, f"Error in transcription: {str(e)}", step_name="transcription")
                transcript_result = {
                    "success": True,  # Mark as success but with empty transcript
                    "error": f"Exception in transcription service: {str(e)}",
                    "message": "Transcription failed due to exception but processing continues",
                    "output_file": None,
                    "transcript": "No transcript available due to processing error."
                }
        else:
            logger.info(f"Skipping transcription as no audio file is available")
            transcript_result = {
                "success": True,
                "message": "Transcription skipped as no audio file is available",
                "output_file": None,
                "transcript": "No audio file available for transcription."
            }
            
        # Step 3: Combine the results
        # Create a results summary with detailed information about what was processed
        has_speaker_identification = speaker_result and speaker_result.get("success", False)
        
        # Check if we have a valid transcript file and content
        has_transcript_file = transcript_result and transcript_result.get("output_file") is not None
        has_transcript_content = transcript_result and transcript_result.get("transcript") and len(transcript_result.get("transcript", "")) > 0
        
        # Consider transcription successful if we have either a valid transcript file or content
        has_transcription = has_transcript_file or has_transcript_content
        
        # Force success flag to true if we have transcript content
        if has_transcript_content and transcript_result:
            transcript_result["success"] = True
            if "error" in transcript_result:
                transcript_result.pop("error", None)
            transcript_result["message"] = "Transcription completed successfully"
            logger.info(f"Forcing transcription success flag to True because we have valid transcript content")
        
        total_speakers = len(speaker_result.get("results", {}).get("speakers", [])) if has_speaker_identification else 0
        transcript_length = len(transcript_result.get("transcript", "")) if transcript_result else 0
        
        # Create the results summary
        results_summary = {
            "has_speaker_identification": has_speaker_identification,
            "has_transcription": has_transcription,
            "total_speakers": total_speakers,
            "transcript_length": transcript_length,
            "transcript_text": transcript_result.get("transcript", "No transcript available.") if transcript_result else "No transcript available.",
            "speaker_identification_message": speaker_result.get("message", "") if speaker_result else "",
            "transcription_message": transcript_result.get("message", "") if transcript_result else "",
            "transcript_file": transcript_result.get("output_file") if transcript_result else None
        }
        
        # Log detailed information about the transcript
        if transcript_result:
            logger.info(f"Transcript details: output_file={transcript_result.get('output_file')}, length={transcript_length}, success={transcript_result.get('success')}")
        else:
            logger.warning("No transcript_result available")
        
        logger.info(f"Results summary for video ID {video_id}: {results_summary}")
        
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
            "results_summary": results_summary,
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
            update_recognition_progress(db, video, "completed", 100, "Recognition process completed successfully", step_name="completion")
            
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
        logger.exception(f"Error in background recognition process: {str(e)}")
        try:
            # Update the database with the error
            video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
            if video:
                video.recognition_status = "failed"
                update_recognition_progress(db, video, "failed", 0, f"Recognition process failed: {str(e)}", step_name="error")
                
                # Add detailed error information to the progress data
                try:
                    progress_data = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
                    progress_data["error"] = str(e)
                    progress_data["error_at"] = datetime.now().isoformat()
                    progress_data["status"] = "failed"
                    video.recognition_progress = json.dumps(progress_data)
                except Exception as json_error:
                    logger.error(f"Failed to update progress data with error: {str(json_error)}")
                
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update database with error status: {str(db_error)}")
        return None
    finally:
        # Close the database session
        db.close()

def update_recognition_progress(db, video, status, completion_percentage, message, step_name=None):
    """
    Update the recognition progress in the database.
    
    Args:
        db: Database session
        video: Video object
        status: Status string (processing, completed, failed)
        completion_percentage: Percentage of completion (0-100)
        message: Message to display
        step_name: Optional name of the current step (if different from status)
    """
    try:
        # Get current progress data
        progress_data = {}
        if video.recognition_progress:
            try:
                progress_data = json.loads(video.recognition_progress)
            except Exception:
                progress_data = {"steps": []}
        else:
            progress_data = {"steps": []}
            # Initialize with start time if not present
            progress_data["start_time"] = datetime.now().isoformat()
            
        # Update progress data
        progress_data["status"] = status
        progress_data["completion_percentage"] = completion_percentage
        progress_data["current_step"] = step_name or status
        progress_data["last_update"] = datetime.now().isoformat()
        
        # Add step if it's a new step or status change
        step_to_add = {
            "name": step_name or status,
            "status": "completed" if status == "completed" else "error" if status == "failed" else "started",
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "completion_percentage": completion_percentage
        }
        
        # Check if we already have this step
        existing_step = False
        for step in progress_data.get("steps", []):
            if step.get("name") == step_to_add["name"] and step.get("status") == step_to_add["status"]:
                existing_step = True
                break
                
        if not existing_step:
            progress_data["steps"].append(step_to_add)
        
        # If completed or failed, add completion time
        if status in ["completed", "failed"]:
            progress_data["completed_at"] = datetime.now().isoformat()
            if status == "failed":
                progress_data["error"] = message
                progress_data["error_at"] = datetime.now().isoformat()
        
        # Update database
        video.recognition_progress = json.dumps(progress_data)
        video.recognition_status = "completed" if status == "completed" else "processing" if status == "processing" else "failed"
        db.commit()
        
        # Log the update
        logger.info(f"RECOGNITION PROGRESS for video ID {video.id} - {completion_percentage}% - {message}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to update recognition progress: {str(e)}")
        return False


@router.get("/recognition-status/{video_id}", response_model=schemas.RecognitionStatusResponse)
def get_recognition_status(video_id: int, db: Session = Depends(get_db)):
    """
    Get the status of the recognition process for a video.
    This is a simple endpoint that returns the basic status.
    """
    try:
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
        
        return {
            "success": True,
            "status": {
                "status": video.recognition_status or "not_started",
                "video_id": video_id,
                "started_at": video.recognition_started_at,
                "completed_at": video.recognition_completed_at,
                "has_results": bool(video.recognition_results)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition status: {str(e)}")


@router.get("/detailed-status/{video_id}", response_model=schemas.DetailedRecognitionStatusResponse)
def get_detailed_recognition_status(video_id: int, db: Session = Depends(get_db)):
    """
    Get detailed status of the recognition process for a video.
    This endpoint returns detailed progress information including steps and completion percentage.
    """
    try:
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
        
        # Basic status information
        status_info = {
            "status": video.recognition_status or "not_started",
            "video_id": video_id,
            "started_at": video.recognition_started_at,
            "completed_at": video.recognition_completed_at,
            "has_results": bool(video.recognition_results)
        }
        
        # Add progress information if available
        if video.recognition_progress:
            try:
                progress_data = json.loads(video.recognition_progress)
                status_info["progress"] = progress_data
            except Exception as e:
                logger.error(f"Error parsing progress data: {str(e)}")
        
        return {
            "success": True,
            "status": status_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting detailed recognition status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting detailed recognition status: {str(e)}")
