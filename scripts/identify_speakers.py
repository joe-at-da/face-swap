#!/usr/bin/env python3
"""
Identify Speakers in Videos

This script identifies speakers in videos using facial recognition.
It uses the MP encodings file to match faces in the video with known MPs.

Usage:
    python identify_speakers.py --input /path/to/video.mp4 --encodings /path/to/mp_encodings.json --results /path/to/results.json [--output /path/to/output.mp4]

Example:
    python identify_speakers.py --input /app/data/temp/parliament_video.mp4 --encodings /app/data/mp_encodings.json --results /app/data/results.json
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
logger = logging.getLogger("identify_speakers")

# Constants
DEFAULT_SAMPLE_RATE = 5  # Process every Nth frame
FACE_RECOGNITION_TOLERANCE = 0.6  # Lower is more strict (0.6 is typical)
MIN_FACE_SIZE = 80  # Minimum face size (width or height) in pixels - balanced for quality vs detection
MIN_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to include in results
CENTER_FRAME_THRESHOLD_X = 0.25  # How close to center a face must be horizontally (smaller = stricter)
CENTER_FRAME_THRESHOLD_Y = 0.5  # Relaxed vertical threshold - much less important than horizontal

def ensure_directory(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def load_mp_encodings(encodings_file):
    """Load MP encodings from a JSON file."""
    try:
        with open(encodings_file, 'r') as f:
            data = json.load(f)
        
        # Validate the data format
        if not all(key in data for key in ['names', 'encodings']):
            raise ValueError("Invalid MP encodings file format")
        
        # Convert encodings to numpy arrays
        encodings = [np.array(encoding) for encoding in data['encodings']]
        
        logger.info(f"Loaded {len(data['names'])} MP encodings")
        
        return {
            'names': data['names'],
            'encodings': encodings,
            'parliament_ids': data.get('parliament_ids', [None] * len(data['names']))
        }
    except Exception as e:
        logger.error(f"Error loading MP encodings: {str(e)}")
        raise

def identify_speakers_in_video(video_path, mp_encodings, output_path=None, sample_rate=DEFAULT_SAMPLE_RATE):
    """
    Identify speakers in a video using facial recognition.
    
    Args:
        video_path: Path to the video file
        mp_encodings: Dict with MP names and encodings
        output_path: Optional path to save the output video with speaker identification
        sample_rate: Process every Nth frame
        
    Returns:
        Dict with identification results
    """
    try:
        logger.info(f"Identifying speakers in video: {video_path}")
        
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
        
        # Set up output video if requested
        video_writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Initialize variables for speaker tracking
        speaker_appearances = []  # List of speaker appearances with timestamps
        processed_frames = 0
        faces_detected = 0
        
        # Process the video
        frame_idx = 0
        while True:
            # Read a frame
            ret, frame = video.read()
            if not ret:
                break
            
            # Calculate timestamp for this frame
            timestamp = frame_idx / fps if fps > 0 else 0
            
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
                        top, right, bottom, left = face_location
                        
                        # Skip small faces
                        face_width = right - left
                        face_height = bottom - top
                        if face_width < MIN_FACE_SIZE or face_height < MIN_FACE_SIZE:
                            logger.debug(f"Skipping small face: {face_width}x{face_height} pixels")
                            continue
                        
                        # Skip faces that aren't in the center frame
                        face_center_x = (left + right) / 2
                        face_center_y = (top + bottom) / 2
                        frame_center_x = width / 2
                        frame_center_y = height / 2
                        
                        # Calculate distance from center as a percentage of frame dimensions
                        x_distance_pct = abs(face_center_x - frame_center_x) / (width / 2)
                        y_distance_pct = abs(face_center_y - frame_center_y) / (height / 2)
                        
                        # Skip if the face is too far from center (lower values = stricter center requirement)
                        if x_distance_pct > CENTER_FRAME_THRESHOLD_X:
                            logger.info(f"Skipping face not in horizontal center (x_distance: {x_distance_pct:.2f})")
                            continue
                            
                        # Also check vertical centering
                        if y_distance_pct > CENTER_FRAME_THRESHOLD_Y:
                            logger.info(f"Skipping face not in vertical center (y_distance: {y_distance_pct:.2f})")
                            continue
                            
                        # Log the accepted face position
                        logger.info(f"Processing center frame face at position ({x_distance_pct:.2f}, {y_distance_pct:.2f}) relative to center")
                        
                        # Compare with known MP encodings
                        matches = face_recognition.compare_faces(
                            mp_encodings['encodings'], 
                            face_encoding, 
                            tolerance=FACE_RECOGNITION_TOLERANCE
                        )
                        
                        # Calculate face distances
                        face_distances = face_recognition.face_distance(mp_encodings['encodings'], face_encoding)
                        
                        # Find the best match
                        if True in matches:
                            best_match_idx = np.argmin(face_distances)
                            confidence = 1.0 - face_distances[best_match_idx]
                            
                            if confidence >= MIN_CONFIDENCE_THRESHOLD:
                                name = mp_encodings['names'][best_match_idx]
                                parliament_id = mp_encodings['parliament_ids'][best_match_idx]
                                
                                # Record this appearance
                                speaker_appearances.append({
                                    "name": name,
                                    "parliament_id": parliament_id,
                                    "confidence": float(confidence),
                                    "timestamp": timestamp,
                                    "frame_idx": frame_idx,
                                    "face_location": face_location
                                })
                                
                                logger.info(f"Frame {frame_idx}: Identified {name} with {confidence:.2f} confidence")
                                
                                # Draw on the frame if we're creating an output video
                                if video_writer:
                                    # Draw a box around the face
                                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                                    
                                    # Draw a label with the name and confidence
                                    label = f"{name} ({confidence:.2f})"
                                    font = cv2.FONT_HERSHEY_DUPLEX
                                    cv2.putText(frame, label, (left, top - 10), font, 0.5, (0, 255, 0), 1)
                
                # Log progress occasionally
                if processed_frames % 100 == 0:
                    progress = (frame_idx / frame_count) * 100 if frame_count > 0 else 0
                    logger.info(f"Processed {processed_frames} frames ({progress:.1f}% complete)")
            
            # Write the frame to the output video if requested
            if video_writer:
                video_writer.write(frame)
            
            frame_idx += 1
        
        # Close the video and writer
        video.release()
        if video_writer:
            video_writer.release()
        
        # Group appearances by speaker
        speakers_data = {}
        for appearance in speaker_appearances:
            name = appearance["name"]
            if name not in speakers_data:
                speakers_data[name] = {
                    "name": name,
                    "parliament_id": appearance["parliament_id"],
                    "appearances": [],
                    "confidence": 0,
                    "total_confidence": 0,
                    "start_time": float('inf'),
                    "end_time": 0,
                    "duration": 0
                }
            
            # Add this appearance
            speakers_data[name]["appearances"].append(appearance)
            speakers_data[name]["total_confidence"] += appearance["confidence"]
            speakers_data[name]["start_time"] = min(speakers_data[name]["start_time"], appearance["timestamp"])
            speakers_data[name]["end_time"] = max(speakers_data[name]["end_time"], appearance["timestamp"])
        
        # Calculate average confidence and duration for each speaker
        for name, data in speakers_data.items():
            if data["appearances"]:
                data["confidence"] = data["total_confidence"] / len(data["appearances"])
                data["duration"] = data["end_time"] - data["start_time"]
        
        # Convert to a list and sort by duration (longest speaking time first)
        speakers = list(speakers_data.values())
        speakers.sort(key=lambda x: x["duration"], reverse=True)
        
        # Create the results
        results = {
            "video_path": video_path,
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
                "processed_at": datetime.now().isoformat()
            },
            "speakers": speakers,
            "output_video": output_path if output_path else None
        }
        
        logger.info(f"Processing complete. Identified {len(speakers)} speakers in {processed_frames} frames.")
        
        return {
            "success": True,
            "results": results
        }
    
    except Exception as e:
        logger.exception(f"Error identifying speakers: {str(e)}")
        return {
            "success": False,
            "error": f"Error identifying speakers: {str(e)}"
        }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Identify speakers in videos using facial recognition")
    parser.add_argument("--input", required=True, help="Path to the input video file")
    parser.add_argument("--encodings", required=True, help="Path to the MP encodings JSON file")
    parser.add_argument("--results", required=True, help="Path to save the results JSON file")
    parser.add_argument("--output", help="Path to save the output video with speaker identification")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Process every Nth frame")
    
    args = parser.parse_args()
    
    try:
        # Load MP encodings
        mp_encodings = load_mp_encodings(args.encodings)
        
        # Process the video
        result = identify_speakers_in_video(
            args.input, 
            mp_encodings, 
            args.output, 
            args.sample_rate
        )
        
        if result["success"]:
            # Save the results
            with open(args.results, "w") as f:
                json.dump(result["results"], f, indent=2)
            
            logger.info(f"Results saved to: {args.results}")
            return 0
        else:
            logger.error(f"Speaker identification failed: {result.get('error', 'Unknown error')}")
            return 1
    
    except Exception as e:
        logger.exception(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
