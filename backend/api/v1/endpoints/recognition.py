"""
API endpoints for facial and voice recognition.
"""

import os
import json
import time
import logging
import datetime
from typing import Dict, List, Optional, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks, Body, Request, Security
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import sqlalchemy as sa
from pathlib import Path
import threading
import shutil

from backend.api.deps import get_db, get_current_user
from backend.core.security import get_api_key
from backend.db import models
from backend.schemas import recognition as schemas
from backend.services.recognition import FacialRecognitionService, VoiceRecognitionService
from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
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
    return await _process_combined_recognition(video_id, save_output, db, current_user.id if current_user else None)


@router.post("/api/combined-recognition", dependencies=[Security(get_api_key)])
async def process_combined_recognition_api(
    video_id: int = Body(..., description="ID of the video to process"),
    save_output: bool = Body(True, description="Whether to save output files"),
    db: Session = Depends(get_db)
):
    """
    Process combined facial and voice recognition for a video using API key authentication.
    This endpoint starts the recognition process in the background and returns immediately.
    
    Authentication is required via API key.
    """
    return await _process_combined_recognition(video_id, save_output, db, None)


async def _process_combined_recognition(
    video_id: int,
    save_output: bool,
    db: Session,
    user_id: Optional[int] = None
):
    """
    Process combined facial and voice recognition for a video.
    This endpoint starts the recognition process in the background and returns immediately.
    """
    try:
        logger.info(f"Processing combined recognition for video ID: {video_id}")
        logger.info(f"User ID: {user_id if user_id else 'None (API key authentication)'}")
        
        
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
            args=(video_id, save_output, user_id)
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
        update_recognition_progress(db, video, "processing", 10, "Files verified, starting multimodal recognition", step_name="file_check")
        
        # CRITICAL ALIGNMENT FIX: Use the same multimodal recognition service as the sequential pipeline
        # This ensures both pipelines produce identical recognition events and clips
        logger.info(f"Starting multimodal recognition using the same service as sequential pipeline")
        
        try:
            # Initialize the multimodal recognition service (same as sequential pipeline)
            multimodal_service = MultimodalRecognitionService()
            
            # Update progress for multimodal recognition start
            update_recognition_progress(db, video, "processing", 25, "Starting multimodal recognition", step_name="multimodal_recognition")
            
            # Call the same multimodal recognition method used by sequential pipeline
            logger.info(f"Calling start_combined_recognition for video {video_id} (aligning with sequential pipeline)")
            multimodal_result = multimodal_service.start_combined_recognition(video_id)
            
            if multimodal_result.get("success", False):
                logger.info(f"Multimodal recognition completed successfully for video {video_id}")
                
                # Update progress after successful multimodal recognition
                update_recognition_progress(db, video, "processing", 90, "Multimodal recognition completed successfully", step_name="multimodal_recognition")
                
                # Extract results from multimodal service (same format as sequential pipeline)
                recognition_results = multimodal_result.get("results", {})
                recognition_events = recognition_results.get("recognition_events", [])
                segments = recognition_results.get("segments", [])
                faces = recognition_results.get("faces", [])
                
                logger.info(f"Multimodal recognition produced {len(recognition_events)} recognition events, {len(segments)} segments, {len(faces)} faces")
                
                # Create combined result in the same format as sequential pipeline
                combined_result = {
                    "success": True,
                    "video_id": video_id,
                    "recognition_events": recognition_events,
                    "segments": segments,
                    "faces": faces,
                    "multimodal_results": recognition_results,
                    "processing_details": {
                        "video_available": bool(video_path and os.path.exists(video_path)),
                        "audio_available": bool(audio_path and os.path.exists(audio_path)),
                        "video_path": video_path,
                        "audio_path": audio_path,
                        "timestamp": datetime.now().isoformat(),
                        "pipeline_type": "non_sequential_aligned"
                    },
                    "message": "Multimodal recognition completed successfully (aligned with sequential pipeline)"
                }
                
            else:
                error_msg = multimodal_result.get("error", "Unknown multimodal recognition error")
                logger.error(f"Multimodal recognition failed for video {video_id}: {error_msg}")
                
                # Update progress to indicate failure
                update_recognition_progress(db, video, "failed", 50, f"Multimodal recognition failed: {error_msg}", step_name="multimodal_recognition")
                
                # Create error result
                combined_result = {
                    "success": False,
                    "video_id": video_id,
                    "error": error_msg,
                    "recognition_events": [],
                    "segments": [],
                    "faces": [],
                    "processing_details": {
                        "video_available": bool(video_path and os.path.exists(video_path)),
                        "audio_available": bool(audio_path and os.path.exists(audio_path)),
                        "video_path": video_path,
                        "audio_path": audio_path,
                        "timestamp": datetime.now().isoformat(),
                        "pipeline_type": "non_sequential_aligned"
                    },
                    "message": f"Multimodal recognition failed: {error_msg}"
                }
                
        except Exception as e:
            error_msg = f"Exception in multimodal recognition: {str(e)}"
            logger.exception(error_msg)
            
            # Update progress to indicate failure
            update_recognition_progress(db, video, "failed", 25, error_msg, step_name="multimodal_recognition")
            
            # Create error result
            combined_result = {
                "success": False,
                "video_id": video_id,
                "error": error_msg,
                "recognition_events": [],
                "segments": [],
                "faces": [],
                "processing_details": {
                    "video_available": bool(video_path and os.path.exists(video_path)),
                    "audio_available": bool(audio_path and os.path.exists(audio_path)),
                    "video_path": video_path,
                    "audio_path": audio_path,
                    "timestamp": datetime.now().isoformat(),
                    "pipeline_type": "non_sequential_aligned"
                },
                "message": error_msg
            }
        
        # Save combined output file if requested (same as sequential pipeline)
        if save_output and combined_result.get("success"):
            try:
                # Create combined output file
                combined_output_filename = f"{os.path.splitext(os.path.basename(video_path if video_path else 'unknown'))[0]}_multimodal_recognition.json"
                output_dir = os.path.dirname(video_path if video_path else "/app/data/temp")
                combined_output_file = os.path.join(output_dir, combined_output_filename)
                
                with open(combined_output_file, 'w') as f:
                    json.dump(combined_result, f, indent=2, default=str)
                logger.info(f"Multimodal recognition results saved to: {combined_output_file}")
                combined_result["combined_output_file"] = combined_output_file
            except Exception as e:
                logger.warning(f"Failed to save multimodal results to file: {str(e)}")
        
        # Update the database with the results and final progress (same as sequential pipeline)
        try:
            if combined_result.get("success"):
                # Update progress with completion status
                update_recognition_progress(db, video, "completed", 100, "Multimodal recognition process completed successfully", step_name="completion")
                
                # Update video record with recognition results
                video.recognition_results = json.dumps(combined_result)
                video.recognition_status = "completed"
                video.recognition_completed_at = datetime.now()
            else:
                # Update progress with failure status
                update_recognition_progress(db, video, "failed", 100, f"Multimodal recognition failed: {combined_result.get('error', 'Unknown error')}", step_name="completion")
                
                # Update video record with error status
                video.recognition_status = "failed"
                video.error_message = combined_result.get("error", "Unknown multimodal recognition error")
            
            db.commit()
            logger.info(f"Database updated with multimodal recognition results for video ID: {video_id}")
        except Exception as e:
            logger.error(f"Failed to update database with multimodal recognition results: {str(e)}")
        
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


