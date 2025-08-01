#!/bin/bash
# Script to run the resume_parliament_processing.py script inside the Docker container

# Default values
CAPTURE_ID=""
STAGE=""
DEBUG=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --capture-id)
      CAPTURE_ID="$2"
      shift 2
      ;;
    --stage)
      STAGE="$2"
      shift 2
      ;;
    --debug)
      DEBUG="--debug"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check required arguments
if [ -z "$CAPTURE_ID" ] || [ -z "$STAGE" ]; then
  echo "Usage: $0 --capture-id CAPTURE_ID --stage [recognition|export] [--debug]"
  exit 1
fi

# Get the Docker container ID for the app container
CONTAINER_ID=$(docker ps | grep "the-mp-app" | awk '{print $1}')

if [ -z "$CONTAINER_ID" ]; then
  echo "Error: Docker container for the-mp-app not found. Make sure the Docker container is running."
  exit 1
fi

echo "Found Docker container: $CONTAINER_ID"

# Copy the resume script to the container
echo "Copying resume_parliament_processing.py to the container..."
docker cp "$(dirname "$0")/resume_parliament_processing.py" "$CONTAINER_ID:/app/backend/scripts/"

# Make the script executable in the container
echo "Making script executable in the container..."
docker exec "$CONTAINER_ID" chmod +x /app/backend/scripts/resume_parliament_processing.py

# Run the script in the container
echo "Running script in the container..."
docker exec -it "$CONTAINER_ID" python /app/backend/scripts/resume_parliament_processing.py --capture-id "$CAPTURE_ID" --stage "$STAGE" $DEBUG

echo "Script execution completed."
