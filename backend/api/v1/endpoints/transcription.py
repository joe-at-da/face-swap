from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body, Query
from sqlalchemy.orm import Session
import os
import subprocess
from pathlib import Path
from datetime import datetime

from backend.api.deps import get_db, get_current_user
from backend.core.security import has_permission
from backend.db import models
from backend.db.models.user import UserRole
from backend.db.models.transcription import ParliamentTranscription
from backend.db.models.speaker import SpeakerIdentification
from backend.schemas import transcription as schemas
from backend.services.tasks import transcription_tasks
from backend.services.utils import make_json_serializable

router = APIRouter()

@router.post("/", response_model=schemas.TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    transcription: schemas.TranscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new transcription for a video clip.
    This will start a background task to process the transcription.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP])
    
    # Check if video clip exists
    clip = db.query(models.VideoClip).filter(models.VideoClip.id == transcription.video_clip_id).first()
    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video clip not found"
        )
    
    # Check if transcription already exists
    existing = db.query(models.Transcription).filter(
        models.Transcription.video_clip_id == transcription.video_clip_id
    ).first()
    
    if existing:
        # If it exists but failed, we can retry
        if existing.status == "failed":
            existing.status = "processing"
            existing.error_message = None
            db.commit()
            db.refresh(existing)
            
            # Start transcription task
            transcription_tasks.transcribe_video_clip.delay(
                clip_id=transcription.video_clip_id,
                language=transcription.language
            )
            
            return existing
        else:
            # If it's already processing or ready, return it
            return existing
    
    # Create new transcription record
    db_transcription = models.Transcription(
        video_clip_id=transcription.video_clip_id,
        language=transcription.language,
        status="processing",
        text="",
        segments=[]
    )
    db.add(db_transcription)
    db.commit()
    db.refresh(db_transcription)
    
    # Start transcription task
    transcription_tasks.transcribe_video_clip.delay(
        clip_id=transcription.video_clip_id,
        language=transcription.language
    )
    
    return db_transcription

@router.get("/{transcription_id}", response_model=schemas.TranscriptionResponse)
async def get_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific transcription by ID."""
    transcription = db.query(models.Transcription).filter(
        models.Transcription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    return transcription

@router.get("/clip/{clip_id}", response_model=schemas.TranscriptionResponse)
async def get_transcription_by_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get the transcription for a specific video clip."""
    transcription = db.query(models.Transcription).filter(
        models.Transcription.video_clip_id == clip_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found for this clip"
        )
    
    return transcription

