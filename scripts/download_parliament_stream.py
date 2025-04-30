#!/usr/bin/env python3
"""
Script to download Parliament TV streams using yt-dlp.
This approach is more reliable for handling various streaming formats.

Usage:
    python download_parliament_stream.py <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python download_parliament_stream.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120
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
    
    # Call our extraction script
    extract_script = Path(__file__).parent / "extract_parliament_stream_v4.py"
    
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

def check_yt_dlp_installed():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_yt_dlp():
    """Install yt-dlp using pip."""
    logger.info("Installing yt-dlp...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
        logger.info("yt-dlp installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install yt-dlp: {e}")
        return False

def download_stream(stream_url, output_file, duration=None):
    """
    Download a stream using yt-dlp.
    
    Args:
        stream_url (str): The URL of the stream to download
        output_file (str): The output file path
        duration (int, optional): The duration in seconds to download
        
    Returns:
        str: The path to the downloaded file
    """
    logger.info(f"Downloading stream: {stream_url}")
    
    # Ensure yt-dlp is installed
    if not check_yt_dlp_installed():
        if not install_yt_dlp():
            raise RuntimeError("yt-dlp is required but could not be installed.")
    
    # Create the output directory if it doesn't exist
    output_dir = Path(output_file).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare the yt-dlp command
    yt_dlp_cmd = ['yt-dlp']
    
    # Add duration limit if specified
    if duration:
        yt_dlp_cmd.extend(['--download-sections', f'*0-{duration}'])
    
    # Add output file and stream URL
    yt_dlp_cmd.extend(['-o', str(output_file), stream_url])
    
    logger.info(f"Running yt-dlp command: {' '.join(yt_dlp_cmd)}")
    
    try:
        # Run the yt-dlp command
        process = subprocess.Popen(
            yt_dlp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"yt-dlp error: {stderr}")
            raise RuntimeError(f"yt-dlp failed with return code {process.returncode}")
        
        logger.info(f"Download completed successfully. Output file: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Error during download: {e}")
        raise

def process_video_with_time_marker(input_file, time_marker_seconds, output_file=None, duration=None):
    """
    Process a video file starting at the specified time marker.
    
    Args:
        input_file (str): The path to the input video file
        time_marker_seconds (float): The time marker in seconds to start processing from
        output_file (str, optional): The output file path
        duration (int, optional): The duration in seconds to process
        
    Returns:
        str: The path to the processed video file
    """
    logger.info(f"Processing video: {input_file}")
    logger.info(f"Starting at time marker: {time_marker_seconds} seconds")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the provided output file or generate one
    if not output_file:
        output_dir = Path("data/media/parliament_captures")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare the ffmpeg command
    ffmpeg_cmd = ['ffmpeg', '-i', str(input_file), '-ss', str(time_marker_seconds)]
    
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
        
        # Wait for the process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr}")
            raise RuntimeError(f"ffmpeg failed with return code {process.returncode}")
        
        logger.info(f"Processing completed successfully. Output file: {output_file}")
        return str(output_file)
    
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Download and process Parliament TV streams.')
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
        
        # Create a timestamp for the temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a temporary directory for downloads
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Set the download duration (download a bit more than needed to account for the time marker)
        download_duration = args.duration
        if download_duration and time_marker_seconds:
            # We don't need to add the time marker to the download duration
            # as we'll start from the beginning and then cut at the time marker
            pass
        
        # Download the stream
        temp_file = temp_dir / f"temp_stream_{timestamp}.mp4"
        downloaded_file = download_stream(stream_url, temp_file, download_duration)
        
        # Process the downloaded file with the time marker
        if time_marker_seconds:
            output_file = process_video_with_time_marker(
                downloaded_file,
                time_marker_seconds,
                output_file=args.output,
                duration=args.duration
            )
            
            # Clean up the temporary file
            try:
                Path(downloaded_file).unlink()
                logger.info(f"Deleted temporary file: {downloaded_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
            
            logger.info(f"Final output file: {output_file}")
        else:
            # If no time marker, just use the downloaded file
            if args.output:
                # Copy the file to the output location
                import shutil
                shutil.copy2(downloaded_file, args.output)
                logger.info(f"Copied downloaded file to: {args.output}")
                
                # Clean up the temporary file
                try:
                    Path(downloaded_file).unlink()
                    logger.info(f"Deleted temporary file: {downloaded_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")
                
                logger.info(f"Final output file: {args.output}")
            else:
                # Just use the downloaded file as the output
                logger.info(f"Final output file: {downloaded_file}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
