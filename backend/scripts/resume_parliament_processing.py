#!/usr/bin/env python3
"""
Resume Parliament TV Processing Script

This script mimics the flow of the /supabase-automation/process-parliament-tv endpoint
but allows resuming from a specific stage in the process. It follows the same flow
as the API endpoint without any hardcoding or cheating.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths to handle imports correctly whether running from project root or backend directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(backend_dir)

# Try different import paths
sys.path.insert(0, project_root)  # For running from project root with 'python backend/scripts/...'
sys.path.insert(0, backend_dir)   # For running from backend dir with 'python scripts/...'

logger.info(f"Script directory: {script_dir}")
logger.info(f"Backend directory: {backend_dir}")
logger.info(f"Project root: {project_root}")
logger.info(f"Python path: {sys.path}")

# Import local modules
try:
    # In Docker, the app is installed as a package, so we can import directly
    from backend.db.session import get_db
    from backend.db import models
    from backend.services.recognition.multimodal_recognition import MultimodalRecognitionService
    from backend.services.parliament_tv import ParliamentTVCapture
    from backend.services.integration.supabase_integration import SupabaseIntegration
    from backend.services.utils import make_json_serializable
    logger.info("Successfully imported modules")
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    logger.error("Make sure you're running this script from either the project root or the backend directory")
    logger.error("Try: python backend/scripts/resume_parliament_processing.py (from project root)")
    logger.error("Or: cd backend && python scripts/resume_parliament_processing.py (from backend dir)")
    sys.exit(1)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Resume Parliament TV processing')
    parser.add_argument('--capture-id', type=str, required=True, help='Capture session ID to resume')
    parser.add_argument('--stage', type=str, choices=['recognition', 'export'], 
                        required=True, help='Stage to resume from')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    return parser.parse_args()

def setup_environment(debug=False):
    """Set up environment variables based on debug parameter."""
    if debug:
        os.environ["DEBUG_MODE"] = "true"
        logger.info("Debug mode enabled: Using shorter durations for testing")
    else:
        os.environ["DEBUG_MODE"] = "false"
        
    # Keep TEST_MODE separate from debug parameter
    # TEST_MODE should only be set explicitly, not via the debug parameter
    os.environ["TEST_MODE"] = "false"

def extract_partial_transcription_results(capture_id):
    """Extract partial transcription results from chunk files even if the full process failed."""
    logger.info(f"Attempting to extract partial transcription results for capture {capture_id}")
    
    # Look for chunk directories
    chunk_dirs = glob.glob(f"/app/data/temp/chunks/{capture_id}_*")
    if not chunk_dirs:
        logger.warning(f"No chunk directories found for capture {capture_id}")
        return None
    
    # Sort by creation time (newest first)
    chunk_dirs.sort(key=os.path.getctime, reverse=True)
    latest_chunk_dir = chunk_dirs[0]
    logger.info(f"Using latest chunk directory: {latest_chunk_dir}")
    
    # Look for transcript files
    transcript_files = glob.glob(f"/app/data/temp/audio_extracts/transcript_chunk_*.txt")
    if not transcript_files:
        logger.warning("No transcript chunk files found")
        return None
    
    # Read and combine available transcripts
    combined_transcript = ""
    for transcript_file in sorted(transcript_files):
        try:
            with open(transcript_file, 'r') as f:
                content = f.read().strip()
                if content:
                    combined_transcript += content + "\n\n"
            logger.info(f"Added content from {transcript_file}")
        except Exception as e:
            logger.error(f"Error reading transcript file {transcript_file}: {str(e)}")
    
    if not combined_transcript:
        logger.warning("No transcript content found in chunk files")
        return None
    
    logger.info(f"Successfully extracted {len(combined_transcript)} characters of partial transcript data")
    return combined_transcript


def resume_recognition(capture_id, db_session):
    """Resume the recognition process for a capture session."""
    logger.info(f"Resuming recognition for capture session {capture_id}")
    
    # Get the capture session
    capture = db_session.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        logger.error(f"Capture session {capture_id} not found")
        return False
    
    # Initialize recognition service
    recognition_service = MultimodalRecognitionService()
    
    # Start recognition
    recognition_result = recognition_service.start_combined_recognition(capture_id)
    
    if not recognition_result.get("success", False):
        logger.error(f"Failed to start recognition: {recognition_result.get('error', 'Unknown error')}")
        # Try to extract partial results before giving up
        partial_transcript = extract_partial_transcription_results(capture_id)
        if partial_transcript:
            logger.info("Found partial transcription results, continuing with export")
            return True
        return False
    
    logger.info(f"Started recognition for session {capture_id}")
    
    # Wait for recognition to complete
    max_wait_time = 7200  # 2 hours max for recognition (increased from 1 hour)
    start_time = time.time()
    recognition_completed = False
    last_status_check = 0
    last_status = None
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check recognition status directly from the database
            db_session.refresh(capture)
            status_value = capture.recognition_status
            
            # Only log status if it has changed or every 5 minutes
            current_time = time.time()
            if status_value != last_status or current_time - last_status_check > 300:
                logger.info(f"Recognition status: {status_value}")
                last_status = status_value
                last_status_check = current_time
            
            if status_value == "completed":
                recognition_completed = True
                break
            elif status_value == "failed":
                error_message = capture.error_message if hasattr(capture, 'error_message') else "Unknown error"
                logger.error(f"Recognition failed: {error_message}")
                
                # Check if the error is related to transcription timeout
                if "timeout" in str(error_message).lower():
                    logger.warning("Detected transcription timeout. Attempting to continue with export anyway.")
                    logger.warning("Some audio chunks may not have been transcribed, but we'll use what we have.")
                    return True  # Continue with export despite timeout errors
                return False
            elif status_value is None:
                # Check if the recognition process has started
                if not capture.recognition_started_at:
                    # If recognition hasn't started yet, try to start it
                    if time.time() - start_time > 300:  # Wait 5 minutes before retrying
                        logger.info("Recognition hasn't started yet, retrying...")
                        recognition_result = recognition_service.start_combined_recognition(capture_id)
                        if not recognition_result.get("success", False):
                            logger.error(f"Failed to start recognition: {recognition_result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error checking recognition status: {str(e)}")
            # Continue the loop and try again after waiting
        
        # Wait before checking again
        time.sleep(60)
    
    if not recognition_completed:
        logger.error(f"Recognition timed out after {max_wait_time} seconds")
        logger.warning("Attempting to continue with export despite timeout. Some data may be incomplete.")
        return True  # Continue with export despite timeout
    
    logger.info(f"Recognition completed for session {capture_id}")
    return True

def export_to_supabase(capture_id, db_session):
    """Export recognition results to Supabase."""
    logger.info(f"Exporting recognition results to Supabase for capture session {capture_id}")
    
    # Get the capture session
    capture = db_session.query(models.CaptureSession).filter(models.CaptureSession.id == capture_id).first()
    if not capture:
        logger.error(f"Capture session {capture_id} not found")
        return False
    
    # Initialize recognition service
    recognition_service = MultimodalRecognitionService()
    
    # Get recognition results
    logger.info(f"Retrieving recognition results for session {capture_id} for Supabase export")
    recognition_data = recognition_service.get_recognition_results(capture_id)
    
    # Log the recognition data structure (not the full content)
    if recognition_data:
        logger.info(f"Recognition data retrieved for session {capture_id}. Keys: {list(recognition_data.keys())}")
        logger.info(f"Recognition data type: {type(recognition_data)}")
        
        # Check for identified_speakers
        if "identified_speakers" in recognition_data:
            logger.info(f"Found {len(recognition_data['identified_speakers'])} identified_speakers in recognition_data")
        else:
            logger.warning("No identified_speakers found in recognition_data")
        
        # Check for parliament_clips
        if "parliament_clips" in recognition_data:
            logger.info(f"Found {len(recognition_data['parliament_clips'])} parliament_clips in recognition_data")
            
            # Check for placeholder transcripts in parliament_clips
            placeholder_count = 0
            total_clips = len(recognition_data['parliament_clips'])
            for clip in recognition_data['parliament_clips']:
                if "Speech segment from" in clip.get('transcript', ''):
                    placeholder_count += 1
            
            if placeholder_count > 0:
                placeholder_percentage = (placeholder_count / total_clips) * 100 if total_clips > 0 else 0
                logger.warning(f"Found {placeholder_count} clips with placeholder transcripts ({placeholder_percentage:.1f}%)")
                logger.warning("This may be due to transcription timeouts or matching issues")
        else:
            logger.warning("No parliament_clips found in recognition_data")
            
        # Check for transcription data
        if "transcription" in recognition_data:
            logger.info("Found transcription data in recognition_data")
            if "speakers" in recognition_data["transcription"]:
                logger.info(f"Found {len(recognition_data['transcription']['speakers'])} speakers in transcription data")
                
                # Check for incomplete transcription data due to timeouts
                if "chunks" in recognition_data["transcription"]:
                    chunks = recognition_data["transcription"]["chunks"]
                    failed_chunks = [c for c in chunks if not c.get("success", False)]
                    if failed_chunks:
                        logger.warning(f"Found {len(failed_chunks)} failed transcription chunks out of {len(chunks)}")
                        logger.warning("Proceeding with partial transcription data")
        else:
            logger.warning("No transcription data found in recognition_data")
    else:
        logger.error(f"No recognition data found for session {capture_id}")
        # Don't return here, try to continue with empty data for diagnostic purposes
        recognition_data = {}
    
    # Handle capture_metadata properly - it might be a string or a dict
    capture_metadata = {}
    if capture.capture_metadata:
        if isinstance(capture.capture_metadata, dict):
            capture_metadata = capture.capture_metadata
        elif isinstance(capture.capture_metadata, str):
            try:
                capture_metadata = json.loads(capture.capture_metadata)
            except json.JSONDecodeError:
                logger.error(f"Error parsing capture metadata JSON for capture {capture_id}")
        else:
            logger.error(f"Unexpected metadata type: {type(capture.capture_metadata)}")
    
    # Use default Docker container paths if file_path is None
    if capture.file_path is None:
        video_file_path = f"/app/data/media/parliament_tv_{capture_id}.mp4"
        audio_file_path = f"/app/data/temp/audio_extracts/audio_{capture_id}.mp3"
    else:
        video_file_path = capture.file_path
        audio_file_path = os.path.join(os.path.dirname(capture.file_path), f"audio_{capture_id}.mp3")
    
    video_metadata = {
        "video_id": capture_id,
        "title": capture.title,
        "description": capture.description,
        "duration": capture.duration,
        "file_path": video_file_path,
        "audio_path": audio_file_path,
        "video_url": capture_metadata.get("video_url"),
        "audio_url": capture_metadata.get("audio_url"),
        "original_url": capture_metadata.get("original_url")
    }
    
    # Export to Supabase using service role for privileged operations
    logger.info(f"Initializing SupabaseIntegration for export of session {capture_id}")
    supabase = SupabaseIntegration()
    
    # Ensure all metadata is properly serializable
    logger.info(f"Serializing recognition data and video metadata for session {capture_id}")
    try:
        serializable_recognition_data = make_json_serializable(recognition_data)
        logger.info(f"Successfully serialized recognition data for session {capture_id}")
    except Exception as e:
        logger.error(f"Error serializing recognition data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Create a minimal serializable version
        serializable_recognition_data = {"error": "Serialization failed", "original_keys": list(recognition_data.keys()) if isinstance(recognition_data, dict) else "Not a dict"}
    
    try:
        serializable_video_metadata = make_json_serializable(video_metadata)
        logger.info(f"Successfully serialized video metadata for session {capture_id}")
    except Exception as e:
        logger.error(f"Error serializing video metadata: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Create a minimal serializable version
        serializable_video_metadata = {"video_id": capture_id, "error": "Serialization failed"}
    
    # Get the combined AV path from process metadata if available
    process = db_session.query(models.RecognitionProcess).filter(models.RecognitionProcess.video_id == capture_id).first()
    if process and process.process_metadata:
        try:
            metadata = {}
            if isinstance(process.process_metadata, str):
                try:
                    metadata = json.loads(process.process_metadata)
                except json.JSONDecodeError:
                    logger.error(f"Error parsing process metadata JSON for process {process.id}")
            elif isinstance(process.process_metadata, dict):
                metadata = process.process_metadata
            else:
                logger.error(f"Unexpected process metadata type: {type(process.process_metadata)}")
            
            # Check for combined_av_path in the parsed metadata
            if metadata and "combined_av_path" in metadata:
                video_file_path = metadata["combined_av_path"]
                logger.info(f"Using combined AV path from metadata: {video_file_path}")
        except Exception as e:
            logger.error(f"Error processing metadata for combined AV path: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info(f"Exporting recognition results to Supabase for session {capture_id} with video path: {video_file_path}")
    try:
        # Check if the video file exists before attempting to export
        if os.path.exists(video_file_path):
            logger.info(f"Video file exists at {video_file_path}, size: {os.path.getsize(video_file_path)} bytes")
        else:
            logger.warning(f"Video file does not exist at {video_file_path}, checking for alternatives")
            # Try to find the file in the media directory
            media_dir = "/app/data/media"
            potential_files = [f for f in os.listdir(media_dir) if str(capture_id) in f and f.endswith('.mp4')]
            if potential_files:
                video_file_path = os.path.join(media_dir, potential_files[0])
                logger.info(f"Found alternative video file: {video_file_path}")
            else:
                logger.error(f"No suitable video file found for session {capture_id}")
        
        # Export recognition results to Supabase
        try:
            logger.warning(f"🚀 CALLING export_and_upload_recognition for video_id={capture_id}")
            export_result = supabase.export_and_upload_recognition(
                video_path=video_file_path,
                recognition_results=serializable_recognition_data,
                video_metadata=serializable_video_metadata,
                db_session=db_session,
                video_id=capture_id,
                upload_media=True
            )
            logger.info(f"Export result for session {capture_id}: {export_result}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to Supabase: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    except Exception as e:
        logger.error(f"Error in export process: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    setup_environment(args.debug)
    
    # Get database session
    db_session = next(get_db())
    
    try:
        if args.stage == 'recognition':
            # Resume from recognition stage
            if resume_recognition(args.capture_id, db_session):
                # If recognition succeeds, continue to export
                export_to_supabase(args.capture_id, db_session)
        elif args.stage == 'export':
            # Resume from export stage
            export_to_supabase(args.capture_id, db_session)
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
