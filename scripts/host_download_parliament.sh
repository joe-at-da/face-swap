#!/bin/bash
# Script to download a Parliament TV stream on the host and process it in Docker

# Check if URL is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <parliament_tv_event_url> [--duration SECONDS]"
    echo "Example: $0 https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38 --duration 120"
    exit 1
fi

# Prepare the command arguments
URL="$1"
shift
ARGS="$@"

# Extract duration from arguments if provided
DURATION=60  # Default duration
for arg in $ARGS; do
    if [[ $arg == "--duration" || $arg == "-d" ]]; then
        DURATION="${@:$((i+1)):1}"
        break
    fi
    ((i++))
done

# Create data directories if they don't exist
mkdir -p data/temp
mkdir -p data/media/parliament_captures

# Step 1: Extract stream info using Python script on host
echo "Extracting stream info from Parliament TV URL..."
python scripts/extract_parliament_stream_v4.py "$URL" --output data/temp/stream_info.json

# Check if extraction was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to extract stream info."
    exit 1
fi

# Step 2: Parse the stream info to get the direct stream URL and time marker
STREAM_URL=$(grep -o '"direct_stream": "[^"]*"' data/temp/stream_info.json | cut -d'"' -f4)
TIME_MARKER=$(grep -o '"seconds": [0-9.]*' data/temp/stream_info.json | cut -d' ' -f2)

if [ -z "$STREAM_URL" ]; then
    echo "Error: Could not extract stream URL from stream info."
    exit 1
fi

echo "Stream URL: $STREAM_URL"
echo "Time marker: $TIME_MARKER seconds"

# Step 3: Download a segment of the stream using yt-dlp on host
# Install yt-dlp if not already installed
if ! command -v yt-dlp &> /dev/null; then
    echo "Installing yt-dlp..."
    pip install yt-dlp
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_FILE="data/temp/parliament_stream_$TIMESTAMP.mp4"

echo "Downloading stream segment to $TEMP_FILE..."
yt-dlp -o "$TEMP_FILE" --no-check-certificate "$STREAM_URL"

# Check if download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download stream segment with yt-dlp. Trying ffmpeg..."
    
    # Try with ffmpeg as fallback
    if command -v ffmpeg &> /dev/null; then
        ffmpeg -i "$STREAM_URL" -t $DURATION -c copy -y "$TEMP_FILE"
        
        if [ $? -ne 0 ]; then
            echo "Error: Failed to download stream segment with ffmpeg."
            exit 1
        fi
    else
        echo "Error: Neither yt-dlp nor ffmpeg could download the stream."
        exit 1
    fi
fi

echo "Download completed successfully."

# Step 4: Copy the downloaded file to the Docker container
echo "Copying downloaded file to Docker container..."
docker cp "$TEMP_FILE" the-mp-app-1:/app/data/temp/

# Step 5: Process the video inside the Docker container with facial recognition
echo "Processing video inside Docker container..."

# Copy the facial recognition script to the container
docker cp scripts/facial_recognition_capture.py the-mp-app-1:/app/scripts/

# Make the script executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/facial_recognition_capture.py

# Install OpenCV in the container
docker exec the-mp-app-1 pip install opencv-python numpy

# Run the facial recognition script in the container
docker exec -it the-mp-app-1 python /app/scripts/facial_recognition_capture.py "/app/data/temp/$(basename $TEMP_FILE)" --duration $DURATION

# Check if processing was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to process video with facial recognition."
    exit 1
fi

# Step 6: Copy the processed files back to the host
echo "Copying processed files from Docker container to host..."
docker cp the-mp-app-1:/app/data/media/parliament_captures/. ./data/media/parliament_captures/

echo "Parliament TV capture with facial recognition completed successfully."
echo "Output files are in ./data/media/parliament_captures/"
