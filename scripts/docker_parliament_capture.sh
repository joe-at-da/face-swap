#!/bin/bash
# Script to run the Parliament TV capture inside the Docker container

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <parliament_tv_url> [--duration SECONDS] [--output OUTPUT_FILE]"
    echo "Example: $0 https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120"
    exit 1
fi

# Prepare the command arguments
URL="$1"
shift
ARGS="$@"

# Create data directory if it doesn't exist
mkdir -p data/temp

# Copy the extraction script to the container
docker cp scripts/extract_parliament_stream_v2.py the-mp-app-1:/app/scripts/
docker cp scripts/parliament_capture.py the-mp-app-1:/app/scripts/

# Make the scripts executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/extract_parliament_stream_v2.py
docker exec the-mp-app-1 chmod +x /app/scripts/parliament_capture.py

# Run the capture script inside the container
echo "Running Parliament TV capture inside Docker container..."
docker exec -it the-mp-app-1 python /app/scripts/parliament_capture.py "$URL" $ARGS

# Check the exit status
if [ $? -ne 0 ]; then
    echo "Error: Parliament TV capture failed."
    exit 1
fi

echo "Parliament TV capture completed successfully."
