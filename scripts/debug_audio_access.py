#!/usr/bin/env python3
import os
import sys
import glob
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - debug-audio-access - %(levelname)s - %(message)s",
)
logger = logging.getLogger("debug-audio-access")

def debug_audio_file_access(filename: str):
    """
    Debug audio file access issues by checking all possible locations
    
    Args:
        filename: The filename to check for
    """
    # Get the data directory from environment variable
    data_dir = os.getenv("DATA_DIR", "/app/data")
    logger.info(f"Data directory: {data_dir}")
    
    # Look for the audio file in common locations
    possible_locations = [
        os.path.join(data_dir, "temp", "audio_extracts", filename),
        os.path.join(data_dir, filename),
        os.path.join(data_dir, "**", filename)
    ]
    
    logger.info(f"Checking for file: {filename}")
    
    # Try to find the file
    for location in possible_locations:
        logger.info(f"Checking location: {location}")
        
        # For the wildcard path, use glob
        if "**" in location:
            logger.info(f"Using glob to search recursively")
            matching_files = glob.glob(location, recursive=True)
            if matching_files:
                logger.info(f"Found files with glob: {matching_files}")
            else:
                logger.info("No files found with glob")
        elif os.path.exists(location):
            logger.info(f"File exists at: {location}")
            logger.info(f"File size: {os.path.getsize(location)} bytes")
            logger.info(f"File permissions: {oct(os.stat(location).st_mode)[-3:]}")
        else:
            logger.info(f"File does not exist at: {location}")
    
    # Check all audio files in the audio_extracts directory
    audio_extracts_dir = os.path.join(data_dir, "temp", "audio_extracts")
    if os.path.exists(audio_extracts_dir):
        logger.info(f"Listing all files in {audio_extracts_dir}:")
        for file in os.listdir(audio_extracts_dir):
            logger.info(f"  - {file}")
    else:
        logger.info(f"Directory does not exist: {audio_extracts_dir}")

def main():
    parser = argparse.ArgumentParser(description="Debug audio file access issues")
    parser.add_argument("filename", help="Filename to check for")
    args = parser.parse_args()
    
    debug_audio_file_access(args.filename)

if __name__ == "__main__":
    main()
