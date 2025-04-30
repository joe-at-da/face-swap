#!/bin/bash
# Script to run the local Parliament TV capture inside the Docker container

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE]"
    echo "Example: $0 https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120"
    exit 1
fi

# Prepare the command arguments
URL="$1"
shift
ARGS="$@"

# Create data directory if it doesn't exist
mkdir -p data/temp
mkdir -p data/media

# Copy the extraction and capture scripts to the container
docker cp scripts/extract_parliament_stream_v3.py the-mp-app-1:/app/scripts/
docker cp scripts/local_parliament_capture.py the-mp-app-1:/app/scripts/

# Make the scripts executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/extract_parliament_stream_v3.py
docker exec the-mp-app-1 chmod +x /app/scripts/local_parliament_capture.py

# Install requests library if not already installed
docker exec the-mp-app-1 pip install requests

# Run the capture script inside the container
echo "Running Parliament TV capture inside Docker container..."
docker exec -it the-mp-app-1 python /app/scripts/local_parliament_capture.py "$URL" $ARGS

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Error: Parliament TV capture failed."
    exit 1
fi

echo "Parliament TV capture completed successfully."

# Copy the captured files from the container to the host
echo "Copying captured files from container to host..."
docker cp the-mp-app-1:/root/parliament_captures/. ./data/media/parliament_captures/

echo "Files copied to ./data/media/parliament_captures/"
