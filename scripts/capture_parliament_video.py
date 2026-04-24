#!/usr/bin/env python3
"""
Capture Parliament Video

This script captures 2+ minutes of Parliament-style video for face recognition demo.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Add the project root directory to Python path (so we can import backend)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force disable test mode for this demo
os.environ["TEST_MODE"] = "false"

from backend.services.video.capture import StreamCapture

def capture_parliament_video(duration_seconds=120):
    """Capture Parliament video for face recognition demo."""
    print(f"Capturing {duration_seconds} seconds of Parliament-style video...")
    
    # Create local temp directory
    local_temp_dir = Path(tempfile.mkdtemp(prefix="parliament_capture_"))
    
    # Initialize capture with Parliament-style video and override temp directory
    capture = StreamCapture()
    capture.temp_dir = local_temp_dir  # Override the temp directory
    
    # Create output file path
    output_dir = Path("/tmp/parliament_capture")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"parliament_capture_{timestamp}.mp4"
    
    print(f"Output file: {output_file}")
    print(f"Using stream URL: {capture.stream_url}")
    
    # Start capture
    try:
        capture.start_capture(
            output_file=str(output_file),
            duration=duration_seconds
        )
        
        # Wait for capture to complete
        capture._current_process.wait()
        
        # Check if file was created and get its duration
        if output_file.exists():
            # Get video duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
                str(output_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            format_info = json.loads(result.stdout)
            duration = float(format_info['format']['duration'])
            
            print(f"✅ Successfully captured {duration:.2f} seconds of video")
            print(f"📁 Video saved to: {output_file}")
            return str(output_file)
        else:
            print("❌ No video file was created")
            return None
            
    except Exception as e:
        print(f"❌ Error during capture: {e}")
        return None

if __name__ == "__main__":
    import json
    
    # Capture 2 minutes of Parliament video
    video_path = capture_parliament_video(120)
    
    if video_path:
        print(f"\n✅ Parliament video captured successfully!")
        print(f"📹 Video path: {video_path}")
        print(f"\n🔗 Use this video for face recognition demo:")
        print(f"python parliament_face_recognition_simple.py --video {video_path} --focus-last-seconds 60")
    else:
        print(f"\n❌ Failed to capture Parliament video")
