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

def create_directories(temp_dir=None, media_dir=None):
    """Create necessary directories for storing temporary and output files.
    
    Args:
        temp_dir: Optional directory for temporary files. If None, uses TEMP_STORAGE_PATH env var or /tmp
        media_dir: Optional directory for media files. If None, uses MEDIA_STORAGE_PATH env var or default
        
    Returns:
        Tuple of (temp_dir, media_dir) with absolute paths
    """
    # Use provided paths, environment variables, or default paths
    if temp_dir is None or temp_dir == "":
        temp_dir = os.environ.get('TEMP_STORAGE_PATH')
        if not temp_dir or temp_dir == "":
            temp_dir = '/tmp'
        print(f"DEBUG - Using temp_dir from env: {temp_dir}")
    
    if media_dir is None or media_dir == "":
        media_base = os.environ.get('MEDIA_STORAGE_PATH')
        if media_base and media_base != "":
            media_dir = os.path.join(media_base, 'parliament_captures')
        else:
            media_dir = '/app/data/media'
            logger.warning(f"MEDIA_STORAGE_PATH not set, using default: {media_dir}")
        print(f"DEBUG - Using media_dir: {media_dir}")
    else:
        print(f"DEBUG - Using provided media_dir: {media_dir}")

    # Ensure paths are valid strings
    if temp_dir is None or temp_dir == "":
        temp_dir = '/tmp'
    if media_dir is None or media_dir == "":
        media_dir = '/app/data/media'
    
    # Ensure paths are absolute
    temp_dir = os.path.abspath(str(temp_dir))
    media_dir = os.path.abspath(str(media_dir))
    
    print(f"DEBUG - After conversion, temp_dir: {temp_dir}")
    print(f"DEBUG - After conversion, media_dir: {media_dir}")
    
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

def extract_direct_stream_url(url):
    """Extract the direct stream URL from a Parliament TV web page.
    
    Args:
        url: URL of the Parliament TV event
        
    Returns:
        Direct stream URL if successful, None otherwise
    """
    logger.info(f"Extracting direct stream URL from: {url}")
    
    # Check if the URL is already a direct stream URL (ends with .m3u8)
    if url.endswith('.m3u8'):
        logger.info("URL appears to be a direct stream URL already")
        return url
    
    # Use the extract_stream_url function to get the stream info
    stream_info = extract_stream_url(url)
    
    if stream_info and 'direct_stream' in stream_info:
        return stream_info['direct_stream']
    
    logger.error("Failed to extract direct stream URL")
    return None

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

