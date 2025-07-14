#!/usr/bin/env python3
"""
Script to identify the MP in frame from any capture at a specified timestamp by comparing face embeddings
with parliament member embeddings using the ParliamentMemberMatcher class.

This script incorporates the recent improvements to the embedding matching logic:
1. Consistent normalization using the normalize_embedding utility function
2. Proper handling of embedding types (list vs numpy array)
3. Enhanced validation for embedding norms and invalid values
4. Improved matching logic with better confidence thresholding
"""

import os
import sys
import cv2
import logging
import argparse
import face_recognition
import numpy as np

# Add the backend directory to the path so we can import from it
sys.path.append('/app')

# Import the ParliamentMemberMatcher class and utility functions
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher
from backend.services.recognition.member_matching.embedding import normalize_embedding
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def identify_mp_in_frame(image_path, output_path, confidence_threshold=0.4):
    """Identify the MP in the frame using ParliamentMemberMatcher."""
    logger.info(f"Identifying MP in {image_path}")
    
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Failed to read image from {image_path}")
        return False
    
    # Convert to RGB for face_recognition
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    face_locations = face_recognition.face_locations(rgb_image)
    logger.info(f"Detected {len(face_locations)} faces")
    
    # Extract face embeddings
    face_embeddings = face_recognition.face_encodings(rgb_image, face_locations)
    logger.info(f"Extracted {len(face_embeddings)} face embeddings")
    
    # Initialize the ParliamentMemberMatcher
    # Create a mock supabase service since we don't need actual Supabase functionality
    class MockSupabaseService:
        def __init__(self):
            pass
        
        def get_parliament_members(self):
            return []
    
    # Initialize the matcher with the mock service
    matcher = ParliamentMemberMatcher(MockSupabaseService())
    
    # Set debug mode
    matcher.debug_mode = True
    
    # Load member embeddings from the consolidated JSON file
    try:
        mp_encodings_file = "/app/data/mp_encodings.json"
        logger.info(f"Loading member embeddings from {mp_encodings_file}")
        
        with open(mp_encodings_file, 'r') as f:
            mp_encodings = json.load(f)
            
        # Check if the file has the expected structure
        if 'ids' in mp_encodings and 'encodings' in mp_encodings and 'names' in mp_encodings:
            member_ids = mp_encodings['ids']
            encodings = mp_encodings['encodings']
            names = mp_encodings['names']
            
            logger.info(f"Loaded data for {len(member_ids)} members from JSON file")
            
            # Create a dictionary of member names for display
            member_names = {}
            for i, member_id in enumerate(member_ids):
                if i < len(names):
                    member_names[str(member_id)] = names[i]
                else:
                    member_names[str(member_id)] = f"Unknown MP {member_id}"
            
            # Add member names to the matcher for display
            matcher.members = []
            for i, member_id in enumerate(member_ids):
                if i < len(names):
                    matcher.members.append({
                        'id': str(member_id),
                        'member_id': str(member_id),
                        'name': names[i]
                    })
            
            # Process each member's embedding
            valid_count = 0
            for i, member_id in enumerate(member_ids):
                if i < len(encodings):
                    embedding = encodings[i]
                    
                    # Skip if embedding is None or empty
                    if embedding is None or len(embedding) == 0:
                        continue
                    
                    # Convert to numpy array and ensure it's the right shape
                    embedding_array = np.array(embedding)
                    
                    # Check if the shape is correct (should be 128 elements)
                    if embedding_array.shape == (128,):
                        matcher.member_embeddings[str(member_id)] = embedding_array
                        valid_count += 1
                    else:
                        logger.warning(f"Skipping embedding for member {member_id} with invalid shape: {embedding_array.shape}")
            
            logger.info(f"Added {valid_count} valid member embeddings to matcher")
        else:
            logger.error("MP encodings file has unexpected structure")
    except Exception as e:
        logger.error(f"Error loading member embeddings: {str(e)}")
    
    # Create debug image
    debug_image = image.copy()
    
    # Process each face
    for i, (face_location, face_embedding) in enumerate(zip(face_locations, face_embeddings)):
        top, right, bottom, left = face_location
        
        # Match the face to a member using the matcher
        # Use a lower confidence threshold for testing
        match_result = matcher._match_face_to_member(
            face_embedding=face_embedding.tolist(),
            confidence_threshold=confidence_threshold
            # The method doesn't accept debug_matching parameter
        )
        
        # Log the match result
        logger.info(f"Match result for Face {i+1}: {match_result}")
        
        # Draw rectangle around face
        cv2.rectangle(debug_image, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Add match info
        if match_result and match_result.get('name') != 'Unidentified':
            name = match_result.get('name', 'Unknown')
            confidence = match_result.get('confidence', 0.0)
            has_warning = match_result.get('confidence_gap_warning', False)
            
            if confidence >= confidence_threshold:
                if has_warning:
                    text = f"{name}: {confidence:.2f} (WARNING: similar matches)"
                    color = (0, 165, 255)  # Orange for warning
                else:
                    text = f"{name}: {confidence:.2f}"
                    color = (0, 255, 0)  # Green for passing match
            else:
                text = f"{name}: {confidence:.2f} (below threshold)"
                color = (0, 165, 255)  # Orange for below threshold
        else:
            text = "Unidentified"
            color = (0, 0, 255)  # Red for no match
        
        cv2.putText(
            debug_image,
            text,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )
    
    # Save debug image
    cv2.imwrite(output_path, debug_image)
    logger.info(f"Saved debug image to {output_path}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Identify MP in frame from a capture at a specific timestamp")
    parser.add_argument("--capture-id", required=True, help="Capture ID")
    parser.add_argument("--timestamp", required=True, help="Timestamp in seconds")
    parser.add_argument("--threshold", type=float, default=0.4, help="Confidence threshold (0.0-1.0)")
    parser.add_argument("--image", help="Path to the image file (optional, will be generated if not provided)")
    parser.add_argument("--output", help="Output path for the debug image (optional, will be generated if not provided)")
    
    args = parser.parse_args()
    
    # Generate default image and output paths if not provided
    if not args.image:
        args.image = f"/tmp/frame_{args.capture_id}_{args.timestamp}s.jpg"
    
    if not args.output:
        args.output = f"/tmp/frame_{args.capture_id}_{args.timestamp}s_identified.jpg"
    
    # Check if the image exists, if not, extract it from the video
    if not os.path.exists(args.image):
        logger.info(f"Image {args.image} not found, extracting from video")
        
        # Construct video path
        video_path = f"/app/data/media/{args.capture_id}.mp4"
        
        # Check if video exists
        if os.path.exists(video_path):
            try:
                # Open the video
                cap = cv2.VideoCapture(video_path)
                
                # Convert timestamp to frame number
                timestamp = int(args.timestamp)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_number = int(timestamp * fps)
                
                # Set the frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                # Read the frame
                ret, frame = cap.read()
                
                # Release the video
                cap.release()
                
                # Check if frame was read successfully
                if ret:
                    # Save the frame
                    cv2.imwrite(args.image, frame)
                    logger.info(f"Extracted frame at {timestamp}s from {video_path} and saved to {args.image}")
                else:
                    logger.error(f"Failed to extract frame at {timestamp}s from {video_path}")
                    return False
            except Exception as e:
                logger.error(f"Error extracting frame from video: {e}")
                return False
        else:
            logger.error(f"Video file {video_path} not found")
            return False
    
    logger.info("Starting MP identification")
    logger.info(f"Image: {args.image}")
    logger.info(f"Output path: {args.output}")
    logger.info(f"Confidence threshold: {args.threshold}")
    
    success = identify_mp_in_frame(args.image, args.output, confidence_threshold=args.threshold)
    
    if success:
        logger.info(f"✅ MP identification completed successfully")
        logger.info(f"Debug image saved to: {args.output}")
    else:
        logger.error(f"❌ MP identification failed")

if __name__ == "__main__":
    main()
