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

# Constants for face detection and filtering
MIN_FACE_SIZE = 20  # Minimum face size in pixels
CENTER_FRAME_THRESHOLD_X = 0.8  # How far from center horizontally a face can be (0-1, lower = stricter)
CENTER_FRAME_THRESHOLD_Y = 0.8  # How far from center vertically a face can be (0-1, lower = stricter)

def load_encodings(encodings_file, filter_category=None, max_encodings=None):
    """Load face encodings from a JSON file.
    
    Args:
        encodings_file: Path to the JSON file containing face encodings
        filter_category: Optional category to filter MPs (e.g., 'commons' for House of Commons)
        max_encodings: Optional maximum number of encodings to load
        
    Returns:
        Dictionary containing names, encodings, and parliament_ids
    """
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
        
        # Filter by category if specified
        if filter_category and "categories" in data:
            filtered_indices = [i for i, category in enumerate(data.get("categories", [])) 
                              if category and filter_category.lower() in category.lower()]
            
            if filtered_indices:
                logger.info(f"Filtering MPs by category: {filter_category}")
                data["names"] = [data["names"][i] for i in filtered_indices]
                data["encodings"] = [data["encodings"][i] for i in filtered_indices]
                
                # Also filter parliament_ids if available
                if "parliament_ids" in data:
                    data["parliament_ids"] = [data["parliament_ids"][i] for i in filtered_indices]
                    
                logger.info(f"Filtered to {len(data['names'])} MPs in category {filter_category}")
        
        # Limit number of encodings if specified
        if max_encodings and max_encodings > 0 and max_encodings < len(data["names"]):
            logger.info(f"Limiting to {max_encodings} encodings (out of {len(data['names'])})")
            data["names"] = data["names"][:max_encodings]
            data["encodings"] = data["encodings"][:max_encodings]
            
            # Also limit parliament_ids if available
            if "parliament_ids" in data:
                data["parliament_ids"] = data["parliament_ids"][:max_encodings]
        
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

def calculate_face_quality(frame, face_location):
    """Calculate a quality score for a face based on size, position, and basic image quality.
    
    Args:
        frame: The video frame containing the face
        face_location: Tuple of (top, right, bottom, left) coordinates
        
    Returns:
        A quality score (higher is better)
    """
    try:
        top, right, bottom, left = face_location
        face_width = right - left
        face_height = bottom - top
        frame_height, frame_width = frame.shape[:2]
        
        # Calculate face size score (larger is better) - max 30 points
        size_score = min((face_width * face_height) / (frame_width * frame_height) * 300, 30)
        
        # Calculate position score (centered horizontally is better) - max 50 points
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        x_distance = abs(face_center_x - frame_width/2) / (frame_width/2)  # 0 = center, 1 = edge
        position_score = (1 - x_distance) * 50  # Horizontal position is most important
        
        # Extract a small sample of the face region for quality analysis (center area)
        face_center_x_local = face_width // 2
        face_center_y_local = face_height // 2
        sample_size = min(face_width, face_height) // 4  # Use a quarter of the face for analysis
        
        sample_left = max(left + face_center_x_local - sample_size, left)
        sample_right = min(left + face_center_x_local + sample_size, right)
        sample_top = max(top + face_center_y_local - sample_size, top)
        sample_bottom = min(top + face_center_y_local + sample_size, bottom)
        
        # If we can't get a proper sample, use the whole face
        if sample_right - sample_left < 10 or sample_bottom - sample_top < 10:
            sample_left, sample_right, sample_top, sample_bottom = left, right, top, bottom
            
        face_sample = frame[sample_top:sample_bottom, sample_left:sample_right]
        
        # Calculate basic image quality metrics - max 20 points
        try:
            # Convert to grayscale for analysis
            if len(face_sample.shape) == 3:  # Color image
                gray_sample = cv2.cvtColor(face_sample, cv2.COLOR_BGR2GRAY)
            else:  # Already grayscale
                gray_sample = face_sample
                
            # Simple contrast measure (standard deviation of pixel values)
            contrast = gray_sample.std()
            quality_score = min(contrast / 5, 20)  # Cap at 20 points
        except Exception:
            # If image analysis fails, assign a moderate score
            quality_score = 10
        
        # Combine scores
        total_score = size_score + position_score + quality_score
        
        return total_score
    except Exception as e:
        logger.warning(f"Error calculating face quality: {str(e)}")
        return 0  # Return lowest score on error

