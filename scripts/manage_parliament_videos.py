#!/usr/bin/env python3
"""
Parliament TV Video Management Utility

This script helps manage Parliament TV video files and clean up temporary files.
It provides functionality to:
1. List all captured videos
2. Delete specific videos
3. Clean up temporary files
4. Check disk usage

Usage:
  python manage_parliament_videos.py list
  python manage_parliament_videos.py delete <video_id>
  python manage_parliament_videos.py cleanup
  python manage_parliament_videos.py disk-usage
"""

import os
import sys
import glob
import json
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Default data directory
DATA_DIR = os.environ.get('DATA_DIR', '/app/data/temp')

def format_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def list_videos():
    """List all Parliament TV videos"""
    # Find all video files
    video_files = glob.glob(os.path.join(DATA_DIR, "parliament_stream_*.mp4"))
    
    if not video_files:
        print("No Parliament TV videos found.")
        return
    
    print(f"Found {len(video_files)} Parliament TV videos:")
    print("-" * 80)
    print(f"{'ID':<10} {'Filename':<40} {'Size':<15} {'Created':<20}")
    print("-" * 80)
    
    for video_file in sorted(video_files):
        filename = os.path.basename(video_file)
        size = os.path.getsize(video_file)
        created = datetime.fromtimestamp(os.path.getctime(video_file))
        
        # Try to extract ID from filename
        video_id = "Unknown"
        try:
            # Assuming filename format: parliament_stream_YYYYMMDD_HHMMSS_ID.mp4
            parts = filename.split("_")
            if len(parts) >= 4:
                video_id = parts[-1].split(".")[0]
        except:
            pass
        
        print(f"{video_id:<10} {filename:<40} {format_size(size):<15} {created.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("-" * 80)

def delete_video(video_id):
    """Delete a specific video and its associated files"""
    # Find the video file
    video_pattern = f"parliament_stream_*_{video_id}.mp4"
    video_files = glob.glob(os.path.join(DATA_DIR, video_pattern))
    
    if not video_files:
        print(f"No video found with ID: {video_id}")
        return
    
    # Find associated files
    associated_patterns = [
        f"parliament_capture_log_*_{video_id}.json",
        f"stream_info_*_{video_id}.json"
    ]
    
    associated_files = []
    for pattern in associated_patterns:
        associated_files.extend(glob.glob(os.path.join(DATA_DIR, pattern)))
    
    # Confirm deletion
    print(f"Found {len(video_files)} video file(s) and {len(associated_files)} associated file(s) for ID: {video_id}")
    for file in video_files + associated_files:
        print(f"  - {os.path.basename(file)}")
    
    confirm = input("Are you sure you want to delete these files? (y/n): ")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return
    
    # Delete files
    deleted_files = []
    for file in video_files + associated_files:
        try:
            os.remove(file)
            deleted_files.append(os.path.basename(file))
        except Exception as e:
            print(f"Error deleting {file}: {str(e)}")
    
    print(f"Successfully deleted {len(deleted_files)} files:")
    for file in deleted_files:
        print(f"  - {file}")

def cleanup_temp_files():
    """Clean up temporary files"""
    # Define patterns for temporary files
    temp_patterns = [
        "test_stream_*.mp4",
        "stream_info_*.json"
    ]
    
    total_count = 0
    total_size = 0
    
    print("Cleaning up temporary files...")
    
    for pattern in temp_patterns:
        files = glob.glob(os.path.join(DATA_DIR, pattern))
        if files:
            pattern_size = sum(os.path.getsize(f) for f in files)
            print(f"Found {len(files)} files matching '{pattern}' ({format_size(pattern_size)})")
            
            total_count += len(files)
            total_size += pattern_size
            
            # Delete files
            for file in files:
                try:
                    os.remove(file)
                    print(f"  - Deleted: {os.path.basename(file)}")
                except Exception as e:
                    print(f"  - Error deleting {os.path.basename(file)}: {str(e)}")
    
    print(f"Cleanup complete. Deleted {total_count} files, freed up {format_size(total_size)}.")

def check_disk_usage():
    """Check disk usage in the data directory"""
    # Get total size of data directory
    total_size = 0
    file_count = 0
    
    for dirpath, dirnames, filenames in os.walk(DATA_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
                file_count += 1
    
    # Get disk usage by file type
    file_types = {
        "Parliament Videos": "parliament_stream_*.mp4",
        "Test Streams": "test_stream_*.mp4",
        "Sample Videos": "sample_video_*.mp4",
        "Capture Videos": "capture_*.mp4",
        "JSON Files": "*.json",
        "Frame Images": "frames/*"
    }
    
    print(f"Disk Usage Report for {DATA_DIR}")
    print("-" * 80)
    print(f"Total size: {format_size(total_size)} ({file_count} files)")
    print("-" * 80)
    print(f"{'File Type':<20} {'Count':<10} {'Size':<15} {'Percentage':<10}")
    print("-" * 80)
    
    for file_type, pattern in file_types.items():
        files = glob.glob(os.path.join(DATA_DIR, pattern))
        if files:
            type_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
            percentage = (type_size / total_size) * 100 if total_size > 0 else 0
            print(f"{file_type:<20} {len(files):<10} {format_size(type_size):<15} {percentage:.2f}%")
    
    print("-" * 80)
    
    # Check available disk space
    total, used, free = shutil.disk_usage(DATA_DIR)
    print(f"Disk space: {format_size(total)} total, {format_size(used)} used, {format_size(free)} free")
    print(f"Disk usage: {(used / total) * 100:.2f}%")

def main():
    parser = argparse.ArgumentParser(description="Parliament TV Video Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all Parliament TV videos")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific video")
    delete_parser.add_argument("video_id", help="ID of the video to delete")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up temporary files")
    
    # Disk usage command
    disk_usage_parser = subparsers.add_parser("disk-usage", help="Check disk usage")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_videos()
    elif args.command == "delete":
        delete_video(args.video_id)
    elif args.command == "cleanup":
        cleanup_temp_files()
    elif args.command == "disk-usage":
        check_disk_usage()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
