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
                    
                    # Match against MPs with tighter tolerance
                    matches = face_recognition.compare_faces([mp['encoding'] for mp in mp_data], encoding, tolerance=0.5)
                    
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
                                    
                                    # Get landmarks on original-sized crops
                                    face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)[i]
                                    mp_landmarks = face_recognition.face_landmarks(mp_rgb, mp_locations)[0]
                                    
                                    # Store original dimensions
                                    h1_orig, w1_orig = face_crop.shape[:2]
                                    h2_orig, w2_orig = mp_crop.shape[:2]
                                    
                                    # Use letterboxing to match height without stretching
                                    h1, w1 = face_crop.shape[:2]
                                    h2, w2 = mp_crop.shape[:2]
                                    target_height = max(h1, h2)
                                    
                                    # Calculate scale factors
                                    scale1 = target_height / h1 if h1 != target_height else 1
                                    scale2 = target_height / h2 if h2 != target_height else 1
                                    
                                    # Resize face_crop to target height
                                    if h1 != target_height:
                                        new_w1 = int(w1 * target_height / h1)
                                        face_crop_resized = cv2.resize(face_crop, (new_w1, target_height))
                                    else:
                                        face_crop_resized = face_crop.copy()
                                    
                                    # Resize mp_crop to target height
                                    if h2 != target_height:
                                        new_w2 = int(w2 * target_height / h2)
                                        mp_crop_resized = cv2.resize(mp_crop, (new_w2, target_height))
                                    else:
                                        mp_crop_resized = mp_crop.copy()
                                    
                                    # Save originals before drawing landmarks
                                    face_crop_original = face_crop_resized.copy()
                                    mp_crop_original = mp_crop_resized.copy()
                                    
                                    # Draw landmarks on face_crop (green) - scale coordinates
                                    for landmark_name, landmark_points in face_landmarks.items():
                                        for point in landmark_points:
                                            # Adjust for crop offset and scale
                                            x_scaled = int((point[0] - left) * scale1)
                                            y_scaled = int((point[1] - top) * scale1)
                                            if 0 <= x_scaled < face_crop_resized.shape[1] and 0 <= y_scaled < face_crop_resized.shape[0]:
                                                cv2.circle(face_crop_resized, (x_scaled, y_scaled), 6, (0, 255, 0), -1)
                                    
                                    # Draw landmarks on mp_crop (yellow) - scale coordinates
                                    for landmark_name, landmark_points in mp_landmarks.items():
                                        for point in landmark_points:
                                            # Adjust for crop offset and scale
                                            x_scaled = int((point[0] - mp_left) * scale2)
                                            y_scaled = int((point[1] - mp_top) * scale2)
                                            if 0 <= x_scaled < mp_crop_resized.shape[1] and 0 <= y_scaled < mp_crop_resized.shape[0]:
                                                cv2.circle(mp_crop_resized, (x_scaled, y_scaled), 6, (0, 255, 255), -1)
                                    
                                    # Create 4-image layout
                                    comparison = np.hstack([face_crop_resized, face_crop_original, mp_crop_resized, mp_crop_original])
                                    
                                    # Add labels
                                    cv2.putText(comparison, "VIDEO (dots)", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                                    cv2.putText(comparison, "VIDEO (orig)", (face_crop_resized.shape[1] + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                                    cv2.putText(comparison, "MP (dots)", (face_crop_resized.shape[1] * 2 + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                                    cv2.putText(comparison, "MP (orig)", (face_crop_resized.shape[1] * 3 + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                                    cv2.putText(comparison, f"{mp_name}", (5, comparison.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                                    
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
    
    return detected_faces, face_count

# Generate HTML report
def generate_html_report(detected_faces, total_faces, output_dir, mp_count):
    """Generate HTML report with comparison images."""
    report_path = output_dir / "report.html"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Parliament Face Recognition Demo Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ text-align: center; background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #0076C0; }}
        .comparison {{ background: white; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }}
        .comparison.found {{ border-left: 4px solid #4CAF50; }}
        .comparison.not-found {{ border-left: 4px solid #f44336; }}
        .comparison img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
        .comparison-info {{ padding: 15px; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .mp-name {{ font-weight: bold; color: #0076C0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Parliament Face Recognition Demo</h1>
        <p>Processed Parliament TV video with face recognition and MP matching</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Configuration: Using regenerated MP encodings (mp_encodings_new.json), Tighter tolerance (0.5)</p>
    </div>

    <div class="legend" style="background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h3>📍 Comparison Layout Legend</h3>
        <p><strong>Left to Right:</strong> Video face (with green dots) | Video face (original) | MP photo (with yellow dots) | MP photo (original)</p>
        <p><span style="color: green;">● Green dots</span> = Facial landmarks from video face (68 feature points)</p>
        <p><span style="color: #FFD700;">● Yellow dots</span> = Facial landmarks from MP reference photo (68 feature points)</p>
        <p>MP name is displayed at the bottom of each comparison.</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{total_faces}</div>
            <div>Faces Detected</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(detected_faces)}</div>
            <div>MPs Identified</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_faces - len(detected_faces)}</div>
            <div>Unknown Faces</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{mp_count}</div>
            <div>MPs in Database</div>
        </div>
    </div>
    
    <h2>🔍 Face Recognition Results - Side-by-Side Comparisons</h2>
    <p style="margin-left: 20px; color: #666;">Left side: Video face from Parliament TV | Right side: MP reference photo</p>
"""
    
    for i, face in enumerate(detected_faces, 1):
        html_content += f"""
    <div class="comparison found">
        <div class="comparison-info">
            <h3>Face {i} - <span class="timestamp">{face['timestamp']:.1f}s</span> - MP ID: {face['mp_id']}</h3>
            <p><span class='mp-name'>MP Match Found</span> - Offset: {face['horizontal_offset']:.3f}</p>
        </div>
        <img src="comparisons/comparison_{face['face_id']:03d}.jpg" alt="Comparison {i}" loading="lazy" style="max-width: 100%; height: auto;">
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    logger.info(f"✅ HTML report generated: {report_path}")
    return report_path

# Main
if __name__ == "__main__":
    import face_recognition
    
    video_path = "/tmp/parliament_last_30s.mp4"
    output_dir = Path("/tmp/parliament_face_demo")
    
    logger.info("Loading MP encodings...")
    mp_data = load_mp_encodings()
    mp_count = len(mp_data)
    
    logger.info("Processing video...")
    detected_faces, total_faces = process_video(video_path, mp_data, output_dir)
    
    logger.info(f"✅ Found {len(detected_faces)} MP matches")
    
    # Generate HTML report
    report_path = generate_html_report(detected_faces, total_faces, output_dir, mp_count)
    
    # Print matches and report path prominently
    if detected_faces:
        print("\n" + "="*60)
        print("🎯 PARLIAMENT FACE RECOGNITION RESULTS")
        print("="*60)
        print(f"\n✅ {len(detected_faces)} MP matches found out of {total_faces} total faces")
        print(f"\n📊 MP IDENTIFICATIONS:")
        for face in detected_faces:
            print(f"  - {face['mp_name']} at {face['timestamp']:.2f}s (offset: {face['horizontal_offset']:.3f})")
        print("\n" + "="*60)
        print(f"📁 HTML REPORT: {report_path}")
        print(f"📁 COMPARISON IMAGES: {output_dir}/comparisons/")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("❌ No MP matches found")
        print(f"📁 HTML REPORT: {report_path}")
        print("="*60 + "\n")
