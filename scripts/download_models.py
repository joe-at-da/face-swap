#!/usr/bin/env python3
"""
Script to download face recognition models during container initialization.
This ensures that the required ONNX models are available when the container is deployed.
"""

import os
import sys
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model URLs and destinations
MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "path": "/app/models/face_recognition/face_detection_yunet_2023mar.onnx"
    },
    "face_recognition_sface_2021dec.onnx": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "path": "/app/models/face_recognition/face_recognition_sface_2021dec.onnx"
    }
}

def download_file(url, destination):
    """
    Download a file from a URL to a destination path.
    
    Args:
        url: URL to download from
        destination: Path to save the file to
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(destination):
            logger.info(f"File already exists: {destination}")
            return True
        
        # Download the file
        logger.info(f"Downloading {url} to {destination}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save the file
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Download complete: {destination}")
        return True
    
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return False

def main():
    """
    Main function to download all models.
    """
    success = True
    
    for model_name, model_info in MODELS.items():
        if not download_file(model_info["url"], model_info["path"]):
            success = False
    
    if success:
        logger.info("All models downloaded successfully")
        return 0
    else:
        logger.error("Failed to download some models")
        return 1

if __name__ == "__main__":
    sys.exit(main())
