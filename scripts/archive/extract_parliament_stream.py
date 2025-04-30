#!/usr/bin/env python3
"""
Script to extract video stream URLs from Parliament TV event pages.
Usage: python extract_parliament_stream.py <parliament_tv_event_url>
Example: python extract_parliament_stream.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38
"""

import sys
import re
import json
import subprocess
import argparse
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

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
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return timedelta(minutes=minutes, seconds=seconds)
        except ValueError:
            pass
    
    return None

def seconds_to_hms(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def extract_event_id(url):
    """Extract the event ID from the Parliament TV URL."""
    match = re.search(r'/index/([a-zA-Z0-9-]+)', url)
    if match:
        return match.group(1)
    return None

def fetch_page_content(url):
    """Fetch the content of the Parliament TV event page."""
    try:
        result = subprocess.run(
            ['curl', '-s', url],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error fetching page: {e}")
        return None

def extract_video_player_url(html_content, event_id):
    """Extract the video player URL from the HTML content."""
    # Look for the video player URL pattern
    player_url_pattern = re.compile(r'(https://videoplayback\.parliamentlive\.tv/Player/[^"\']+)')
    match = player_url_pattern.search(html_content)
    
    if match:
        return match.group(1)
    
    # Alternative: try to find the player URL based on the event ID
    player_url = f"https://videoplayback.parliamentlive.tv/Player/Index/{event_id}?audioOnly=False&autoStart=True"
    return player_url

def extract_stream_urls(player_url):
    """Extract the actual stream URLs from the player page."""
    try:
        # Fetch the player page
        result = subprocess.run(
            ['curl', '-s', player_url],
            capture_output=True,
            text=True,
            check=True
        )
        player_html = result.stdout
        
        # Look for different types of stream URLs
        hls_pattern = re.compile(r'(https://[^"\']+\.m3u8[^"\']*)')
        mp4_pattern = re.compile(r'(https://[^"\']+\.mp4[^"\']*)')
        
        # Try to find HLS streams first (preferred)
        hls_matches = hls_pattern.findall(player_html)
        if hls_matches:
            return {'hls': hls_matches}
        
        # If no HLS streams, look for MP4 streams
        mp4_matches = mp4_pattern.findall(player_html)
        if mp4_matches:
            return {'mp4': mp4_matches}
        
        # If still no streams found, check network requests
        print("No direct stream URLs found in player page. Trying to analyze network requests...")
        
        # Use curl with verbose output to see redirects and network activity
        result = subprocess.run(
            ['curl', '-v', '-s', player_url],
            capture_output=True,
            text=True
        )
        
        # Look for any URLs in the verbose output
        all_urls = re.findall(r'(https://[^"\'>\s]+)', result.stderr)
        media_urls = [url for url in all_urls if '.m3u8' in url or '.mp4' in url]
        
        if media_urls:
            return {'detected': media_urls}
        
        # If still nothing, check for the Redbee player configuration
        redbee_config = re.search(r'var\s+config\s*=\s*({[^;]+});', player_html)
        if redbee_config:
            try:
                config_str = redbee_config.group(1)
                # Clean up the string to make it valid JSON
                config_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', config_str)
                config = json.loads(config_str)
                return {'config': config}
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing player configuration: {e}")
        
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error fetching player page: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract video stream URLs from Parliament TV event pages.')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--output', '-o', help='Output file for the stream information')
    args = parser.parse_args()
    
    url = args.url
    print(f"Analyzing Parliament TV URL: {url}")
    
    # Extract the time marker if present
    time_marker = extract_time_marker(url)
    if time_marker:
        total_seconds = time_marker.total_seconds()
        print(f"Time marker found: {seconds_to_hms(total_seconds)} ({total_seconds} seconds)")
    else:
        print("No time marker found. Will start from the beginning.")
    
    # Extract the event ID
    event_id = extract_event_id(url)
    if not event_id:
        print("Could not extract event ID from URL.")
        return 1
    
    print(f"Event ID: {event_id}")
    
    # Fetch the page content
    html_content = fetch_page_content(url)
    if not html_content:
        print("Failed to fetch page content.")
        return 1
    
    # Extract the video player URL
    player_url = extract_video_player_url(html_content, event_id)
    if not player_url:
        print("Could not find video player URL.")
        return 1
    
    print(f"Video player URL: {player_url}")
    
    # Extract the stream URLs
    stream_info = extract_stream_urls(player_url)
    if not stream_info:
        print("Could not find any stream URLs.")
        return 1
    
    # Add the time marker to the stream info
    if time_marker:
        stream_info['time_marker'] = {
            'hms': seconds_to_hms(time_marker.total_seconds()),
            'seconds': time_marker.total_seconds()
        }
    
    # Add the event ID to the stream info
    stream_info['event_id'] = event_id
    
    # Print the stream information
    print("\nStream Information:")
    print(json.dumps(stream_info, indent=2))
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(stream_info, f, indent=2)
        print(f"\nStream information saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
