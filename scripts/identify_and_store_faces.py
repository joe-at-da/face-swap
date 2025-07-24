#!/usr/bin/env python3
"""
Script to identify known faces and store unidentified faces for later identification.

This script:
1. Identifies faces that match existing profiles in the database
2. Stores unidentified faces for later identification
3. Filters out faces that aren't in the center of the frame
"""

import os
import sys
import json
import argparse
import cv2
import face_recognition
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
import uuid
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CENTER_FRAME_THRESHOLD_X = 0.25  # How close to center a face must be horizontally (smaller = stricter)
CENTER_FRAME_THRESHOLD_Y = 0.5  # Relaxed vertical threshold - much less important than horizontal
MIN_FACE_SIZE = 80  # Minimum face size (width or height) in pixels - balanced for quality vs detection

def load_encodings(encodings_file):
    """Load face encodings from a JSON file."""
    try:
        with open(encodings_file, 'r') as f:
            data = json.load(f)
        
        # Check if the data has the required fields
        if not all(key in data for key in ["names", "encodings"]):
            logger.error(f"Invalid encodings file format: {encodings_file}")
            return None
        
        # Check if the encodings are empty
        if len(data["names"]) == 0 or len(data["encodings"]) == 0:
            logger.warning(f"MP encodings file exists but contains no encodings. Will proceed with face detection only.")
            # Return empty data structure that's valid
            return {
                "names": [],
                "encodings": [],
                "parliament_ids": [],
                "empty": True
            }
        
        # Convert encodings back to numpy arrays
        data["encodings"] = [np.array(encoding) for encoding in data["encodings"]]
        data["empty"] = False
        
        logger.info(f"Loaded {len(data['names'])} face encodings")
        return data
    except Exception as e:
        logger.error(f"Error loading encodings: {str(e)}")
        return None

