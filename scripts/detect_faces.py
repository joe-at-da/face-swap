#!/usr/bin/env python3
"""
Detect Faces in Videos

This script processes videos and detects faces in frames, returning face detection results.
It's used by the facial recognition service to identify faces in video files.

Usage:
    python detect_faces.py --video /path/to/video.mp4 [--output /path/to/output.json]

Example:
    python detect_faces.py --video /app/data/temp/parliament_video.mp4 --output /app/data/temp/faces.json
"""

import os
import sys
import argparse
import logging
import json
import cv2
import numpy as np
import face_recognition
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("detect_faces")

def detect_faces_in_video(video_path, output_path=None):
    """
    Detect faces in a video file.
    
    Args:
        video_path: Path to the video file
        output_path: Optional path to save results as JSON
        
    Returns:
        List of face detection results
    """
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return []
        
        logger.info(f"Processing video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"Video FPS: {fps}, Total frames: {total_frames}")
        
        face_detections = []
        frame_count = 0
        processed_frames = 0
        
        # Process frames (sample every 30 frames to reduce processing time)
        sample_rate = 30
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Sample frames to reduce processing time
            if frame_count % sample_rate != 0:
                continue
            
            processed_frames += 1
            
            # Convert BGR to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces in the frame
            try:
                # Try face detection with CNN model first
                face_locations = face_recognition.face_locations(rgb_frame, model="cnn")
                
                # If CNN fails, try HOG model
                if not face_locations:
                    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                
                if face_locations:
                    timestamp = frame_count / fps
                    
                    for i, (top, right, bottom, left) in enumerate(face_locations):
                        face_detection = {
                            "frame_number": frame_count,
                            "timestamp": timestamp,
                            "face_id": f"face_{processed_frames}_{i}",
                            "box": [left, top, right - left, bottom - top],
                            "confidence": 1.0,  # face_recognition doesn't provide confidence
                            "face_location": {
                                "top": top,
                                "right": right,
                                "bottom": bottom,
                                "left": left
                            }
                        }
                        face_detections.append(face_detection)
                        
                        logger.info(f"Detected face at frame {frame_count}, timestamp {timestamp:.2f}s")
                
            except Exception as e:
                logger.warning(f"Face detection failed for frame {frame_count}: {str(e)}")
                continue
        
        cap.release()
        
        logger.info(f"Processed {processed_frames} frames out of {total_frames}")
        logger.info(f"Total faces detected: {len(face_detections)}")
        
        # Save results if output path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump({
                    "video_path": video_path,
                    "total_frames": total_frames,
                    "processed_frames": processed_frames,
                    "face_detections": face_detections,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f"Results saved to: {output_path}")
        
        return face_detections
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Detect faces in video files")
    parser.add_argument("--input", help="Path to the video file (alternative to --video)")
    parser.add_argument("--video", help="Path to the video file")
    parser.add_argument("--output", help="Path to save results as JSON")
    
    args = parser.parse_args()
    
    # Use --input if --video not provided (for compatibility)
    video_path = args.video or args.input
    if not video_path:
        parser.error("Either --video or --input must be provided")
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Detect faces
    face_detections = detect_faces_in_video(video_path, args.output)
    
    if face_detections:
        logger.info(f"Successfully detected {len(face_detections)} faces")
    else:
        logger.warning("No faces detected in the video")
    
    # Print summary
    print(f"Video: {video_path}")
    print(f"Faces detected: {len(face_detections)}")
    if args.output:
        print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()
