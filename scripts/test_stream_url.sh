#!/bin/bash
# Script to test if a stream URL is valid by downloading a small segment

if [ -z "$1" ]; then
    echo "Usage: $0 <stream_url>"
    exit 1
fi

STREAM_URL="$1"
OUTPUT_FILE="data/temp/test_stream_$(date +%Y%m%d_%H%M%S).mp4"

# Create temp directory if it doesn't exist
mkdir -p data/temp

echo "Testing stream URL: $STREAM_URL"
echo "Attempting to download a 5-second segment..."

# Try to download a 5-second segment using ffmpeg
ffmpeg -i "$STREAM_URL" -t 5 -c copy -y "$OUTPUT_FILE" 2>&1

# Check if download was successful
if [ $? -eq 0 ]; then
    echo "Success! The stream URL is valid."
    echo "Downloaded a 5-second test segment to: $OUTPUT_FILE"
    
    # Get file info
    echo "File information:"
    ffprobe -v quiet -print_format json -show_format -show_streams "$OUTPUT_FILE"
    
    # Play the file if requested
    if [ "$2" == "--play" ]; then
        echo "Opening the file with the default player..."
        open "$OUTPUT_FILE"
    fi
else
    echo "Failed to download from the stream URL. It may be invalid or inaccessible."
fi
