#!/usr/bin/env python3
"""
Extract Audio from Parliament TV URL

This script extracts just the audio from a Parliament TV URL and saves it as an MP3 file.
It uses yt-dlp to extract the audio stream.

Usage:
    python extract_audio.py <parliament_tv_url> [--output OUTPUT_FILE]

Example:
    python extract_audio.py "https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e"
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract-audio')

def check_command_exists(command):
    """Check if a command exists in the system PATH."""
    try:
        subprocess.run(["which", command], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def extract_audio(url, output_file=None):
    """Extract audio from a Parliament TV URL and save it as an MP3 file."""
    logger.info(f"Extracting audio from: {url}")
    
    # Validate that the URL is a Parliament TV URL
    if not url or not isinstance(url, str):
        logger.error(f"Invalid URL provided: {url}")
        return None
        
    # Strict validation for Parliament TV URLs
    valid_domains = ["parliamentlive.tv", "parliament.tv"]
    is_valid = False
    
    for domain in valid_domains:
        if domain in url:
            is_valid = True
            break
    
    if not is_valid:
        logger.error(f"URL does not appear to be a valid Parliament TV URL: {url}")
        logger.error("Only URLs from parliamentlive.tv or parliament.tv are supported")
        return None
    
    # Check if yt-dlp is installed
    if not check_command_exists("yt-dlp"):
        logger.error("yt-dlp not found. Please install it with: pip install yt-dlp")
        return None
    
    # Generate output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"parliament_audio_{timestamp}.mp3"
    
    # Make sure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Run yt-dlp to extract and download just the audio
        cmd = [
            "yt-dlp",
            "--no-check-certificate",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            "-o", output_file,
            url
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            logger.info(f"Audio extraction successful: {output_file}")
            return output_file
        else:
            logger.error(f"yt-dlp failed with return code {result.returncode}")
            logger.error(f"yt-dlp output: {result.stdout}")
            logger.error(f"yt-dlp error: {result.stderr}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running yt-dlp: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract Audio from Parliament TV URL')
    parser.add_argument('url', help='Parliament TV URL')
    parser.add_argument('--output', '-o', help='Output file for the audio (default: parliament_audio_TIMESTAMP.mp3)')
    args = parser.parse_args()
    
    # Extract the audio
    output_file = extract_audio(args.url, args.output)
    
    if not output_file:
        logger.error("Failed to extract audio")
        return 1
    
    logger.info(f"Audio saved to: {output_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
