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
    # Use environment variables if available, otherwise use default paths
    temp_dir = os.environ.get('TEMP_STORAGE_PATH')
    media_base = os.environ.get('MEDIA_STORAGE_PATH')
    
    # Set default paths if environment variables are not set or empty
    if not temp_dir:
        temp_dir = '/app/data/temp'
        logger.warning(f"TEMP_STORAGE_PATH not set, using default: {temp_dir}")
    
    if not media_base:
        media_base = '/app/data/media'
        logger.warning(f"MEDIA_STORAGE_PATH not set, using default: {media_base}")
    
    # Create media directory for parliament captures
    media_dir = os.path.join(media_base, 'parliament_captures')
    
    # Ensure paths are absolute
    temp_dir = os.path.abspath(temp_dir)
    media_dir = os.path.abspath(media_dir)
    
    logger.info(f"Using temp directory: {temp_dir}")
    logger.info(f"Using media directory: {media_dir}")
    
    # Create directories if they don't exist
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created/verified temp directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to create temp directory {temp_dir}: {str(e)}")
        # Fallback to a directory we know should work
        temp_dir = '/tmp'
        os.makedirs(temp_dir, exist_ok=True)
        logger.warning(f"Using fallback temp directory: {temp_dir}")
    
    try:
        os.makedirs(media_dir, exist_ok=True)
        logger.info(f"Created/verified media directory: {media_dir}")
    except Exception as e:
        logger.error(f"Failed to create media directory {media_dir}: {str(e)}")
        # Fallback to temp directory if media directory creation fails
        media_dir = temp_dir
        logger.warning(f"Using fallback media directory: {media_dir}")
    
    logger.info(f"Final directories - temp: {temp_dir}, media: {media_dir}")
    
    return temp_dir, media_dir

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
    """Download a stream using ffmpeg."""
    logger.info(f"Downloading stream: {stream_url}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Duration: {duration} seconds")
    
    # Validate inputs
    if not stream_url:
        logger.error("Stream URL is empty")
        return False
        
    if not output_file:
        logger.error("Output file path is empty")
        return False
    
    # Convert to string if it's a Path object
    output_file = str(output_file)
    
    # Ensure output directory exists
    try:
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Ensured output directory exists: {output_dir}")
    except Exception as e:
        logger.error(f"Failed to create output directory: {str(e)}")
        return False
    
    # Check if the stream has audio
    has_audio = False
    try:
        logger.info("Checking if stream has audio...")
        cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", stream_url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output to check for audio streams
        streams_data = json.loads(result.stdout)
        streams = streams_data.get('streams', [])
        
        for stream in streams:
            if stream.get('codec_type') == 'audio':
                has_audio = True
                break
                
        logger.info(f"Stream has audio: {has_audio}")
    except Exception as e:
        logger.warning(f"Error checking if stream has audio: {str(e)}")
        # Assume it might have audio
        has_audio = True
        logger.info("Assuming stream has audio due to error checking")
    
    # Build the ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", stream_url, "-c:v", "copy"]
    
    # Always include audio options to ensure we capture audio if it's available
    cmd.extend(["-c:a", "aac", "-ac", "2", "-ar", "44100", "-strict", "experimental"])
    
    # Add duration if specified
    if duration:
        cmd.extend(["-t", str(duration)])
    
    # Add output file
    cmd.append(output_file)
    
    logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Stream download completed successfully")
        
        # Verify the output file exists and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Output file created successfully: {output_file} ({os.path.getsize(output_file)} bytes)")
            
            # Verify the output has audio
            try:
                verify_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", output_file]
                verify_result = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
                
                verify_data = json.loads(verify_result.stdout)
                output_has_audio = False
                for stream in verify_data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        output_has_audio = True
                        break
                        
                if not output_has_audio and has_audio:
                    logger.warning("Stream had audio but output file does not have audio!")
                    logger.warning("Attempting to add silent audio track...")
                    
                    # Create silent audio and merge with video
                    silent_cmd = [
                        "ffmpeg", "-i", output_file, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
                        "-c:v", "copy", "-c:a", "aac", "-shortest", "-y", f"{output_file}.with_audio.mp4"
                    ]
                    subprocess.run(silent_cmd, check=True, capture_output=True, text=True)
                    # Replace original file
                    os.rename(f"{output_file}.with_audio.mp4", output_file)
                    logger.info("Added silent audio track to the output file")
                else:
                    logger.info(f"Output file has audio: {output_has_audio}")
            except Exception as e:
                logger.warning(f"Error verifying audio in output file: {str(e)}")
            
            # Final verification that the file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Download completed successfully. File saved at: {output_file}")
                # Print the output file path for easier parsing by other scripts
                print(f"Output file: {output_file}")
                return True
            else:
                logger.error(f"Final verification failed: File does not exist or is empty at {output_file}")
                return False
        else:
            logger.error(f"Output file does not exist or is empty: {output_file}")
            return False
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
    parser.add_argument('--duration', '-d', type=int, default=1800, help='Maximum duration to capture in seconds (default: 1800)')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--capture-id', help='Capture ID for file naming')
    
    try:
        args = parser.parse_args()
        
        # Validate URL
        if not args.url:
            logger.error("URL cannot be empty")
            print(json.dumps({"error": "URL cannot be empty", "success": False}))
            return 1
            
        # Validate duration
        if args.duration is not None and args.duration <= 0:
            logger.warning(f"Invalid duration: {args.duration}, using default of 1800 seconds")
            args.duration = 1800
            
        # Validate capture ID
        if args.capture_id and not str(args.capture_id).isdigit():
            logger.warning(f"Capture ID should be numeric, got: {args.capture_id}")
            # We'll still use it, but log a warning
            
        logger.info(f"Starting capture with URL: {args.url}")
        logger.info(f"Duration: {args.duration} seconds")
        logger.info(f"Capture ID: {args.capture_id if args.capture_id else 'None'}")
        logger.info(f"Output path: {args.output if args.output else 'Not specified, will use default'}")        
    except Exception as e:
        logger.error(f"Error parsing command-line arguments: {str(e)}")
        print(json.dumps({"error": f"Error parsing command-line arguments: {str(e)}", "success": False}))
        return 1
    
    # Check for required tools
    if not check_command_exists("ffmpeg"):
        logger.error("ffmpeg not found in PATH. Please install it with: brew install ffmpeg")
        return 1
    
    # Create necessary directories
    temp_dir, media_dir = create_directories()
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    capture_id = args.capture_id if args.capture_id else ''
    
    # Check if the URL is already a direct stream URL
    direct_stream_url = None
    stream_info = {}
    time_marker = None
    
    if args.url.endswith('.m3u8'):
        logger.info("Input appears to be a direct stream URL")
        direct_stream_url = args.url
    else:
        # Extract the direct stream URL
        stream_info_file = os.path.join(temp_dir, f"stream_info_{timestamp}.json")
        stream_info = extract_stream_url(args.url, stream_info_file)
        
        if not stream_info:
            logger.error("Failed to extract stream URL. Exiting.")
            return 1
        
        # Get the direct stream URL
        direct_stream_url = stream_info.get('direct_stream')
        if not direct_stream_url:
            logger.error("No direct stream URL found in stream info.")
            return 1
        
        # Get time marker if available
        if 'time_marker' in stream_info and 'seconds' in stream_info['time_marker']:
            time_marker = stream_info['time_marker']['seconds']
            logger.info(f"Time marker: {time_marker} seconds")
    
    logger.info(f"Direct stream URL: {direct_stream_url}")
    
    # Download the stream with capture ID in the filename
    try:
        if args.output:
            # Use the provided output path
            output_file = args.output
            logger.info(f"Using provided output file path: {output_file}")
        else:
            # Generate a filename with the capture ID if available
            safe_capture_id = str(args.capture_id) if args.capture_id else 'unknown'
            output_file = os.path.join(temp_dir, f"parliament_stream_{timestamp}_{safe_capture_id}.mp4")
            logger.info(f"Generated output file path: {output_file}")
        
        # Ensure the output file path is absolute
        output_file = os.path.abspath(output_file)
        logger.info(f"Absolute output path: {output_file}")
        
        # Validate the output file path
        if not output_file.endswith('.mp4'):
            logger.warning(f"Output file does not have .mp4 extension: {output_file}")
            output_file = f"{output_file}.mp4"
            logger.info(f"Added .mp4 extension: {output_file}")
        
        # Make sure the output directory exists
        output_dir = os.path.dirname(output_file)
        logger.info(f"Creating output directory if needed: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Double-check that the directory was created
        if not os.path.exists(output_dir):
            logger.error(f"Failed to create output directory: {output_dir}")
            # Fallback to temp directory
            output_file = os.path.join(temp_dir, f"parliament_stream_{timestamp}_{safe_capture_id}.mp4")
            logger.warning(f"Using fallback output file path: {output_file}")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
    except Exception as e:
        logger.error(f"Error setting up output file path: {str(e)}")
        # Fallback to a safe path
        safe_capture_id = str(args.capture_id) if args.capture_id else 'unknown'
        output_file = os.path.join(temp_dir, f"parliament_stream_{timestamp}_{safe_capture_id}.mp4")
        logger.warning(f"Using fallback output file path due to error: {output_file}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if not download_stream(direct_stream_url, output_file, args.duration):
        logger.error("Failed to download stream. Exiting.")
        return 1
    
    # Process the video with facial recognition - ALWAYS include capture ID in the filename
    try:
        if args.output:
            # Use the provided output path for the final file as well
            final_output_file = args.output
            logger.info(f"Using provided output file path for final output: {final_output_file}")
        else:
            # Generate a filename with the capture ID if available
            safe_capture_id = str(args.capture_id) if args.capture_id else 'unknown'
            final_output_file = os.path.join(media_dir, f"parliament_capture_{timestamp}_{safe_capture_id}.mp4")
            logger.info(f"Generated final output file path: {final_output_file}")
        
        # Ensure the final output file path is absolute
        final_output_file = os.path.abspath(final_output_file)
        logger.info(f"Absolute final output path: {final_output_file}")
        
        # Validate the output file path
        if not final_output_file.endswith('.mp4'):
            logger.warning(f"Final output file does not have .mp4 extension: {final_output_file}")
            final_output_file = f"{final_output_file}.mp4"
            logger.info(f"Added .mp4 extension to final output: {final_output_file}")
        
        # Make sure the output directory exists
        final_output_dir = os.path.dirname(final_output_file)
        logger.info(f"Creating final output directory if needed: {final_output_dir}")
        os.makedirs(final_output_dir, exist_ok=True)
        
        # Double-check that the directory was created
        if not os.path.exists(final_output_dir):
            logger.error(f"Failed to create final output directory: {final_output_dir}")
            # Fallback to temp directory
            final_output_file = os.path.join(temp_dir, f"parliament_capture_{timestamp}_{safe_capture_id}.mp4")
            logger.warning(f"Using fallback final output file path: {final_output_file}")
            os.makedirs(os.path.dirname(final_output_file), exist_ok=True)
    except Exception as e:
        logger.error(f"Error setting up final output file path: {str(e)}")
        # Fallback to a safe path
        safe_capture_id = str(args.capture_id) if args.capture_id else 'unknown'
        final_output_file = os.path.join(temp_dir, f"parliament_capture_{timestamp}_{safe_capture_id}.mp4")
        logger.warning(f"Using fallback final output file path due to error: {final_output_file}")
        os.makedirs(os.path.dirname(final_output_file), exist_ok=True)
    
    # Don't overwrite the input file - use a different output path
    processed_file = process_with_facial_recognition(output_file, final_output_file, args.duration)
    
    if not processed_file:
        logger.error("Failed to process with facial recognition. Exiting.")
        logger.info(f"However, the raw capture file is available at: {output_file}")
        
        # Check if the raw capture file exists and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            # Return the raw capture file path as output
            print(f"Output file: {output_file}")
            # Also print in JSON format for easier parsing
            print(json.dumps({"output_file": output_file, "success": True}))
            return 0
        else:
            logger.error(f"Raw capture file does not exist or is empty: {output_file}")
            print(json.dumps({"error": "Capture failed", "success": False}))
            return 1
    
    logger.info("Parliament TV capture with facial recognition completed successfully.")
    logger.info(f"Output file: {processed_file}")
    
    # Print the result as JSON for easy parsing by other scripts
    result = {
        "success": True,
        "input_url": args.url,
        "stream_url": direct_stream_url,
        "output_file": processed_file,
        "time_marker": time_marker,
        "duration": args.duration,
        "capture_id": args.capture_id  # Include the capture ID in the result
    }
    
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
