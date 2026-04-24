#!/usr/bin/env python3
"""
Simple Parliament Face Recognition Demo

This script processes existing Parliament video files for face recognition
and creates side-by-side comparisons with the MP face database.

Usage:
    python parliament_face_recognition_simple.py --video /path/to/video.mp4 --focus-last-seconds 60
"""

import os
import sys
import cv2
import numpy as np
import argparse
import logging
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Add the project root directory to Python path (so we can import backend)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Force disable test mode for this demo
os.environ["TEST_MODE"] = "false"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import backend modules
try:
    from backend.services.recognition.face_recognition import FaceRecognitionService
    from backend.services.recognition.facial_recognition import FacialRecognitionService
    from backend.db.session import SessionLocal
    from backend.db.models import FaceProfile
    logger.info("Successfully imported backend modules")
except ImportError as e:
    logger.error(f"Failed to import backend modules: {e}")
    logger.error("Make sure you're running from the project root directory")
    sys.exit(1)

class SimpleParliamentFaceRecognitionDemo:
    def __init__(self):
        """Initialize the demo with face recognition services."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="parliament_demo_"))
        self.output_dir = Path("/tmp/parliament_face_demo")
        
        # Create output directories
        self.faces_dir = self.output_dir / "faces"
        self.comparisons_dir = self.output_dir / "comparisons"
        self.data_dir = self.output_dir / "data"
        
        for dir_path in [self.output_dir, self.faces_dir, self.comparisons_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize face recognition services with local paths
        # Override the models directory to use local storage
        local_models_dir = self.temp_dir / "models" / "face_recognition"
        local_models_dir.mkdir(parents=True, exist_ok=True)
        
        # Override face recognition service initialization
        import backend.services.recognition.face_recognition as fr_module
        
        def local_init(self):
            # Use local models directory
            models_dir = str(local_models_dir)
            os.makedirs(models_dir, exist_ok=True)
            
            # Initialize face detector
            try:
                self.face_detector_model = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
                
                # Download the model if it doesn't exist
                if not os.path.exists(self.face_detector_model):
                    logger.info(f"Downloading face detector model to {self.face_detector_model}")
                    self._download_face_detector_model()
                
                self.face_detector = cv2.FaceDetectorYN.create(
                    self.face_detector_model,
                    "",
                    (320, 320),
                    0.3,  # Score threshold
                    0.3,  # NMS threshold
                    5000  # Top K
                )
                logger.info("Face detector initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing face detector: {str(e)}")
                self.face_detector = None
            
            # Initialize face recognizer
            try:
                self.face_recognizer_model = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")
                
                # Download the model if it doesn't exist
                if not os.path.exists(self.face_recognizer_model):
                    logger.info(f"Downloading face recognizer model to {self.face_recognizer_model}")
                    self._download_face_recognizer_model()
                
                self.face_recognizer = cv2.FaceRecognizerSF.create(
                    self.face_recognizer_model,
                    ""
                )
                logger.info("Face recognizer initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing face recognizer: {str(e)}")
                self.face_recognizer = None
        
        fr_module.FaceRecognitionService.__init__ = local_init
        
        self.face_service = FaceRecognitionService()
        
        # Load existing MP face profiles
        self.mp_faces = self.load_mp_faces()
        logger.info(f"Initialized demo with {len(self.mp_faces)} MP face profiles")
        logger.info(f"Output directory: {self.output_dir}")
    
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
    
    def extract_last_seconds(self, video_path, focus_seconds=60):
        """Extract last N seconds from video using FFmpeg."""
        try:
            # Get video duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            format_info = json.loads(result.stdout)
            duration = float(format_info['format']['duration'])
            
            # Calculate start time for last N seconds
            start_time = max(0, duration - focus_seconds)
            extract_duration = min(focus_seconds, duration)
            
            logger.info(f"Video duration: {duration:.2f}s, extracting from {start_time:.2f}s for {extract_duration:.2f}s")
            
            # Extract last N seconds
            output_path = self.temp_dir / f"last_{focus_seconds}s.mp4"
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-ss', str(start_time),
                '-t', str(extract_duration),
                '-c', 'copy',
                str(output_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Extracted last {focus_seconds}s to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error extracting last {focus_seconds}s: {e}")
            return None
    
    def process_video_faces(self, video_path):
        """Process video for face detection and recognition."""
        logger.info(f"Processing video for face recognition: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return []
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return []
        
        # Get video info
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        logger.info(f"Video info: {frame_count} frames, {fps:.2f} FPS, {duration:.2f} seconds")
        
        # Process every 3 seconds (consistent with Parliament system)
        frame_interval = int(3 * fps)
        detected_faces = []
        
        frame_number = 0
        face_count = 0
        
        while frame_number < frame_count:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame for face detection
            timestamp = frame_number / fps
            
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
        
        # Add padding
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
    
    def match_faces_with_mps(self, detected_faces):
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
            comparison_img = detected_img.copy()
            
            if match_result['found']:
                # Add MP information text
                mp_name = match_result['mp_name']
                similarity = match_result['similarity']
                text = f"MP: {mp_name} ({similarity:.3f})"
                color = (0, 255, 0)  # Green for found
            else:
                text = "NOT FOUND"
                color = (0, 0, 255)  # Red for not found
            
            # Add text overlay
            cv2.putText(comparison_img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(comparison_img, f"Time: {face_data['timestamp']:.1f}s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(comparison_img, f"Confidence: {face_data['confidence']:.3f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
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
        """Create comprehensive HTML report."""
        html_content = f"""
