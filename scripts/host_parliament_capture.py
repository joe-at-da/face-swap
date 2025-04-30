#!/usr/bin/env python3
"""
Host-based Parliament TV stream capture with facial recognition.
This script downloads a Parliament TV stream on the host machine and processes it with facial recognition in Docker.

Usage: python host_parliament_capture.py <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]
Example: python host_parliament_capture.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120
"""

import sys
import os
import json
import argparse
import subprocess
import tempfile
import logging
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"parliament_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger('host_parliament_capture')

def create_directories():
    """Create necessary directories for storing temporary and output files."""
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/media/parliament_captures", exist_ok=True)
    logger.info("Created necessary directories.")

def extract_stream_info(url, output_file):
    """Extract stream information from the Parliament TV URL."""
    logger.info(f"Extracting stream info from: {url}")
    
    try:
        cmd = [
            sys.executable,
            "scripts/extract_parliament_stream_v4.py",
            url,
            "--output", output_file
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Stream info extraction completed. Output saved to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting stream info: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def check_command_exists(command):
    """Check if a command exists in the system PATH."""
    try:
        subprocess.run(["which", command], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def download_stream(stream_url, output_file, duration=None):
    """Download the stream using yt-dlp or ffmpeg."""
    logger.info(f"Downloading stream from: {stream_url}")
    logger.info(f"Output file: {output_file}")
    
    if duration:
        logger.info(f"Duration limit: {duration} seconds")
    
    # Check if yt-dlp is available
    if check_command_exists("yt-dlp"):
        # Try with yt-dlp
        try:
            cmd = ["yt-dlp", "-o", output_file, "--no-check-certificate"]
            
            if duration:
                # Correct format for download-sections is "*start-end"
                cmd.extend(["--download-sections", f"*0-{duration}"])
            
            cmd.append(stream_url)
            
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Download completed successfully using yt-dlp.")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"yt-dlp download failed: {e}")
            logger.warning(f"STDOUT: {e.stdout}")
            logger.warning(f"STDERR: {e.stderr}")
    else:
        logger.warning("yt-dlp not found in PATH")
    
    # Check if ffmpeg is available
    if check_command_exists("ffmpeg"):
        # Try with ffmpeg
        try:
            cmd = ["ffmpeg", "-i", stream_url]
            
            if duration:
                cmd.extend(["-t", str(duration)])
            
            cmd.extend(["-c", "copy", "-y", output_file])
            
            logger.info(f"Trying ffmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Download completed successfully using ffmpeg.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg download failed: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            return False
    else:
        logger.error("Neither yt-dlp nor ffmpeg found in PATH. Please install one of these tools.")
        return False

def process_with_facial_recognition(input_file, duration=None):
    """Process the downloaded video with facial recognition in Docker."""
    logger.info(f"Processing {input_file} with facial recognition in Docker")
    
    # Get the container name
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=the-mp-app"],
            check=True, capture_output=True, text=True
        )
        containers = result.stdout.strip().split('\n')
        if not containers or not containers[0]:
            logger.error("No Docker container found with name 'the-mp-app'")
            return False
        
        container_name = containers[0]
        logger.info(f"Found Docker container: {container_name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting Docker container: {e}")
        return False
    
    # Copy the file to the Docker container
    try:
        docker_path = f"/app/data/temp/{os.path.basename(input_file)}"
        subprocess.run(
            ["docker", "cp", input_file, f"{container_name}:{docker_path}"],
            check=True, capture_output=True, text=True
        )
        logger.info(f"Copied {input_file} to Docker container at {docker_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error copying file to Docker: {e}")
        return False
    
    # Copy the facial recognition script to the container
    try:
        subprocess.run(
            ["docker", "cp", "scripts/facial_recognition_capture.py", f"{container_name}:/app/scripts/"],
            check=True, capture_output=True, text=True
        )
        logger.info("Copied facial_recognition_capture.py to Docker container")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error copying script to Docker: {e}")
        return False
    
    # Make the script executable
    try:
        subprocess.run(
            ["docker", "exec", container_name, "chmod", "+x", "/app/scripts/facial_recognition_capture.py"],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error making script executable: {e}")
        return False
    
    # Run the facial recognition script in the container
    try:
        cmd = ["docker", "exec", container_name, "python", "/app/scripts/facial_recognition_capture.py", docker_path]
        
        if duration:
            cmd.extend(["--duration", str(duration)])
        
        cmd.append("--docker")
        
        logger.info(f"Running facial recognition: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Facial recognition processing completed successfully.")
        logger.info(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running facial recognition: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def copy_results_from_docker():
    """Copy the processed files from Docker to the host."""
    logger.info("Copying processed files from Docker to host")
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=the-mp-app"],
            check=True, capture_output=True, text=True
        )
        containers = result.stdout.strip().split('\n')
        if not containers or not containers[0]:
            logger.error("No Docker container found with name 'the-mp-app'")
            return False
        
        container_name = containers[0]
        
        subprocess.run(
            ["docker", "cp", f"{container_name}:/app/data/media/parliament_captures/.", "./data/media/parliament_captures/"],
            check=True, capture_output=True, text=True
        )
        logger.info("Successfully copied processed files from Docker to host")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error copying results from Docker: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Host-based Parliament TV stream capture with facial recognition.')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--duration', '-d', type=int, help='Maximum duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--skip-facial-recognition', action='store_true', help='Skip facial recognition processing')
    args = parser.parse_args()
    
    # Check for required tools
    if not check_command_exists("yt-dlp") and not check_command_exists("ffmpeg"):
        logger.error("Neither yt-dlp nor ffmpeg found in PATH. Please install one of these tools.")
        logger.error("You can install them with: brew install yt-dlp ffmpeg")
        return 1
    
    # Create necessary directories
    create_directories()
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Extract stream info
    stream_info_file = f"data/temp/stream_info_{timestamp}.json"
    if not extract_stream_info(args.url, stream_info_file):
        logger.error("Failed to extract stream info. Exiting.")
        return 1
    
    # Read stream info
    try:
        with open(stream_info_file, 'r') as f:
            stream_info = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error reading stream info: {e}")
        return 1
    
    # Get the stream URL
    stream_url = None
    if 'direct_stream' in stream_info:
        stream_url = stream_info['direct_stream']
    elif 'hls' in stream_info and stream_info['hls']:
        stream_url = stream_info['hls'][0]
    elif 'mp4' in stream_info and stream_info['mp4']:
        stream_url = stream_info['mp4'][0]
    
    if not stream_url:
        logger.error("No stream URL found in stream info.")
        return 1
    
    logger.info(f"Stream URL: {stream_url}")
    
    # Get time marker if available
    time_marker = None
    if 'time_marker' in stream_info and 'seconds' in stream_info['time_marker']:
        time_marker = stream_info['time_marker']['seconds']
        logger.info(f"Time marker: {time_marker} seconds")
    
    # Download the stream
    download_file = f"data/temp/parliament_stream_{timestamp}.mp4"
    if not download_stream(stream_url, download_file, args.duration):
        logger.error("Failed to download stream. Exiting.")
        return 1
    
    # Process with facial recognition
    if not process_with_facial_recognition(download_file, args.duration):
        logger.error("Failed to process with facial recognition. Exiting.")
        return 1
    
    # Copy results from Docker
    if not copy_results_from_docker():
        logger.error("Failed to copy results from Docker. Exiting.")
        return 1
    
    logger.info("Parliament TV capture with facial recognition completed successfully.")
    logger.info("Output files are in ./data/media/parliament_captures/")
    return 0

if __name__ == "__main__":
    sys.exit(main())
