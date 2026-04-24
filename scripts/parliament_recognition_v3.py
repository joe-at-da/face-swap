#!/usr/bin/env python3
"""
Parliament Face Recognition Demo v3 - Using face_recognition library
to match against existing MP encodings.
"""

import os
import sys
import cv2
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load MP encodings
def load_mp_encodings():
    """Load MP encodings from JSON file."""
    encodings_file = Path("data/mp_encodings_new.json")
    with open(encodings_file, 'r') as f:
        data = json.load(f)
    
    ids = data['ids']
    names = data['names']
    encodings = data['encodings']
    
    mp_data = []
    for i in range(len(ids)):
        mp_data.append({
            'id': ids[i],
            'name': names[i],
            'encoding': np.array(encodings[i])
        })
    
    logger.info(f"Loaded {len(mp_data)} MP encodings from {encodings_file}")
    return mp_data

# Process video
def process_video(video_path, mp_data, output_dir):
    """Process video for face recognition."""
    cap = cv2.VideoCapture(str(video_path))
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    logger.info(f"Video: {frame_count} frames, {fps:.2f} FPS, {frame_width}x{frame_height}")
    
    # Create output directories
    comparisons_dir = output_dir / "comparisons"
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    
    # Advanced filtering criteria
    MIN_FACE_SIZE = 200
    MIN_FACE_AREA = 40000
    MAX_HORIZONTAL_OFFSET = 0.4
    
    # Process every 3 seconds
    frame_interval = int(3 * fps)
    detected_faces = []
    
    frame_number = 0
    face_count = 0
    filtered_count = 0
    
    while frame_number < frame_count:
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_number / fps
        
        # Convert to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        if face_encodings:
            logger.info(f"Found {len(face_encodings)} faces at {timestamp:.2f}s")
            
            for i, encoding in enumerate(face_encodings):
                face_count += 1
                
                # Apply advanced filtering
                top, right, bottom, left = face_locations[i]
                w = right - left
                h = bottom - top
                face_area = w * h
                face_center_x = left + w / 2
                horizontal_offset = abs(face_center_x - frame_width / 2) / (frame_width / 2)
                
                passes_filter = True
                if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                    passes_filter = False
                if face_area < MIN_FACE_AREA:
                    passes_filter = False
                if horizontal_offset > MAX_HORIZONTAL_OFFSET:
                    passes_filter = False
                
                if passes_filter:
                    filtered_count += 1
                    
                    # Match against MPs
                    matches = face_recognition.compare_faces([mp['encoding'] for mp in mp_data], encoding, tolerance=0.6)
                    
                    if True in matches:
                        match_index = matches.index(True)
                        mp_id = mp_data[match_index]['id']
                        mp_name = mp_data[match_index]['name']
                        logger.info(f"Face {filtered_count} matched: {mp_name} (offset: {horizontal_offset:.3f})")
                        
                        # Save cropped face from video
                        face_crop = frame[top:bottom, left:right]
                        face_crop_path = comparisons_dir / f"face_{filtered_count:03d}_video.jpg"
                        cv2.imwrite(str(face_crop_path), face_crop)
                        
                        # Load MP reference photo
                        mp_photo_path = Path("data/mp_photos") / f"{mp_id}.jpg"
                        if mp_photo_path.exists():
                            mp_photo = cv2.imread(str(mp_photo_path))
                            if mp_photo is not None:
                                # Detect face in MP photo and crop
                                mp_rgb = cv2.cvtColor(mp_photo, cv2.COLOR_BGR2RGB)
                                mp_locations = face_recognition.face_locations(mp_rgb, model="hog")
                                if mp_locations:
                                    mp_top, mp_right, mp_bottom, mp_left = mp_locations[0]
                                    mp_crop = mp_photo[mp_top:mp_bottom, mp_left:mp_right]
                                    mp_crop_path = comparisons_dir / f"face_{filtered_count:03d}_mp.jpg"
                                    cv2.imwrite(str(mp_crop_path), mp_crop)
                                    
                                    # Resize to match height for side-by-side comparison
                                    h1, w1 = face_crop.shape[:2]
                                    h2, w2 = mp_crop.shape[:2]
                                    if h1 != h2:
                                        # Resize mp_crop to match face_crop height
                                        new_w2 = int(w2 * h1 / h2)
                                        mp_crop = cv2.resize(mp_crop, (new_w2, h1))
                                    
                                    # Create side-by-side comparison
                                    comparison = np.hstack([face_crop, mp_crop])
                                    comparison_path = comparisons_dir / f"comparison_{filtered_count:03d}.jpg"
                                    cv2.imwrite(str(comparison_path), comparison)
                        
                        detected_faces.append({
                            'frame_number': frame_number,
                            'timestamp': timestamp,
                            'face_id': filtered_count,
                            'mp_name': mp_name,
                            'mp_id': mp_id,
                            'location': face_locations[i],
                            'horizontal_offset': horizontal_offset
                        })
                    else:
                        logger.info(f"Face {filtered_count} no match (offset: {horizontal_offset:.3f})")
        
        frame_number += frame_interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    cap.release()
    logger.info(f"Processed: {face_count} total faces, {filtered_count} passed filter, {len(detected_faces)} matched")
    
    return detected_faces

# Main
if __name__ == "__main__":
    import face_recognition
    
    video_path = "/tmp/parliament_last_30s.mp4"
    output_dir = Path("/tmp/parliament_face_demo")
    
    logger.info("Loading MP encodings...")
    mp_data = load_mp_encodings()
    
    logger.info("Processing video...")
    detected_faces = process_video(video_path, mp_data, output_dir)
    
    logger.info(f"✅ Found {len(detected_faces)} MP matches")
    
    # Print matches
    if detected_faces:
        print("\n=== MP IDENTIFICATIONS ===")
        for face in detected_faces:
            print(f"  - {face['mp_name']} at {face['timestamp']:.2f}s (center offset: {face['horizontal_offset']:.3f})")
        print(f"\n📁 Comparisons saved to: {output_dir}/comparisons/")
    else:
        print("\n❌ No MP matches found")