<!DOCTYPE html>
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
        .similarity {{ color: #4CAF50; font-weight: bold; }}
        .not-found {{ color: #f44336; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Parliament Face Recognition Demo</h1>
        <p>Processed Parliament TV video with face recognition and MP matching</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Configuration: TEST_MODE=disabled, Full video processing enabled</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{len(comparison_results)}</div>
            <div>Faces Detected</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{sum(1 for r in comparison_results if r['match_result']['found'])}</div>
            <div>MPs Identified</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{sum(1 for r in comparison_results if not r['match_result']['found'])}</div>
            <div>Unknown Faces</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(self.mp_faces)}</div>
            <div>MPs in Database</div>
        </div>
    </div>
    
    <h2>🔍 Face Recognition Results</h2>
"""
        
        for result in comparison_results:
            css_class = "found" if result['match_result']['found'] else "not-found"
            
            if result['match_result']['found']:
                match_info = f"""
                <p><span class="mp-name">{result['match_result']['mp_name']}</span></p>
                <p>Role: {result['match_result']['mp_role']}</p>
                <p>Party: {result['match_result']['mp_party']}</p>
                <p>Similarity: <span class="similarity">{result['match_result']['similarity']:.4f}</span></p>
"""
            else:
                match_info = "<p><span class='not-found'>No MP match found</span></p>"
            
            html_content += f"""
    <div class="comparison {css_class}">
        <div class="comparison-info">
            <h3>Face {result['face_id']} - <span class="timestamp">{result['timestamp']:.1f}s</span> - Confidence: {result['confidence']:.4f}</h3>
            {match_info}
        </div>
        <img src="{result['comparison_path']}" alt="Comparison {result['face_id']}" loading="lazy">
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
    
    def run_demo(self, video_path, focus_seconds=60):
        """Run the complete face recognition demo."""
        logger.info("Starting Simple Parliament Face Recognition Demo")
        logger.info(f"Configuration: Focus on last {focus_seconds}s of video")
        logger.info(f"TEST_MODE: {os.environ.get('TEST_MODE', 'not set')}")
        
        # Step 1: Extract last N seconds
        focus_video = self.extract_last_seconds(video_path, focus_seconds)
        if not focus_video:
            logger.error("Failed to extract focus segment")
            return False
        
        # Step 2: Process faces
        detected_faces = self.process_video_faces(focus_video)
        if not detected_faces:
            logger.warning("No faces detected in video")
            # Continue anyway to show the process worked
        
        # Step 3: Match with MP database
        matched_faces = self.match_faces_with_mps(detected_faces)
        
        # Step 4: Create comparisons
        comparison_results = self.create_side_by_side_comparisons(matched_faces)
        
        # Step 5: Create HTML report
        html_path = self.create_html_report(comparison_results)
        
        logger.info(f"✅ Demo completed successfully!")
        logger.info(f"📊 Results saved to: {self.output_dir}")
        logger.info(f"🌐 HTML report: {html_path}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Simple Parliament Face Recognition Demo")
    parser.add_argument("--video", required=True, help="Path to Parliament video file")
    parser.add_argument("--focus-last-seconds", type=int, default=60, help="Focus on last N seconds for face recognition")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"❌ Video file not found: {args.video}")
        return
    
    demo = SimpleParliamentFaceRecognitionDemo()
    success = demo.run_demo(
        video_path=args.video,
        focus_seconds=args.focus_last_seconds
    )
    
    if success:
        print(f"\n✅ Demo completed successfully!")
        print(f"📊 Results saved to: {demo.output_dir}")
        print(f"🌐 HTML report: {demo.output_dir / 'report.html'}")
        print(f"\n🔗 To view results, open the HTML report in your browser")
    else:
        print(f"\n❌ Demo failed!")

if __name__ == "__main__":
    main()
