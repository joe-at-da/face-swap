#!/usr/bin/env python3
"""
Direct Parliament TV Capture Script

This script captures video directly from a Parliament TV player URL.

Usage:
    python direct_parliament_capture.py <player_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python direct_parliament_capture.py "https://videoplayback.parliamentlive.tv/Player/Index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=2025-02-04T13%3A25%3A38%2B00%3A00&audioOnly=False&autoStart=True" --duration 60
"""

import os
import sys
import re
import json
import time
import argparse
import subprocess
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, unquote

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct_parliament_capture")

def extract_event_id_from_player_url(player_url):
    """Extract the event ID from the Parliament TV player URL."""
    match = re.search(r'/Index/([a-zA-Z0-9-]+)', player_url)
    if match:
        return match.group(1)
    return None

def extract_time_marker_from_player_url(player_url):
    """Extract the time marker from the Parliament TV player URL."""
    parsed_url = urlparse(player_url)
    query_params = parse_qs(parsed_url.query)
    
    if 'in' in query_params:
        time_str = unquote(query_params['in'][0])
        # The format is like: 2025-02-04T13:25:38+00:00
        try:
            # Extract just the time part
            time_part = time_str.split('T')[1].split('+')[0]
            parts = time_part.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing time marker: {e}")
    
    return None

def extract_stream_url_from_player_page(player_url):
    """Extract the stream URL from the Parliament TV player page."""
    logger.info(f"Extracting stream URL from player page: {player_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(player_url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # Create a temporary directory for output files
        os.makedirs("temp", exist_ok=True)
        
        # Save the HTML content to a file for debugging
        event_id = extract_event_id_from_player_url(player_url)
        output_file = f"temp/player_{event_id}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Saved player page to {output_file}")
        
        # Look for HLS streams
        hls_pattern = re.compile(r'(https://[^"\']+\.m3u8[^"\']*)')
        hls_matches = hls_pattern.findall(html_content)
        if hls_matches:
            stream_url = unquote(hls_matches[0])
            logger.info(f"Found HLS stream URL: {stream_url}")
            return stream_url
        
        # Look for MP4 streams
        mp4_pattern = re.compile(r'(https://[^"\']+\.mp4[^"\']*)')
        mp4_matches = mp4_pattern.findall(html_content)
        if mp4_matches:
            stream_url = unquote(mp4_matches[0])
            logger.info(f"Found MP4 stream URL: {stream_url}")
            return stream_url
        
        # If no direct stream URL found, try to construct one based on the event ID
        if event_id:
            direct_stream_url = f"https://p7of6fc-a2-westeurope-fay.cdn.redbee.live/parliamentlive/vod/entities/{event_id}/mat/era4H923HNQyTa_00823ARVcd-idx-2.m3u8"
            logger.info(f"Constructed direct stream URL: {direct_stream_url}")
            return direct_stream_url
        
        logger.error("Could not find any stream URL in the player page.")
        return None
    
    except requests.RequestException as e:
        logger.error(f"Error fetching player page: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def capture_stream(stream_url, output_file=None, duration=None, time_marker_seconds=None):
    """
    Capture a stream to a file.
    
    Args:
        stream_url (str): The URL of the stream to capture
        output_file (str, optional): The output file path
        duration (int, optional): The duration in seconds to capture
        time_marker_seconds (float, optional): The time marker in seconds to start capturing from
        
    Returns:
        str: The path to the captured file
    """
    logger.info(f"Capturing stream: {stream_url}")
    
    if time_marker_seconds:
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
    ffmpeg_cmd = ['ffmpeg']
    
    # Add input options
    ffmpeg_cmd.extend(['-i', stream_url])
    
    # Add time marker if specified
    if time_marker_seconds:
        ffmpeg_cmd.extend(['-ss', str(time_marker_seconds)])
    
    # Add duration if specified
    if duration:
        ffmpeg_cmd.extend(['-t', str(duration)])
    
    # Add output options for fast copying (no re-encoding)
    ffmpeg_cmd.extend([
        '-c', 'copy',  # Copy all streams without re-encoding (much faster)
        '-movflags', '+faststart',  # Optimize for web streaming
        '-y',  # Overwrite output file if it exists
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
        
        # Monitor the process
        logger.info(f"Started ffmpeg process with PID: {process.pid}")
        
        # If duration is specified, wait for the process to complete
        if duration:
            logger.info(f"Capturing for {duration} seconds...")
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ffmpeg error: {stderr}")
                raise RuntimeError(f"ffmpeg failed with return code {process.returncode}")
            
            logger.info(f"Capture completed successfully. Output file: {output_file}")
            return str(output_file)
        else:
            # If no duration specified, return the process for manual stopping
            logger.info("Capture started. Process will continue until manually stopped.")
            return str(output_file), process
    
    except Exception as e:
        logger.error(f"Error during capture: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Direct Parliament TV Capture')
    parser.add_argument('url', help='Parliament TV player URL')
    parser.add_argument('--duration', '-d', type=int, help='Duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    args = parser.parse_args()
    
    try:
        # Extract the event ID and time marker from the player URL
        event_id = extract_event_id_from_player_url(args.url)
        if not event_id:
            logger.error("Could not extract event ID from player URL.")
            return 1
        
        logger.info(f"Event ID: {event_id}")
        
        # Extract the time marker if present
        time_marker = extract_time_marker_from_player_url(args.url)
        time_marker_seconds = None
        if time_marker:
            time_marker_seconds = time_marker.total_seconds()
            logger.info(f"Time marker: {time_marker_seconds} seconds")
        
        # Extract the stream URL from the player page
        stream_url = extract_stream_url_from_player_page(args.url)
        if not stream_url:
            logger.error("Could not extract stream URL from player page.")
            return 1
        
        # Capture the stream
        output_file = capture_stream(
            stream_url,
            output_file=args.output,
            duration=args.duration,
            time_marker_seconds=time_marker_seconds
        )
        
        logger.info(f"Capture completed. Output file: {output_file}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
