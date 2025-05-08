"""
API endpoints for facial and voice recognition.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import sqlalchemy as sa

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.schemas import recognition as schemas
from backend.services.recognition import FacialRecognitionService, VoiceRecognitionService
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
facial_recognition_service = FacialRecognitionService()
voice_recognition_service = VoiceRecognitionService()

@router.get("/test")
async def test_recognition_endpoint():
    """Test endpoint to check if the recognition router is working."""
    return {"status": "success", "message": "Recognition API is working correctly"}


@router.post("/facial-recognition", response_model=schemas.FacialRecognitionResponse)
async def process_facial_recognition(
    request: schemas.FacialRecognitionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process facial recognition for a video.
    """
    logger.info(f"Processing facial recognition for video ID: {request.video_id}")
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video with ID {request.video_id} not found")
    
    # Check if the video file exists
    video_path = video.video_path
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file not found for video ID {request.video_id}")
    
    # Process facial recognition
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(video_path)
        output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_facial_recognition.mp4"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the facial recognition service
    result = facial_recognition_service.detect_faces_in_video(video_path, output_file)
    
    # Update the database with the facial recognition results
    if result["success"] and result.get("output_file"):
        video.facial_recognition_path = result["output_file"]
        db.commit()
    
    return result


@router.post("/speaker-identification", response_model=schemas.SpeakerIdentificationResponse)
async def process_speaker_identification(
    request: schemas.SpeakerIdentificationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process speaker identification for a video.
    """
    logger.info(f"Processing speaker identification for video ID: {request.video_id}")
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video with ID {request.video_id} not found")
    
    # Check if the video file exists
    video_path = video.video_path
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file not found for video ID {request.video_id}")
    
    # Process speaker identification
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(video_path)
        output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_speaker_identification.mp4"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the facial recognition service for speaker identification
    result = facial_recognition_service.identify_speakers(video_path, output_file)
    
    # Update the database with the speaker identification results
    if result["success"] and result.get("output_file"):
        video.speaker_identification_path = result["output_file"]
        if result.get("results_file"):
            video.speaker_identification_results = result["results_file"]
        db.commit()
    
    return result


@router.post("/transcription", response_model=schemas.TranscriptionResponse)
async def process_transcription(
    request: schemas.TranscriptionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process transcription for an audio file.
    """
    logger.info(f"Processing transcription for audio ID: {request.audio_id}")
    
    # Get the audio from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.audio_id).first()
    
    if not capture:
        raise HTTPException(status_code=404, detail=f"Audio with ID {request.audio_id} not found")
    
    # Check if the audio file exists
    audio_path = capture.audio_path
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found for audio ID {request.audio_id}")
    
    # Process transcription
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(audio_path)
        output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_transcript.txt"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the voice recognition service
    result = voice_recognition_service.transcribe_audio(audio_path, output_file)
    
    return result


@router.post("/voice-identification", response_model=schemas.VoiceIdentificationResponse)
async def process_voice_identification(
    request: schemas.VoiceIdentificationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process voice identification for an audio file.
    """
    logger.info(f"Processing voice identification for audio ID: {request.audio_id}")
    
    # Get the audio from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.audio_id).first()
    
    if not capture:
        raise HTTPException(status_code=404, detail=f"Audio with ID {request.audio_id} not found")
    
    # Check if the audio file exists
    audio_path = capture.audio_path
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found for audio ID {request.audio_id}")
    
    # Process voice identification
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(audio_path)
        output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_voice_identification.json"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the voice recognition service
    result = voice_recognition_service.identify_speakers_in_audio(audio_path, output_file)
    
    # Update the database with the voice identification results
    if result["success"] and result.get("results_file"):
        capture.voice_identification_results = result["results_file"]
        db.commit()
    
    return result


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
        
        # Check for audio path in both standard fields
        audio_path = video.audio_path
        if not audio_path or not os.path.exists(audio_path):
            # Try the audio_file_path field which is used in newer captures
            audio_path = video.audio_file_path if hasattr(video, 'audio_file_path') else None
            if audio_path and os.path.exists(audio_path):
                logger.info(f"Using audio_file_path: {audio_path}")
            else:
                logger.warning(f"Audio file not found in any field")
                audio_path = None
        else:
            logger.info(f"Using audio_path: {audio_path}")
        
        # Determine which processing modes are available based on file availability
        can_do_facial_recognition = video_path and os.path.exists(video_path)
        can_do_transcription = audio_path and os.path.exists(audio_path)
        
        logger.info(f"Can do facial recognition: {can_do_facial_recognition}, Can do transcription: {can_do_transcription}")
        
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
                # Call the facial recognition service
                speaker_result = facial_recognition_service.identify_speakers(
                    video_path, 
                    speaker_output_file
                )
                
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
            
            # Process transcription with proper error handling
            try:
                transcript_result = voice_recognition_service.transcribe_audio(audio_path, transcript_output_file)
                
                if not transcript_result.get("success"):
                    logger.error(f"Transcription failed: {transcript_result.get('error')}")
                    # If facial recognition succeeded but transcription failed, return a partial success
                    if speaker_result and speaker_result.get("success"):
                        transcript_result = {
                            "success": False,
                            "error": f"Transcription failed: {transcript_result.get('error')}",
                            "message": "Transcription failed but speaker identification succeeded",
                            "transcript": "",
                            "output_file": None
                        }
                    else:
                        # Both failed, return an error
                        return JSONResponse(
                            status_code=500,
                            content={
                                "success": False, 
                                "error": f"Transcription failed: {transcript_result.get('error')}",
                                "message": "Combined recognition failed at transcription step"
                            }
                        )
            except Exception as e:
                logger.exception(f"Exception in voice recognition service: {str(e)}")
                # If facial recognition succeeded but transcription failed, return a partial success
                if speaker_result and speaker_result.get("success"):
                    transcript_result = {
                        "success": False,
                        "error": f"Exception in voice recognition service: {str(e)}",
                        "message": "Transcription failed but speaker identification succeeded",
                        "transcript": "",
                        "output_file": None
                    }
                else:
                    # Both failed, return an error
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False, 
                            "error": f"Exception in voice recognition service: {str(e)}",
                            "message": "Combined recognition failed due to exception in transcription"
                        }
                    )
        else:
            logger.info(f"Skipping transcription as no audio file is available")
            transcript_result = {
                "success": True,
                "message": "Transcription skipped as no audio file is available",
                "transcript": "",
                "output_file": None
            }
        
        # Step 3: Combine the results
        # Determine the base filename for combined output
        if can_do_facial_recognition:
            base_filename = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.dirname(video_path)
        elif can_do_transcription:
            base_filename = os.path.splitext(os.path.basename(audio_path))[0]
            output_dir = os.path.dirname(audio_path)
        else:
            # This shouldn't happen due to earlier checks, but just in case
            base_filename = f"capture_{video_id}"
            output_dir = "/app/data/temp"
            
        combined_output_filename = f"{base_filename}_combined_recognition.json"
        combined_output_file = os.path.join(output_dir, combined_output_filename) if save_output else None
        
        # Create combined result with appropriate success status
        # Overall success is true if at least one of the processes succeeded
        overall_success = (speaker_result and speaker_result.get("success", False)) or \
                         (transcript_result and transcript_result.get("success", False))
        
        combined_result = {
            "success": overall_success,
            "video_id": video_id,
            "speaker_identification": speaker_result,
            "transcription": transcript_result,
            "combined_output_file": combined_output_file,
            "message": "Recognition completed with available data"
        }
        
        # Add processing details to the result
        combined_result["processing_details"] = {
            "video_available": can_do_facial_recognition,
            "audio_available": can_do_transcription,
            "video_path": video_path if can_do_facial_recognition else None,
            "audio_path": audio_path if can_do_transcription else None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save combined result if requested
        if save_output and combined_output_file:
            try:
                # Ensure the output directory exists
                os.makedirs(os.path.dirname(combined_output_file), exist_ok=True)
                
                with open(combined_output_file, 'w') as f:
                    json.dump(combined_result, f, indent=2)
                logger.info(f"Combined recognition results saved to: {combined_output_file}")
            except Exception as e:
                logger.warning(f"Failed to save combined results to file: {str(e)}")
        
        # Update the database with the results and final progress
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
            
            progress = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
            progress["status"] = "completed"
            progress["completed_at"] = datetime.now().isoformat()
            progress["steps"].append({
                "name": "completion",
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
            # Update video record with recognition results
            video.recognition_results = json.dumps(combined_result)
            video.recognition_progress = json.dumps(progress)
            video.recognition_status = "completed"
            video.recognition_completed_at = datetime.now()
            db.commit()
            logger.info(f"Database updated with recognition results for video ID: {video_id}")
        except Exception as e:
            logger.error(f"Failed to update database with recognition results: {str(e)}")
        
        return combined_result
    except Exception as e:
        logger.error(f"Error in combined recognition: {str(e)}")
        # Update progress with error status
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
            
            progress = json.loads(video.recognition_progress) if video.recognition_progress else {"steps": []}
            progress["status"] = "error"
            progress["error"] = str(e)
            progress["error_at"] = datetime.now().isoformat()
            video.recognition_progress = json.dumps(progress)
            video.recognition_status = "error"
            db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update error status: {str(update_error)}")
            
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/update-mp-database", response_model=Dict)
async def update_mp_database(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update the MP database with the latest photos and face encodings.
    """
    logger.info("Updating MP database")
    
    # Call the facial recognition service to update the MP database
    result = facial_recognition_service.update_mp_database()
    
    return result


@router.get("/list/parliament-tv", response_model=Dict)
async def get_all_parliament_tv_recognitions(
    limit: int = Query(100, description="Maximum number of recognition results to return"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all Parliament TV recognition results with pagination.
    """
    logger.info(f"Getting all Parliament TV recognition results with limit={limit}, offset={offset}")
    
    # Get all captures with recognition results
    query = db.query(models.CaptureSession).filter(
        models.CaptureSession.recognition_status.in_(["completed", "processing", "error"])
    ).order_by(models.CaptureSession.id.desc())
    
    # Apply pagination
    total_count = query.count()
    captures = query.offset(offset).limit(limit).all()
    
    # Format the results
    recognitions = []
    for capture in captures:
        # Skip if no recognition data
        if not capture.recognition_status:
            continue
            
        # Create a base recognition object
        recognition = {
            "id": len(recognitions) + 1,  # Generate a unique ID
            "capture_id": capture.id,
            "status": capture.recognition_status,
            "type": "combined",  # Default to combined
            "results": capture.recognition_results if hasattr(capture, 'recognition_results') and capture.recognition_results else None,
            "error_message": None,
            "created_at": capture.recognition_started_at.isoformat() if capture.recognition_started_at else capture.created_at.isoformat(),
            "updated_at": capture.recognition_completed_at.isoformat() if capture.recognition_completed_at else capture.updated_at.isoformat(),
        }
        
        # Add error message if status is error
        if capture.recognition_status == "error" and hasattr(capture, 'recognition_progress') and capture.recognition_progress:
            try:
                progress = json.loads(capture.recognition_progress)
                if "error" in progress:
                    recognition["error_message"] = progress["error"]
            except (json.JSONDecodeError, TypeError):
                pass
        
        recognitions.append(recognition)
    
    return {
        "success": True,
        "recognitions": recognitions,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

@router.get("/recognition-status/{video_id}", response_model=Dict)
async def get_recognition_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get the status of a recognition process for a specific video.
    """
    logger.info(f"Getting recognition status for video ID: {video_id}")
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == video_id).first()
    if not video:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f"Video not found for video ID {video_id}"}
        )
    
    # Get the recognition status
    try:
        # Check if we have recognition results even if status is not set
        if video.recognition_results and not video.recognition_status:
            actual_status = "completed"  # If we have results but no status, mark as completed
        else:
            actual_status = video.recognition_status or "not_started"
            
        status = {
            "video_id": video_id,
            "status": actual_status,
            "started_at": video.recognition_started_at.isoformat() if video.recognition_started_at else None,
            "completed_at": video.recognition_completed_at.isoformat() if video.recognition_completed_at else None,
            "progress": json.loads(video.recognition_progress) if hasattr(video, 'recognition_progress') and video.recognition_progress else None,
            "has_results": bool(video.recognition_results) if hasattr(video, 'recognition_results') else False
        }
    except AttributeError as e:
        # Handle case where columns don't exist yet
        logger.warning(f"Recognition status columns not available: {str(e)}")
        status = {
            "video_id": video_id,
            "status": "not_started",
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "has_results": False,
            "message": "Recognition tracking not fully set up in database"
        }
    
    return {"success": True, "status": status}
