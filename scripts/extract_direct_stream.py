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
    
    # Ensure URL has audio parameter set to false (not audio-only)
    if "audioOnly=" in url and "audioOnly=True" in url:
        url = url.replace("audioOnly=True", "audioOnly=False")
    elif "audioOnly=" not in url:
        if "?" in url:
            url += "&audioOnly=False"
        else:
            url += "?audioOnly=False"
    
    logger.info(f"Using URL with audio parameter: {url}")
    
    # Check if yt-dlp is installed
    if not check_command_exists("yt-dlp"):
        logger.error("yt-dlp not found. Please install it with: brew install yt-dlp")
        return None
    
    try:
        # First, list all available formats to understand what's available
        format_cmd = [
            "yt-dlp",
            "--no-check-certificate",
            "--list-formats",
            url
        ]
        
        logger.info(f"Listing available formats: {' '.join(format_cmd)}")
        format_result = subprocess.run(format_cmd, capture_output=True, text=True)
        logger.info(f"Available formats:\n{format_result.stdout}")
        
        # Run yt-dlp to get the direct stream URL with best format that includes audio
        cmd = [
            "yt-dlp",
            "--no-check-certificate",
            "--dump-json",
            "--no-playlist",
            # Explicitly request format with both video and audio
            "--format", "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio/best",
            url
        ]
        
        # Add more detailed logging
        logger.info(f"Extracting from URL: {url}")
        logger.info(f"Using command: {' '.join(cmd)}")
        
        logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        try:
            info = json.loads(result.stdout)
            
            # Get the direct stream URL
            direct_url = info.get('url')
            has_audio = False
            
            # Check if the format has audio
            if 'requested_formats' in info:
                for fmt in info['requested_formats']:
                    if fmt.get('acodec', 'none') != 'none':
                        has_audio = True
                        break
                
                # If we have multiple formats (separate audio/video), use the direct URL from info
                if len(info['requested_formats']) > 1:
                    logger.info("Found separate audio and video streams, using direct URL from info")
                    direct_url = info.get('url')
            elif info.get('acodec', 'none') != 'none':
                has_audio = True
            
            if not direct_url or not has_audio:
                formats = info.get('formats', [])
                if formats:
                    # Find a format with both video and audio
                    for fmt in formats:
                        if fmt.get('acodec', 'none') != 'none' and fmt.get('vcodec', 'none') != 'none':
                            direct_url = fmt.get('url')
                            has_audio = True
                            logger.info(f"Selected format with audio: {fmt.get('format_id')} - {fmt.get('format')}")
                            break
                    
                    # If no combined format found, get highest quality video
                    if not direct_url:
                        formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                        direct_url = formats[0].get('url')
                        logger.warning("Could not find format with audio, using highest quality video")
            
            if direct_url:
                logger.info(f"Found direct stream URL: {direct_url}")
                logger.info(f"Stream has audio: {has_audio}")
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
        
        # Try an alternative approach using youtube-dl
        try:
            logger.info("Trying alternative approach with youtube-dl...")
            cmd = [
                "youtube-dl",
                "--no-check-certificate",
                "--dump-json",
                "--no-playlist",
                "--format", "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio/best",
                url
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            try:
                info = json.loads(result.stdout)
                direct_url = info.get('url')
                
                if direct_url:
                    logger.info(f"Found direct stream URL using youtube-dl: {direct_url}")
                    return direct_url
                else:
                    logger.error("No direct stream URL found in youtube-dl output")
            except json.JSONDecodeError:
                logger.error("Failed to parse youtube-dl output as JSON")
        except subprocess.CalledProcessError:
            pass
        
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
