#!/usr/bin/env python3
"""
Parliament TV Direct Capture with Facial Recognition

This script extracts the direct stream URL from a Parliament TV web page,
downloads the stream, and processes it with facial recognition to detect
when the speaker is no longer present.

Usage:
    python parliament_capture_direct.py <parliament_tv_url> [--duration SECONDS] [--output OUTPUT_PATH]

Example:
    python parliament_capture_direct.py "https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38" --duration 60
"""

import sys
import os
import json
import argparse
import subprocess
import logging
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
logger = logging.getLogger('parliament_capture_direct')

def create_directories():
    """Create necessary directories for storing temporary and output files."""
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/media/parliament_captures", exist_ok=True)
    logger.info("Created necessary directories.")

def check_command_exists(command):
    """Check if a command exists in the system PATH."""
    try:
        subprocess.run(["which", command], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def extract_stream_url(url, output_file=None):
    """Extract the direct stream URL from a Parliament TV web page."""
    logger.info(f"Extracting stream URL from: {url}")
    
    # Check if the URL is already a direct stream URL (ends with .m3u8)
    if url.endswith('.m3u8'):
        logger.info("URL appears to be a direct stream URL already")
        stream_info = {"direct_stream": url}
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(stream_info, f)
        
        return stream_info
    
    # If not a direct stream URL, extract it from Parliament TV page
    try:
        cmd = [
            sys.executable,
            "scripts/extract_direct_stream.py",
            url
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # If no output file specified, parse the output directly
        if not output_file:
            # Find the JSON in the output
            output_lines = result.stdout.split('\n')
            json_start = None
            json_end = None
            
            for i, line in enumerate(output_lines):
                if line.strip().startswith('{'):
                    json_start = i
                if json_start is not None and line.strip().endswith('}'):
                    json_end = i
                    break
            
            if json_start is not None and json_end is not None:
                json_str = '\n'.join(output_lines[json_start:json_end+1])
                stream_info = json.loads(json_str)
                return stream_info
            else:
                logger.error("Could not find JSON in output")
                return None
        else:
            logger.info(f"Stream URL extraction completed. Output saved to {output_file}")
            with open(output_file, 'r') as f:
                stream_info = json.load(f)
            return stream_info
    except subprocess.CalledProcessError as e:
        logger.error(f"Error extracting stream URL: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return None

def download_stream(stream_url, output_file, duration=None):
    """Download the stream using ffmpeg."""
    if not stream_url:
        logger.error("No stream URL provided for download")
        return False
        
    logger.info(f"Downloading stream from: {stream_url}")
    logger.info(f"Output file: {output_file}")
    
    if duration:
        logger.info(f"Duration limit: {duration} seconds")
    
    # Use ffmpeg to download the stream
    try:
        # First, probe the stream to check for audio
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", stream_url]
        logger.info(f"Probing stream: {' '.join(probe_cmd)}")
        probe_result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
        
        # Parse the probe result
        has_audio = False
        try:
            probe_data = json.loads(probe_result.stdout)
            streams = probe_data.get('streams', [])
            for stream in streams:
                if stream.get('codec_type') == 'audio':
                    has_audio = True
                    break
            
            if not has_audio:
                logger.warning("No audio stream detected in the source! This may affect transcription.")
                logger.info("Attempting to download with audio anyway...")
        except json.JSONDecodeError:
            logger.warning("Could not parse ffprobe output, continuing with download")
        
        # Download the stream with explicit audio mapping
        # Use -y to overwrite output files without asking
        # Use -c:v copy to copy video without re-encoding
        # Use -c:a aac to ensure audio is captured and encoded as AAC
        # Use -ac 2 to ensure stereo audio
        # Use -ar 44100 to set audio sample rate to 44.1kHz (standard)
        cmd = [
            "ffmpeg", "-y", "-i", stream_url, 
            "-c:v", "copy", 
            "-c:a", "aac", 
            "-ac", "2", 
            "-ar", "44100", 
            "-strict", "experimental"
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        # If no audio was detected, try to force audio capture
        if not has_audio:
            logger.info("Attempting to capture with explicit audio settings")
            cmd.extend(["-c:v", "copy", "-c:a", "aac", "-strict", "experimental", "-y", output_file])
        else:
            cmd.extend(["-c", "copy", "-y", output_file])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Verify the output has audio
        verify_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", output_file]
        verify_result = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
        
        try:
            verify_data = json.loads(verify_result.stdout)
            output_has_audio = False
            for stream in verify_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    output_has_audio = True
                    break
            
            if not output_has_audio:
                logger.warning("Output file does not have an audio stream!")
                # If we still don't have audio, try one more approach with re-encoding
                if not has_audio:
                    logger.info("Attempting to re-encode with synthetic audio")
                    # Create silent audio and merge with video
                    silent_cmd = [
                        "ffmpeg", "-i", output_file, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
                        "-c:v", "copy", "-c:a", "aac", "-shortest", "-y", f"{output_file}.with_audio.mp4"
                    ]
                    subprocess.run(silent_cmd, check=True, capture_output=True, text=True)
                    # Replace original file
                    os.rename(f"{output_file}.with_audio.mp4", output_file)
        except json.JSONDecodeError:
            logger.warning("Could not verify audio in output file")
        
        logger.info("Download completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading stream: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False

def process_with_facial_recognition(video_file, output_file=None, duration=None):
    """Process the video with facial recognition."""
    logger.info(f"Processing video with facial recognition: {video_file}")
    
    try:
        cmd = [sys.executable, "scripts/facial_recognition_capture.py", video_file]
        
        if duration:
            cmd.extend(["--duration", str(duration)])
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Parse the output to find the path to the processed video
        output_lines = result.stdout.split('\n')
        processed_file = None
        
        for line in output_lines:
            if "Output file:" in line:
                processed_file = line.split("Output file:")[1].strip()
                break
        
        logger.info(f"Facial recognition processing completed. Output file: {processed_file}")
        return processed_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing video with facial recognition: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Parliament TV Direct Capture with Facial Recognition')
    parser.add_argument('url', help='Parliament TV event URL or direct stream URL')
    parser.add_argument('--duration', '-d', type=int, help='Maximum duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--capture-id', help='Capture ID for file naming')
    args = parser.parse_args()
    
    # Check for required tools
    if not check_command_exists("ffmpeg"):
        logger.error("ffmpeg not found in PATH. Please install it with: brew install ffmpeg")
        return 1
    
    # Create necessary directories
    create_directories()
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    capture_id = args.capture_id if args.capture_id else ''
    
    # Check if the URL is already a direct stream URL
    direct_stream_url = None
    if args.url.endswith('.m3u8'):
        logger.info("Input appears to be a direct stream URL")
        direct_stream_url = args.url
    else:
        # Extract the direct stream URL
        stream_info_file = f"data/temp/stream_info_{timestamp}.json"
        stream_info = extract_stream_url(args.url, stream_info_file)
        
        if not stream_info:
            logger.error("Failed to extract stream URL. Exiting.")
            return 1
        
        # Get the direct stream URL
        direct_stream_url = stream_info.get('direct_stream')
        if not direct_stream_url:
            logger.error("No direct stream URL found in stream info.")
            return 1
    
    logger.info(f"Direct stream URL: {direct_stream_url}")
    
    # Get time marker if available
    time_marker = None
    if 'time_marker' in stream_info and 'seconds' in stream_info['time_marker']:
        time_marker = stream_info['time_marker']['seconds']
        logger.info(f"Time marker: {time_marker} seconds")
    
    # Download the stream with capture ID in the filename
    if args.output:
        output_file = args.output
    else:
        # Include capture ID in the filename if provided
        if args.capture_id:
            output_file = f"data/temp/parliament_stream_{timestamp}_{args.capture_id}.mp4"
        else:
            output_file = f"data/temp/parliament_stream_{timestamp}.mp4"
    
    logger.info(f"Using output file: {output_file}")
    if not download_stream(direct_stream_url, output_file, args.duration):
        logger.error("Failed to download stream. Exiting.")
        return 1
    
    # Process the video with facial recognition
    final_output_file = args.output or f"data/media/parliament_captures/parliament_capture_{timestamp}_{capture_id}.mp4"
    
    # Don't overwrite the input file - use a different output path
    processed_file = process_with_facial_recognition(output_file, final_output_file, args.duration)
    
    if not processed_file:
        logger.error("Failed to process with facial recognition. Exiting.")
        logger.info(f"However, the raw capture file is available at: {output_file}")
        # Return the raw capture file path as output
        print(f"Output file: {output_file}")
        return 0
    
    logger.info("Parliament TV capture with facial recognition completed successfully.")
    logger.info(f"Output file: {processed_file}")
    
    # Print the result as JSON for easy parsing by other scripts
    result = {
        "success": True,
        "input_url": args.url,
        "stream_url": direct_stream_url,
        "output_file": processed_file,
        "time_marker": time_marker,
        "duration": args.duration
    }
    
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
