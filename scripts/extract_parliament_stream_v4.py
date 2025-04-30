#!/usr/bin/env python3
"""
Wrapper script for extract_direct_stream.py to maintain backward compatibility.
This script extracts video stream URLs from Parliament TV event pages using yt-dlp.

Usage: python extract_parliament_stream_v4.py <parliament_tv_event_url>
Example: python extract_parliament_stream_v4.py https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38

Note: This script is a wrapper around extract_direct_stream.py, which is the recommended
script to use for new development.
"""

import sys
import json
import argparse
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extract_parliament_stream_v4')

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
    """Fetch the content of a URL using requests."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return None

def format_player_url(event_id, time_marker=None):
    """
    Format the player URL in the exact format expected by Parliament TV.
    """
    base_url = f"https://videoplayback.parliamentlive.tv/Player/Index/{event_id}"
    
    if time_marker:
        # Format the time marker as ISO 8601 date with the current date
        # The format should be: 2025-02-04T13:25:38+00:00
        current_date = datetime.now().strftime("%Y-%m-%d")
        time_str = seconds_to_hms(time_marker.total_seconds())
        iso_time = f"{current_date}T{time_str}+00:00"
        
        # URL encode the time parameter
        encoded_time = quote(iso_time)
        
        return f"{base_url}?in={encoded_time}&audioOnly=False&autoStart=True"
    else:
        return f"{base_url}?audioOnly=False&autoStart=True"

def extract_stream_urls(event_id, time_marker=None):
    """
    Extract stream URLs from the Parliament TV player page.
    """
    # Format the player URL
    player_url = format_player_url(event_id, time_marker)
    print(f"Fetching player URL: {player_url}")
    
    # Set up headers for the request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    
    try:
        # Fetch the player page
        response = requests.get(player_url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
        
        # Create a temporary directory for output files
        os.makedirs("temp", exist_ok=True)
        
        # Save the HTML content to a file for debugging
        output_file = f"temp/player_{event_id}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved player page to {output_file}")
        
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
                
                try:
                    additional_response = requests.get(url, headers=headers, timeout=30)
                    additional_response.raise_for_status()
                    additional_html_content = additional_response.text
                    
                    # Save the HTML content to a file for debugging
                    additional_output_file = f"temp/player_{name}_{event_id}.html"
                    with open(additional_output_file, 'w', encoding='utf-8') as f:
                        f.write(additional_html_content)
                    print(f"Saved additional player page to {additional_output_file}")
                    
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
                
                except requests.RequestException as e:
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
        
    except requests.RequestException as e:
        print(f"Error fetching player page: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def extract_direct_stream(url, output_file=None):
    """Extract the direct stream URL using extract_direct_stream.py."""
    logger.info(f"Extracting direct stream URL from: {url}")
    
    try:
        cmd = [
            sys.executable,
            "scripts/extract_direct_stream.py",
            url
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running command: {' '.join(cmd)}")
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

def main():
    parser = argparse.ArgumentParser(description='Extract video stream URLs from Parliament TV event pages.')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--output', '-o', help='Output file for the stream information')
    args = parser.parse_args()
    
    url = args.url
    logger.info(f"Analyzing Parliament TV URL: {url}")
    
    # Use the new extract_direct_stream.py script
    stream_info = extract_direct_stream(url, args.output)
    
    if not stream_info:
        logger.error("Could not extract stream information.")
        return 1
    
    # Print the stream information if not saving to file
    if not args.output:
        print("\nStream Information:")
        print(json.dumps(stream_info, indent=2))
    else:
        logger.info(f"Stream information saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