def save_unidentified_face(face_image, face_location, output_dir):
    """Save an unidentified face to the output directory."""
    try:
        # Create a unique ID for the face
        face_id = str(uuid.uuid4())
        
        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract the face from the image
        top, right, bottom, left = face_location
        face = face_image[top:bottom, left:right]
        
        # Save the face image
        face_filename = os.path.join(output_dir, f"unidentified_face_{face_id}.jpg")
        cv2.imwrite(face_filename, cv2.cvtColor(face, cv2.COLOR_RGB2BGR))
        
        # Generate face encoding with proper error handling
        try:
            face_encodings = face_recognition.face_encodings(face_image, [face_location])
            if not face_encodings:
                logger.warning(f"Failed to locate face in extracted region at {face_location}")
                return None, None
            face_encoding = face_encodings[0]
        except Exception as encoding_error:
            logger.warning(f"Failed to generate face encoding: {str(encoding_error)}")
            return None, None
        
        # Save the face metadata
        # Use just the filename without the path for easier access from the frontend
        face_basename = os.path.basename(face_filename)
        metadata = {
            "id": face_id,
            "timestamp": datetime.now().isoformat(),
            "face_location": face_location,
            "encoding": face_encoding.tolist(),
            "identified": False,
            "filename": face_basename
        }
        
        metadata_filename = os.path.join(output_dir, f"unidentified_face_{face_id}.json")
        with open(metadata_filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved unidentified face {face_id} to {face_filename}")
        return face_id, face_filename
    except Exception as e:
        logger.error(f"Error saving unidentified face: {str(e)}")
        return None, None

def process_video(video_path, encodings_file, results_file, output_file=None, unidentified_dir=None, skip_frames_file=None):
    """Process a video to identify known faces and store unidentified faces."""
    # Load known face encodings
    known_data = load_encodings(encodings_file)
    if not known_data:
        return {
            "success": False,
            "error": "Failed to load known face encodings"
        }
    
    # Track problematic frames that should be skipped
    problematic_frames = set()
    
    # Open the video
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        return {
            "success": False,
            "error": f"Failed to open video: {video_path}"
        }
    
    # Get video properties
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Set up video writer if output file is specified
    video_writer = None
    if output_file:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))
    
    # Initialize results
    results = {
        "video_path": video_path,
        "processed_at": datetime.now().isoformat(),
        "speakers": [],
        "unidentified_faces": [],
        "total_frames": total_frames,
        "processed_frames": 0,
        "problematic_frames": []
    }
    
    # Load frames to skip if provided
    frames_to_skip = set()
    if skip_frames_file and os.path.exists(skip_frames_file):
        try:
            with open(skip_frames_file, 'r') as f:
                frames_to_skip = set(json.load(f))
            logger.info(f"Loaded {len(frames_to_skip)} frames to skip from {skip_frames_file}")
        except Exception as e:
            logger.warning(f"Error loading skip frames file: {str(e)}")
    
    # Process every 30th frame (adjust as needed for performance)
    frame_interval = 30
    frame_count = 0
    
    # Track identified speakers and unidentified faces
    identified_speakers = {}
    unidentified_faces = {}
    
    try:
        while True:
            ret, frame = video.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Process every Nth frame and skip problematic frames
            if frame_count % frame_interval != 0 or frame_count in frames_to_skip:
                if frame_count in frames_to_skip:
                    logger.info(f"Skipping problematic frame {frame_count}")
                if video_writer:
                    video_writer.write(frame)
                continue
            
            # Convert frame from BGR to RGB (face_recognition uses RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Skip this frame if it's been marked as problematic
            if frame_count in problematic_frames:
                logger.info(f"Skipping previously problematic frame {frame_count}")
                if video_writer:
                    video_writer.write(frame)
                continue
                
            # Find all faces in the frame
            try:
                # First try with default model (CNN)
                face_locations = face_recognition.face_locations(rgb_frame, model="cnn")
                
                # If no faces detected with CNN, try with HOG model as fallback
                if not face_locations:
                    logger.warning(f"No faces detected with CNN model in frame {frame_count}, trying HOG model")
                    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                
                if not face_locations:
                    logger.warning(f"No faces detected in frame {frame_count} with either model")
                    # Mark as problematic for future runs
                    results["problematic_frames"].append(frame_count)
                    if video_writer:
                        video_writer.write(frame)
                    continue
            except Exception as e:
                logger.warning(f"Error detecting faces in frame {frame_count}: {str(e)}")
                # Mark as problematic for future runs
                results["problematic_frames"].append(frame_count)
                if video_writer:
                    video_writer.write(frame)
                continue
                
            if face_locations:
                # Generate face encodings with error handling
                try:
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    # Check if we got encodings for all detected faces
                    if len(face_encodings) != len(face_locations):
                        logger.warning(f"Got {len(face_encodings)} encodings for {len(face_locations)} faces in frame {frame_count}")
                        # Mark frames with encoding issues as problematic
                        results["problematic_frames"].append(frame_count)
                        if video_writer:
                            video_writer.write(frame)
                        continue
                except Exception as e:
                    logger.warning(f"Error generating face encodings in frame {frame_count}: {str(e)}")
                    results["problematic_frames"].append(frame_count)
                    if video_writer:
                        video_writer.write(frame)
                    continue
                
                # Identify faces
                def identify_faces(frame, face_locations, known_face_encodings, known_face_names, known_parliament_ids=None):
                    """Identify faces in a frame."""
                    face_encodings = face_recognition.face_encodings(frame, face_locations)
                    face_names = []
                    face_ids = []
                    
                    # If we have empty encodings, mark all faces as unknown
                    if len(known_face_encodings) == 0:
                        logger.info("No known face encodings available, marking all faces as unknown")
                        for _ in face_encodings:
                            face_names.append("Unknown")
                            face_ids.append("")
                        return face_encodings, face_names, face_ids
                    
                    for face_encoding in face_encodings:
                        # Compare face with known faces
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                        name = "Unknown"
                        parliament_id = ""
                        
                        # Use the known face with the smallest distance to the new face
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        if len(face_distances) > 0:
                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                name = known_face_names[best_match_index]
                                if known_parliament_ids and len(known_parliament_ids) > best_match_index:
                                    parliament_id = known_parliament_ids[best_match_index]
                        
                        face_names.append(name)
                        face_ids.append(parliament_id)
                    
                    return face_encodings, face_names, face_ids
                
                face_encodings, face_names, face_ids = identify_faces(rgb_frame, face_locations, known_data["encodings"], known_data["names"], known_data["parliament_ids"])
                
                # Process each face
                for i, (face_encoding, face_location, name) in enumerate(zip(face_encodings, face_locations, face_names)):
                    # Get face dimensions and position
                    top, right, bottom, left = face_location
                    face_width = right - left
                    face_height = bottom - top
                    
                    # Skip small faces
                    if face_width < MIN_FACE_SIZE or face_height < MIN_FACE_SIZE:
                        logger.debug(f"Skipping small face: {face_width}x{face_height} pixels")
                        continue
                    
                    # Skip faces that aren't in the center frame
                    face_center_x = (left + right) / 2
                    face_center_y = (top + bottom) / 2
                    frame_center_x = frame_width / 2
                    frame_center_y = frame_height / 2
                    
                    # Calculate distance from center as a percentage of frame dimensions
                    x_distance_pct = abs(face_center_x - frame_center_x) / (frame_width / 2)
                    y_distance_pct = abs(face_center_y - frame_center_y) / (frame_height / 2)
                    
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
                    
                    # Get the timestamp
                    timestamp = frame_count / fps
                    
                    # Add to identified speakers if not already added
                    if name not in identified_speakers:
                        identified_speakers[name] = {
                            "name": name,
                            "confidence": 1.0,  # Placeholder for now
                            "appearances": []
                        }
                    
                    # Add this appearance
                    identified_speakers[name]["appearances"].append({
                        "frame": frame_count,
                        "timestamp": timestamp,
                        "face_location": face_location
                    })
                    
                    # Draw a box around the face and label it
                    if video_writer:
                        top, right, bottom, left = face_location
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # This is an unidentified face
                    # Save it if unidentified_dir is specified
                    if unidentified_dir and name == "Unknown":
                        # Generate a unique ID for this face if we haven't seen it before
                        # For simplicity, we're just using the face location as a key
                        face_key = f"{face_location}"
                        
                        if face_key not in unidentified_faces:
                            face_id, face_filename = save_unidentified_face(rgb_frame, face_location, unidentified_dir)
                            unidentified_faces[face_key] = {
                                "id": face_id,
                                "filename": face_filename,
                                "appearances": []
                            }
                        
                        # Add this appearance to unidentified faces
                        unidentified_faces[face_key]["appearances"].append({
                            "frame": frame_count,
                            "timestamp": timestamp,
                            "face_location": face_location
                        })
                        
                        # Draw a box around the face and label it
                        if video_writer:
                            top, right, bottom, left = face_location
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    else:
                        # This is an unidentified face
                        # Save it if unidentified_dir is specified
                        if unidentified_dir:
                            # Generate a unique ID for this face if we haven't seen it before
                            face_key = f"{face_location}"
                            
                            if face_key not in unidentified_faces:
                                face_id, face_filename = save_unidentified_face(rgb_frame, face_location, unidentified_dir)
                                
                                if face_id:
                                    timestamp = frame_count / fps
                                    unidentified_faces[face_key] = {
                                        "id": face_id,
                                        "filename": face_filename,
                                        "appearances": [{
                                            "frame": frame_count,
                                            "timestamp": timestamp,
                                            "face_location": face_location
                                        }]
                                    }
                                else:
                                    # If face extraction failed, mark this frame as problematic
                                    logger.warning(f"Failed to save unidentified face in frame {frame_count}")
                                    results["problematic_frames"].append(frame_count)
                            else:
                                # We've seen this face before, just add another appearance
                                timestamp = frame_count / fps
                                unidentified_faces[face_key]["appearances"].append({
                                    "frame": frame_count,
                                    "timestamp": timestamp,
                                    "face_location": face_location
                                })
                        
                        # Draw a box around the unidentified face
                        if video_writer:
                            top, right, bottom, left = face_location
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                            cv2.putText(frame, "Unknown", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Write the frame to the output video
            if video_writer:
                video_writer.write(frame)
            
            # Update processed frames count
            results["processed_frames"] = frame_count
            
            # Log progress every 100 processed frames
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                logger.info(f"Processing progress: {progress:.2f}% ({frame_count}/{total_frames})")
    
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing video: {str(e)}"
        }
    finally:
        # Release resources
        video.release()
        if video_writer:
            video_writer.release()
    
    # Format the results
    for name, speaker in identified_speakers.items():
        # Calculate time segments from appearances
        time_segments = []
        current_segment = None
        
        for appearance in sorted(speaker["appearances"], key=lambda x: x["timestamp"]):
            timestamp = appearance["timestamp"]
            
            if current_segment is None:
                current_segment = {"start": timestamp, "end": timestamp}
            elif timestamp - current_segment["end"] < 5:  # If less than 5 seconds gap, extend the segment
                current_segment["end"] = timestamp
            else:
                time_segments.append(current_segment)
                current_segment = {"start": timestamp, "end": timestamp}
        
        if current_segment:
            time_segments.append(current_segment)
        
        # Add to results
        results["speakers"].append({
            "name": name,
            "confidence": speaker["confidence"],
            "time_segments": time_segments,
            "appearances": speaker["appearances"]
        })
    
    # Add unidentified faces to results
    for face_key, face_data in unidentified_faces.items():
        # Calculate time segments from appearances
        time_segments = []
        current_segment = None
        
        for appearance in sorted(face_data["appearances"], key=lambda x: x["timestamp"]):
            timestamp = appearance["timestamp"]
            
            if current_segment is None:
                current_segment = {"start": timestamp, "end": timestamp}
            elif timestamp - current_segment["end"] < 5:  # If less than 5 seconds gap, extend the segment
                current_segment["end"] = timestamp
            else:
                time_segments.append(current_segment)
                current_segment = {"start": timestamp, "end": timestamp}
        
        if current_segment:
            time_segments.append(current_segment)
        
        # Add to results
        # Use basename of the filename to ensure consistency with the metadata
        filename = os.path.basename(face_data["filename"]) if face_data["filename"] else ""
        
        results["unidentified_faces"].append({
            "id": face_data["id"],
            "filename": filename,
            "time_segments": time_segments,
            "appearances": face_data["appearances"]
        })
    
    # Save the results
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Processed {frame_count} frames, found {len(identified_speakers)} speakers and {len(unidentified_faces)} unidentified faces")
    
    return {
        "success": True,
        "message": f"Processed {frame_count} frames, found {len(identified_speakers)} speakers and {len(unidentified_faces)} unidentified faces",
        "speakers": list(identified_speakers.values()),
        "unidentified_faces": list(unidentified_faces.values()),
        "results_file": results_file,
        "output_file": output_file
    }

def main():
    parser = argparse.ArgumentParser(description="Identify known faces and store unidentified faces in a video")
    parser.add_argument("--input", required=True, help="Path to the input video file")
    parser.add_argument("--encodings", required=True, help="Path to the known face encodings file")
    parser.add_argument("--results", required=True, help="Path to save the results JSON file")
    parser.add_argument("--output", help="Path to save the output video with face boxes")
    parser.add_argument("--unidentified-dir", help="Directory to save unidentified faces")
    parser.add_argument("--skip-frames", help="Path to a JSON file containing frame numbers to skip")
    
    args = parser.parse_args()
    
    # Process the video
    result = process_video(
        args.input,
        args.encodings,
        args.results,
        args.output,
        args.unidentified_dir,
        args.skip_frames
    )
    
    if result["success"]:
        logger.info("Video processing completed successfully")
        sys.exit(0)
    else:
        logger.error(f"Video processing failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
