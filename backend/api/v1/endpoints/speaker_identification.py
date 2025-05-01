from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

from backend.db.session import get_db
from backend.db import models
from backend.core.security import get_current_active_user, has_permission
from backend.db.models.user import UserRole
from backend.schemas.speaker import SpeakerIdentificationRequest, SpeakerIdentificationResponse
from backend.services.utils import make_json_serializable

router = APIRouter()

@router.post("/", response_model=Dict)
async def identify_speakers(
    request: SpeakerIdentificationRequest = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Identify speakers in a Parliament TV video.
    This will process the video and identify MPs speaking in the video.
    """
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == request.capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {request.capture_id} not found"
        )
    
    # Check if the file exists
    if not capture.file_path or not os.path.exists(capture.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file for capture {request.capture_id} not found"
        )
    
    # Create a new speaker identification record
    speaker_identification = models.SpeakerIdentification(
        capture_session_id=capture.id,
        status="pending",
        created_by_id=current_user.id,
        threshold=request.threshold
    )
    
    db.add(speaker_identification)
    db.commit()
    db.refresh(speaker_identification)
    
    # Start the speaker identification process in the background
    if background_tasks:
        background_tasks.add_task(
            process_speaker_identification,
            speaker_identification.id,
            capture.file_path,
            request.threshold,
            request.update_db
        )
    
    return {
        "id": speaker_identification.id,
        "capture_id": capture.id,
        "status": "pending",
        "message": "Speaker identification started",
        "created_at": speaker_identification.created_at
    }

@router.get("/{identification_id}", response_model=Dict)
async def get_speaker_identification(
    identification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get the results of a speaker identification process.
    """
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the speaker identification record
    identification = db.query(models.SpeakerIdentification).filter(
        models.SpeakerIdentification.id == identification_id
    ).first()
    
    if not identification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Speaker identification with ID {identification_id} not found"
        )
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == identification.capture_session_id
    ).first()
    
    # Prepare the response
    response = {
        "id": identification.id,
        "capture_id": identification.capture_session_id,
        "status": identification.status,
        "created_at": identification.created_at,
        "updated_at": identification.updated_at,
        "results": identification.results,
        "output_file": identification.output_file,
        "threshold": identification.threshold
    }
    
    # Add capture details if available
    if capture:
        response["capture"] = {
            "id": capture.id,
            "title": capture.title,
            "status": capture.status,
            "file_path": capture.file_path,
            "created_at": capture.created_at
        }
    
    return make_json_serializable(response)

@router.get("/", response_model=List[Dict])
async def get_speaker_identifications(
    capture_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get all speaker identifications with optional filtering.
    """
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Build the query
    query = db.query(models.SpeakerIdentification)
    
    # Apply filters
    if capture_id:
        query = query.filter(models.SpeakerIdentification.capture_session_id == capture_id)
    
    if status:
        query = query.filter(models.SpeakerIdentification.status == status)
    
    # Execute the query
    identifications = query.all()
    
    # Prepare the response
    results = []
    for identification in identifications:
        results.append({
            "id": identification.id,
            "capture_id": identification.capture_session_id,
            "status": identification.status,
            "created_at": identification.created_at,
            "updated_at": identification.updated_at,
            "results": identification.results,
            "output_file": identification.output_file,
            "threshold": identification.threshold
        })
    
    return make_json_serializable(results)

@router.get("/capture/{capture_id}", response_model=List[Dict])
async def get_speaker_identifications_by_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get all speaker identifications for a specific capture session.
    """
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Check if capture exists
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # Get all identifications for this capture
    identifications = db.query(models.SpeakerIdentification).filter(
        models.SpeakerIdentification.capture_session_id == capture_id
    ).all()
    
    # Prepare the response
    results = []
    for identification in identifications:
        results.append({
            "id": identification.id,
            "capture_id": identification.capture_session_id,
            "status": identification.status,
            "created_at": identification.created_at,
            "updated_at": identification.updated_at,
            "results": identification.results,
            "output_file": identification.output_file,
            "threshold": identification.threshold
        })
    
    return make_json_serializable(results)

@router.delete("/{identification_id}", response_model=Dict)
async def delete_speaker_identification(
    identification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Delete a speaker identification record and its associated files.
    """
    # Check permissions
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the speaker identification record
    identification = db.query(models.SpeakerIdentification).filter(
        models.SpeakerIdentification.id == identification_id
    ).first()
    
    if not identification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Speaker identification with ID {identification_id} not found"
        )
    
    # Delete associated files
    files_deleted = []
    if identification.output_file and os.path.exists(identification.output_file):
        try:
            os.remove(identification.output_file)
            files_deleted.append(os.path.basename(identification.output_file))
        except Exception as e:
            print(f"Error deleting file {identification.output_file}: {str(e)}")
    
    # Delete JSON results file if it exists
    if identification.output_file:
        json_file = identification.output_file.replace('.mp4', '.json')
        if os.path.exists(json_file):
            try:
                os.remove(json_file)
                files_deleted.append(os.path.basename(json_file))
            except Exception as e:
                print(f"Error deleting file {json_file}: {str(e)}")
    
    # Delete the database record
    db.delete(identification)
    db.commit()
    
    return {
        "message": f"Speaker identification {identification_id} deleted successfully",
        "files_deleted": files_deleted
    }

def process_speaker_identification(
    identification_id: int,
    video_path: str,
    threshold: float = 0.6,
    update_db: bool = False
):
    """
    Process a video for speaker identification.
    This function is meant to be run as a background task.
    """
    # Create a database session
    db = next(get_db())
    
    try:
        # Get the speaker identification record
        identification = db.query(models.SpeakerIdentification).filter(
            models.SpeakerIdentification.id == identification_id
        ).first()
        
        if not identification:
            print(f"Speaker identification with ID {identification_id} not found")
            return
        
        # Update status to processing
        identification.status = "processing"
        db.commit()
        
        # Create output directory
        output_dir = Path("/app/data/media/identified_videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"identified_{identification.capture_session_id}_{timestamp}.mp4"
        
        # Run the speaker identification script
        cmd = [
            "python",
            "/app/scripts/speaker_identification.py",
            video_path,
            "--output", str(output_file),
            "--threshold", str(threshold)
        ]
        
        if update_db:
            cmd.append("--update-db")
        
        print(f"Running speaker identification: {' '.join(cmd)}")
        
        # Execute the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        # Check if the process was successful
        if process.returncode != 0:
            print(f"Speaker identification failed: {stderr}")
            identification.status = "failed"
            identification.results = {
                "error": stderr,
                "command": " ".join(cmd)
            }
            db.commit()
            return
        
        # Load the results from the JSON file
        json_file = str(output_file).replace('.mp4', '.json')
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                results = json.load(f)
        else:
            results = {
                "error": "Results file not found",
                "stdout": stdout,
                "stderr": stderr
            }
        
        # Update the speaker identification record
        identification.status = "completed"
        identification.results = results
        identification.output_file = str(output_file)
        db.commit()
        
        print(f"Speaker identification completed successfully: {output_file}")
        
    except Exception as e:
        print(f"Error in process_speaker_identification: {str(e)}")
        
        # Update the record with the error
        try:
            identification.status = "failed"
            identification.results = {
                "error": str(e)
            }
            db.commit()
        except:
            pass
    
    finally:
        db.close()
