#!/usr/bin/env python
"""
Visual debugging tool for parliament member face matching.

This tool:
1. Takes an input image containing faces
2. Runs face detection and recognition
3. Matches faces to parliament members
4. Creates a visual debug image with match results
"""
import os
import sys
import logging
import cv2
import numpy as np
import face_recognition
import json
import argparse
from pathlib import Path

# Add the app directory to the path
sys.path.append("/app")

# Import the matcher
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Visual debugging tool for parliament member face matching")
    parser.add_argument("--image", type=str, help="Path to the input image")
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for matching")
    parser.add_argument("--house", type=str, default="1", help="House ID to filter members (1=Commons, 2=Lords, None=All)")
    parser.add_argument("--output", type=str, default="/app/data/temp/recognition/debug", help="Output directory for debug images")
    return parser.parse_args()

def main():
    # Parse arguments
    args = parse_args()
    
    # Set default image path if not provided
    if args.image is None:
        args.image = "/app/data/temp/recognition/test_frame.jpg"
    
    # Check if the image exists
    if not os.path.exists(args.image):
        logger.error(f"Image not found at {args.image}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize the matcher
    logger.info("Initializing ParliamentMemberMatcher...")
    matcher = ParliamentMemberMatcher(None)
    
    # Load parliament members
    logger.info("Loading parliament members...")
    success = matcher.load_parliament_members()
    if not success:
        logger.error("Failed to load parliament members")
        return
    
    # Print information about members in the database
    logger.info(f"Total members in database: {len(matcher.member_embeddings)}")
    
    # Load the image
    logger.info(f"Loading image from {args.image}")
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"Failed to load image from {args.image}")
        return
    
    # Convert to RGB for face_recognition
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    logger.info("Detecting faces...")
    face_locations = face_recognition.face_locations(rgb_image)
    
    if not face_locations:
        logger.error("No faces detected in the image")
        return
    
    logger.info(f"Detected {len(face_locations)} faces")
    
    # Create a copy of the image for debugging
    debug_image = image.copy()
    
    # Process each face
    for i, (top, right, bottom, left) in enumerate(face_locations):
        logger.info(f"Processing face {i+1}...")
        
        # Extract face encoding
        face_encodings = face_recognition.face_encodings(rgb_image, [(top, right, bottom, left)])
        
        if not face_encodings:
            logger.error(f"Failed to extract encoding for face {i+1}")
            continue
        
        face_encoding = face_encodings[0]
        
        # Match face to member
        house_filter = None if args.house.lower() == "none" else args.house
        match_result = matcher.match_face_to_member(face_encoding, confidence_threshold=args.threshold, house=house_filter)
        
        # Draw bounding box
        if match_result.get('matched', False):
            # Green box for matched faces
            color = (0, 255, 0)
            member_id = match_result.get('member_id', 'Unknown')
            name = match_result.get('name', 'Unknown')
            confidence = match_result.get('confidence', 0.0)
            
            # Draw bounding box
            cv2.rectangle(debug_image, (left, top), (right, bottom), color, 2)
            
            # Draw match info
            text = f"{name} (ID: {member_id})"
            cv2.putText(debug_image, text, (left, top-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            text_conf = f"Confidence: {confidence:.4f}"
            cv2.putText(debug_image, text_conf, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            logger.info(f"Face {i+1}: Matched to {name} (ID: {member_id}) with confidence {confidence:.4f}")
        else:
            # Red box for unmatched faces
            color = (0, 0, 255)
            cv2.rectangle(debug_image, (left, top), (right, bottom), color, 2)
            cv2.putText(debug_image, "No match", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            logger.info(f"Face {i+1}: No match found")
    
    # Add info to the image
    info_img = np.zeros((200, debug_image.shape[1], 3), dtype=np.uint8)
    cv2.putText(info_img, "Visual Debugging Results", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(info_img, f"Confidence Threshold: {args.threshold}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    house_text = "Commons" if args.house == "1" else "Lords" if args.house == "2" else "All"
    cv2.putText(info_img, f"House Filter: {house_text}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    cv2.putText(info_img, f"Green box = Matched MP, Red = No match", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    # Combine the images
    combined_img = np.vstack([debug_image, info_img])
    
    # Save the debug image
    output_filename = os.path.basename(args.image).split('.')[0] + "_debug.jpg"
    output_path = os.path.join(args.output, output_filename)
    cv2.imwrite(output_path, combined_img)
    
    logger.info(f"Saved debug image to {output_path}")

if __name__ == "__main__":
    main()