@router.post("/search", response_model=List[schemas.TranscriptionSearchResult])
async def search_transcriptions(
    search: schemas.TranscriptionSearch,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Search for text within transcriptions.
    If video_clip_id is provided, search only within that clip.
    """
    query = search.query.lower()
    
    # Build query for transcriptions
    transcription_query = db.query(models.Transcription, models.VideoClip).join(
        models.VideoClip, models.Transcription.video_clip_id == models.VideoClip.id
    ).filter(
        models.Transcription.status == "ready"
    )
    
    # Filter by clip ID if provided
    if search.video_clip_id:
        transcription_query = transcription_query.filter(
            models.Transcription.video_clip_id == search.video_clip_id
        )
    
    results = []
    for transcription, clip in transcription_query.all():
        # Search within transcription text
        if query in transcription.text.lower():
            # Find matching segments
            matches = []
            for segment in transcription.segments:
                if query in segment.get("text", "").lower():
                    matches.append(schemas.TranscriptionSegment(**segment))
            
            if matches:
                results.append(schemas.TranscriptionSearchResult(
                    video_clip_id=clip.id,
                    clip_title=clip.title,
                    matches=matches
                ))
    
    return results

@router.post("/parliament-tv", response_model=Dict)
async def transcribe_parliament_tv(
    background_tasks: BackgroundTasks,
    data: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a transcription for a Parliament TV video.
    This will start a background task to process the transcription.
    
    Required fields in request body:
    - capture_id: ID of the Parliament TV capture to transcribe
    - format: Output format (txt, srt, json, docx)
    - speaker_id: Optional ID of speaker identification to use for speaker attribution
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    capture_id = data.get("capture_id")
    output_format = data.get("format", "txt")
    speaker_id = data.get("speaker_id")
    language = data.get("language", "en")
    model = data.get("model", "medium")
    
    if not capture_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="capture_id is required"
        )
    
    # Check if capture exists
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == capture_id
    ).first()
    
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture session with ID {capture_id} not found"
        )
    
    # Check if file exists
    if not capture.file_path or not os.path.exists(capture.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file for capture {capture_id} not found"
        )
    
    # Check if transcription already exists
    existing = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == capture_id
    ).first()
    
    if existing:
        # If it exists but failed, we can retry
        if existing.status == "failed":
            existing.status = "processing"
            existing.error_message = None
            db.commit()
            db.refresh(existing)
            
            # Start transcription in background
            background_tasks.add_task(
                process_parliament_transcription,
                existing.id,
                capture.file_path,
                output_format,
                speaker_id,
                language,
                model
            )
            
            return make_json_serializable({
                "id": existing.id,
                "capture_id": capture_id,
                "status": "processing",
                "message": "Transcription restarted",
                "created_at": existing.created_at
            })
        else:
            # If it's already processing or ready, return it
            return make_json_serializable({
                "id": existing.id,
                "capture_id": capture_id,
                "status": existing.status,
                "output_file": existing.output_file,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at
            })
    
    # Create new transcription record
    new_transcription = ParliamentTranscription(
        capture_session_id=capture_id,
        status="processing",
        language=language,
        format=output_format,
        model=model,
        created_by_id=current_user.id
    )
    
    # If speaker ID is provided, link it
    if speaker_id:
        speaker_identification = db.query(models.SpeakerIdentification).filter(
            models.SpeakerIdentification.id == speaker_id
        ).first()
        
        if speaker_identification:
            new_transcription.speaker_identification_id = speaker_id
    
    db.add(new_transcription)
    db.commit()
    db.refresh(new_transcription)
    
    # Start transcription in background
    background_tasks.add_task(
        process_parliament_transcription,
        new_transcription.id,
        capture.file_path,
        output_format,
        speaker_id,
        language,
        model
    )
    
    return make_json_serializable({
        "id": new_transcription.id,
        "capture_id": capture_id,
        "status": "processing",
        "message": "Transcription started",
        "created_at": new_transcription.created_at
    })

@router.get("/parliament-tv/{transcription_id}", response_model=Dict)
async def get_parliament_tv_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific Parliament TV transcription by ID.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    transcription = db.query(models.ParliamentTranscription).filter(
        models.ParliamentTranscription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    # Get the capture session
    capture = db.query(models.CaptureSession).filter(
        models.CaptureSession.id == transcription.capture_session_id
    ).first()
    
    # Prepare the response
    response = {
        "id": transcription.id,
        "capture_id": transcription.capture_session_id,
        "status": transcription.status,
        "language": transcription.language,
        "format": transcription.format,
        "model": transcription.model,
        "output_file": transcription.output_file,
        "error_message": transcription.error_message,
        "speaker_identification_id": transcription.speaker_identification_id,
        "created_at": transcription.created_at,
        "updated_at": transcription.updated_at
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

@router.get("/parliament-tv/capture/{capture_id}", response_model=Dict)
async def get_parliament_tv_transcriptions_by_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all transcriptions for a specific Parliament TV capture.
    """
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
    
    # Get all transcriptions for this capture
    transcriptions = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == capture_id
    ).all()
    
    # Prepare the response
    results = []
    for transcription in transcriptions:
        results.append({
            "id": transcription.id,
            "capture_id": transcription.capture_session_id,
            "status": transcription.status,
            "language": transcription.language,
            "format": transcription.format,
            "model": transcription.model,
            "output_file": transcription.output_file,
            "created_at": transcription.created_at,
            "updated_at": transcription.updated_at
        })
    
    return make_json_serializable(results)

