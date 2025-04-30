#!/bin/bash
# Script to download the Parliament TV stream on the host machine
# and then process it inside the Docker container

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

# Create data directories if they don't exist
mkdir -p data/temp
mkdir -p data/media/parliament_captures

# Extract duration from arguments if provided
DURATION=60  # Default duration
for arg in $ARGS; do
    if [[ $arg == "--duration" || $arg == "-d" ]]; then
        DURATION="${@:$((i+1)):1}"
        break
    fi
    ((i++))
done

# Step 1: Extract stream info using Python script on host
echo "Extracting stream info from Parliament TV URL..."
python scripts/extract_parliament_stream_v3.py "$URL" --output data/temp/stream_info.json

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

# Step 3: Download a segment of the stream using ffmpeg on host
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_FILE="data/temp/parliament_stream_$TIMESTAMP.mp4"

echo "Downloading stream segment to $TEMP_FILE..."
ffmpeg -i "$STREAM_URL" -t $DURATION -c copy -y "$TEMP_FILE"

# Check if download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download stream segment."
    exit 1
fi

echo "Download completed successfully."

# Step 4: Copy the downloaded file to the Docker container
echo "Copying downloaded file to Docker container..."
docker cp "$TEMP_FILE" the-mp-app-1:/app/data/temp/

# Step 5: Process the video inside the Docker container
echo "Processing video inside Docker container..."
docker exec -it the-mp-app-1 ffmpeg -i "/app/data/temp/$(basename $TEMP_FILE)" -ss $TIME_MARKER -t $DURATION -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k -movflags +faststart "/app/data/media/parliament_captures/processed_$TIMESTAMP.mp4"

# Check if processing was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to process video in Docker container."
    exit 1
fi

echo "Processing completed successfully."

# Step 6: Copy the processed file back to the host
echo "Copying processed file from Docker container to host..."
docker cp "the-mp-app-1:/app/data/media/parliament_captures/processed_$TIMESTAMP.mp4" "./data/media/parliament_captures/"

echo "Parliament TV capture completed successfully."
echo "Output file: ./data/media/parliament_captures/processed_$TIMESTAMP.mp4"