def download_stream(stream_url, output_dir, capture_id, duration=1800):
    """
    Download a stream using ffmpeg.
    
    Args:
        stream_url: URL of the stream to download
        output_dir: Directory to save the output file
        capture_id: ID of the capture
        duration: Maximum duration to capture in seconds (default: 30 minutes)
        
    Returns:
        Path to the output file if successful, None otherwise
    """
    # Debug output
    print(f"DEBUG - download_stream called with:")
    print(f"DEBUG - stream_url: {stream_url}, type: {type(stream_url)}")
    print(f"DEBUG - output_dir: {output_dir}, type: {type(output_dir)}")
    print(f"DEBUG - capture_id: {capture_id}, type: {type(capture_id)}")
    print(f"DEBUG - duration: {duration}, type: {type(duration)}")
    
    # Check if the stream URL is valid
    if not stream_url or not isinstance(stream_url, str) or not stream_url.strip():
        logger.error("Stream URL is None, empty, or not a string")
        return None
    
    # Ensure output_dir is valid
    if output_dir is None or output_dir == "":
        logger.error("Output directory is None or empty")
        print(f"DEBUG - Output directory is None or empty, using /tmp")
        output_dir = "/tmp"
        
    # Convert output_dir to string if it's a Path object
    output_dir = str(output_dir)
        
    # Ensure output directory exists
    try:
        if not os.path.exists(output_dir):
            logger.info(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
        output_dir = "/tmp"
        logger.warning(f"Using fallback output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"parliament_capture_{capture_id}_{timestamp}.mp4")
    
    logger.info(f"Downloading stream: {stream_url}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Duration: {duration} seconds")
    
    try:
        # Build ffmpeg command
        cmd = ["ffmpeg", "-y", "-i", stream_url, "-c:v", "copy"]
        
        # Check if the stream has audio
        audio_check_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", stream_url]
        try:
            audio_check_result = subprocess.run(audio_check_cmd, capture_output=True, text=True, timeout=10)
            has_audio = "audio" in audio_check_result.stdout
            logger.info(f"Stream has audio: {has_audio}")
        except Exception as e:
            logger.warning(f"Error checking for audio in stream: {str(e)}")
            # Assume it has audio by default
            has_audio = True
        
        if has_audio:
            cmd.extend(["-c:a", "aac", "-ac", "2", "-ar", "44100", "-strict", "experimental"])
        else:
            # For streams without audio, we'll add silent audio after downloading the video
            logger.warning("Stream does not have audio, will add silent audio after download")
            # Just copy the video for now
            # We'll add silent audio in a separate step after downloading
        
        # Add duration limit if specified
        if duration and duration > 0:
            cmd.extend(["-t", str(duration)])
        
        # Add output file
        cmd.append(output_file)
        
        # Run ffmpeg command
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Verify the output file exists and has content
        if os.path.exists(output_file):
            if os.path.getsize(output_file) > 0:
                # Verify if the output file has audio
                try:
                    audio_check_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", output_file]
                    audio_check_result = subprocess.run(audio_check_cmd, capture_output=True, text=True, timeout=10)
                    output_has_audio = "audio" in audio_check_result.stdout
                    logger.info(f"Output file has audio: {output_has_audio}")
                    
                    if not output_has_audio:
                        logger.warning("Output file does not have audio, adding silent audio track")
                        # Add silent audio track in a separate command
                        silent_audio_cmd = [
                            "ffmpeg", "-y", "-i", output_file, "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                            "-c:v", "copy", "-c:a", "aac", "-shortest", output_file + ".with_audio.mp4"
                        ]
                        print(f"DEBUG - Running silent audio command: {' '.join(silent_audio_cmd)}")
                        subprocess.run(silent_audio_cmd, capture_output=True, text=True, check=True)
                        # Replace original file with the one with audio
                        os.replace(output_file + ".with_audio.mp4", output_file)
                        logger.info("Added silent audio track to the output file")
                    else:
                        logger.info("Output file already has audio")
                except Exception as e:
                    logger.warning(f"Error verifying audio in output file: {str(e)}")
                
                logger.info(f"Download completed successfully: {output_file}")
                return output_file
            else:
                logger.error(f"Output file is empty: {output_file}")
                return None
        else:
            logger.error(f"Output file does not exist: {output_file}")
            print(f"DEBUG - Current directory contents: {os.listdir(os.path.dirname(output_file))}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg command failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        print(f"DEBUG - ffmpeg error: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        print(f"DEBUG - Unexpected error: {str(e)}")
        import traceback
        print(f"DEBUG - Traceback: {traceback.format_exc()}")
        return None

def process_with_facial_recognition(video_file, output_file=None, duration=None):
    """Process the video with facial recognition."""
    logger.info(f"Processing video with facial recognition: {video_file}")
    
    if not video_file or not os.path.exists(video_file):
        logger.error(f"Video file does not exist: {video_file}")
        return None
    
    if not output_file:
        # Create output file path based on input file
        output_dir = os.path.dirname(video_file)
        filename = os.path.basename(video_file)
        name, ext = os.path.splitext(filename)
        output_file = os.path.join(output_dir, f"{name}_processed{ext}")
    
    # Run facial recognition script
    try:
        cmd = [
            sys.executable,
            "-m", "backend.scripts.facial_recognition",
            "--input", video_file,
            "--output", output_file
        ]
        
        if duration:
            cmd.extend(["--duration", str(duration)])
        
        logger.info(f"Running facial recognition command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Extract the output file path from the result
        processed_file = None
        for line in result.stdout.split('\n'):
            if line.startswith("Output file:"):
                processed_file = line.split("Output file:")[1].strip()
                break
        
        logger.info(f"Facial recognition processing completed. Output file: {processed_file}")
        return processed_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing video with facial recognition: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in facial recognition: {str(e)}")
        return None

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Download Parliament TV stream")
    parser.add_argument("url", help="URL of the Parliament TV event or direct stream")
    parser.add_argument("--capture-id", type=int, help="ID of the capture", required=True)
    parser.add_argument("--duration", type=int, help="Maximum duration to capture in seconds", default=1800)
    parser.add_argument("--temp-dir", help="Directory for temporary files")
    parser.add_argument("--media-dir", help="Directory for media files")
    parser.add_argument("--facial-recognition", action="store_true", help="Enable facial recognition")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    # Print debug information about arguments
    print(f"DEBUG - Command line arguments:")
    print(f"DEBUG - url: {args.url}")
    print(f"DEBUG - capture_id: {args.capture_id}")
    print(f"DEBUG - duration: {args.duration}")
    print(f"DEBUG - temp_dir: {args.temp_dir}")
    print(f"DEBUG - media_dir: {args.media_dir}")
    print(f"DEBUG - facial_recognition: {args.facial_recognition}")
    print(f"DEBUG - output: {args.output}")
    
    # Validate URL
    if not args.url or not isinstance(args.url, str) or not args.url.strip():
        logger.error("URL is None, empty, or not a string")
        return 1
    
    # Create directories - ensure they're strings if provided
    temp_dir_arg = str(args.temp_dir) if args.temp_dir else None
    media_dir_arg = str(args.media_dir) if args.media_dir else None
    temp_dir, media_dir = create_directories(temp_dir_arg, media_dir_arg)
    
    # Ensure temp_dir and media_dir are not None
    if temp_dir is None:
        temp_dir = "/tmp"
        logger.warning(f"Using fallback temp directory: {temp_dir}")
    if media_dir is None:
        media_dir = "/tmp"
        logger.warning(f"Using fallback media directory: {media_dir}")
    
    # Check for required tools
    if not check_command_exists("ffmpeg"):
        logger.error("ffmpeg is not installed or not in PATH")
        return 1
        
    if not check_command_exists("ffprobe"):
        logger.warning("ffprobe is not installed or not in PATH, some features may not work")
    
    # Extract direct stream URL if needed
    if not args.url.endswith('.m3u8'):
        print(f"DEBUG - Extracting direct stream URL from: {args.url}")
        direct_stream = extract_direct_stream_url(args.url)
        if not direct_stream:
            logger.error("Failed to extract direct stream URL")
            return 1
        print(f"DEBUG - Extracted direct stream URL: {direct_stream}")
    else:
        direct_stream = args.url
        print(f"DEBUG - Using provided direct stream URL: {direct_stream}")
    
    # Download the stream
    print(f"DEBUG - Downloading stream to directory: {media_dir}")
    output_file = download_stream(direct_stream, media_dir, args.capture_id, args.duration)
        
    if output_file is None:
        logger.error("Failed to download stream")
        return 1
        
    # Validate the output file path
    if not output_file.endswith('.mp4'):
        logger.warning(f"Output file does not have .mp4 extension: {output_file}")
        output_file = f"{output_file}.mp4"
        logger.info(f"Added .mp4 extension: {output_file}")
        
    # Make sure the output directory exists
    output_dir = os.path.dirname(output_file)
    logger.info(f"Creating output directory if needed: {output_dir}")
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory {output_dir}: {str(e)}")
        # Fallback to temp directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join("/tmp", f"parliament_capture_{args.capture_id}_{timestamp}.mp4")
        logger.warning(f"Using fallback output file path: {output_file}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"DEBUG - Stream downloaded successfully to: {output_file}")
    
    # Process with facial recognition if enabled
    if args.facial_recognition:
        logger.info("Processing with facial recognition...")
        success = process_with_facial_recognition(output_file)
        if not success:
            logger.error("Failed to process with facial recognition")
            return 1
    
    # Print the output file path for easier parsing by other scripts
    print(f"Output file: {output_file}")
    logger.info("Parliament TV capture completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
