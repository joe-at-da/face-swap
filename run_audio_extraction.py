#!/usr/bin/env python3
"""
Run audio extraction for a specific capture ID.
This script bypasses the syntax issues in parliament_tv.py and directly runs the extract_audio_for_capture.py script.
"""

import os
import sys
import subprocess

def run_audio_extraction(capture_id):
    """Run audio extraction for a specific capture ID."""
    print(f"Running audio extraction for capture ID: {capture_id}")
    
    # Path to the extract_audio_for_capture.py script
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "extract_audio_for_capture.py")
    
    if not os.path.exists(script_path):
        print(f"Error: Script not found at {script_path}")
        return False
    
    # Run the script
    cmd = [sys.executable, script_path, str(capture_id)]
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Audio extraction successful for capture ID: {capture_id}")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"Audio extraction failed for capture ID: {capture_id}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running audio extraction: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_audio_extraction.py <capture_id>")
        sys.exit(1)
    
    capture_id = sys.argv[1]
    success = run_audio_extraction(capture_id)
    
    if success:
        print("Audio extraction completed successfully")
        sys.exit(0)
    else:
        print("Audio extraction failed")
        sys.exit(1)