@router.get("/parliament-tv-list", response_model=Dict)
async def get_all_parliament_tv_transcriptions(
    limit: int = Query(100, description="Maximum number of transcriptions to return"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all Parliament TV transcriptions with pagination.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get total count
    total_count = db.query(ParliamentTranscription).count()
    
    # Get transcriptions with pagination
    transcriptions = db.query(ParliamentTranscription).order_by(
        ParliamentTranscription.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Convert to dictionary format
    results = []
    for t in transcriptions:
        result = {
            "id": t.id,
            "capture_id": t.capture_id,
            "language": t.language,
            "status": t.status,
            "text": t.text[:200] if t.text else None,  # Include a preview of the text
            "segments": t.segments[:3] if t.segments else None,  # Include first few segments
            "error_message": t.error_message,
            "output_file": t.output_file,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        results.append(result)
    
    return {
        "success": True,
        "transcriptions": results,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

@router.delete("/parliament-tv/{transcription_id}", response_model=Dict)
async def delete_parliament_tv_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a Parliament TV transcription and its associated files.
    """
    has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
    
    # Get the transcription
    transcription = db.query(models.ParliamentTranscription).filter(
        models.ParliamentTranscription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    # Delete associated files
    files_deleted = []
    if transcription.output_file and os.path.exists(transcription.output_file):
        try:
            os.remove(transcription.output_file)
            files_deleted.append(os.path.basename(transcription.output_file))
        except Exception as e:
            print(f"Error deleting file {transcription.output_file}: {str(e)}")
    
    # Delete metadata file if it exists
    if transcription.output_file:
        metadata_file = transcription.output_file.replace('.txt', '.meta.json')
        metadata_file = metadata_file.replace('.srt', '.meta.json')
        metadata_file = metadata_file.replace('.json', '.meta.json')
        metadata_file = metadata_file.replace('.docx', '.meta.json')
        
        if os.path.exists(metadata_file):
            try:
                os.remove(metadata_file)
                files_deleted.append(os.path.basename(metadata_file))
            except Exception as e:
                print(f"Error deleting file {metadata_file}: {str(e)}")
    
    # Delete the database record
    db.delete(transcription)
    db.commit()
    
    return {
        "message": f"Transcription {transcription_id} deleted successfully",
        "files_deleted": files_deleted
    }

def process_parliament_transcription(
    transcription_id: int,
    video_path: str,
    output_format: str = "txt",
    speaker_id: Optional[int] = None,
    language: str = "en",
    model: str = "medium"
):
    """
    Process a Parliament TV video for transcription.
    This function is meant to be run as a background task.
    """
    # Create a database session
    db = next(get_db())
    
    try:
        # Get the transcription record
        transcription = db.query(ParliamentTranscription).filter(
            ParliamentTranscription.id == transcription_id
        ).first()
        
        if not transcription:
            print(f"Transcription with ID {transcription_id} not found")
            return
        
        # Update status to processing
        transcription.status = "processing"
        db.commit()
        
        # Check if the video file exists
        if not os.path.exists(video_path):
            error_msg = f"Video file not found: {video_path}"
            print(error_msg)
            transcription.status = "failed"
            transcription.error_message = error_msg
            db.commit()
            return
        
        # Check if the video has an audio stream
        has_audio = False
        try:
            # Use ffprobe to check for audio streams
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", 
                "stream=codec_type", "-of", "json", video_path
            ]
            probe_result = subprocess.run(
                probe_cmd, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            # Parse the probe result
            import json
            probe_data = json.loads(probe_result.stdout)
            streams = probe_data.get('streams', [])
            for stream in streams:
                if stream.get('codec_type') == 'audio':
                    has_audio = True
                    break
            
            if not has_audio:
                print("No audio stream detected in the video file!")
                
                # Check if this is a Parliament TV capture
                is_parliament_tv = False
                if transcription.capture_session_id:
                    capture = db.query(models.CaptureSession).filter(
                        models.CaptureSession.id == transcription.capture_session_id
                    ).first()
                    
                    if capture and capture.metadata:
                        try:
                            if isinstance(capture.metadata, dict) and 'parliament_tv_url' in capture.metadata:
                                is_parliament_tv = True
                        except Exception as e:
                            print(f"Error checking metadata: {str(e)}")
                
                if is_parliament_tv:
                    # For Parliament TV, audio should be handled separately
                    print("This is a Parliament TV capture - audio should be extracted separately")
                    print("Use the dedicated audio extraction endpoint instead")
                    error_msg = "Parliament TV captures require separate audio extraction. Use the audio extraction endpoint."
                    transcription.status = "failed"
                    transcription.error_message = error_msg
                    db.commit()
                    return
                else:
                    # For non-Parliament TV videos, create a silent audio track
                    print("Creating silent audio track for non-Parliament TV video...")
                    temp_audio_file = f"{video_path}.audio_fixed.mp4"
                    
                    # Create a video with silent audio
                    silent_cmd = [
                        "ffmpeg", "-i", video_path, "-f", "lavfi", 
                        "-i", "anullsrc=r=44100:cl=stereo", "-c:v", "copy", 
                        "-c:a", "aac", "-shortest", "-y", temp_audio_file
                    ]
                    
                    silent_result = subprocess.run(
                        silent_cmd,
                        capture_output=True,
                        text=True
                    )
                    
                    if silent_result.returncode == 0 and os.path.exists(temp_audio_file):
                        print(f"Created video with silent audio track: {temp_audio_file}")
                        video_path = temp_audio_file
                        has_audio = True
                    else:
                        error_msg = "Failed to create audio track for the video. Transcription requires audio."
                        print(error_msg)
                        print(f"FFmpeg output: {silent_result.stderr}")
                        transcription.status = "failed"
                        transcription.error_message = error_msg
                        db.commit()
                        return
        except Exception as e:
            print(f"Error checking for audio stream: {str(e)}")
            # Continue anyway, as the transcription script might handle this
        
        # Create output directory
        output_dir = Path("/app/data/media/transcriptions")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"transcript_{transcription.capture_session_id}_{timestamp}.{output_format}"
        
        # Get speaker identification file if provided
        speaker_id_path = None
        if speaker_id:
            speaker_identification = db.query(models.SpeakerIdentification).filter(
                models.SpeakerIdentification.id == speaker_id
            ).first()
            
            if speaker_identification and speaker_identification.results:
                # The results should be stored in a JSON file
                if speaker_identification.output_file:
                    speaker_id_path = speaker_identification.output_file.replace('.mp4', '.json')
        
        # Run the transcription script
        cmd = [
            "python",
            "/app/scripts/parliament_transcription.py",
            video_path,
            "--output", str(output_file),
            "--format", output_format,
            "--language", language,
            "--model", model
        ]
        
        if speaker_id_path:
            cmd.extend(["--speaker-id", speaker_id_path])
        
        print(f"Running transcription: {' '.join(cmd)}")
        
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
            print(f"Transcription failed: {stderr}")
            transcription.status = "failed"
            transcription.error_message = stderr
            db.commit()
            return
        
        # Update the transcription record
        transcription.status = "completed"
        transcription.output_file = str(output_file)
        db.commit()
        
        print(f"Transcription completed successfully: {output_file}")
        
        # Clean up temporary files if we created them
        if video_path.endswith('.audio_fixed.mp4') and os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"Removed temporary audio file: {video_path}")
            except Exception as e:
                print(f"Error removing temporary file: {str(e)}")
        
    except Exception as e:
        print(f"Error in process_parliament_transcription: {str(e)}")
        
        # Update the record with the error
        try:
            transcription.status = "failed"
            transcription.error_message = str(e)
            db.commit()
        except:
            pass
    
    finally:
        db.close()