@router.get("/results/{video_id}", response_model=Dict[str, Any])
def get_recognition_results(video_id: int, db: Session = Depends(get_db)):
    """
    Get recognition results for a video.
    This endpoint returns the full recognition results for a video, including speakers and segments.
    """
    try:
        logger.info(f"Getting recognition results for video ID: {video_id}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
        
        # Check if recognition results exist
        if not video.recognition_results:
            raise HTTPException(status_code=404, detail=f"No recognition results found for video ID {video_id}")
        
        # Parse and return the recognition results
        try:
            # If the results are stored as a JSON string, parse them
            if isinstance(video.recognition_results, str):
                results = json.loads(video.recognition_results)
            else:
                results = video.recognition_results
                
            # Return the results directly as the frontend expects
            # The frontend is looking for speakers and segments
            if isinstance(results, dict) and ('speakers' in results or 'segments' in results):
                return results
            elif isinstance(results, dict) and 'results' in results:
                return results['results']
            else:
                # Fallback to the original format
                return {
                    "success": True,
                    "video_id": video_id,
                    "speakers": results.get('speakers', []),
                    "segments": results.get('segments', [])
                }
        except Exception as e:
            logger.error(f"Error parsing recognition results for video ID {video_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error parsing recognition results: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting recognition results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recognition results: {str(e)}")


@router.get("/speakers/{video_id}", response_model=Dict[str, Any])
def get_unidentified_speakers(video_id: int, db: Session = Depends(get_db)):
    """
    Get unidentified speakers from recognition results for a video.
    This endpoint extracts speaker data from recognition results and returns unidentified speakers.
    """
    try:
        logger.info(f"Getting unidentified speakers for video ID: {video_id}")
        
        # Get the video from the database
        video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail=f"Video with ID {video_id} not found")
        
        # Check if recognition results exist
        if not video.recognition_results:
            logger.warning(f"No recognition results found for video ID: {video_id}")
            return {"unidentified_speakers": []}
        
        # Parse recognition results
        try:
            results_data = json.loads(video.recognition_results)
        except json.JSONDecodeError:
            logger.error(f"Error parsing recognition results for video ID: {video_id}")
            return {"unidentified_speakers": []}
        
        # Extract speakers from results
        speakers = results_data.get("speakers", [])
        
        # Filter for unidentified speakers (those without a profile_id)
        unidentified_speakers = []
        for speaker in speakers:
            if not speaker.get("profile_id") and not speaker.get("profileId"):
                # Add face matches if available
                if "face_matches" not in speaker and "faceMatches" not in speaker:
                    # Try to find face matches in the results
                    speaker["face_matches"] = []
                    
                unidentified_speakers.append(speaker)
        
        logger.info(f"Found {len(unidentified_speakers)} unidentified speakers for video ID: {video_id}")
        
        return {"unidentified_speakers": unidentified_speakers}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting unidentified speakers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting unidentified speakers: {str(e)}")
