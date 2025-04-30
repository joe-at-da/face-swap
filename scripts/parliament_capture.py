#!/usr/bin/env python3
"""
Parliament TV Stream Capture Script

This script extracts the video stream URL from a Parliament TV event page,
then captures the video starting at the specified time marker.

Usage:
    python parliament_capture.py <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python parliament_capture.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parliament_capture")

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the StreamCapture class and other project modules
from backend.services.video.capture import StreamCapture
from backend.core.config import settings

def extract_stream_info(parliament_tv_url):
    """
    Extract stream information from a Parliament TV URL using our extraction script.
    """
    logger.info(f"Extracting stream info from: {parliament_tv_url}")
    
    # Call our extraction script
    extract_script = Path(__file__).parent / "extract_parliament_stream_v3.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(extract_script), parliament_tv_url],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output from the extraction script
        output_lines = result.stdout.strip().split('\n')
        json_start = output_lines.index("Stream Information:") + 1
        json_str = '\n'.join(output_lines[json_start:])
        
        stream_info = json.loads(json_str)
        logger.info(f"Successfully extracted stream info: {json.dumps(stream_info, indent=2)}")
        
        return stream_info
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting stream info: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise RuntimeError(f"Failed to extract stream info from {parliament_tv_url}")
    
    except Exception as e:
        logger.error(f"Unexpected error extracting stream info: {e}")
        raise

def capture_stream_with_time_marker(stream_url, time_marker_seconds=None, duration=None, output_file=None):
    """
    Capture a stream starting at the specified time marker.
    
    Args:
        stream_url (str): The URL of the stream to capture
        time_marker_seconds (float, optional): The time marker in seconds to start capturing from
        duration (int, optional): The duration in seconds to capture
        output_file (str, optional): The output file path
        
    Returns:
        str: The path to the captured video file
    """
    logger.info(f"Capturing stream: {stream_url}")
    
    if time_marker_seconds:
        logger.info(f"Starting at time marker: {time_marker_seconds} seconds")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the provided output file or generate one
    if not output_file:
        # Use a directory we know is writable
        # First try the user's home directory
        home_dir = Path.home()
        output_dir = home_dir / "parliament_captures"
        
        # If we're in Docker, try data directory which should be mounted
        docker_data_dir = Path("/Users/joebradley/Veedoo/Development/the-mp/data/temp")
        if docker_data_dir.exists() and os.access(docker_data_dir, os.W_OK):
            output_dir = docker_data_dir
        
        # Create the directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
        
        logger.info(f"Using output directory: {output_dir}")
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare the ffmpeg command
    ffmpeg_cmd = ['ffmpeg']
    
    # Add input options
    if time_marker_seconds:
        # For HLS streams, we need to use the -ss option after the input
        # This is more accurate for HLS streams
        ffmpeg_cmd.extend(['-i', stream_url, '-ss', str(time_marker_seconds)])
    else:
        ffmpeg_cmd.extend(['-i', stream_url])
    
    # Add duration if specified
    if duration:
        ffmpeg_cmd.extend(['-t', str(duration)])
    
    # Add output options for good quality
    ffmpeg_cmd.extend([
        '-c:v', 'libx264',  # Use H.264 codec for video
        '-preset', 'medium',  # Balance between encoding speed and compression
        '-crf', '23',  # Constant Rate Factor (0-51, lower means better quality)
        '-c:a', 'aac',  # Use AAC codec for audio
        '-b:a', '128k',  # Audio bitrate
        '-movflags', '+faststart',  # Optimize for web streaming
        str(output_file)
    ])
    
    logger.info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
    
    try:
        # Run the ffmpeg command
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor the process
        logger.info(f"Started ffmpeg process with PID: {process.pid}")
        
        # If duration is specified, wait for the process to complete
        if duration:
            logger.info(f"Capturing for {duration} seconds...")
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ffmpeg error: {stderr}")
                raise RuntimeError(f"ffmpeg failed with return code {process.returncode}")
            
            logger.info(f"Capture completed successfully. Output file: {output_file}")
        else:
            # If no duration specified, return the process for manual stopping
            logger.info("Capture started. Process will continue until manually stopped.")
            return str(output_file), process
        
        return str(output_file), None
    
    except Exception as e:
        logger.error(f"Error during capture: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Capture video from Parliament TV.')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--duration', '-d', type=int, help='Duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    args = parser.parse_args()
    
    try:
        # Extract stream info from the Parliament TV URL
        stream_info = extract_stream_info(args.url)
        
        # Get the stream URL and time marker
        if 'direct_stream' in stream_info:
            stream_url = stream_info['direct_stream']
        elif 'hls' in stream_info and stream_info['hls']:
            stream_url = stream_info['hls'][0]
        elif 'mp4' in stream_info and stream_info['mp4']:
            stream_url = stream_info['mp4'][0]
        else:
            logger.error("No valid stream URL found in the extracted information.")
            return 1
        
        # Get the time marker if available
        time_marker_seconds = None
        if 'time_marker' in stream_info and 'seconds' in stream_info['time_marker']:
            time_marker_seconds = stream_info['time_marker']['seconds']
        
        # Capture the stream
        output_file, process = capture_stream_with_time_marker(
            stream_url,
            time_marker_seconds=time_marker_seconds,
            duration=args.duration,
            output_file=args.output
        )
        
        # If no duration was specified and the process is still running,
        # wait for user to press Ctrl+C to stop
        if process:
            try:
                print("\nCapture in progress. Press Ctrl+C to stop...")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping capture...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                print(f"Capture stopped. Output file: {output_file}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
