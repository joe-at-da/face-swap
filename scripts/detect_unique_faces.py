#!/usr/bin/env python3
"""
Detect Unique Faces in Videos

This script processes videos, detects faces in frames, and identifies unique faces.
It stores the unique face encodings for later identification.

Usage:
    python detect_unique_faces.py --video /path/to/video.mp4 [--output /path/to/output/directory] [--sample-rate 5]

Example:
    python detect_unique_faces.py --video /app/data/temp/parliament_video.mp4 --output /app/data/face_profiles --sample-rate 10
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
import uuid

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("detect_unique_faces")

# Constants
DEFAULT_OUTPUT_DIR = "/app/data/face_profiles"
DEFAULT_SAMPLE_RATE = 5  # Process every Nth frame
FACE_SIMILARITY_THRESHOLD = 0.6  # Threshold for considering faces as the same person

def ensure_directory(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_unique_id():
    """Generate a unique ID for a face."""
    return str(uuid.uuid4())[:8]

def process_video(video_path, output_dir, sample_rate=DEFAULT_SAMPLE_RATE):
    """
    Process a video to detect unique faces.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save face images and data
        sample_rate: Process every Nth frame
        
    Returns:
        Dict with processing results
    """
    try:
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Sample rate: {sample_rate} (processing every {sample_rate}th frame)")
        
        # Ensure output directory exists
        ensure_directory(output_dir)
        
        # Create a directory for this video's faces
        video_name = Path(video_path).stem
        video_faces_dir = Path(output_dir) / f"video_{video_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        video_faces_dir.mkdir(parents=True, exist_ok=True)
        
        # Open the video
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            return {
                "success": False,
                "error": f"Could not open video file: {video_path}"
            }
        
        # Get video properties
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        logger.info(f"Video properties: {width}x{height} @ {fps} fps, {frame_count} frames, {duration:.2f} seconds")
        
        # Initialize variables for face tracking
        known_face_encodings = []
        known_face_ids = []
        face_appearances = {}  # Map face IDs to their appearances (frame, location, etc.)
        processed_frames = 0
        faces_detected = 0
        unique_faces = 0
        
        # Process the video
        frame_idx = 0
        while True:
            # Read a frame
            ret, frame = video.read()
            if not ret:
                break
            
            # Process every Nth frame
            if frame_idx % sample_rate == 0:
                processed_frames += 1
                
                # Convert BGR to RGB (face_recognition uses RGB)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Find faces in the frame
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if face_locations:
                    # Get face encodings
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    faces_detected += len(face_locations)
                    
                    # Process each face
                    for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
                        # Check if this face matches any known face
                        matches = []
                        if known_face_encodings:
                            # Compare with known faces
                            matches = face_recognition.compare_faces(
                                known_face_encodings, 
                                face_encoding, 
                                tolerance=FACE_SIMILARITY_THRESHOLD
                            )
                        
                        # If we found a match
                        if any(matches):
                            # Find the first matching face ID
                            match_index = matches.index(True)
                            face_id = known_face_ids[match_index]
                            
                            # Update the average encoding for this face
                            # This helps improve recognition over time
                            known_face_encodings[match_index] = np.mean(
                                [known_face_encodings[match_index], face_encoding], 
                                axis=0
                            )
                        else:
                            # This is a new face, assign a new ID
                            face_id = get_unique_id()
                            known_face_ids.append(face_id)
                            known_face_encodings.append(face_encoding)
                            unique_faces += 1
                            
                            # Initialize the face appearances
                            face_appearances[face_id] = {
                                "id": face_id,
                                "first_seen_frame": frame_idx,
                                "first_seen_time": frame_idx / fps if fps > 0 else 0,
                                "appearances": [],
                                "encoding": face_encoding.tolist(),
                                "face_images": []
                            }
                        
                        # Record this appearance
                        top, right, bottom, left = face_location
                        timestamp = frame_idx / fps if fps > 0 else 0
                        
                        # Save the face image
                        face_image = frame[top:bottom, left:right]
                        face_filename = f"face_{face_id}_{frame_idx}.jpg"
                        face_path = str(video_faces_dir / face_filename)
                        cv2.imwrite(face_path, face_image)
                        
                        # Add to appearances
                        appearance = {
                            "frame": frame_idx,
                            "timestamp": timestamp,
                            "location": face_location,
                            "image_path": face_path
                        }
                        
                        face_appearances[face_id]["appearances"].append(appearance)
                        face_appearances[face_id]["face_images"].append(face_path)
                        
                        # Log progress occasionally
                        if unique_faces % 5 == 0 and len(face_appearances[face_id]["appearances"]) == 1:
                            logger.info(f"Found {unique_faces} unique faces so far")
                
                # Log progress occasionally
                if processed_frames % 100 == 0:
                    progress = (frame_idx / frame_count) * 100 if frame_count > 0 else 0
                    logger.info(f"Processed {processed_frames} frames ({progress:.1f}% complete)")
            
            frame_idx += 1
        
        # Close the video
        video.release()
        
        # Save the face data to a JSON file
        face_data = {
            "video_path": video_path,
            "video_name": video_name,
            "video_properties": {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration
            },
            "processing_info": {
                "processed_frames": processed_frames,
                "sample_rate": sample_rate,
                "faces_detected": faces_detected,
                "unique_faces": unique_faces,
                "processed_at": datetime.now().isoformat()
            },
            "faces": list(face_appearances.values())
        }
        
        face_data_file = video_faces_dir / "face_data.json"
        with open(face_data_file, "w") as f:
            json.dump(face_data, f, indent=2)
        
        # Create a summary file with just the unique faces and their encodings
        unique_faces_data = {
            "video_path": video_path,
            "video_name": video_name,
            "processed_at": datetime.now().isoformat(),
            "unique_faces": [
                {
                    "id": face_id,
                    "encoding": face_appearances[face_id]["encoding"],
                    "appearances": len(face_appearances[face_id]["appearances"]),
                    "first_seen_time": face_appearances[face_id]["first_seen_time"],
                    "sample_image": face_appearances[face_id]["face_images"][0] if face_appearances[face_id]["face_images"] else None
                }
                for face_id in known_face_ids
            ]
        }
        
        unique_faces_file = video_faces_dir / "unique_faces.json"
        with open(unique_faces_file, "w") as f:
            json.dump(unique_faces_data, f, indent=2)
        
        logger.info(f"Processing complete. Found {unique_faces} unique faces in {processed_frames} frames.")
        logger.info(f"Face data saved to: {face_data_file}")
        logger.info(f"Unique faces data saved to: {unique_faces_file}")
        
        return {
            "success": True,
            "video_path": video_path,
            "output_directory": str(video_faces_dir),
            "face_data_file": str(face_data_file),
            "unique_faces_file": str(unique_faces_file),
            "processed_frames": processed_frames,
            "faces_detected": faces_detected,
            "unique_faces": unique_faces
        }
    
    except Exception as e:
        logger.exception(f"Error processing video: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing video: {str(e)}"
        }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Detect unique faces in videos")
    parser.add_argument("--video", required=True, help="Path to the video file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for face data")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Process every Nth frame")
    
    args = parser.parse_args()
    
    # Process the video
    result = process_video(args.video, args.output, args.sample_rate)
    
    if result["success"]:
        logger.info("Video processing completed successfully")
        return 0
    else:
        logger.error(f"Video processing failed: {result.get('error', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