def process_video(video_path, encodings_file, results_file, output_file=None, unidentified_dir=None, skip_frames_file=None, frame_skip=5, filter_mps=None, max_encodings=None, detection_model="hog"):
    """Process a video to identify known faces and store unidentified faces.
    
    Args:
        video_path: Path to the video file
        encodings_file: Path to the known face encodings file
        results_file: Path to save the results JSON file
        output_file: Optional path to save the output video with face boxes
        unidentified_dir: Optional directory to save unidentified faces
        skip_frames_file: Optional path to a JSON file containing frame numbers to skip
        frame_skip: Process every Nth frame (default: 5)
        filter_mps: Optional category to filter MPs (e.g., 'commons')
        max_encodings: Optional maximum number of encodings to load
        detection_model: Face detection model to use ('hog' or 'cnn')
    """
    # Load known face encodings with filtering options
    known_data = load_encodings(encodings_file, filter_mps, max_encodings)
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
        "appearances": [],
        "unidentified_faces": [],
        "total_frames": total_frames,
        "processed_frames": 0,
        "problematic_frames": [],
        "speakers": [],
        "best_faces": []
    }
    
    # Track best faces for each unique person - store minimal information to save memory
    best_faces = defaultdict(lambda: {'score': 0, 'face_location': None, 'frame_number': None, 'timestamp': None, 'position': None})
    
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
            # Log progress periodically
            if frame_count > 0 and frame_count % 50 == 0:
                logger.info(f"Processing progress: frame {frame_count}")
                
            try:
                ret, frame = video.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Skip frames based on frame_skip parameter (process every Nth frame)
                if frame_count % frame_skip != 0:
                    continue
                
                # Skip frames that are in the skip list
                if frame_count in frames_to_skip:
                    logger.info(f"Skipping frame {frame_count} as requested")
                    continue
                    
                logger.info(f"Processing frame {frame_count}")
            except Exception as frame_error:
                logger.error(f"Error reading frame {frame_count}: {str(frame_error)}")
                # Continue to next frame if there's an error with this one
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
                # Use specified detection model (HOG is default as it's more memory-efficient)
                logger.info(f"Detecting faces in frame {frame_count} using {detection_model} model")
                face_locations = face_recognition.face_locations(rgb_frame, model=detection_model)
                
                if not face_locations:
                    logger.warning(f"No faces detected in frame {frame_count} with {detection_model} model")
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
                
                # Call identify_faces function
                try:
                    logger.info(f"Identifying faces in frame {frame_count}")
                    face_encodings, face_names, face_ids = identify_faces(rgb_frame, face_locations, known_data["encodings"], known_data["names"], known_data.get("parliament_ids", []))
                    logger.info(f"Identified {len(face_names)} faces in frame {frame_count}")
                except Exception as e:
                    logger.error(f"Error identifying faces in frame {frame_count}: {str(e)}")
                    results["problematic_frames"].append(frame_count)
                    if video_writer:
                        video_writer.write(frame)
                    continue
                
                # Process each face
                for i, (face_encoding, face_location, name) in enumerate(zip(face_encodings, face_locations, face_names)):
                    # Get face dimensions and position
                    top, right, bottom, left = face_location
                    face_width = right - left
                    face_height = bottom - top
                    
                    # Calculate face quality score for best face selection
                    quality_score = calculate_face_quality(frame, face_location)
                    
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
                    
                    # Track best face for this person (by name or by parliament_id if available)
                    person_id = face_ids[i] if face_ids[i] else name
                    
                    # If this is a better quality face than what we've seen before, update it
                    if quality_score > best_faces[person_id]['score']:
                        logger.info(f"New best face for {person_id} with quality score {quality_score:.2f} (previous: {best_faces[person_id]['score']:.2f})")
                        best_faces[person_id] = {
                            'score': quality_score,
                            'face_location': face_location,
                            'frame_number': frame_count,
                            'position': (x_distance_pct, y_distance_pct),
                            'timestamp': frame_count / fps,
                            'frame_position': video.get(cv2.CAP_PROP_POS_MSEC)  # Store frame position for later extraction
                        }
                    
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
                    
                    # This is an unidentified face - track it but don't save intermediate images
                    # Just track it for best face selection
                    if name == "Unknown":
                        # Use a single key for all unidentified faces
                        # We'll just track them as "Unknown" and save the best one
                        face_key = "Unknown"
                        
                        if face_key not in unidentified_faces:
                            unidentified_faces[face_key] = {
                                "id": str(uuid.uuid4())[:8],  # Shorter ID for filename
                                "filename": None,  # We'll only save the best face at the end
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
                    # We've already handled both known and unknown faces above
                    # No need for an else clause here
                        
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
    
    # We'll handle unidentified faces as part of the best face extraction below
    # Clear the unidentified_faces list in results since we're only keeping best faces
    results["unidentified_faces"] = []
    
    # Add best face information to results
    results["best_faces"] = []
    
    # Reopen the video to extract best faces
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        logger.error(f"Could not reopen video for best face extraction: {video_path}")
    
    # Process and save the best face for each person (both identified and unidentified)
    # After processing all frames, save the best faces with sequential numbering
    if unidentified_dir:
        # First, collect all the faces we want to save
        faces_to_save = []
        
        # Collect all faces to save
        for person_id, face_data in best_faces.items():
            logger.info(f"Best face for {person_id}: quality score {face_data['score']:.2f}, frame {face_data['frame_number']}")
            
            # Extract the face image from the video at the stored frame position
            top, right, bottom, left = face_data['face_location']
            
            # Seek to the frame position where this face was found
            video.set(cv2.CAP_PROP_POS_MSEC, face_data['frame_position'])
            ret, frame = video.read()
            
            if ret:
                # Extract the face
                face_img = frame[top:bottom, left:right]
                
                # Add to our collection with all necessary data
                faces_to_save.append({
                    "person_id": person_id,
                    "face_img": face_img,
                    "quality_score": face_data['score'],
                    "frame_number": face_data['frame_number'],
                    "timestamp": face_data['timestamp'],
                    "face_location": face_data['face_location'],
                    "position": face_data['position']
                })
            else:
                logger.warning(f"Could not extract best face for {person_id} at frame position {face_data['frame_position']}")
        
        # Now save all faces with sequential numbering
        for i, face_data in enumerate(faces_to_save, 1):
            # Simple sequential filename
            best_face_filename = os.path.join(unidentified_dir, f"{i}.jpg")
            
            # Save the face image
            cv2.imwrite(best_face_filename, face_data["face_img"])
            
            # Add to results
            results["best_faces"].append({
                "person_id": face_data["person_id"],
                "quality_score": face_data["quality_score"],
                "frame_number": face_data["frame_number"],
                "timestamp": face_data["timestamp"],
                "face_location": face_data["face_location"],
                "position": face_data["position"],
                "filename": os.path.basename(best_face_filename)
            })
            
            # If this is an unidentified face, also add it to the unidentified_faces list
            if face_data["person_id"].startswith("Unknown_"):
                results["unidentified_faces"].append({
                    "id": str(i),  # Use the same number as the filename
                    "filename": os.path.basename(best_face_filename),
                    "quality_score": face_data["quality_score"],
                    "frame_number": face_data["frame_number"],
                    "timestamp": face_data["timestamp"]
                })
    
    # Save the results
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Processed {frame_count} frames, found {len(identified_speakers)} speakers, {len(unidentified_faces)} unidentified faces, and {len(results['best_faces'])} best faces")
    
    return {
        "success": True,
        "message": f"Processed {frame_count} frames, found {len(identified_speakers)} speakers, {len(unidentified_faces)} unidentified faces, and {len(results['best_faces'])} best faces",
        "speakers": list(identified_speakers.values()),
        "unidentified_faces": list(unidentified_faces.values()),
        "best_faces": results["best_faces"],
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
    parser.add_argument("--frame-skip", type=int, default=5, help="Process every Nth frame (default: 5)")
    parser.add_argument("--filter-mps", help="Filter MPs by category (e.g., 'commons' for House of Commons only)")
    parser.add_argument("--max-encodings", type=int, help="Maximum number of MP encodings to load (for testing with limited memory)")
    parser.add_argument("--detection-model", choices=["hog", "cnn"], default="hog", help="Face detection model to use: 'hog' (faster, less memory) or 'cnn' (more accurate, more memory)")
    
    
    args = parser.parse_args()
    
    # Process the video
    result = process_video(
        args.input,
        args.encodings,
        args.results,
        args.output,
        args.unidentified_dir,
        args.skip_frames,
        args.frame_skip,
        args.filter_mps,
        args.max_encodings,
        args.detection_model
    )
    
    if result["success"]:
        logger.info("Video processing completed successfully")
        sys.exit(0)
    else:
        logger.error(f"Video processing failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
