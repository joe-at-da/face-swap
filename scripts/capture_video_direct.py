#!/usr/bin/env python3
"""
Direct Parliament Video Capture

This script directly captures Parliament-style video using ffmpeg without the problematic capture class.
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime

def capture_parliament_video_direct(duration_seconds=120):
    """Capture Parliament video directly using ffmpeg."""
    print(f"Capturing {duration_seconds} seconds of Parliament-style video...")
    
    # Use a longer Parliament-style video
    stream_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    # Create output directory
    output_dir = Path("/tmp/parliament_capture")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
    
    print(f"Output file: {output_file}")
    print(f"Stream URL: {stream_url}")
    
    # Build ffmpeg command
    cmd = [
        'ffmpeg', '-y',
        '-i', stream_url,
        '-t', str(duration_seconds),
        '-c', 'copy',
        str(output_file)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Run ffmpeg capture
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Get video duration
            cmd_probe = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
                str(output_file)
            ]
            probe_result = subprocess.run(cmd_probe, capture_output=True, text=True)
            
            if probe_result.returncode == 0:
                format_info = json.loads(probe_result.stdout)
                duration = float(format_info['format']['duration'])
                
                print(f"✅ Successfully captured {duration:.2f} seconds of video")
                print(f"📁 Video saved to: {output_file}")
                print(f"📊 File size: {output_file.stat().st_size / (1024*1024):.2f} MB")
                return str(output_file)
            else:
                print(f"❌ Failed to get video info: {probe_result.stderr}")
                return None
        else:
            print(f"❌ FFmpeg failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Capture timed out")
        return None
    except Exception as e:
        print(f"❌ Error during capture: {e}")
        return None

if __name__ == "__main__":
    # Capture 2 minutes of Parliament video
    video_path = capture_parliament_video_direct(120)
    
    if video_path:
        print(f"\n✅ Parliament video captured successfully!")
        print(f"📹 Video path: {video_path}")
        print(f"\n🔗 Use this video for face recognition demo:")
        print(f"python parliament_face_recognition_simple.py --video {video_path} --focus-last-seconds 60")
    else:
        print(f"\n❌ Failed to capture Parliament video")
