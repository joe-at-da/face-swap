#!/usr/bin/env python3
"""
Local Parliament TV Stream Capture Script

This script extracts the video stream URL from a Parliament TV event page,
then downloads the stream locally and processes it starting at the specified time marker.

Usage:
    python local_parliament_capture.py <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python local_parliament_capture.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parliament_capture")

def extract_stream_info(parliament_tv_url):
    """
    Extract stream information from a Parliament TV URL using our extraction script.
    """
    logger.info(f"Extracting stream info from: {parliament_tv_url}")
    
    # Import the extraction module directly
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_parliament_stream_v3 import extract_time_marker, extract_event_id, extract_stream_urls_using_requests, seconds_to_hms
    
    # Extract the time marker if present
    time_marker = extract_time_marker(parliament_tv_url)
    time_marker_seconds = None
    if time_marker:
        time_marker_seconds = time_marker.total_seconds()
        logger.info(f"Time marker found: {seconds_to_hms(time_marker_seconds)} ({time_marker_seconds} seconds)")
    else:
        logger.info("No time marker found. Will start from the beginning.")
    
    # Extract the event ID
    event_id = extract_event_id(parliament_tv_url)
    if not event_id:
        logger.error("Could not extract event ID from URL.")
        raise ValueError("Invalid Parliament TV URL")
    
    logger.info(f"Event ID: {event_id}")
    
    # Extract stream URLs
    stream_info = extract_stream_urls_using_requests(event_id, time_marker)
    
    if not stream_info or (not stream_info.get('hls') and not stream_info.get('mp4') and not stream_info.get('direct_stream')):
        logger.error("Could not find any stream URLs.")
        raise ValueError("No stream URLs found")
    
    # Add the time marker to the stream info
    if time_marker:
        stream_info['time_marker'] = {
            'hms': seconds_to_hms(time_marker_seconds),
            'seconds': time_marker_seconds
        }
    
    # Add the event ID to the stream info
    stream_info['event_id'] = event_id
    
    logger.info(f"Successfully extracted stream info: {json.dumps(stream_info, indent=2)}")
    
    return stream_info

def download_stream_segment(stream_url, output_path, duration=60):
    """
    Download a segment of the stream to a local file.
    
    Args:
        stream_url (str): The URL of the stream
        output_path (str): The path to save the downloaded segment
        duration (int): The duration in seconds to download
        
    Returns:
        str: The path to the downloaded file
    """
    logger.info(f"Downloading stream segment from: {stream_url}")
    
    # Create the output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use ffmpeg to download a segment of the stream
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', stream_url,
        '-t', str(duration),
        '-c', 'copy',  # Just copy the stream without re-encoding
        '-y',  # Overwrite output file if it exists
        str(output_path)
    ]
    
    logger.info(f"Running download command: {' '.join(ffmpeg_cmd)}")
    
    try:
        # Run the ffmpeg command
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg download error: {stderr}")
            raise RuntimeError(f"ffmpeg download failed with return code {process.returncode}")
        
        logger.info(f"Download completed successfully. Output file: {output_path}")
        return str(output_path)
    
    except Exception as e:
        logger.error(f"Error during download: {e}")
        raise

def process_video_with_time_marker(input_file, time_marker_seconds=None, duration=None, output_file=None):
    """
    Process a video file starting at the specified time marker.
    
    Args:
        input_file (str): The path to the input video file
        time_marker_seconds (float, optional): The time marker in seconds to start processing from
        duration (int, optional): The duration in seconds to process
        output_file (str, optional): The output file path
        
    Returns:
        str: The path to the processed video file
    """
    logger.info(f"Processing video: {input_file}")
    
    if time_marker_seconds:
        logger.info(f"Starting at time marker: {time_marker_seconds} seconds")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the provided output file or generate one
    if not output_file:
        # Use a directory we know is writable
        home_dir = Path.home()
        output_dir = home_dir / "parliament_captures"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
        logger.info(f"Using output directory: {output_dir}")
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare the ffmpeg command
    ffmpeg_cmd = ['ffmpeg', '-i', str(input_file)]
    
    # Add time marker if specified
    if time_marker_seconds:
        ffmpeg_cmd.extend(['-ss', str(time_marker_seconds)])
    
    # Add duration if specified
    if duration:
        ffmpeg_cmd.extend(['-t', str(duration)])
    
    # Add output options for good quality
    ffmpeg_cmd.extend([
        '-c', 'copy',  # Copy all streams without re-encoding (much faster)
        '-movflags', '+faststart',  # Optimize for web streaming
        str(output_file)
    ])
    
    logger.info(f"Running processing command: {' '.join(ffmpeg_cmd)}")
    
    try:
        # Run the ffmpeg command
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg processing error: {stderr}")
            raise RuntimeError(f"ffmpeg processing failed with return code {process.returncode}")
        
        logger.info(f"Processing completed successfully. Output file: {output_file}")
        return str(output_file)
    
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Capture video from Parliament TV.')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--duration', '-d', type=int, help='Duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--download-only', action='store_true', help='Only download the stream without processing')
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
        
        # Create a timestamp for the temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Parse the stream URL to get the filename
        parsed_url = urlparse(stream_url)
        stream_filename = Path(parsed_url.path).name
        
        # Create a temporary directory for downloads
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        # Set the download duration
        download_duration = args.duration or 60  # Default to 60 seconds if not specified
        
        # Download the stream segment
        temp_file = temp_dir / f"temp_{timestamp}_{stream_filename}.mp4"
        downloaded_file = download_stream_segment(stream_url, temp_file, download_duration)
        
        # If download-only flag is set, we're done
        if args.download_only:
            logger.info(f"Download-only mode. Downloaded file: {downloaded_file}")
            return 0
        
        # Process the downloaded file with the time marker
        process_video_with_time_marker(
            downloaded_file,
            time_marker_seconds=time_marker_seconds,
            duration=args.duration,
            output_file=args.output
        )
        
        # Clean up the temporary file
        try:
            Path(downloaded_file).unlink()
            logger.info(f"Deleted temporary file: {downloaded_file}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file: {e}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
