#!/usr/bin/env python3
"""
Facial Recognition-based Video Capture Script

This script captures video from a stream and automatically stops when the person
is no longer detected in the video frame.

Usage:
    python facial_recognition_capture.py <video_url> [--duration SECONDS] [--output OUTPUT_FILE]

Example:
    python facial_recognition_capture.py http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4 --duration 60
"""

import os
import sys
import time
import argparse
import subprocess
import logging
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("facial_recognition_capture")

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import cv2
        import numpy as np
        return True
    except ImportError:
        return False

def install_dependencies():
    """Install required dependencies."""
    logger.info("Installing dependencies...")
    try:
        # Use apt-get in Docker environment to install OpenCV dependencies
        if os.path.exists('/.dockerenv'):
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'python3-opencv', 'libopencv-dev'], check=True)
        else:
            # Use pip for non-Docker environments
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'opencv-python', 'numpy'], check=True)
        
        logger.info("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def capture_video_with_facial_recognition(video_url, output_file=None, max_duration=None, face_detection_interval=1):
    """
    Capture video from a URL and stop when no face is detected for a certain period.
    
    Args:
        video_url (str): The URL of the video to capture
        output_file (str, optional): The output file path
        max_duration (int, optional): Maximum duration to capture in seconds
        face_detection_interval (int): How often to check for faces (in seconds)
        
    Returns:
        str: The path to the captured video file
    """
    logger.info(f"Capturing video from: {video_url}")
    
    # Create a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use the provided output file or generate one
    if not output_file:
        output_dir = Path("data/media/parliament_captures")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"facial_recognition_capture_{timestamp}.mp4"
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary directory for frames
    temp_dir = Path("data/temp/frames")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the face detection classifier
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Open the video stream
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        logger.error(f"Error: Could not open video stream: {video_url}")
        return None
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    logger.info(f"Video properties: {width}x{height} @ {fps} fps")
    
    # Create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))
    
    # Variables to track face detection
    face_detected = False
    no_face_frames = 0
    max_no_face_frames = int(fps * 5)  # 5 seconds without a face
    
    # Variables to track duration
    start_time = time.time()
    frame_count = 0
    check_interval_frames = int(fps * face_detection_interval)
    
    try:
        while True:
            # Check if maximum duration has been reached
            if max_duration and (time.time() - start_time) > max_duration:
                logger.info(f"Maximum duration of {max_duration} seconds reached.")
                break
            
            # Read a frame
            ret, frame = cap.read()
            if not ret:
                logger.info("End of video stream reached.")
                break
            
            # Write the frame to the output video
            out.write(frame)
            
            # Only check for faces at the specified interval to improve performance
            frame_count += 1
            if frame_count % check_interval_frames == 0:
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                # Save a frame with face detection for debugging
                debug_frame = frame.copy()
                for (x, y, w, h) in faces:
                    cv2.rectangle(debug_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                debug_frame_path = temp_dir / f"frame_{frame_count}.jpg"
                cv2.imwrite(str(debug_frame_path), debug_frame)
                
                # Update face detection status
                if len(faces) > 0:
                    if not face_detected:
                        logger.info(f"Face detected at frame {frame_count}.")
                    face_detected = True
                    no_face_frames = 0
                else:
                    if face_detected:
                        logger.info(f"No face detected at frame {frame_count}.")
                    face_detected = False
                    no_face_frames += 1
                
                # If no face has been detected for a while, stop capturing
                if face_detected and no_face_frames > max_no_face_frames:
                    logger.info(f"No face detected for {max_no_face_frames / fps} seconds. Stopping capture.")
                    break
                
                # Log progress
                elapsed_time = time.time() - start_time
                logger.info(f"Processed frame {frame_count}, elapsed time: {elapsed_time:.2f}s, faces detected: {len(faces)}")
    
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user.")
    except Exception as e:
        logger.error(f"Error during capture: {e}")
    finally:
        # Release resources
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        logger.info(f"Capture completed. Output file: {output_file}")
        return str(output_file)

def main():
    parser = argparse.ArgumentParser(description='Capture video with facial recognition.')
    parser.add_argument('url', help='Video URL or file path')
    parser.add_argument('--duration', '-d', type=int, help='Maximum duration to capture in seconds')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--interval', '-i', type=int, default=1, help='Face detection interval in seconds')
    parser.add_argument('--docker', action='store_true', help='Running in Docker environment')
    args = parser.parse_args()
    
    try:
        # Check and install dependencies if needed
        if not check_dependencies():
            if not install_dependencies():
                logger.error("Required dependencies could not be installed.")
                return 1
            
            # Re-import after installation
            import cv2
            import numpy as np
        
        # Determine if the URL is a local file or a remote URL
        is_local_file = os.path.exists(args.url)
        logger.info(f"Input is a {'local file' if is_local_file else 'remote URL'}: {args.url}")
        
        # Capture video with facial recognition
        output_file = capture_video_with_facial_recognition(
            args.url,
            output_file=args.output,
            max_duration=args.duration,
            face_detection_interval=args.interval
        )
        
        # Print the output file for capturing by the parent process
        print(f"Output file: {output_file}")
        
        if output_file:
            logger.info(f"Video capture completed successfully. Output file: {output_file}")
            return 0
        else:
            logger.error("Video capture failed.")
            return 1
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
