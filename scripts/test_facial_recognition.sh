#!/bin/bash
# Script to test facial recognition with a sample video

# Create data directories if they don't exist
mkdir -p data/temp
mkdir -p data/media/parliament_captures

# Step 1: Download a sample video with faces
SAMPLE_VIDEO_URL="http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_FILE="data/temp/sample_video_$TIMESTAMP.mp4"

echo "Downloading sample video to $TEMP_FILE..."
curl -L "$SAMPLE_VIDEO_URL" -o "$TEMP_FILE"

# Check if download was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to download sample video."
    exit 1
fi

echo "Download completed successfully."

# Step 2: Copy the downloaded file to the Docker container
echo "Copying sample video to Docker container..."
docker cp "$TEMP_FILE" the-mp-app-1:/app/data/temp/

# Step 3: Copy the facial recognition script to the container
docker cp scripts/facial_recognition_capture.py the-mp-app-1:/app/scripts/

# Step 4: Make the script executable in the container
docker exec the-mp-app-1 chmod +x /app/scripts/facial_recognition_capture.py

# Step 5: Install OpenCV in the container
echo "Installing OpenCV in Docker container..."
docker exec the-mp-app-1 apt-get update
docker exec the-mp-app-1 apt-get install -y python3-opencv libopencv-dev

# Downgrade NumPy to a compatible version
echo "Downgrading NumPy to a compatible version..."
docker exec the-mp-app-1 pip uninstall -y numpy
docker exec the-mp-app-1 pip install "numpy<2.0.0"

# Step 6: Run the facial recognition script in the container
echo "Running facial recognition on sample video..."
docker exec -it the-mp-app-1 python /app/scripts/facial_recognition_capture.py "/app/data/temp/$(basename $TEMP_FILE)" --duration 20 --docker

# Step 7: Copy the processed files back to the host
echo "Copying processed files from Docker container to host..."
docker cp the-mp-app-1:/app/data/media/parliament_captures/. ./data/media/parliament_captures/

echo "Facial recognition test completed."
echo "Output files are in ./data/media/parliament_captures/"
