#!/usr/bin/env python3
"""
Parliament Face Recognition Demo

Process 2 minutes of Parliament video, focus on last 60 seconds,
extract faces, match with existing MP face encodings, and create side-by-side comparisons.

Usage:
    python parliament_face_recognition_demo.py --video /path/to/parliament_video.mp4
"""

import os
import sys
import cv2
import numpy as np
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from backend.services.recognition.face_recognition import FaceRecognitionService
from backend.services.recognition.facial_recognition import FacialRecognitionService
from backend.db.session import SessionLocal
from backend.db.models import FaceProfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParliamentFaceRecognitionDemo:
    def __init__(self):
        """Initialize the demo with face recognition services."""
        self.face_service = FaceRecognitionService()
        self.facial_service = FacialRecognitionService()
        
        # Create output directories
        self.output_dir = Path("/tmp/parliament_face_demo")
        self.faces_dir = self.output_dir / "faces"
        self.comparisons_dir = self.output_dir / "comparisons"
        self.data_dir = self.output_dir / "data"
        
        for dir_path in [self.output_dir, self.faces_dir, self.comparisons_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing MP face profiles
        self.mp_faces = self.load_mp_faces()
        logger.info(f"Loaded {len(self.mp_faces)} MP face profiles")
    
    def load_mp_faces(self):
        """Load existing MP face profiles from database."""
        try:
            session = SessionLocal()
            face_profiles = session.query(FaceProfile).all()
            
            mp_faces = []
            for profile in face_profiles:
                if profile.face_encoding:
                    mp_faces.append({
                        'id': profile.id,
                        'name': profile.name,
                        'role': profile.role,
                        'party': profile.party,
                        'face_encoding': json.loads(profile.face_encoding) if isinstance(profile.face_encoding, str) else profile.face_encoding,
                        'face_image_path': profile.face_image_path,
                        'confidence_score': profile.confidence_score
                    })
            
            session.close()
            return mp_faces
            
        except Exception as e:
            logger.error(f"Error loading MP faces: {e}")
            return []
    
    def process_video(self, video_path):
        """Process video and extract faces from last 60 seconds."""
        logger.info(f"Processing video: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return False
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return False
        
        # Get video info
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        logger.info(f"Video info: {frame_count} frames, {fps:.2f} FPS, {duration:.2f} seconds")
        
        # Focus on last 60 seconds
        start_frame = max(0, frame_count - int(60 * fps))
        logger.info(f"Processing frames {start_frame} to {frame_count} (last 60 seconds)")
        
        # Process every 3 seconds (1 FPS for 30fps video)
        frame_interval = int(3 * fps)
        detected_faces = []
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        frame_number = start_frame
        face_count = 0
        
        while frame_number < frame_count:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame for face detection
            timestamp = frame_number / fps
            logger.info(f"Processing frame {frame_number} at {timestamp:.2f}s")
            
            # Detect faces in frame
            face_results = self.face_service.process_video_frame(frame)
            
            if face_results:
                logger.info(f"Found {len(face_results)} faces at timestamp {timestamp:.2f}s")
                
                for i, face_result in enumerate(face_results):
                    face_count += 1
                    face_data = {
                        'frame_number': frame_number,
                        'timestamp': timestamp,
                        'face_id': face_count,
                        'box': face_result['box'],
                        'confidence': face_result['confidence'],
                        'embedding': face_result.get('embedding', []),
                        'landmarks': face_result.get('landmarks', [])
                    }
                    
                    # Save face image
                    face_image_path = self.save_face_image(frame, face_result, face_count, timestamp)
                    face_data['image_path'] = str(face_image_path)
                    
                    detected_faces.append(face_data)
            
            # Skip to next frame (3 seconds later)
            frame_number += frame_interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        cap.release()
        logger.info(f"Processed video: {len(detected_faces)} faces detected")
        
        # Save detected faces data
        faces_data_path = self.data_dir / "detected_faces.json"
        with open(faces_data_path, 'w') as f:
            json.dump(detected_faces, f, indent=2)
        
        return detected_faces
    
    def save_face_image(self, frame, face_result, face_id, timestamp):
        """Save detected face image."""
        x, y, w, h = face_result['box']
        face_image = frame[y:y+h, x:x+w]
        
        # Add some padding
        padding = 20
        y_padded = max(0, y - padding)
        x_padded = max(0, x - padding)
        h_padded = min(frame.shape[0] - y_padded, h + 2 * padding)
        w_padded = min(frame.shape[1] - x_padded, w + 2 * padding)
        
        face_image_padded = frame[y_padded:y_padded+h_padded, x_padded:x_padded+w_padded]
        
        # Save face image
        face_filename = f"face_{face_id:03d}_t{timestamp:.1f}s.jpg"
        face_path = self.faces_dir / face_filename
        cv2.imwrite(str(face_path), face_image_padded)
        
        return face_path
    
    def match_faces(self, detected_faces):
        """Match detected faces with existing MP face encodings."""
        logger.info(f"Matching {len(detected_faces)} detected faces with {len(self.mp_faces)} MP faces")
        
        matched_faces = []
        
        for detected_face in detected_faces:
            if not detected_face.get('embedding'):
                detected_face['match_result'] = {
                    'found': False,
                    'reason': 'No embedding available'
                }
                matched_faces.append(detected_face)
                continue
            
            detected_embedding = np.array(detected_face['embedding'])
            best_match = None
            best_similarity = 0.0
            
            # Compare with each MP face
            for mp_face in self.mp_faces:
                if not mp_face.get('face_encoding'):
                    continue
                
                mp_embedding = np.array(mp_face['face_encoding'])
                
                # Calculate cosine similarity
                similarity = np.dot(detected_embedding, mp_embedding) / (
                    np.linalg.norm(detected_embedding) * np.linalg.norm(mp_embedding)
                )
                
                if similarity > best_similarity and similarity > 0.5:  # Threshold
                    best_similarity = similarity
                    best_match = mp_face
            
            if best_match:
                detected_face['match_result'] = {
                    'found': True,
                    'mp_name': best_match['name'],
                    'mp_role': best_match['role'],
                    'mp_party': best_match['party'],
                    'similarity': best_similarity,
                    'mp_image_path': best_match['face_image_path']
                }
                logger.info(f"Face {detected_face['face_id']} matched with {best_match['name']} (similarity: {best_similarity:.4f})")
            else:
                detected_face['match_result'] = {
                    'found': False,
                    'reason': 'No match above threshold'
                }
                logger.info(f"Face {detected_face['face_id']} no match found")
            
            matched_faces.append(detected_face)
        
        # Save matched faces data
        matched_data_path = self.data_dir / "matched_faces.json"
        with open(matched_data_path, 'w') as f:
            json.dump(matched_faces, f, indent=2)
        
        return matched_faces
    
    def create_side_by_side_comparisons(self, matched_faces):
        """Create side-by-side comparison images."""
        logger.info(f"Creating {len(matched_faces)} side-by-side comparisons")
        
        comparison_results = []
        
        for face_data in matched_faces:
            face_id = face_data['face_id']
            detected_face_path = face_data['image_path']
            match_result = face_data['match_result']
            
            # Load detected face image
            detected_img = cv2.imread(str(detected_face_path))
            if detected_img is None:
                logger.error(f"Cannot load detected face image: {detected_face_path}")
                continue
            
            # Create comparison image
            if match_result['found']:
                # Load MP image
                mp_image_path = match_result.get('mp_image_path')
                if mp_image_path and os.path.exists(mp_image_path):
                    mp_img = cv2.imread(mp_image_path)
                    if mp_img is not None:
                        # Resize both images to same height
                        target_height = 200
                        detected_resized = cv2.resize(detected_img, (int(detected_img.shape[1] * target_height / detected_img.shape[0]), target_height))
                        mp_resized = cv2.resize(mp_img, (int(mp_img.shape[1] * target_height / mp_img.shape[0]), target_height))
                        
                        # Create side-by-side image
                        comparison_img = np.hstack([detected_resized, mp_resized])
                        
                        # Add text overlay
                        cv2.putText(comparison_img, f"Detected Face", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(comparison_img, f"MP: {match_result['mp_name']}", (detected_resized.shape[1] + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(comparison_img, f"Score: {match_result['similarity']:.3f}", (detected_resized.shape[1] + 10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(comparison_img, f"Time: {face_data['timestamp']:.1f}s", (detected_resized.shape[1] + 10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    else:
                        comparison_img = detected_img
                        cv2.putText(comparison_img, f"MP Image Not Found", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    comparison_img = detected_img
                    cv2.putText(comparison_img, f"MP Image Not Available", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                comparison_img = detected_img
                cv2.putText(comparison_img, "NOT FOUND", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(comparison_img, f"Time: {face_data['timestamp']:.1f}s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Save comparison image
            comparison_filename = f"comparison_{face_id:03d}.jpg"
            comparison_path = self.comparisons_dir / comparison_filename
            cv2.imwrite(str(comparison_path), comparison_img)
            
            comparison_results.append({
                'face_id': face_id,
                'comparison_path': str(comparison_path),
                'timestamp': face_data['timestamp'],
                'confidence': face_data['confidence'],
                'match_result': match_result
            })
        
        # Save comparison results
        comparison_data_path = self.data_dir / "comparison_results.json"
        with open(comparison_data_path, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        return comparison_results
    
    def create_html_report(self, comparison_results):
        """Create HTML report with all comparisons."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Parliament Face Recognition Demo Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .comparison {{ margin: 20px 0; border: 1px solid #ccc; padding: 15px; }}
        .comparison img {{ max-width: 100%; height: auto; }}
        .found {{ border-color: #4CAF50; }}
        .not-found {{ border-color: #f44336; }}
        .stats {{ background: #f0f0f0; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Parliament Face Recognition Demo</h1>
        <p>Processed 2-minute Parliament video (last 60 seconds focus)</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <h2>Statistics</h2>
        <p>Total faces detected: {len(comparison_results)}</p>
        <p>Faces matched with MPs: {sum(1 for r in comparison_results if r['match_result']['found'])}</p>
        <p>Faces not found: {sum(1 for r in comparison_results if not r['match_result']['found'])}</p>
    </div>
    
    <h2>Face Recognition Results</h2>
"""
        
        for result in comparison_results:
            css_class = "found" if result['match_result']['found'] else "not-found"
            
            if result['match_result']['found']:
                match_info = f"""
                <p><strong>MP:</strong> {result['match_result']['mp_name']}</p>
                <p><strong>Role:</strong> {result['match_result']['mp_role']}</p>
                <p><strong>Party:</strong> {result['match_result']['mp_party']}</p>
                <p><strong>Similarity:</strong> {result['match_result']['similarity']:.4f}</p>
"""
            else:
                match_info = "<p><strong>Status:</strong> No MP match found</p>"
            
            html_content += f"""
    <div class="comparison {css_class}">
        <h3>Face {result['face_id']} - Time: {result['timestamp']:.1f}s - Confidence: {result['confidence']:.4f}</h3>
        <img src="{result['comparison_path']}" alt="Comparison {result['face_id']}">
        {match_info}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Save HTML report
        html_path = self.output_dir / "report.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report created: {html_path}")
        return html_path
    
    def run_demo(self, video_path):
        """Run the complete face recognition demo."""
        logger.info("Starting Parliament Face Recognition Demo")
        
        # Step 1: Process video and extract faces
        detected_faces = self.process_video(video_path)
        if not detected_faces:
            logger.error("No faces detected in video")
            return False
        
        # Step 2: Match faces with MP database
        matched_faces = self.match_faces(detected_faces)
        
        # Step 3: Create side-by-side comparisons
        comparison_results = self.create_side_by_side_comparisons(matched_faces)
        
        # Step 4: Create HTML report
        html_path = self.create_html_report(comparison_results)
        
        logger.info(f"Demo completed successfully!")
        logger.info(f"Results saved to: {self.output_dir}")
        logger.info(f"HTML report: {html_path}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Parliament Face Recognition Demo")
    parser.add_argument("--video", required=True, help="Path to Parliament video file")
    
    args = parser.parse_args()
    
    demo = ParliamentFaceRecognitionDemo()
    success = demo.run_demo(args.video)
    
    if success:
        print(f"\n✅ Demo completed successfully!")
        print(f"📊 Results saved to: {demo.output_dir}")
        print(f"🌐 HTML report: {demo.output_dir / 'report.html'}")
    else:
        print(f"\n❌ Demo failed!")

if __name__ == "__main__":
    main()
