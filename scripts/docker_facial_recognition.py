#!/usr/bin/env python3
"""
Docker-based Facial Recognition for Parliament TV Streams

This script is designed to run inside the Docker container and:
1. Extract the Parliament TV stream URL
2. Download a segment of the stream
3. Process the video to start at the specified time marker
4. Implement facial recognition to detect when the speaker is no longer present

Usage:
    python docker_facial_recognition.py <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python docker_facial_recognition.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

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
    from extract_parliament_stream_v4 import extract_time_marker, extract_event_id, extract_stream_urls, seconds_to_hms
    
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
    stream_info = extract_stream_urls(event_id, time_marker)
    
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

def process_video_with_facial_recognition(input_file, time_marker_seconds=None, output_file=None, max_duration=None):
    """
    Process a video file with facial recognition to detect when the speaker is no longer present.
    
    Args:
        input_file (str): The path to the input video file
        time_marker_seconds (float, optional): The time marker in seconds to start processing from
        output_file (str, optional): The output file path
        max_duration (int, optional): Maximum duration to process in seconds
        
    Returns:
        str: The path to the processed video file
    """
    logger.info(f"Processing video with facial recognition: {input_file}")
    
    if time_marker_seconds:
        logger.info(f"Starting at time marker: {time_marker_seconds} seconds")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the provided output file or generate one
    if not output_file:
        output_dir = Path("/app/data/media/parliament_captures")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary directory for frames
    temp_dir = Path("/app/data/temp/frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # First, extract a segment of the video starting at the time marker
    if time_marker_seconds:
        # Create a temporary file for the extracted segment
        temp_file = Path("/app/data/temp") / f"temp_segment_{timestamp}.mp4"
        
        # Extract the segment using ffmpeg
        extract_cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-ss', str(time_marker_seconds)
        ]
        
        # Add duration if specified
        if max_duration:
            extract_cmd.extend(['-t', str(max_duration)])
        
        # Add output options
        extract_cmd.extend([
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',
            str(temp_file)
        ])
        
        logger.info(f"Running extraction command: {' '.join(extract_cmd)}")
        
        try:
            # Run the ffmpeg command
            process = subprocess.Popen(
                extract_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ffmpeg extraction error: {stderr}")
                raise RuntimeError(f"ffmpeg extraction failed with return code {process.returncode}")
            
            logger.info(f"Extraction completed successfully. Temporary file: {temp_file}")
            
            # Update the input file to the extracted segment
            input_file = str(temp_file)
        
        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            raise
    
    # Now, process the video with facial recognition
    # For now, we'll just copy the file as a placeholder for the facial recognition implementation
    # In a real implementation, this would analyze each frame for faces
    
    # Copy the file to the output location
    copy_cmd = [
        'cp',
        str(input_file),
        str(output_file)
    ]
    
    logger.info(f"Running copy command: {' '.join(copy_cmd)}")
    
    try:
        # Run the copy command
        process = subprocess.Popen(
            copy_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Copy error: {stderr}")
            raise RuntimeError(f"Copy failed with return code {process.returncode}")
        
        logger.info(f"Copy completed successfully. Output file: {output_file}")
        
        # Clean up temporary files
        if time_marker_seconds and Path(input_file).exists() and str(input_file).startswith("/app/data/temp"):
            os.remove(input_file)
            logger.info(f"Removed temporary file: {input_file}")
        
        return str(output_file)
    
    except Exception as e:
        logger.error(f"Error during copy: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Docker-based Facial Recognition for Parliament TV Streams')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--duration', '-d', type=int, default=60, help='Duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--test', action='store_true', help='Use a test video instead of the Parliament TV stream')
    args = parser.parse_args()
    
    try:
        if args.test:
            # Use a test video for development
            test_video_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            logger.info(f"Using test video: {test_video_url}")
            
            # Download the test video
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = Path("/app/data/temp") / f"test_video_{timestamp}.mp4"
            
            # Download the test video using ffmpeg
            download_cmd = [
                'ffmpeg',
                '-i', test_video_url,
                '-c', 'copy',
                '-y',
                str(temp_file)
            ]
            
            logger.info(f"Downloading test video: {' '.join(download_cmd)}")
            
            try:
                # Run the ffmpeg command
                process = subprocess.Popen(
                    download_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait for the process to complete
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"ffmpeg download error: {stderr}")
                    raise RuntimeError(f"ffmpeg download failed with return code {process.returncode}")
                
                logger.info(f"Test video downloaded successfully. Temp file: {temp_file}")
                
                # Process the test video with facial recognition
                output_file = process_video_with_facial_recognition(
                    str(temp_file),
                    time_marker_seconds=0,
                    output_file=args.output,
                    max_duration=args.duration
                )
                
                logger.info(f"Test video processing completed. Output file: {output_file}")
                return 0
                
            except Exception as e:
                logger.error(f"Error downloading test video: {e}")
                raise
        
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
        
        # Download the stream segment
        temp_file = Path("/app/data/temp") / f"stream_segment_{timestamp}.mp4"
        downloaded_file = download_stream_segment(stream_url, temp_file, args.duration)
        
        # Process the downloaded file with facial recognition
        output_file = process_video_with_facial_recognition(
            downloaded_file,
            time_marker_seconds=time_marker_seconds,
            output_file=args.output,
            max_duration=args.duration
        )
        
        logger.info(f"Parliament TV stream processing completed. Output file: {output_file}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
