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
    
    def download_full_video(self, video_url: str, audio_url: str, output_dir: str, session_id: str) -> Dict[str, Any]:
        """
        Download the full video and audio streams.
        
        Args:
            video_url: Direct video stream URL
            audio_url: Direct audio stream URL
            output_dir: Directory to save the downloaded files
            session_id: Session ID for the capture
            
        Returns:
            Dict with video_path and audio_path
        """
        try:
            import subprocess
            import os
            from datetime import datetime
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"parliament_tv_{session_id}_{timestamp}.mp4"
            audio_filename = f"audio_{session_id}_{timestamp}.mp3"
            
            video_path = os.path.join(output_dir, video_filename)
            audio_path = os.path.join(output_dir, audio_filename)
            
            logger.info(f"Downloading video from {video_url} to {video_path}")
            logger.info(f"Downloading audio from {audio_url} to {audio_path}")
            
            # Start video download in background
            video_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i", video_url,
                "-c", "copy",  # Copy without re-encoding
                video_path
            ]
            
            video_process = subprocess.Popen(video_cmd, 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE)
            
            # Start audio download in background
            audio_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output files
                "-i", audio_url,
                "-c", "copy",  # Copy without re-encoding
                audio_path
            ]
            
            audio_process = subprocess.Popen(audio_cmd, 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE)
            
            logger.info("Started video and audio downloads in background")
            
            return {
                "video_path": video_path,
                "audio_path": audio_path,
                "video_process": video_process,
                "audio_process": audio_process
            }
            
        except Exception as e:
            logger.error(f"Error downloading full video: {str(e)}")
            raise ValueError(f"Error downloading full video: {str(e)}")
    
    def process_segment(self, 
                      original_url: str,
                      video_url: str, 
                      audio_url: str, 
                      start_time: int, 
                      end_time: int,
                      title: str,
                      description: str,
                      session_id: str = None) -> Dict[str, Any]:
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
                                 total_duration: int = None,
                                 is_live: bool = False,
                                 session_id: str = None) -> Dict[str, Any]:
        """
        Process a video sequentially in 30-minute segments.
        
        Args:
            original_url: Original Parliament TV URL
            video_url: Direct video stream URL
            audio_url: Direct audio stream URL
            title: Title for the video
            description: Description for the video
            total_duration: Total duration in seconds (if known)
            is_live: Whether the video is live
            session_id: Optional session ID to use
            
        Returns:
            Dict with processing results
        """
        try:
            import time
            from datetime import datetime
            
            segment_duration = self.DEFAULT_SEGMENT_DURATION
            start_time = 0
            segment_results = []
            
            # If it's a live stream, we'll keep processing until the stream ends
            if is_live:
                logger.info(f"Processing live stream in {segment_duration}s segments")
                
                while True:
                    end_time = start_time + segment_duration
                    
                    # Process the current segment
                    segment_title = f"{title} (Live Segment {len(segment_results) + 1})"
                    segment_result = self.process_segment(
                        original_url=original_url,
                        video_url=video_url,
                        audio_url=audio_url,
                        start_time=start_time,
                        end_time=end_time,
                        title=segment_title,
                        description=description,
                        session_id=session_id
                    )
                    
                    segment_results.append({
                        "segment": len(segment_results) + 1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "result": segment_result
                    })
                    
                    # Check if the stream is still live
                    # For now, we'll just check if the segment processing was successful
                    if not segment_result.get("success", False):
                        logger.info(f"Segment {len(segment_results)} processing failed, assuming stream has ended")
                        break
                    
                    # Move to the next segment
                    start_time = end_time
                    
                    # Wait a bit before starting the next segment
                    time.sleep(5)
            else:
                # For archived videos, we know the total duration
                if not total_duration:
                    # If total_duration is not provided, try to get it from ffprobe
                    try:
                        import subprocess
                        import json
                        
                        cmd = [
                            "ffprobe",
                            "-v", "quiet",
                            "-print_format", "json",
                            "-show_format",
                            video_url
                        ]
                        
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                        info = json.loads(result.stdout)
                        
                        if 'format' in info and 'duration' in info['format']:
                            total_duration = int(float(info['format']['duration']))
                            logger.info(f"Detected video duration: {total_duration} seconds")
                        else:
                            # Default to 2 hours if we can't determine the duration
                            total_duration = 7200
                            logger.warning(f"Could not determine video duration, using default: {total_duration} seconds")
                    except Exception as e:
                        logger.error(f"Error determining video duration: {str(e)}")
                        # Default to 2 hours if we can't determine the duration
                        total_duration = 7200
                        logger.warning(f"Using default duration: {total_duration} seconds")
                
                logger.info(f"Processing archived video with duration {total_duration}s in {segment_duration}s segments")
                
                # Process the video in segments
                while start_time < total_duration:
                    end_time = min(start_time + segment_duration, total_duration)
                    
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
                        session_id=session_id
                    )
                    
                    segment_results.append({
                        "segment": len(segment_results) + 1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "result": segment_result
                    })
                    
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
