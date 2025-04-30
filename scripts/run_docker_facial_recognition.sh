#!/bin/bash
# Script to run the facial recognition script inside the Docker container

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <parliament_tv_event_url> [--duration SECONDS] [--output OUTPUT_FILE] [--test]"
    echo "Example: $0 https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120"
    exit 1
fi

# Prepare the command arguments
URL="$1"
shift
ARGS="$@"

# Create data directories if they don't exist
mkdir -p data/temp
mkdir -p data/media/parliament_captures

# Copy the scripts to the container
docker cp scripts/extract_parliament_stream_v4.py the-mp-app-1:/app/scripts/
docker cp scripts/docker_facial_recognition.py the-mp-app-1:/app/scripts/

# Make the scripts executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/extract_parliament_stream_v4.py
docker exec the-mp-app-1 chmod +x /app/scripts/docker_facial_recognition.py

# Install requests library if not already installed
docker exec the-mp-app-1 pip install requests

# Run the facial recognition script inside the container
echo "Running facial recognition inside Docker container..."
docker exec -it the-mp-app-1 python /app/scripts/docker_facial_recognition.py "$URL" $ARGS

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Error: Facial recognition failed."
    exit 1
fi

# Copy the captured files from the container to the host
echo "Copying captured files from container to host..."
docker cp the-mp-app-1:/app/data/media/parliament_captures/. ./data/media/parliament_captures/

echo "Facial recognition completed successfully."
echo "Files copied to ./data/media/parliament_captures/"
