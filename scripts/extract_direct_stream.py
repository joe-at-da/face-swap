#!/usr/bin/env python3
"""
Extract Direct Stream URL from Parliament TV

This script uses yt-dlp to extract the direct stream URL from a Parliament TV URL.
It handles both the web page URL and the player URL formats.

Usage:
    python extract_direct_stream.py <parliament_tv_url> [--output OUTPUT_FILE]

Example:
    python extract_direct_stream.py "https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38"
"""

import sys
import os
import json
import argparse
import subprocess
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract_direct_stream')

def check_command_exists(command):
    """Check if a command exists in the system PATH."""
    try:
        subprocess.run(["which", command], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def extract_time_marker(url):
    """Extract the time marker from the URL if present."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if 'in' in query_params:
        time_str = query_params['in'][0]
        # Parse the time string (format: HH:MM:SS)
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
        except ValueError:
            pass
    
    return None

def extract_event_id(url):
    """Extract the event ID from the Parliament TV URL."""
    import re
    match = re.search(r'/index/([a-zA-Z0-9-]+)', url)
    if match:
        return match.group(1)
    
    match = re.search(r'/Index/([a-zA-Z0-9-]+)', url)
    if match:
        return match.group(1)
    
    return None

def extract_direct_stream_url(url):
    """Extract the direct stream URL using yt-dlp."""
    logger.info(f"Extracting direct stream URL from: {url}")
    
    # Check if yt-dlp is installed
    if not check_command_exists("yt-dlp"):
        logger.error("yt-dlp not found. Please install it with: brew install yt-dlp")
        return None
    
    try:
        # Run yt-dlp to get the direct stream URL
        cmd = [
            "yt-dlp",
            "--no-check-certificate",
            "--dump-json",
            "--no-playlist",
            url
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        try:
            info = json.loads(result.stdout)
            
            # Get the direct stream URL
            direct_url = info.get('url')
            if not direct_url:
                formats = info.get('formats', [])
                if formats:
                    # Get the highest quality format
                    formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                    direct_url = formats[0].get('url')
            
            if direct_url:
                logger.info(f"Found direct stream URL: {direct_url}")
                return direct_url
            else:
                logger.error("No direct stream URL found in yt-dlp output")
                return None
        except json.JSONDecodeError:
            logger.error("Failed to parse yt-dlp output as JSON")
            logger.debug(f"yt-dlp output: {result.stdout}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running yt-dlp: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        
        # Try an alternative approach using ffmpeg probe
        try:
            logger.info("Trying alternative approach with ffprobe...")
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                url
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            try:
                info = json.loads(result.stdout)
                direct_url = info.get('format', {}).get('filename')
                
                if direct_url:
                    logger.info(f"Found direct stream URL using ffprobe: {direct_url}")
                    return direct_url
                else:
                    logger.error("No direct stream URL found in ffprobe output")
                    return None
            except json.JSONDecodeError:
                logger.error("Failed to parse ffprobe output as JSON")
                return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running ffprobe: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Extract Direct Stream URL from Parliament TV')
    parser.add_argument('url', help='Parliament TV URL')
    parser.add_argument('--output', '-o', help='Output file for the stream information')
    args = parser.parse_args()
    
    # Extract the direct stream URL
    direct_url = extract_direct_stream_url(args.url)
    
    if not direct_url:
        logger.error("Failed to extract direct stream URL")
        return 1
    
    # Extract the event ID and time marker
    event_id = extract_event_id(args.url)
    time_marker = extract_time_marker(args.url)
    
    # Create the result object
    result = {
        "direct_stream": direct_url,
        "event_id": event_id
    }
    
    if time_marker:
        result["time_marker"] = {
            "seconds": time_marker
        }
    
    # Print the result
    print(json.dumps(result, indent=2))
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Stream information saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
