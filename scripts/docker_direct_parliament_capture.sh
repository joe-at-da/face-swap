#!/bin/bash
# Script to run the direct Parliament TV capture inside the Docker container

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <parliament_tv_player_url> [--duration SECONDS] [--output OUTPUT_FILE]"
    echo "Example: $0 \"https://videoplayback.parliamentlive.tv/Player/Index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=2025-02-04T13%3A25%3A38%2B00%3A00&audioOnly=False&autoStart=True\" --duration 60"
    exit 1
fi

# Prepare the command arguments
URL="$1"
shift
ARGS="$@"

# Create data directories if they don't exist
mkdir -p data/temp
mkdir -p data/media/parliament_captures

# Copy the script to the container
docker cp scripts/direct_parliament_capture.py the-mp-app-1:/app/scripts/

# Make the script executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/direct_parliament_capture.py

# Install requests library if not already installed
docker exec the-mp-app-1 pip install requests

# Run the capture script inside the container
echo "Running Parliament TV capture inside Docker container..."
docker exec -it the-mp-app-1 python /app/scripts/direct_parliament_capture.py "$URL" $ARGS

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Error: Parliament TV capture failed."
    exit 1
fi

# Copy the captured files from the container to the host
echo "Copying captured files from container to host..."
docker cp the-mp-app-1:/app/data/media/parliament_captures/. ./data/media/parliament_captures/

echo "Parliament TV capture completed successfully."
echo "Files copied to ./data/media/parliament_captures/"
