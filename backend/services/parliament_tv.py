import os
import sys
import json
import time
import signal
import logging
import shlex
import threading
import subprocess
import shutil
import tempfile
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models.capture import CaptureSession as Capture
from backend.db.models.capture_log import CaptureLog

logger = logging.getLogger(__name__)

class ParliamentTVCapture:
    def __init__(self):
        """Initialize the Parliament TV capture service."""
        # Define standard paths
        self.temp_dir = Path("/app/data/temp")
        self.media_dir = Path("/app/data/media")
        self.scripts_dir = Path("/app/scripts")
        self.audio_extracts_dir = Path("/app/data/temp/audio_extracts")
        
        logger.info(f"Initialized with paths: temp={self.temp_dir}, media={self.media_dir}, scripts={self.scripts_dir}, audio={self.audio_extracts_dir}")
        
        # Create directories if they don't exist
        try:
            os.makedirs(str(self.temp_dir), exist_ok=True)
            os.makedirs(str(self.media_dir), exist_ok=True)
            os.makedirs(str(self.audio_extracts_dir), exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directories: {str(e)}")
        
        # Initialize active captures dictionary
        self.active_captures = {}

    def stop_capture(self, capture_id: int) -> Dict:
        """Stop a running capture and download the separate audio stream."""
        logger.info(f"Stopping capture {capture_id}")
        
        try:
            # Check if the capture is active
            if capture_id not in self.active_captures:
                logger.error(f"Capture {capture_id} is not active")
                return {"success": False, "error": f"Capture {capture_id} is not active"}
            
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                logger.error(f"Capture {capture_id} not found in database")
                return {"success": False, "error": f"Capture {capture_id} not found in database"}
            
            # Find and terminate the ffmpeg process
            logger.info(f"Terminating capture process for {capture_id}")
            
            # Get the thread from active_captures
            capture_info = self.active_captures.get(capture_id, {})
            
            # Find and terminate any running ffmpeg processes for this capture
            try:
                # Format the capture ID with leading zeros (e.g., 0096)
                padded_capture_id = str(capture_id).zfill(4)
                
                # Use ps to find ffmpeg processes containing the capture ID
                ps_cmd = ["ps", "-ef"]
                ps_result = subprocess.run(ps_cmd, capture_output=True, text=True)
                
                # Look for ffmpeg processes with this capture ID
                for line in ps_result.stdout.splitlines():
                    if f"capture_{padded_capture_id}" in line and "ffmpeg" in line:
                        # Extract PID (second column in ps output)
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                logger.info(f"Terminating process with PID {pid}")
                                # First try to terminate gracefully
                                os.kill(pid, signal.SIGTERM)
                                # Give it a moment to terminate
                                time.sleep(1)
                                # Check if it's still running
                                try:
                                    os.kill(pid, 0)  # This will raise OSError if process is gone
                                    # If we get here, process is still running, force kill
                                    logger.warning(f"Process {pid} did not terminate gracefully, forcing kill")
                                    os.kill(pid, signal.SIGKILL)
                                    time.sleep(0.5)  # Give it a moment to die
                                except OSError:
                                    # Process is already gone
                                    pass
                            except ValueError:
                                logger.warning(f"Could not parse PID from: {parts[1]}")
                            except Exception as e:
                                logger.error(f"Error killing process: {str(e)}")
            except Exception as proc_err:
                logger.error(f"Error finding/killing ffmpeg processes: {str(proc_err)}")
            
            # Get the temp file path from active_captures
            capture_info = self.active_captures.get(capture_id, {})
            temp_file = capture_info.get("temp_file")
            
            # Format the capture ID with leading zeros
            padded_capture_id = str(capture_id).zfill(4)
            
            # Define the output file path
            output_file = os.path.join(str(self.temp_dir), f"capture_{padded_capture_id}.mp4")
            
            # Convert the temporary TS file to a properly finalized MP4 file if it exists
            if temp_file and os.path.exists(temp_file):
                logger.info(f"Converting temporary TS file to MP4: {temp_file} -> {output_file}")
                
                # Create the ffmpeg command to convert TS to MP4
                convert_cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_file,
                    "-c:v", "copy", "-c:a", "copy",
                    "-movflags", "faststart",  # This ensures the moov atom is at the beginning
                    output_file
                ]
                
                # Run the command
                try:
                    convert_process = subprocess.run(
                        convert_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if convert_process.returncode == 0:
                        logger.info(f"Successfully converted to MP4: {output_file}")
                        
                        # Update the file path in the database
                        db_capture.file_path = output_file
                        
                        # Clean up the temporary file
                        try:
                            os.remove(temp_file)
                            logger.info(f"Removed temporary file: {temp_file}")
                        except Exception as e:
                            logger.warning(f"Failed to remove temporary file: {str(e)}")
                    else:
                        logger.error(f"Failed to convert to MP4: {convert_process.stderr}")
                except Exception as e:
                    logger.error(f"Error during conversion: {str(e)}")
            
            # Update the capture in the database
            db_capture.status = "completed"
            db_capture.end_time = datetime.now()
            db.commit()
            
            # Remove the capture from active_captures
            if capture_id in self.active_captures:
                del self.active_captures[capture_id]
            
            # Log the success
            self.log_capture(db, capture_id, "info", "Capture completed successfully")
            
            # Now extract audio if needed
            if output_file and os.path.exists(output_file):
                try:
                    audio_result = self.extract_audio(db, capture_id)
                    if audio_result.get("success", False):
                        logger.info(f"Successfully extracted audio: {audio_result.get('audio_file')}")
                    else:
                        logger.warning(f"Audio extraction failed: {audio_result.get('error')}")
                except Exception as e:
                    logger.error(f"Error during audio extraction: {str(e)}")
            
            return {"success": True, "file_path": db_capture.file_path}
        except Exception as e:
            logger.error(f"Error stopping capture: {str(e)}")
    
    def start_capture(self, url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> Dict:
        """Start capturing a Parliament TV stream."""
        logger.info(f"Starting capture for URL: {url}, capture_id: {capture_id}")
        logger.info(f"Scheduled start: {scheduled_start}, Scheduled end: {scheduled_end}")
        
        try:
            # Get a database session
            db = next(get_db())
            
            # Get the capture from the database
            db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
            if not db_capture:
                error_msg = f"Capture {capture_id} not found in database"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Extract the stream URL
            stream_info = self.extract_stream_url(url)
            if "error" in stream_info:
                error_msg = f"Failed to extract stream URL: {stream_info['error']}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Get the video and audio URLs
            video_url = stream_info.get("video_url")
            audio_url = stream_info.get("audio_url")
            
            logger.info(f"Stream info: {stream_info}")
            
            # Verify we have a valid video URL
            if not video_url:
                # If we don't have a video URL but we have the original URL, try to use that
                if "original_url" in stream_info and stream_info["original_url"]:
                    logger.warning(f"No video_url found in stream_info, using original URL")
                    video_url = stream_info["original_url"]
                else:
                    logger.error(f"No valid video URL found in stream_info")
                    error_msg = "No valid video stream URL found"
                    logger.error(error_msg)
                    self.log_capture(db, capture_id, "error", error_msg)
                    return {"success": False, "error": error_msg}
            
            if video_url and audio_url:
                logger.info(f"Found separate video and audio URLs for capture {capture_id}")
                logger.info(f"Video URL: {video_url}")
                logger.info(f"Audio URL: {audio_url}")
            elif video_url:
                logger.info(f"Using single video stream URL for capture {capture_id}")
                logger.info(f"Video URL: {video_url}")
            else:
                logger.error("No valid video URL found in stream info")
                
            if not video_url:
                error_msg = "No valid video stream URL found"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Create the output directory if it doesn't exist and ensure it has proper permissions
            os.makedirs(str(self.temp_dir), exist_ok=True)
            
            # Ensure the directory has proper permissions
            try:
                os.chmod(str(self.temp_dir), 0o777)  # rwx for all users
                logger.info(f"Set permissions on directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Could not set permissions on directory: {e}")
                
            # Create the video file path
            padded_capture_id = str(capture_id).zfill(4)
            output_filename = f"capture_{padded_capture_id}.mp4"
            output_path = os.path.join(self.temp_dir, output_filename)
            logger.info(f"Output file path: {output_path}")
            
            # Start the ffmpeg process to capture the video
            cmd = ["ffmpeg", "-y"]
            
            # Add essential options for HLS streams
            cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
            cmd.extend(["-http_persistent", "1"])
            cmd.extend(["-allowed_extensions", "ALL"])
            
            # Check if we have a time marker in the scheduled start time
            start_position = None
        
            # First check if time_marker is in the stream_info
            if "time_marker" in stream_info and stream_info["time_marker"] and "seconds" in stream_info["time_marker"]:
                time_marker_seconds = stream_info["time_marker"]["seconds"]
                if time_marker_seconds > 0:
                    start_position = time_marker_seconds
                    logger.info(f"Using time marker from stream_info: {start_position} seconds")
                    
                    # Update the metadata in the database
                    if not db_capture.metadata:
                        db_capture.metadata = {}
                    db_capture.metadata["time_marker"] = {"seconds": time_marker_seconds}
                    db_capture.metadata["video_url"] = video_url
                    db_capture.metadata["audio_url"] = audio_url
                    db.commit()
                    logger.info(f"Updated metadata in database with time marker: {time_marker_seconds}")
            # Fall back to metadata if not in stream_info
            elif db_capture.metadata and "time_marker" in db_capture.metadata:
                time_marker_seconds = db_capture.metadata.get("time_marker", {}).get("seconds", 0)
                if time_marker_seconds > 0:
                    # If we have a time marker, use it as the start position
                    start_position = time_marker_seconds
                    logger.info(f"Using time marker from metadata: {start_position} seconds")
            elif scheduled_start:
                logger.info(f"Using scheduled start time but no time marker found")
        
            # Add seek option to start at the specified position
            if start_position:
                # For ffmpeg, it's more efficient to put -ss BEFORE -i for seeking
                cmd.extend(["-ss", str(start_position)])
                logger.info(f"Added seek option to ffmpeg command: -ss {start_position}")
                
            # Ensure video_url is a valid string
            if not video_url or not isinstance(video_url, str):
                error_msg = f"Invalid or missing video URL: {video_url}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
                
            # Use the video_url directly - it's already been validated as a string
            actual_video_url = video_url
            logger.info(f"Using video URL: {actual_video_url}")
            
            # Add network-related options to handle Parliament TV URLs
            cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
            cmd.extend(["-http_persistent", "1"])
            cmd.extend(["-allowed_extensions", "ALL"])
            cmd.extend(["-reconnect", "1"])
            cmd.extend(["-reconnect_streamed", "1"])
            cmd.extend(["-reconnect_delay_max", "5"])
            cmd.extend(["-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"])
                
            # Add input file for video
            cmd.extend(["-i", actual_video_url])
            
            # For HLS streams, it's better to use a single input with both video and audio
            # This avoids synchronization issues and HTTP 415 errors
            logger.info(f"Using video URL for both video and audio: {actual_video_url}")
            
            # Add options to handle HLS streams better
            cmd.extend(["-live_start_index", "0"])
            cmd.extend(["-avoid_negative_ts", "make_zero"])
            cmd.extend(["-correct_ts_overflow", "1"])
            
            # Try to use the audio from the video stream if available
            logger.info("Using audio from video stream if available")
            
            # Add additional options for better handling of streams
            cmd.extend(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"])
            
            # Add HLS-specific options
            cmd.extend(["-hls_allow_cache", "1"])
            cmd.extend(["-http_persistent", "1"])
            
            # Use proper codec options to ensure we have a valid MP4 file
            # Instead of just copying the video stream, use a specific codec to ensure compatibility
            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "22"])
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
            
            # Use a simpler approach for initial capture - just save to a temporary TS file
            # We'll convert this to a proper MP4 later
            temp_ts_file = os.path.join(str(self.temp_dir), f"temp_capture_{padded_capture_id}.ts")
            
            # Use TS format for initial capture as it's more resilient to interruptions
            cmd.extend(["-f", "mpegts"])
            cmd.append(temp_ts_file)
            
            # Store the temp file path in the capture info for later processing
            self.active_captures[capture_id]["temp_file"] = temp_ts_file
            
            # We'll convert this to MP4 in the stop_capture method
            cmd.extend(["-avoid_negative_ts", "make_zero"])
            
            # Add duration limit
            # For recorded streams with a time marker, this is the exact duration to capture
            # For live streams, this acts as a safety limit
            cmd.extend(["-t", str(duration)])
            logger.info(f"Setting capture duration to {duration} seconds")
            
            # Add output file
            cmd.extend([str(output_path)])
            
            # Log the full command for debugging
            logger.info(f"Full ffmpeg command: {' '.join(cmd)}")
            
            # Create the output directory if it doesn't exist
            os.makedirs(os.path.dirname(str(output_path)), exist_ok=True)
            
            # Start the ffmpeg process with better error handling
            try:
                # First, test if the stream is accessible
                logger.info(f"Testing stream accessibility for URL: {actual_video_url}")
                test_result = self.test_stream_url(actual_video_url)
                
                if not test_result.get("success", False):
                    error_msg = f"Stream URL is not accessible: {test_result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    self.log_capture(db, capture_id, "error", error_msg)
                    return {"success": False, "error": error_msg}
                
                logger.info(f"Stream URL test successful: {test_result.get('message', '')}")
                
                # Log the time marker if available
                if start_position:
                    logger.info(f"Using time marker for seeking: {start_position} seconds")
                
                # Create a log file for ffmpeg output
                log_file_path = os.path.join(self.temp_dir, f"ffmpeg_log_{capture_id}.txt")
                
                logger.info(f"Stream URL is accessible, starting capture process")
                logger.info(f"Full command: {' '.join(cmd)}")
                
                # Use a different approach to run ffmpeg - run in the background with nohup
                # This prevents zombie processes and ensures the process continues even if the parent exits
                background_cmd = f"nohup {' '.join(cmd)} > {log_file_path} 2>&1 &"
                logger.info(f"Running background command: {background_cmd}")
                
                # Run the command in a shell to use nohup properly
                subprocess.run(background_cmd, shell=True)
                
                logger.info(f"Started ffmpeg process for capture {capture_id} in the background")
                
                # Store information in the active_captures dictionary
                self.active_captures[capture_id] = {
                    "start_time": datetime.now(),
                    "scheduled_end": scheduled_end,
                    "output_file": str(output_path)
                }
                
                # Touch the output file to ensure it exists with proper permissions
                try:
                    with open(output_path, 'w') as f:
                        pass
                    os.chmod(output_path, 0o666)  # rw for all users
                    logger.info(f"Created empty output file with proper permissions: {output_path}")
                except Exception as e:
                    logger.warning(f"Could not create empty output file: {e}")
                
                # Update the database
                db_capture.video_file = str(output_path)
                db_capture.status = "active"
                db_capture.start_time = datetime.now()
                db_capture.end_time = None
                db.commit()
                
                # Log the capture start
                self.log_capture(db, capture_id, "info", f"Started capture for URL: {url}")
                
                return {
                    "success": True,
                    "message": f"Capture {capture_id} started successfully",
                    "output_file": str(output_path),
                    "video_url": actual_video_url,
                    "audio_url": audio_url
                }
            
            except subprocess.TimeoutExpired:
                error_msg = "Timeout while testing stream URL"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Failed to start ffmpeg process: {str(e)}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return {"success": False, "error": f"Failed to start capture: {str(e)}"}
    
    def start_capture_async(self, url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> bool:
        """Start capturing a Parliament TV stream asynchronously."""
        logger.info(f"Starting async capture for URL: {url}, capture_id: {capture_id}")
        
        try:
            # Start the capture in a separate thread
            thread = threading.Thread(
                target=self.start_capture,
                args=(url, capture_id, duration, scheduled_start, scheduled_end)
            )
            thread.daemon = True
            thread.start()
            
            # Store the thread
            if capture_id in self.active_captures:
                self.active_captures[capture_id]["thread"] = thread
            else:
                self.active_captures[capture_id] = {"thread": thread}
            
            return True
        except Exception as e:
            logger.error(f"Failed to start async capture: {str(e)}")
            return False
    
    def extract_stream_url(self, url: str) -> Dict:
        """Extract the direct stream URL from a Parliament TV event URL."""
        try:
            logger.info(f"Extracting stream URL from: {url}")
            
            # Validate URL
            if not url:
                logger.error(f"Invalid URL provided: {url}")
                return {"error": f"Invalid URL provided: {url}"}
                
            # Check if the URL is already a dictionary with direct stream URLs
            if isinstance(url, dict) and "video_url" in url:
                logger.info(f"Direct stream URL is already a dictionary: {url}")
                video_url = url.get("video_url")
                audio_url = url.get("audio_url")
                return {
                    "video_url": video_url,
                    "audio_url": audio_url,
                    "event_id": "direct",
                    "time_marker": {"seconds": 0},
                    "original_url": url.get("original_url", "Direct Stream")
                }
            
            # Check if the URL is already a direct stream URL
            if isinstance(url, str) and ('.m3u8' in url or 'cdn.redbee.live' in url):
                logger.info("URL appears to be a direct stream URL already")
                
                # Determine if this is a video or audio URL
                is_audio = 'audio' in url.lower() and not 'video' in url.lower()
                
                if is_audio:
                    logger.info("URL appears to be an audio stream")
                    # Try to derive the video URL from the audio URL
                    video_url = url.replace('audio', 'video')
                    return {
                        "video_url": video_url,
                        "audio_url": url,
                        "event_id": "direct",
                        "time_marker": {"seconds": 0},
                        "original_url": url
                    }
                else:
                    logger.info("URL appears to be a video stream")
                    # Try to derive the audio URL from the video URL
                    audio_url = None
                    if 'video' in url.lower():
                        audio_url = url.replace('video', 'audio')
                        # Check if we need to add bitrate for audio
                        if '_eng=' not in audio_url and '.m3u8' in audio_url:
                            audio_url = audio_url.replace('.m3u8', '_eng=64000.m3u8')
                    
                    if audio_url:
                        return {
                            "video_url": url,
                            "audio_url": audio_url,
                            "event_id": "direct",
                            "time_marker": {"seconds": 0},
                            "original_url": url
                        }
                    else:
                        return {
                            "video_url": url,
                            "audio_url": None,
                            "event_id": "direct",
                            "time_marker": {"seconds": 0},
                            "original_url": url
                        }
            
            # Set script path
            script_path = "/app/scripts/extract-url.py"
            
            # Verify the script exists
            if not os.path.exists(script_path):
                logger.warning(f"Script not found at {script_path}, checking alternatives")
                # Try alternative locations
                alt_paths = [
                    "/app/backend/scripts/extract-url.py",
                    "/app/scripts/extract-url.py",
                    "/Users/joebradley/Veedoo/Development/the-mp/scripts/extract-url.py"
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        script_path = alt_path
                        logger.info(f"Found script at: {script_path}")
                        break
                else:
                    logger.error("Could not find extract-url.py in any location")
                    return {"error": "Could not find extract-url.py script"}
            
            # Check if Python executable is valid
            python_executable = sys.executable
            if not os.path.exists(python_executable):
                logger.warning(f"Python executable not found: {python_executable}")
                # Try to find python executable
                alt_python_paths = [
                    "/usr/bin/python3",
                    "/usr/bin/python",
                    "/usr/local/bin/python3",
                    "/usr/local/bin/python"
                ]
                for alt_path in alt_python_paths:
                    if os.path.exists(alt_path):
                        python_executable = alt_path
                        logger.info(f"Found Python at: {python_executable}")
                        break
                else:
                    logger.error("Could not find Python executable")
                    return {"error": "Could not find Python executable"}
            
            # Build and run the command
            cmd = [python_executable, script_path, url]
            logger.info(f"Running extract-url command for: {url}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check if the command was successful
            if result.returncode == 0:
                try:
                    # Parse the JSON output
                    stream_info = json.loads(result.stdout)
                    logger.info(f"Successfully extracted stream URL: {stream_info}")
                    
                    # Convert old format to new format if needed
                    if "direct_stream" in stream_info:
                        logger.info(f"Converting old format with direct_stream to new format")
                        direct_stream = stream_info["direct_stream"]
                        if isinstance(direct_stream, dict) and "video_url" in direct_stream:
                            # Extract video_url and audio_url from nested dict
                            return {
                                "video_url": direct_stream.get("video_url"),
                                "audio_url": direct_stream.get("audio_url"),
                                "event_id": stream_info.get("event_id"),
                                "time_marker": stream_info.get("time_marker"),
                                "original_url": stream_info.get("original_url")
                            }
                        else:
                            # If direct_stream is a string, it's the video URL
                            return {
                                "video_url": direct_stream if isinstance(direct_stream, str) else None,
                                "audio_url": None,
                                "event_id": stream_info.get("event_id"),
                                "time_marker": stream_info.get("time_marker"),
                                "original_url": stream_info.get("original_url")
                            }
                    else:
                        # Already in the new format or different structure
                        return {
                            "video_url": stream_info.get("video_url") or stream_info.get("url"),
                            "audio_url": stream_info.get("audio_url"),
                            "event_id": stream_info.get("event_id"),
                            "time_marker": stream_info.get("time_marker"),
                            "original_url": stream_info.get("original_url") or url
                        }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON output: {str(e)}")
                    return {"error": f"Failed to parse JSON output: {str(e)}"}
            else:
                logger.error(f"Command failed with return code {result.returncode}: {result.stderr}")
                return {"error": f"Command failed with return code {result.returncode}: {result.stderr}"}
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}

    def log_capture(self, db: Session, capture_id: int, level: str, message: str):
        """Log a message for a capture."""
        try:
            # Create a new log entry
            log = CaptureLog(
                capture_id=capture_id,
                level=level,
                message=message,
                timestamp=datetime.now()
            )
            db.add(log)
            db.commit()
            logger.debug(f"Added log for capture {capture_id}: [{level}] {message}")
        except Exception as e:
            logger.error(f"Failed to add log for capture {capture_id}: {str(e)}")
            # Don't raise the exception, just log it
            
    def test_stream_url(self, url: str) -> bool:
        """Test if a stream URL is valid and accessible.
        
        Args:
            url: The URL to test
            
        Returns:
            bool: True if the URL is valid and accessible, False otherwise
        """
        try:
            # Use ffprobe to check if the stream is valid
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                url
            ]
            
            # Run the command with a timeout
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5  # 5 second timeout
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                return True
            else:
                logger.warning(f"Stream URL test failed: {url}. Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.warning(f"Stream URL test timed out: {url}")
            return False
        except Exception as e:
            logger.error(f"Error testing stream URL: {url}. Error: {str(e)}")
            return False

    def extract_audio(self, db: Session, capture_id: int) -> Dict:
        """Extract audio from a video file or directly from the stream URL"""
        logger.info(f"Extracting audio for capture {capture_id}")
        
        # Get the capture from the database
        db_capture = db.query(Capture).filter(Capture.id == capture_id).first()
        if not db_capture:
            error_msg = f"Capture {capture_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Check if we have a video file or need to use the source URL
        video_file = db_capture.file_path
        source_url = db_capture.source_url
        
        logger.info(f"Video file path: {video_file}")
        logger.info(f"Source URL: {source_url}")
        
        # Define the output file path - use the audio_extracts_dir
        output_dir = str(self.audio_extracts_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Format capture ID with leading zeros
        padded_capture_id = str(capture_id).zfill(4)
        output_file = os.path.join(output_dir, f"capture_{padded_capture_id}.mp3")
        
        # Start the ffmpeg process to extract the audio
        cmd = ["ffmpeg", "-y"]
        
        if video_file and os.path.exists(video_file):
            # Use the video file if it exists
            logger.info(f"Extracting audio from video file: {video_file}")
            cmd.extend(["-i", video_file])
        elif source_url:
            # Try to extract the stream URL if we don't have a video file
            logger.info(f"Extracting audio directly from source URL: {source_url}")
            
            try:
                # Extract the stream URL
                stream_info = self.extract_stream_url(source_url)
                
                # Get audio and video URLs directly from the standardized format
                audio_url = stream_info.get("audio_url")
                video_url = stream_info.get("video_url")
                
                # Log what we found
                if audio_url:
                    logger.info(f"Found dedicated audio URL: {audio_url}")
                if video_url:
                    logger.info(f"Found video URL: {video_url}")
                    
                # Use audio URL if available
                if audio_url and isinstance(audio_url, str):
                    logger.info(f"Using dedicated audio URL: {audio_url}")
                    cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
                    cmd.extend(["-http_persistent", "1"])
                    cmd.extend(["-allowed_extensions", "ALL"])
                    cmd.extend(["-reconnect", "1"])
                    cmd.extend(["-reconnect_streamed", "1"])
                    cmd.extend(["-reconnect_delay_max", "5"])
                    cmd.extend(["-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"])
                    cmd.extend(["-i", audio_url])
                # Fall back to video URL if no audio URL
                elif video_url and isinstance(video_url, str):
                    logger.info(f"Using video URL for audio extraction: {video_url}")
                    cmd.extend(["-protocol_whitelist", "file,http,https,tcp,tls,crypto"])
                    cmd.extend(["-http_persistent", "1"])
                    cmd.extend(["-allowed_extensions", "ALL"])
                    cmd.extend(["-reconnect", "1"])
                    cmd.extend(["-reconnect_streamed", "1"])
                    cmd.extend(["-reconnect_delay_max", "5"])
                    cmd.extend(["-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"])
                    cmd.extend(["-i", video_url])
                else:
                    error_msg = f"No valid stream URL found in {stream_info}"
                    logger.error(error_msg)
                    self.log_capture(db, capture_id, "error", error_msg)
                    return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = f"Failed to extract stream URL: {str(e)}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
        else:
            error_msg = "No video file or source URL available for audio extraction"
            logger.error(error_msg)
            self.log_capture(db, capture_id, "error", error_msg)
            return {"success": False, "error": error_msg}
        
        # Add audio extraction options
        cmd.extend(["-vn", "-acodec", "libmp3lame", "-ab", "128k"])
        
        # Ensure we're creating an MP3 file
        cmd.extend(["-f", "mp3"])
        
        # Add the output file
        cmd.append(output_file)
        
        # Log the full command for debugging
        logger.info(f"Full ffmpeg command for audio extraction: {' '.join(cmd)}")
        
        try:
            # Create the output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Use a more reliable approach to run ffmpeg
            # Convert the command list to a string with proper escaping
            cmd_str = ' '.join([shlex.quote(str(arg)) for arg in cmd])
            logger.info(f"Running command: {cmd_str}")
            
            # Run the command with shell=False to avoid shell syntax issues
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            logger.info(f"Completed ffmpeg process for audio extraction with return code: {process.returncode}")
            
            # Get stdout and stderr
            stdout = process.stdout
            stderr = process.stderr
            
            # Check if the process completed successfully
            if process.returncode != 0:
                error_msg = f"Failed to extract audio: {stderr}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Check if the output file was created
            if not os.path.exists(output_file):
                error_msg = f"Audio file was not created at {output_file}"
                logger.error(error_msg)
                self.log_capture(db, capture_id, "error", error_msg)
                return {"success": False, "error": error_msg}
            
            # Update the capture in the database
            db_capture.audio_file_path = output_file
            db.commit()
            logger.info(f"Updated database with audio file path: {output_file}")
            
            # Log the success
            self.log_capture(db, capture_id, "info", f"Audio extracted to {output_file}")
            
            return {
                "success": True,
                "audio_file": output_file
            }
        except Exception as e:
            error_msg = f"Error during audio extraction: {str(e)}"
            logger.error(error_msg)
            self.log_capture(db, capture_id, "error", error_msg)
            return {"success": False, "error": error_msg}


# Initialize the Parliament TV capture service
parliament_tv_capture = ParliamentTVCapture()


# Module-level functions for API endpoints
def start_capture(url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> Dict:
    """Start capturing a Parliament TV stream."""
    return parliament_tv_capture.start_capture(url, capture_id, duration, scheduled_start, scheduled_end)


def start_capture_async(url: str, capture_id: int, duration: int = 1800, scheduled_start=None, scheduled_end=None) -> bool:
    """Start capturing a Parliament TV stream asynchronously."""
    return parliament_tv_capture.start_capture_async(url, capture_id, duration, scheduled_start, scheduled_end)


def stop_capture(capture_id: int) -> Dict:
    """Stop a running capture."""
    return parliament_tv_capture.stop_capture(capture_id)


def get_capture_status(capture_id: int) -> Dict:
    """Get the status of a capture."""
    return parliament_tv_capture.get_capture_status(capture_id)


def get_capture_logs(capture_id: int) -> Dict:
    """Get the logs for a capture."""
    return parliament_tv_capture.get_capture_logs(capture_id)


def extract_stream_url(url: str) -> Dict:
    """Extract the direct stream URL from a Parliament TV event URL."""
    return parliament_tv_capture.extract_stream_url(url)


def test_stream_url(url: str) -> Dict:
    """Test if a stream URL is valid and accessible."""
    return parliament_tv_capture.test_stream_url(url)


def extract_audio(db: Session, capture_id: int) -> Dict:
    """Extract audio from a video file or directly from the stream URL."""
    return parliament_tv_capture.extract_audio(db, capture_id)
