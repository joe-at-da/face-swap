"""
API endpoints for facial and voice recognition.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

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
    
    # Get the capture session from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.audio_id).first()
    
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture with ID {request.audio_id} not found")
    
    # Check if the audio file exists
    audio_path = capture.audio_path
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found for capture ID {request.audio_id}")
    
    # Process transcription
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(audio_path)
        output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_transcript.txt"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the voice recognition service for transcription
    result = voice_recognition_service.transcribe_audio(audio_path, output_file)
    
    # Update the database with the transcription results
    if result["success"] and result.get("output_file"):
        # Create a new transcription record
        transcription = models.Transcription(
            capture_session_id=capture.id,
            transcription_path=result["output_file"],
            status="completed",
            source="parliament-tv"
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
    
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
    
    # Get the capture session from the database
    capture = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.audio_id).first()
    
    if not capture:
        raise HTTPException(status_code=404, detail=f"Capture with ID {request.audio_id} not found")
    
    # Check if the audio file exists
    audio_path = capture.audio_path
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found for capture ID {request.audio_id}")
    
    # Process voice identification
    output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(audio_path)
        output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_voice_identification.json"
        output_file = os.path.join(output_dir, output_filename)
    
    # Call the voice recognition service for voice identification
    result = voice_recognition_service.identify_speakers_in_audio(audio_path, output_file)
    
    # Update the database with the voice identification results
    if result["success"] and result.get("results_file"):
        capture.voice_identification_results = result["results_file"]
        db.commit()
    
    return result


@router.post("/combined-recognition", response_model=schemas.CombinedRecognitionResponse)
async def process_combined_recognition(
    request: schemas.CombinedRecognitionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process combined facial and voice recognition for a video.
    """
    logger.info(f"Processing combined recognition for video ID: {request.video_id}")
    
    # Get the video from the database
    video = db.query(models.CaptureSession).filter(models.CaptureSession.id == request.video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail=f"Video with ID {request.video_id} not found")
    
    # Check if the video and audio files exist
    video_path = video.video_path
    audio_path = video.audio_path
    
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file not found for video ID {request.video_id}")
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found for video ID {request.video_id}")
    
    # Process speaker identification
    speaker_output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(video_path)
        speaker_output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_speaker_identification.mp4"
        speaker_output_file = os.path.join(output_dir, speaker_output_filename)
    
    # Call the facial recognition service for speaker identification
    speaker_result = facial_recognition_service.identify_speakers(video_path, speaker_output_file)
    
    if not speaker_result["success"]:
        return {
            "success": False,
            "error": f"Speaker identification failed: {speaker_result.get('error', 'Unknown error')}",
            "message": "Combined recognition failed at speaker identification step"
        }
    
    # Process transcription
    transcript_output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(audio_path)
        transcript_output_filename = f"{os.path.splitext(os.path.basename(audio_path))[0]}_transcript.txt"
        transcript_output_file = os.path.join(output_dir, transcript_output_filename)
    
    # Call the voice recognition service for transcription
    transcript_result = voice_recognition_service.transcribe_audio(audio_path, transcript_output_file)
    
    if not transcript_result["success"]:
        return {
            "success": False,
            "error": f"Transcription failed: {transcript_result.get('error', 'Unknown error')}",
            "message": "Combined recognition failed at transcription step"
        }
    
    # Combine the results
    combined_output_file = None
    if request.save_output:
        # Create output file path
        output_dir = os.path.dirname(video_path)
        combined_output_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_combined_recognition.json"
        combined_output_file = os.path.join(output_dir, combined_output_filename)
    
    # Call the voice recognition service to combine the results
    if speaker_result.get("results_file") and transcript_result.get("output_file"):
        combined_result = voice_recognition_service.combine_transcription_with_speakers(
            transcript_result["output_file"],
            speaker_result["results_file"],
            combined_output_file
        )
    else:
        combined_result = {
            "success": True,
            "message": "Speaker identification and transcription completed, but could not combine results due to missing files",
            "video_output_file": speaker_result.get("output_file"),
            "transcript_file": transcript_result.get("output_file"),
            "results_file": None,
            "results": {
                "speaker_identification": speaker_result.get("results", {}),
                "transcription": transcript_result.get("transcript", "")
            }
        }
    
    # Update the database with the combined results
    if speaker_result["success"] and speaker_result.get("output_file"):
        video.speaker_identification_path = speaker_result["output_file"]
        if speaker_result.get("results_file"):
            video.speaker_identification_results = speaker_result["results_file"]
    
    if transcript_result["success"] and transcript_result.get("output_file"):
        # Create a new transcription record
        transcription = models.Transcription(
            capture_session_id=video.id,
            transcription_path=transcript_result["output_file"],
            status="completed",
            source="parliament-tv"
        )
        db.add(transcription)
    
    if combined_result["success"] and combined_result.get("output_file"):
        video.combined_recognition_results = combined_result["output_file"]
    
    db.commit()
    
    # Return the combined result
    return {
        "success": combined_result["success"],
        "message": combined_result.get("message"),
        "error": combined_result.get("error"),
        "video_output_file": speaker_result.get("output_file"),
        "audio_output_file": None,  # We don't modify the audio file
        "transcript_file": transcript_result.get("output_file"),
        "results_file": combined_result.get("output_file"),
        "results": make_json_serializable({
            "speaker_identification": speaker_result.get("results", {}),
            "transcription": transcript_result.get("transcript", "")
        })
    }


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
