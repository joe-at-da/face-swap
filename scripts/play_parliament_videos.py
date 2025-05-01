#!/usr/bin/env python3
"""
Parliament TV Video Player

A simple utility to list and play Parliament TV videos directly from the data directory.
This serves as a temporary solution until the videos are properly integrated into the main UI.

Usage:
  python play_parliament_videos.py list
  python play_parliament_videos.py play <video_filename>
  python play_parliament_videos.py info
"""

import os
import sys
import glob
import json
import subprocess
from datetime import datetime
import shutil

# Define the data directory where videos are stored
DATA_DIR = "/app/data/temp"
# Use a directory that's accessible from the host
LOCAL_DATA_DIR = "/app/data/host_access"

def format_size(size_bytes):
    """Format file size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def format_timestamp(timestamp):
    """Format timestamp to human-readable format"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

def list_videos():
    """List all Parliament TV videos in the data directory"""
    # Create patterns to match Parliament TV video files
    patterns = [
        os.path.join(DATA_DIR, "parliament_stream_*.mp4"),
        os.path.join(DATA_DIR, "capture_*.mp4")
    ]
    
    videos = []
    for pattern in patterns:
        matching_files = glob.glob(pattern)
        for file_path in matching_files:
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                modified_time = os.path.getmtime(file_path)
                
                videos.append({
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "modified_time": modified_time
                })
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
    
    # Sort videos by modified time (newest first)
    videos.sort(key=lambda x: x["modified_time"], reverse=True)
    
    # Print the list of videos
    print(f"\nFound {len(videos)} Parliament TV videos:\n")
    print(f"{'#':<3} {'Filename':<40} {'Size':<10} {'Modified':<20}")
    print("-" * 80)
    
    for i, video in enumerate(videos, 1):
        print(f"{i:<3} {video['file_name']:<40} {format_size(video['file_size']):<10} {format_timestamp(video['modified_time']):<20}")
    
    print("\nTo play a video, run: python play_parliament_videos.py play <filename>")
    
    return videos

def copy_to_local(file_path):
    """Copy a video file to the local directory for playback"""
    # Create local directory if it doesn't exist
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    
    # Get the filename
    file_name = os.path.basename(file_path)
    local_path = os.path.join(LOCAL_DATA_DIR, file_name)
    
    # Copy the file if it doesn't exist locally
    if not os.path.exists(local_path):
        print(f"Copying {file_name} to local directory...")
        shutil.copy2(file_path, local_path)
    
    return local_path

def play_video(file_name):
    """Play a Parliament TV video"""
    # Find the video file
    patterns = [
        os.path.join(DATA_DIR, file_name),
        os.path.join(DATA_DIR, f"*{file_name}*")
    ]
    
    found_files = []
    for pattern in patterns:
        matching_files = glob.glob(pattern)
        found_files.extend(matching_files)
    
    if not found_files:
        print(f"Error: Video file '{file_name}' not found in {DATA_DIR}")
        return
    
    # Use the first matching file
    file_path = found_files[0]
    print(f"Found video file: {file_path}")
    
    # Copy to local directory for playback
    local_path = copy_to_local(file_path)
    
    # Determine the platform and open the video
    print(f"Opening video: {local_path}")
    
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.call(["open", local_path])
        elif sys.platform == "win32":  # Windows
            os.startfile(local_path)
        else:  # Linux
            subprocess.call(["xdg-open", local_path])
    except Exception as e:
        print(f"Error opening video: {str(e)}")
        print(f"You can manually open the video at: {local_path}")

def show_system_info():
    """Show system information and help"""
    print("\nParliament TV Video Player - System Information\n")
    
    # Check if data directory exists
    if os.path.exists(DATA_DIR):
        print(f"✅ Data directory exists: {DATA_DIR}")
        
        # Check disk space
        try:
            total, used, free = shutil.disk_usage(DATA_DIR)
            print(f"   Disk space: {format_size(used)} used, {format_size(free)} free, {format_size(total)} total")
        except:
            print(f"   Could not determine disk space for {DATA_DIR}")
    else:
        print(f"❌ Data directory does not exist: {DATA_DIR}")
    
    # Check if local directory exists
    if os.path.exists(LOCAL_DATA_DIR):
        print(f"✅ Local directory exists: {LOCAL_DATA_DIR}")
        
        # Check disk space
        try:
            total, used, free = shutil.disk_usage(LOCAL_DATA_DIR)
            print(f"   Disk space: {format_size(used)} used, {format_size(free)} free, {format_size(total)} total")
        except:
            print(f"   Could not determine disk space for {LOCAL_DATA_DIR}")
    else:
        print(f"ℹ️ Local directory will be created when needed: {LOCAL_DATA_DIR}")
    
    # Show help
    print("\nUsage:")
    print("  python play_parliament_videos.py list    - List all Parliament TV videos")
    print("  python play_parliament_videos.py play <filename> - Play a specific video")
    print("  python play_parliament_videos.py info    - Show system information")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Error: No command specified")
        print("Usage: python play_parliament_videos.py [list|play|info]")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_videos()
    elif command == "play":
        if len(sys.argv) < 3:
            print("Error: No filename specified")
            print("Usage: python play_parliament_videos.py play <filename>")
            return
        
        file_name = sys.argv[2]
        play_video(file_name)
    elif command == "info":
        show_system_info()
    else:
        print(f"Error: Unknown command '{command}'")
        print("Usage: python play_parliament_videos.py [list|play|info]")

if __name__ == "__main__":
    main()
