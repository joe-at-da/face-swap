#!/usr/bin/env python3
"""
Comprehensive Parliament TV Face Swap Demonstration

This script provides a detailed demonstration of the complete face swapping pipeline:
1. Face detection with visualization
2. Face recognition with confidence scores and MP matching
3. Target MP information display
4. Face swapping with before/after comparison
5. Technical methodology explanation

Usage:
    python comprehensive_face_swap_demo.py --video-path "/app/data/temp/test_combined.mp4" --target-member-id "115"
"""

import os
import sys
import argparse
import logging
import json
import requests
import subprocess
import tempfile
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("comprehensive_demo")

class ComprehensiveFaceSwapDemo:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="comprehensive_demo_"))
        logger.info(f"Initialized demo with temp directory: {self.temp_dir}")
        
    def get_auth_token(self, username="admin@example.com", password="password"):
        """Get authentication token for API calls."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
        except Exception as e:
            logger.error(f"Failed to get auth token: {str(e)}")
            return None
    
    def get_mp_info(self, member_id: str, token: str) -> Dict[str, Any]:
        """Get MP information from the database."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/api/v1/face-swap/targets",
                headers=headers
            )
            response.raise_for_status()
            
            targets = response.json()
            for target in targets:
                if target.get("member_id") == member_id:
                    return target
            
            return {}
        except Exception as e:
            logger.error(f"Failed to get MP info: {str(e)}")
            return {}
    
    def extract_frame_with_detection(self, video_path: str, timestamp: int = 5) -> str:
        """Extract a frame and perform face detection with visualization."""
        try:
            output_path = self.temp_dir / f"frame_{timestamp}s.jpg"
            
            # Extract frame using ffmpeg
            cmd = [
                "ffmpeg", "-i", str(video_path), 
                "-ss", str(timestamp), 
                "-vframes", str(1), 
                "-q:v", str(2),
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to extract frame: {result.stderr}")
                return None
            
            # Load image and detect faces
            image = cv2.imread(str(output_path))
            if image is None:
                logger.error("Failed to load extracted frame")
                return None
            
            # Use OpenCV for face detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Draw face detection boxes
            annotated_image = image.copy()
            for i, (x, y, w, h) in enumerate(faces):
                # Draw rectangle around face
                cv2.rectangle(annotated_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Add face number label
                cv2.putText(annotated_image, f"Face {i+1}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Save annotated image
            annotated_path = self.temp_dir / f"frame_{timestamp}s_annotated.jpg"
            cv2.imwrite(str(annotated_path), annotated_image)
            
            logger.info(f"Extracted and annotated frame with {len(faces)} faces detected")
            return str(annotated_path)
            
        except Exception as e:
            logger.error(f"Error in frame extraction and detection: {str(e)}")
            return None
    
    def perform_face_recognition_analysis(self, video_path: str, token: str) -> Dict[str, Any]:
        """Perform face recognition and analyze results."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            data = {
                "video_path": video_path,
                "output_format": "json"
            }
            
            # Use the existing face recognition endpoint
            response = requests.post(
                f"{self.base_url}/api/v1/facial-recognition/test",
                json=data,
                headers=headers
            )
            
            if response.status_code == 404:
                # Try alternative endpoint
                response = requests.post(
                    f"{self.base_url}/api/v1/facial-recognition/recognize",
                    json=data,
                    headers=headers
                )
            
            response.raise_for_status()
            recognition_data = response.json()
            
            # Analyze and format the results
            analysis = {
                "total_faces_detected": len(recognition_data.get("faces", [])),
                "identified_speakers": recognition_data.get("identified_speakers", {}),
                "unidentified_faces": recognition_data.get("unidentified_faces", []),
                "face_details": []
            }
            
            # Process each detected face
            for face in recognition_data.get("faces", []):
                face_detail = {
                    "face_id": face.get("face_id"),
                    "timestamp": face.get("timestamp"),
                    "location": face.get("face_location"),
                    "size": f"{face.get('face_width', 0)}x{face.get('face_height', 0)}",
                    "quality_score": face.get("quality_score", 0),
                    "sharpness": face.get("sharpness", 0),
                    "eyes_open_score": face.get("eyes_open_score", 0)
                }
                analysis["face_details"].append(face_detail)
            
            logger.info(f"Face recognition analysis: {analysis['total_faces_detected']} faces detected")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to perform face recognition analysis: {str(e)}")
            return {"error": str(e), "total_faces_detected": 0}
    
    def perform_face_swap_with_analysis(self, image_path: str, target_member_id: str, token: str) -> Dict[str, Any]:
        """Perform face swapping with detailed analysis."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Copy image to accessible location
            import shutil
            temp_image_path = f"/tmp/demo_face_{target_member_id}.jpg"
            shutil.copy2(image_path, temp_image_path)
            
            with open(temp_image_path, 'rb') as image_file:
                files = {
                    'image': (os.path.basename(temp_image_path), image_file, 'image/jpeg'),
                    'target_member_id': (None, target_member_id),
                    'blend_factor': (None, '0.7')
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/face-swap/image",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                swap_data = response.json()
                
                # Copy the result to our temp directory
                output_path = self.temp_dir / f"face_swapped_{target_member_id}.jpg"
                try:
                    shutil.copy2(swap_data['output_path'], output_path)
                except:
                    # Fallback to HTTP download
                    swap_response = requests.get(
                        f"{self.base_url}/api/v1/face-swap/image{swap_data['output_path']}",
                        headers=headers
                    )
                    swap_response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(swap_response.content)
                
                # Clean up
                try:
                    os.unlink(temp_image_path)
                except:
                    pass
                
                analysis = {
                    "success": True,
                    "faces_detected": swap_data.get("faces_detected", 0),
                    "faces_swapped": swap_data.get("faces_swapped", 0),
                    "target_member_id": target_member_id,
                    "output_path": str(output_path),
                    "blend_factor": 0.7,
                    "message": swap_data.get("message", "")
                }
                
                logger.info(f"Face swap completed: {analysis['faces_swapped']} faces swapped")
                return analysis
                
        except Exception as e:
            logger.error(f"Failed to perform face swap: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_before_after_comparison(self, original_path: str, swapped_path: str) -> str:
        """Create a side-by-side before/after comparison image."""
        try:
            # Load images
            original = cv2.imread(original_path)
            swapped = cv2.imread(swapped_path)
            
            if original is None or swapped is None:
                logger.error("Failed to load images for comparison")
                return None
            
            # Ensure images have the same height
            height = max(original.shape[0], swapped.shape[0])
            original = cv2.resize(original, (int(original.shape[1] * height / original.shape[0]), height))
            swapped = cv2.resize(swapped, (int(swapped.shape[1] * height / swapped.shape[0]), height))
            
            # Create side-by-side comparison
            comparison = np.hstack([original, swapped])
            
            # Add labels
            cv2.putText(comparison, "BEFORE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(comparison, "AFTER", (original.shape[1] + 20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            # Save comparison
            comparison_path = self.temp_dir / "before_after_comparison.jpg"
            cv2.imwrite(str(comparison_path), comparison)
            
            logger.info(f"Created before/after comparison: {comparison_path}")
            return str(comparison_path)
            
        except Exception as e:
            logger.error(f"Error creating comparison: {str(e)}")
            return None
    
    def generate_technical_explanation(self) -> str:
        """Generate technical methodology explanation."""
        explanation = """
# Face Swapping Technical Methodology

## Current System: OpenCV-Based Approach

### Face Detection
- **Method**: OpenCV Haar Cascade Classifier
- **File**: haarcascade_frontalface_default.xml
- **Advantages**: Fast, lightweight, works in Docker
- **Limitations**: Less accurate than deep learning methods

### Face Recognition
- **Method**: Face recognition library with 128-dimensional embeddings
- **Database**: 1318 MPs with pre-computed face encodings
- **Matching**: Euclidean distance comparison
- **Confidence**: Based on distance threshold (typically < 0.6)

### Face Swapping Process
1. **Face Detection**: Locate faces in source image
2. **Face Extraction**: Extract face regions with padding
3. **Target Loading**: Load target MP face from database
4. **Resizing**: Match target face size to source face
5. **Mask Creation**: Create circular mask for blending
6. **Blending**: Use weighted blending with mask
7. **Replacement**: Place blended face back into image

### Blending Algorithm
- **Method**: cv2.addWeighted() with Gaussian mask
- **Blend Factor**: 0.7 (70% target face, 30% original)
- **Mask**: Circular gradient for smooth edges
- **Result**: Seamless face replacement

## Limitations vs AI Alternatives

### Current Limitations
- No 3D face reconstruction
- Limited pose and lighting adaptation
- Basic blending (no advanced texture synthesis)
- No expression preservation

### AI Alternatives (Not Used)
- **DeepFakes**: Neural network-based face synthesis
- **FaceFusion**: Advanced deep learning face swapping
- **GANs**: Generative adversarial networks
- **3DMM**: 3D morphable models

### Why Current Approach?
- **Docker Compatibility**: Works without GPU
- **Speed**: Fast processing suitable for real-time
- **Reliability**: Stable and predictable results
- **Simplicity**: Easy to maintain and debug
"""
        
        # Save explanation
        explanation_path = self.temp_dir / "technical_explanation.md"
        with open(explanation_path, 'w') as f:
            f.write(explanation)
        
        return str(explanation_path)
    
    def run_comprehensive_demo(self, video_path: str, target_member_id: str):
        """Run the complete comprehensive demonstration."""
        logger.info("Starting comprehensive face swap demonstration")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Get target MP information
        logger.info("Step 2: Getting target MP information")
        mp_info = self.get_mp_info(target_member_id, token)
        logger.info(f"Target MP {target_member_id}: {mp_info.get('name', 'Unknown')}")
        
        # Step 3: Extract and annotate frame with face detection
        logger.info("Step 3: Extracting frame with face detection visualization")
        annotated_frame = self.extract_frame_with_detection(video_path)
        if not annotated_frame:
            logger.error("Failed to extract and annotate frame")
            return False
        
        # Step 4: Perform face recognition analysis
        logger.info("Step 4: Performing face recognition analysis")
        recognition_analysis = self.perform_face_recognition_analysis(video_path, token)
        
        # Step 5: Perform face swapping
        logger.info("Step 5: Performing face swapping")
        swap_result = self.perform_face_swap_with_analysis(annotated_frame, target_member_id, token)
        
        if not swap_result.get("success"):
            logger.error("Face swapping failed")
            return False
        
        # Step 6: Create before/after comparison
        logger.info("Step 6: Creating before/after comparison")
        comparison_path = self.create_before_after_comparison(annotated_frame, swap_result["output_path"])
        
        # Step 7: Generate technical explanation
        logger.info("Step 7: Generating technical explanation")
        explanation_path = self.generate_technical_explanation()
        
        # Step 8: Generate comprehensive report
        logger.info("Step 8: Generating comprehensive report")
        report = {
            "demonstration_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "target_member_id": target_member_id,
            "target_mp_info": mp_info,
            "recognition_analysis": recognition_analysis,
            "face_swap_result": swap_result,
            "generated_files": {
                "annotated_frame": annotated_frame,
                "face_swapped_result": swap_result["output_path"],
                "before_after_comparison": comparison_path,
                "technical_explanation": explanation_path
            },
            "technical_summary": {
                "face_detection_method": "OpenCV Haar Cascade",
                "face_recognition_method": "128-dimensional embeddings",
                "face_swapping_method": "OpenCV blending with mask",
                "blend_factor": 0.7,
                "faces_detected": recognition_analysis.get("total_faces_detected", 0),
                "faces_swapped": swap_result.get("faces_swapped", 0)
            }
        }
        
        report_path = self.temp_dir / "comprehensive_demo_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_demo_summary(report)
        
        logger.info(f"Comprehensive demo completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return True
    
    def print_demo_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the demonstration results."""
        print("\n" + "="*80)
        print("🎭 COMPREHENSIVE PARLIAMENT TV FACE SWAP DEMONSTRATION RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        print(f"🎯 Target MP: {report['target_member_id']} - {report['target_mp_info'].get('name', 'Unknown')}")
        
        if report['target_mp_info'].get('party'):
            print(f"🏛️  Party: {report['target_mp_info']['party']}")
        if report['target_mp_info'].get('constituency'):
            print(f"📍 Constituency: {report['target_mp_info']['constituency']}")
        
        print(f"\n🔍 FACE RECOGNITION RESULTS:")
        print(f"   • Total faces detected: {report['recognition_analysis'].get('total_faces_detected', 0)}")
        
        for i, face in enumerate(report['recognition_analysis'].get('face_details', [])[:3]):
            print(f"   • Face {i+1}: Size {face['size']}, Quality {face.get('quality_score', 0):.2f}")
        
        print(f"\n🔄 FACE SWAPPING RESULTS:")
        print(f"   • Faces detected: {report['face_swap_result'].get('faces_detected', 0)}")
        print(f"   • Faces swapped: {report['face_swap_result'].get('faces_swapped', 0)}")
        print(f"   • Blend factor: {report['technical_summary']['blend_factor']}")
        
        print(f"\n🛠️  TECHNICAL METHODOLOGY:")
        print(f"   • Face detection: {report['technical_summary']['face_detection_method']}")
        print(f"   • Face recognition: {report['technical_summary']['face_recognition_method']}")
        print(f"   • Face swapping: {report['technical_summary']['face_swapping_method']}")
        
        print(f"\n📁 GENERATED FILES:")
        for name, path in report['generated_files'].items():
            if path:
                print(f"   • {name}: {path}")
        
        print(f"\n📊 Complete report: {self.temp_dir}/comprehensive_demo_report.json")
        print(f"📖 Technical explanation: {self.temp_dir}/technical_explanation.md")
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive Parliament TV Face Swap Demonstration")
    parser.add_argument("--video-path", required=True, help="Path to existing captured video file")
    parser.add_argument("--target-member-id", required=True, help="Target MP member ID for face swapping")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize demo
    demo = ComprehensiveFaceSwapDemo(base_url=args.base_url)
    
    try:
        # Run comprehensive demonstration
        success = demo.run_comprehensive_demo(
            video_path=args.video_path,
            target_member_id=args.target_member_id
        )
        
        if success:
            print(f"\n✅ Comprehensive demonstration completed successfully!")
            print(f"📁 All results saved in: {demo.temp_dir}")
        else:
            print("\n❌ Demonstration failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
