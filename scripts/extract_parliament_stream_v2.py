#!/usr/bin/env python3
"""
Enhanced script to extract video stream URLs from Parliament TV event pages.
This version uses a more comprehensive approach to find the stream URLs.
Usage: python extract_parliament_stream_v2.py <parliament_tv_event_url>
Example: python extract_parliament_stream_v2.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38
"""

import sys
import re
import json
import subprocess
import argparse
import os
from urllib.parse import urlparse, parse_qs, unquote
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
        player_url = match.group(1)
        # Clean up any HTML entities
        player_url = player_url.replace('&amp;', '&')
        return player_url
    
    # Alternative: try to find the player URL based on the event ID
    player_url = f"https://videoplayback.parliamentlive.tv/Player/Index/{event_id}?audioOnly=False&autoStart=True"
    return player_url

def save_html_to_file(html_content, filename):
    """Save HTML content to a file for debugging."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Saved HTML content to {filename}")

def extract_stream_urls_using_curl_output(event_id, time_marker=None):
    """
    Use curl to fetch the player page and save the output to analyze.
    This is a more direct approach that might work better for some URLs.
    """
    # Create a temporary directory for output files
    os.makedirs("temp", exist_ok=True)
    
    # Construct the player URL
    base_player_url = f"https://videoplayback.parliamentlive.tv/Player/Index/{event_id}"
    
    # Add time marker if present
    player_url = base_player_url
    if time_marker:
        time_str = seconds_to_hms(time_marker.total_seconds())
        player_url = f"{base_player_url}?in={time_str}&audioOnly=False&autoStart=True"
    else:
        player_url = f"{base_player_url}?audioOnly=False&autoStart=True"
    
    print(f"Fetching player URL: {player_url}")
    
    # Use curl to fetch the player page with headers
    output_file = f"temp/player_{event_id}.html"
    headers_file = f"temp/headers_{event_id}.txt"
    
    curl_cmd = [
        'curl', 
        '-s', 
        '-D', headers_file,  # Save headers to file
        '-o', output_file,   # Save body to file
        '-L',                # Follow redirects
        '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',  # User agent
        player_url
    ]
    
    try:
        subprocess.run(curl_cmd, check=True)
        print(f"Saved player page to {output_file}")
        
        # Read the HTML content
        with open(output_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Look for different types of stream URLs
        stream_urls = {}
        
        # Look for HLS streams
        hls_pattern = re.compile(r'(https://[^"\']+\.m3u8[^"\']*)')
        hls_matches = hls_pattern.findall(html_content)
        if hls_matches:
            stream_urls['hls'] = [unquote(url) for url in hls_matches]
        
        # Look for MP4 streams
        mp4_pattern = re.compile(r'(https://[^"\']+\.mp4[^"\']*)')
        mp4_matches = mp4_pattern.findall(html_content)
        if mp4_matches:
            stream_urls['mp4'] = [unquote(url) for url in mp4_matches]
        
        # Look for Redbee player configuration
        redbee_config_pattern = re.compile(r'var\s+config\s*=\s*({[^;]+});')
        redbee_match = redbee_config_pattern.search(html_content)
        if redbee_match:
            try:
                config_str = redbee_match.group(1)
                # Clean up the string to make it valid JSON
                config_str = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', config_str)
                config = json.loads(config_str)
                stream_urls['config'] = config
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing player configuration: {e}")
        
        # Look for other player URLs
        player_urls_pattern = re.compile(r'var\s+(\w+PlayerUrl)\s*=\s*[\'"]([^\'"]+)[\'"]')
        player_urls_matches = player_urls_pattern.findall(html_content)
        if player_urls_matches:
            stream_urls['player_urls'] = {name: unquote(url) for name, url in player_urls_matches}
        
        # If we found player URLs but no stream URLs, try to fetch those URLs
        if 'player_urls' in stream_urls and not (stream_urls.get('hls') or stream_urls.get('mp4')):
            for name, url in stream_urls['player_urls'].items():
                if not url.startswith('http'):
                    url = f"https://videoplayback.parliamentlive.tv{url}"
                
                print(f"Fetching additional player URL: {url}")
                additional_output_file = f"temp/player_{name}_{event_id}.html"
                
                additional_curl_cmd = [
                    'curl', 
                    '-s', 
                    '-o', additional_output_file,
                    '-L',
                    '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                    url
                ]
                
                try:
                    subprocess.run(additional_curl_cmd, check=True)
                    print(f"Saved additional player page to {additional_output_file}")
                    
                    # Read the HTML content
                    with open(additional_output_file, 'r', encoding='utf-8') as f:
                        additional_html_content = f.read()
                    
                    # Look for HLS streams
                    additional_hls_matches = hls_pattern.findall(additional_html_content)
                    if additional_hls_matches:
                        if 'hls' not in stream_urls:
                            stream_urls['hls'] = []
                        stream_urls['hls'].extend([unquote(url) for url in additional_hls_matches])
                    
                    # Look for MP4 streams
                    additional_mp4_matches = mp4_pattern.findall(additional_html_content)
                    if additional_mp4_matches:
                        if 'mp4' not in stream_urls:
                            stream_urls['mp4'] = []
                        stream_urls['mp4'].extend([unquote(url) for url in additional_mp4_matches])
                    
                except subprocess.CalledProcessError as e:
                    print(f"Error fetching additional player page: {e}")
        
        # If still no streams found, try to use the recorded player URL
        if not (stream_urls.get('hls') or stream_urls.get('mp4')) and 'player_urls' in stream_urls and 'recordedPlayerUrl' in stream_urls['player_urls']:
            recorded_url = stream_urls['player_urls']['recordedPlayerUrl']
            if not recorded_url.startswith('http'):
                recorded_url = f"https://videoplayback.parliamentlive.tv{recorded_url}"
            
            # Use a more direct approach to get the stream URL
            print(f"Trying to extract stream URL from recorded player: {recorded_url}")
            
            # Extract the event ID from the recorded player URL
            recorded_event_id = re.search(r'/Recorded/([a-zA-Z0-9-]+)', recorded_url)
            if recorded_event_id:
                recorded_event_id = recorded_event_id.group(1)
                
                # Construct a direct stream URL based on the Redbee CDN pattern
                direct_stream_url = f"https://p7of6fc-a2-westeurope-fay.cdn.redbee.live/parliamentlive/vod/entities/{recorded_event_id}/mat/era4H923HNQyTa_00823ARVcd-idx-2.m3u8"
                stream_urls['direct_stream'] = direct_stream_url
        
        return stream_urls
        
    except subprocess.CalledProcessError as e:
        print(f"Error running curl command: {e}")
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
    
    # Use the direct approach to extract stream URLs
    stream_info = extract_stream_urls_using_curl_output(event_id, time_marker)
    
    if not stream_info or (not stream_info.get('hls') and not stream_info.get('mp4') and not stream_info.get('direct_stream')):
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
