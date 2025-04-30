#!/usr/bin/env python3
"""
Parliament TV Capture Wrapper Script

This script serves as a bridge between the backend API and our facial recognition-based
Parliament TV capture solution. It handles the capture process and returns metadata
about the captured video.

Usage:
    python parliament_capture_wrapper.py <parliament_tv_url> [--duration SECONDS] [--output OUTPUT_PATH]
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
        logging.FileHandler(f"parliament_capture_wrapper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger('parliament_capture_wrapper')

def run_host_capture(url, duration=None, output=None):
    """Run the host-based Parliament TV capture script."""
    logger.info(f"Starting Parliament TV capture for URL: {url}")
    
    cmd = [sys.executable, "scripts/host_parliament_capture.py", url]
    
    if duration:
        cmd.extend(["--duration", str(duration)])
    
    if output:
        cmd.extend(["--output", output])
    
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Parliament TV capture completed successfully.")
        
        # Parse the output to find the path to the captured video
        output_lines = result.stdout.split('\n')
        output_file = None
        
        for line in output_lines:
            if "Output file:" in line:
                output_file = line.split("Output file:")[1].strip()
                break
        
        return {
            "success": True,
            "output_file": output_file,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Parliament TV capture: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return {
            "success": False,
            "error": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr
        }

def get_video_metadata(video_path):
    """Get metadata for the captured video using ffprobe."""
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None
    
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        
        # Extract relevant metadata
        duration = float(metadata.get("format", {}).get("duration", 0))
        size = int(metadata.get("format", {}).get("size", 0))
        
        video_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        
        return {
            "duration": duration,
            "size_bytes": size,
            "width": width,
            "height": height,
            "format": metadata.get("format", {}).get("format_name", ""),
            "path": video_path
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Error getting video metadata: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Parliament TV Capture Wrapper')
    parser.add_argument('url', help='Parliament TV event URL')
    parser.add_argument('--duration', '-d', type=int, help='Maximum duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    args = parser.parse_args()
    
    # Run the host capture script
    result = run_host_capture(args.url, args.duration, args.output)
    
    if not result["success"]:
        logger.error("Parliament TV capture failed.")
        print(json.dumps({
            "success": False,
            "error": "Capture failed. See logs for details."
        }))
        return 1
    
    # Get metadata for the captured video
    output_file = result.get("output_file")
    if output_file and os.path.exists(output_file):
        metadata = get_video_metadata(output_file)
        if metadata:
            result["metadata"] = metadata
    
    # Print the result as JSON
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
