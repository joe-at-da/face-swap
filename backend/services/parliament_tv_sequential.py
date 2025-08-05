"""
Parliament TV Sequential Processing

This module provides functionality for sequential processing of Parliament TV videos
in 30-minute segments to avoid memory issues with long-running videos.
"""

import logging
import os
import json
import time
import requests
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from backend.services.parliament_tv_scraper import ParliamentTVScraper
from backend.services.parliament_tv import ParliamentTVCapture

# Configure logging
logger = logging.getLogger(__name__)

class ParliamentTVSequentialProcessor:
    """
    Handles sequential processing of Parliament TV videos in 30-minute segments.
    """
    
    # Default segment duration in seconds (30 minutes)
    DEFAULT_SEGMENT_DURATION = 1800
    
    def __init__(self):
        """Initialize the sequential processor."""
        self.parliament_tv_capture = ParliamentTVCapture()
        self.scraper = ParliamentTVScraper()
        
    def get_latest_video_info(self) -> Dict[str, Any]:
        """
        Get the latest video from Parliament TV Commons page.
        
        Returns:
            Dict with video information
        """
        return self.scraper.get_latest_video()
    
    def extract_stream_urls(self, url: str) -> Dict[str, Any]:
        """
        Extract the direct stream URLs from a Parliament TV URL.
        
        Args:
            url: Parliament TV URL
            
        Returns:
            Dict with video_url, audio_url, and time_marker
        """
        try:
            import subprocess
            import json
            import sys
            import os
            from pathlib import Path
            
            # Get the path to the extract-url.py script
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                      'scripts', 'extract-url.py')
            
            # Check if the script exists
            if not os.path.exists(script_path):
                logger.error(f"Extract URL script not found at {script_path}")
                # Try alternative path
                script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                          'backend', 'scripts', 'extract-url.py')
                if not os.path.exists(script_path):
                    logger.error(f"Extract URL script not found at alternative path {script_path}")
                    raise FileNotFoundError(f"Extract URL script not found")
            
            logger.info(f"Using extract-url.py script at {script_path}")
            
            # Run the extract-url.py script
            cmd = [sys.executable, script_path, url]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Parse the JSON output
            try:
                stream_info = json.loads(result.stdout)
                logger.info(f"Successfully extracted stream URLs: {stream_info}")
                
                # Extract the direct stream URLs
                if 'direct_stream' in stream_info:
                    direct_stream = stream_info['direct_stream']
                    video_url = direct_stream.get('video_url')
                    audio_url = direct_stream.get('audio_url')
                    
                    # Extract time marker if available
                    time_marker = stream_info.get('time_marker', {})
                    if isinstance(time_marker, dict) and 'seconds' in time_marker:
                        time_marker_seconds = time_marker['seconds']
                    else:
                        time_marker_seconds = 0
                    
                    return {
                        'video_url': video_url,
                        'audio_url': audio_url,
                        'time_marker': {'seconds': time_marker_seconds},
                        'event_id': stream_info.get('event_id')
                    }
                else:
                    logger.error(f"No direct_stream found in extract-url.py output: {stream_info}")
                    raise ValueError("No direct stream URLs found")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse extract-url.py output as JSON: {result.stdout}")
                raise ValueError("Invalid JSON output from extract-url.py")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running extract-url.py: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            raise ValueError(f"Error extracting stream URLs: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting stream URLs: {str(e)}")
            raise ValueError(f"Error extracting stream URLs: {str(e)}")
    
    def download_full_video(self, video_url, audio_url, output_dir, session_id, max_retries=3, timeout=None):
        """
        Download the full video and audio files from the provided URLs simultaneously.
        
        This method runs two FFmpeg processes in parallel with identical parameters
        to ensure that audio and video are downloaded efficiently. It also monitors and reports progress.
        
        Args:
            video_url (str): URL of the video stream
            audio_url (str): URL of the audio stream
            output_dir (str): Directory to save the downloaded files
            session_id (int): Session ID for the capture
            max_retries (int): Maximum number of retries for failed downloads
            timeout (int): Timeout in seconds for each download attempt (None for no timeout)
            
        Returns:
            dict: Dictionary with paths and success status
        """
        try:
            import threading
            import re
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"parliament_tv_{session_id}_{timestamp}.mp4"
            audio_filename = f"audio_{session_id}_{timestamp}.mp3"
            
            video_path = os.path.join(output_dir, video_filename)
            audio_path = os.path.join(output_dir, audio_filename)
            
            # Create progress log files
            video_log = os.path.join(output_dir, f"{session_id}_video_progress.log")
            audio_log = os.path.join(output_dir, f"{session_id}_audio_progress.log")
            
            logger.info(f"========== STARTING SIMULTANEOUS DOWNLOAD for session {session_id} ===========")
            logger.info(f"Downloading video from {video_url} to {video_path}")
            logger.info(f"Downloading audio from {audio_url} to {audio_path}")
            
            # Build FFmpeg commands for video and audio extraction
            # VIDEO COMMAND
            video_cmd = ["ffmpeg", "-y"]
            video_cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
            video_cmd.extend(["-http_persistent", "1"])
            video_cmd.extend(["-allowed_extensions", "ALL"])
            video_cmd.extend(["-i", video_url])
            
            # Add video output options
            video_cmd.extend([
                "-c", "copy",  # Copy without re-encoding
                "-hide_banner",     # Hide banner information
                "-progress", video_log,  # Log progress to file
                video_path           # Output file
            ])
            
            # AUDIO COMMAND - Using exact command structure that works
            audio_cmd = [
                "ffmpeg", "-y",
                "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                "-http_persistent", "1",
                "-allowed_extensions", "ALL",
                "-i", audio_url,
                "-c:a", "libmp3lame",
                "-q:a", "2",
                "-vn",
                "-hide_banner",
                "-progress", audio_log,
                audio_path
            ]
            
            # Log commands
            logger.info(f"Video download command: {' '.join(video_cmd)}")
            logger.info(f"Audio download command: {' '.join(audio_cmd)}")
            
            # Start both processes
            video_process = subprocess.Popen(video_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            audio_process = subprocess.Popen(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"Started video download process with PID {video_process.pid}")
            logger.info(f"Started audio download process with PID {audio_process.pid}")
            
            # Function to monitor progress
            def monitor_progress():
                last_video_progress = 0
                last_audio_progress = 0
                
                # Pattern to extract progress information
                progress_pattern = re.compile(r'out_time_ms=([0-9]+)')
                
                while video_process.poll() is None or audio_process.poll() is None:
                    # Read progress logs
                    video_progress = 0
                    audio_progress = 0
                    
                    try:
                        if os.path.exists(video_log):
                            with open(video_log, 'r') as f:
                                content = f.read()
                                match = progress_pattern.search(content)
                                if match:
                                    # Convert microseconds to seconds
                                    video_progress = int(match.group(1)) / 1000000
                    except Exception as e:
                        logger.error(f"Error reading video progress: {str(e)}")
                    
                    try:
                        if os.path.exists(audio_log):
                            with open(audio_log, 'r') as f:
                                content = f.read()
                                match = progress_pattern.search(content)
                                if match:
                                    # Convert microseconds to seconds
                                    audio_progress = int(match.group(1)) / 1000000
                    except Exception as e:
                        logger.error(f"Error reading audio progress: {str(e)}")
                    
                    # Only log if progress has changed
                    if video_progress != last_video_progress or audio_progress != last_audio_progress:
                        logger.info(f"Download Progress - Video: {video_progress:.2f}s, Audio: {audio_progress:.2f}s")
                        last_video_progress = video_progress
                        last_audio_progress = audio_progress
                    
                    # Sleep to avoid CPU overuse
                    time.sleep(1)
                
                return True
            
            # Start progress monitoring in a separate thread
            monitor_thread = threading.Thread(target=monitor_progress)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Wait for both processes to complete
            video_stdout, video_stderr = video_process.communicate()
            audio_stdout, audio_stderr = audio_process.communicate()
            
            # Wait for monitor thread to finish
            monitor_thread.join(timeout=10)
            
            # Check results
            video_success = video_process.returncode == 0
            audio_success = audio_process.returncode == 0
            
            # Log results
            if video_success:
                logger.info(f"Video download completed successfully: {video_path} ({os.path.getsize(video_path) if os.path.exists(video_path) else 0} bytes)")
            else:
                logger.error(f"Video download failed with code {video_process.returncode}")
                logger.error(f"Video stderr: {video_stderr.decode()}")
            
            if audio_success:
                logger.info(f"Audio download completed successfully: {audio_path} ({os.path.getsize(audio_path) if os.path.exists(audio_path) else 0} bytes)")
            else:
                logger.error(f"Audio download failed with code {audio_process.returncode}")
                logger.error(f"Audio stderr: {audio_stderr.decode()}")
            
            # Verify files exist and have content
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                video_success = True
            else:
                video_success = False
                logger.error(f"Video file does not exist or is empty: {video_path}")
            
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                audio_success = True
            else:
                audio_success = False
                logger.error(f"Audio file does not exist or is empty: {audio_path}")
            
            # Clean up progress log files
            try:
                if os.path.exists(video_log):
                    os.remove(video_log)
                if os.path.exists(audio_log):
                    os.remove(audio_log)
            except Exception as e:
                logger.error(f"Error cleaning up progress logs: {str(e)}")
            
            return {
                "video_path": video_path,
                "audio_path": audio_path,
                "video_success": video_success,
                "audio_success": audio_success
            }
            
        except Exception as e:
            logger.error(f"Error downloading full video: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error downloading full video: {str(e)}")
    
    def extract_segment(self, 
                        video_path: str,
                        audio_path: str,
                        start_time: int,
                        end_time: int,
                        output_dir: str,
                        segment_id: str) -> Dict[str, Any]:
        """
        Extract a segment from the local video and audio files.
        
        Args:
            video_path: Path to the full video file
            audio_path: Path to the full audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            output_dir: Directory to save the segment files
            segment_id: ID for the segment
            
        Returns:
            Dict with segment_video_path and segment_audio_path
        """
        try:
            import subprocess
            import os
            import shutil
            
            # Verify input files exist and are accessible
            if not os.path.exists(video_path):
                logger.error(f"Video file does not exist: {video_path}")
                return {
                    "segment_video_path": None,
                    "segment_audio_path": None,
                    "video_success": False,
                    "audio_success": False,
                    "error": f"Video file does not exist: {video_path}"
                }
            
            if not os.path.exists(audio_path):
                logger.error(f"Audio file does not exist: {audio_path}")
                return {
                    "segment_video_path": None,
                    "segment_audio_path": None,
                    "video_success": False,
                    "audio_success": False,
                    "error": f"Audio file does not exist: {audio_path}"
                }
            
            # Check file sizes
            video_size = os.path.getsize(video_path)
            audio_size = os.path.getsize(audio_path)
            logger.info(f"Input file sizes - Video: {video_size} bytes, Audio: {audio_size} bytes")
            
            if video_size == 0:
                logger.error(f"Video file is empty (0 bytes): {video_path}")
            
            if audio_size == 0:
                logger.error(f"Audio file is empty (0 bytes): {audio_path}")
                return {
                    "segment_video_path": None,
                    "segment_audio_path": None,
                    "video_success": False,
                    "audio_success": False,
                    "error": f"Audio file is empty (0 bytes): {audio_path}"
                }
            
            # Create output directory if it doesn't exist
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created or verified output directory: {output_dir}")
            except Exception as e:
                logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
                return {
                    "segment_video_path": None,
                    "segment_audio_path": None,
                    "video_success": False,
                    "audio_success": False,
                    "error": f"Failed to create output directory: {str(e)}"
                }
            
            # Generate segment filenames
            segment_video_path = os.path.join(output_dir, f"{segment_id}.mp4")
            segment_audio_path = os.path.join(output_dir, f"{segment_id}.mp3")
            
            # Extract video segment using ffmpeg with seeking
            logger.info(f"Extracting video segment {start_time}-{end_time}s from {video_path} to {segment_video_path}")
            video_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-ss", str(start_time),  # Start time
                "-i", video_path,  # Input file (local)
                "-t", str(end_time - start_time),  # Duration
                "-c:v", "libx264",  # Video codec
                "-preset", "fast",
                "-crf", "22",
                "-an",  # No audio
                "-ignore_unknown",  # Ignore unknown HLS tags
                segment_video_path
            ]
            
            logger.info(f"Running video command: {' '.join(video_cmd)}")
            video_process = subprocess.run(video_cmd, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
            
            video_stdout = video_process.stdout.decode()
            video_stderr = video_process.stderr.decode()
            
            # Extract audio segment using ffmpeg with seeking
            logger.info(f"Extracting audio segment {start_time}-{end_time}s from {audio_path} to {segment_audio_path}")
            
            # Use the exact command structure from the dev branch that works
            audio_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
                "-allowed_extensions", "ALL",
                "-ss", str(start_time),  # Start time
                "-i", audio_path,  # Input file (local)
                "-t", str(end_time - start_time),  # Duration
                "-c:a", "libmp3lame",  # Audio codec
                "-q:a", "2",
                "-vn",  # No video
                "-ignore_unknown",  # Ignore unknown HLS tags
                segment_audio_path
            ]
            
            logger.info(f"Running audio command: {' '.join(audio_cmd)}")
            audio_process = subprocess.run(audio_cmd, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
            
            audio_stdout = audio_process.stdout.decode()
            audio_stderr = audio_process.stderr.decode()
            
            # Check if extraction was successful
            if video_process.returncode != 0:
                logger.error(f"Video segment extraction failed with code {video_process.returncode}")
                logger.error(f"Video stderr: {video_stderr}")
            else:
                # Verify the output file exists and has content
                if os.path.exists(segment_video_path) and os.path.getsize(segment_video_path) > 0:
                    logger.info(f"Video segment extraction completed successfully: {segment_video_path} ({os.path.getsize(segment_video_path)} bytes)")
                else:
                    logger.error(f"Video segment file missing or empty: {segment_video_path}")
                    video_process.returncode = 1  # Mark as failed
                
            if audio_process.returncode != 0:
                logger.error(f"Audio segment extraction failed with code {audio_process.returncode}")
                logger.error(f"Audio stderr: {audio_stderr}")
            else:
                # Verify the output file exists and has content
                if os.path.exists(segment_audio_path) and os.path.getsize(segment_audio_path) > 0:
                    logger.info(f"Audio segment extraction completed successfully: {segment_audio_path} ({os.path.getsize(segment_audio_path)} bytes)")
                else:
                    logger.error(f"Audio segment file missing or empty: {segment_audio_path}")
                    audio_process.returncode = 1  # Mark as failed
            
            # If audio extraction failed but video succeeded, try a different approach for audio
            if video_process.returncode == 0 and audio_process.returncode != 0:
                logger.info("Attempting alternative audio extraction method...")
                
                # Try a simpler ffmpeg command for audio extraction
                alt_audio_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", audio_path,
                    "-ss", str(start_time),
                    "-t", str(end_time - start_time),
                    "-acodec", "copy",
                    segment_audio_path
                ]
                
                logger.info(f"Running alternative audio command: {' '.join(alt_audio_cmd)}")
                alt_audio_process = subprocess.run(alt_audio_cmd,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
                
                if alt_audio_process.returncode == 0 and os.path.exists(segment_audio_path) and os.path.getsize(segment_audio_path) > 0:
                    logger.info(f"Alternative audio extraction succeeded: {segment_audio_path} ({os.path.getsize(segment_audio_path)} bytes)")
                    audio_process.returncode = 0  # Mark as successful
                else:
                    logger.error(f"Alternative audio extraction failed: {alt_audio_process.stderr.decode()}")
            
            return {
                "segment_video_path": segment_video_path if video_process.returncode == 0 else None,
                "segment_audio_path": segment_audio_path if audio_process.returncode == 0 else None,
                "video_success": video_process.returncode == 0,
                "audio_success": audio_process.returncode == 0
            }
            
        except Exception as e:
            logger.error(f"Error extracting segment: {str(e)}")
            raise ValueError(f"Error extracting segment: {str(e)}")
    
    def process_segment(self, 
                      original_url: str,
                      video_url: str, 
                      audio_url: str, 
                      start_time: int, 
                      end_time: int,
                      title: str,
                      description: str,
                      session_id: str = None,
                      video_path: str = None,
                      audio_path: str = None) -> Dict[str, Any]:
        """
        Process a segment of the video by making an API call to the existing processing pipeline.
        
        Args:
            original_url: Original Parliament TV URL
            video_url: Direct video stream URL
            audio_url: Direct audio stream URL
            start_time: Start time in seconds
            end_time: End time in seconds
            title: Title for the segment
            description: Description for the segment
            session_id: Optional session ID to use
            video_path: Optional path to local video segment file
            audio_path: Optional path to local audio segment file
            
        Returns:
            Dict with processing result
        """
        try:
            import requests
            import json
            from backend.core.config import settings
            
            # Construct the API URL with scheme and host for local API calls
            api_url = f"http://localhost:8000/api/v1/supabase-automation/process-parliament-tv"
            
            # Prepare the request payload
            payload = {
                "url": original_url,
                "title": f"{title} (Segment {start_time}-{end_time}s)",
                "description": f"{description} - Processed segment from {start_time} to {end_time} seconds",
                "duration": end_time - start_time,
                "debug": False,
                "segment_info": {
                    "is_segment": True,
                    "start_time": start_time,
                    "end_time": end_time,
                    "video_url": video_url,
                    "audio_url": audio_url,
                    "parent_session_id": session_id
                }
            }
            
            # Add local file paths if provided
            if video_path and audio_path:
                payload["segment_info"]["video_path"] = video_path
                payload["segment_info"]["audio_path"] = audio_path
                payload["segment_info"]["use_local_files"] = True
            
            # Use a default API key for internal calls
            api_key = "8448700525"  # Same key used in testing
            
            # Make the API call
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
            
            logger.info(f"Making API call to process segment {start_time}-{end_time}s")
            response = requests.post(api_url, json=payload, headers=headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully started processing for segment {start_time}-{end_time}s: {result}")
                return result
            else:
                logger.error(f"Error processing segment {start_time}-{end_time}s: {response.status_code} {response.text}")
                return {
                    "success": False,
                    "error": f"API call failed with status code {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error processing segment: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing segment: {str(e)}"
            }
    
    def process_video_sequentially(self, 
                                 original_url: str,
                                 video_url: str, 
                                 audio_url: str, 
                                 title: str,
                                 description: str,
                                 duration: int = None,
                                 total_duration: int = None,
                                 segment_duration: int = 1800,
                                 is_live: bool = False,
                                 session_id: str = None) -> Dict[str, Any]:
        """
        Process a video sequentially in segments of specified duration.
        
        Args:
            video_url: URL of the video stream
            audio_url: URL of the audio stream
            title: Title of the video
            description: Description of the video
            duration: Total duration of the video in seconds. If None, will be determined from the video.
            segment_duration: Duration of each segment in seconds. Default is 1800 (30 minutes).
            
        Returns:
            Dict with results of the processing
        """
        try:
            from backend.core.config import settings
            from backend.db.models.capture import CaptureSession
            from sqlalchemy.orm import Session
            from backend.db.session import get_db
            
            # Create a new capture session if session_id is not provided
            if session_id is None:
                db = next(get_db())
                session = CaptureSession(
                    title=title,
                    description=description,
                    metadata={
                        "video_url": video_url,
                        "audio_url": audio_url,
                        "original_url": original_url,
                        "is_live": is_live
                    }
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                session_id = session.id
                logger.info(f"Created capture session with ID: {session_id}")
            else:
                logger.info(f"Using provided capture session ID: {session_id}")
            
            # Set up output directory
            output_dir = os.path.join(settings.MEDIA_STORAGE_PATH)
            os.makedirs(output_dir, exist_ok=True)
            
            # Download the full video and audio files
            download_result = self.download_full_video(video_url, audio_url, output_dir, session_id)
            video_path = download_result["video_path"]
            audio_path = download_result["audio_path"]
            video_success = download_result["video_success"]
            audio_success = download_result["audio_success"]
            
            # Verify downloads were successful
            if not video_success:
                logger.error(f"Video download failed: {video_path}")
                return {"success": False, "error": "Video download failed"}
            
            if not audio_success:
                logger.error(f"Audio download failed: {audio_path}")
                return {"success": False, "error": "Audio download failed"}
            
            # Double-check files exist and have content
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                logger.error(f"Video file does not exist or is empty: {video_path}")
                return {"success": False, "error": f"Video file does not exist or is empty: {video_path}"}
            
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                logger.error(f"Audio file does not exist or is empty: {audio_path}")
                return {"success": False, "error": f"Audio file does not exist or is empty: {audio_path}"}
            
            start_time = 0
            segment_results = []
            
            # Log successful downloads
            logger.info(f"Successfully downloaded full video to {video_path} ({os.path.getsize(video_path)} bytes)")
            logger.info(f"Successfully downloaded full audio to {audio_path} ({os.path.getsize(audio_path)} bytes)")
            
            # Determine the duration to use
            # First check if total_duration was provided directly
            if total_duration is not None:
                logger.info(f"Using provided total_duration: {total_duration} seconds")
            # Then check if duration was provided
            elif duration is not None:
                total_duration = duration
                logger.info(f"Using provided duration: {total_duration} seconds")
            # Otherwise try to determine from the video file
            else:
                # Try to get duration from the local video file
                try:
                    import json
                    
                    cmd = [
                        "ffprobe",
                        "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        video_path
                    ]
                    
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    info = json.loads(result.stdout)
                    
                    if 'format' in info and 'duration' in info['format']:
                        total_duration = int(float(info['format']['duration']))
                        logger.info(f"Detected video duration: {total_duration} seconds")
                    else:
                        logger.warning("Could not determine video duration from ffprobe output")
                        total_duration = 3600  # Default to 1 hour if we can't determine
                except Exception as e:
                    logger.error(f"Error determining video duration: {str(e)}")
                    total_duration = 3600  # Default to 1 hour if we can't determine
            
            # Process the video in segments
            logger.info(f"Processing video in {segment_duration}s segments, total duration: {total_duration}s")
            
            # Process segments until we reach the end of the video
            while start_time < total_duration:
                end_time = min(start_time + segment_duration, total_duration)
                segment_id = f"{session_id}_{len(segment_results) + 1}"
                
                # Extract segment from local files
                segment_extraction = self.extract_segment(
                    video_path=video_path,
                    audio_path=audio_path,
                    start_time=start_time,
                    end_time=end_time,
                    output_dir=output_dir,
                    segment_id=segment_id
                )
                
                # Process the current segment
                segment_title = f"{title} (Segment {len(segment_results) + 1})"
                segment_result = self.process_segment(
                    original_url=original_url,
                    video_url=video_url,
                    audio_url=audio_url,
                    start_time=start_time,
                    end_time=end_time,
                    title=segment_title,
                    description=description,
                    session_id=session_id,
                    video_path=segment_extraction["segment_video_path"],
                    audio_path=segment_extraction["segment_audio_path"]
                )
                
                segment_results.append({
                    "segment": len(segment_results) + 1,
                    "start_time": start_time,
                    "end_time": end_time,
                    "result": segment_result,
                    "video_path": segment_extraction["segment_video_path"],
                    "audio_path": segment_extraction["segment_audio_path"]
                })
                
                # Check if the segment processing was successful
                if not segment_result.get("success", False):
                    logger.warning(f"Segment {len(segment_results)} processing failed")
                
                # Move to the next segment
                start_time = end_time
                
                # Wait a bit before starting the next segment
                time.sleep(5)
            
            # Return the results of all segments
            return {
                "success": True,
                "segments": segment_results,
                "total_segments": len(segment_results),
                "total_duration": total_duration if not is_live else start_time,
                "is_live": is_live
            }
            
        except Exception as e:
            logger.error(f"Error processing video sequentially: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing video sequentially: {str(e)}",
                "segments": segment_results if 'segment_results' in locals() else []
            }
    
    def concatenate_segments(self, segment_paths: List[str], output_path: str, is_audio: bool = False) -> str:
        """
        Concatenate video or audio segments into a single file.
        
        Args:
            segment_paths: List of paths to segment files
            output_path: Path to save the concatenated file
            is_audio: Whether the segments are audio files
            
        Returns:
            Path to the concatenated file
        """
        try:
            import subprocess
            import os
            
            # Create a temporary file with the list of files to concatenate
            concat_list_path = os.path.join(os.path.dirname(output_path), "concat_list.txt")
            
            with open(concat_list_path, "w") as f:
                for path in segment_paths:
                    f.write(f"file '{path}'\n")
            
            # Use ffmpeg to concatenate the files
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",  # Copy without re-encoding
                output_path
            ]
            
            logger.info(f"Concatenating {len(segment_paths)} {'audio' if is_audio else 'video'} segments")
            subprocess.run(cmd, check=True)
            
            # Remove the temporary file
            os.remove(concat_list_path)
            
            logger.info(f"Successfully concatenated segments to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error concatenating segments: {str(e)}")
            raise ValueError(f"Error concatenating segments: {str(e)}")
