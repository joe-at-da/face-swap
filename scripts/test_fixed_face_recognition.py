#!/usr/bin/env python3
"""
Test Fixed Face Recognition System

This script tests the updated face recognition system with existing video
to verify that MPs are now being identified correctly.

Usage:
    python test_fixed_face_recognition.py --video-path "/app/data/temp/capture_1776949958.mp4"
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
logger = logging.getLogger("fixed_face_recognition")

class FixedFaceRecognitionTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fixed_face_recognition_"))
        logger.info(f"Initialized test with temp directory: {self.temp_dir}")
        
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
    
    def extract_frames_from_video(self, video_path: str) -> List[str]:
        """Extract frames throughout the video for analysis."""
        try:
            frame_paths = []
            
            # Extract frames at regular intervals
            time_points = [0, 15, 30, 45, 60, 75, 85]  # 7 key time points
            
            for timestamp in time_points:
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
                if result.returncode == 0:
                    frame_paths.append(str(output_path))
                    logger.info(f"Extracted frame at {timestamp}s: {output_path}")
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s")
            
            logger.info(f"Extracted {len(frame_paths)} frames from video")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def analyze_faces_with_fixed_system(self, frame_paths: List[str], token: str) -> Dict[str, Any]:
        """Analyze faces using the fixed face recognition system."""
        try:
            all_analyses = []
            identified_mps = {}
            
            logger.info(f"Analyzing faces in {len(frame_paths)} frames with fixed system")
            
            for i, frame_path in enumerate(frame_paths):
                logger.info(f"Analyzing frame {i+1}/{len(frame_paths)}: {os.path.basename(frame_path)}")
                
                headers = {"Authorization": f"Bearer {token}"}
                
                with open(frame_path, 'rb') as image_file:
                    files = {'image': (os.path.basename(frame_path), image_file, 'image/jpeg')}
                    
                    response = requests.post(
                        f"{self.base_url}/api/v1/face-swap/analyze-faces",
                        files=files,
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    analysis = response.json()
                    analysis["frame_path"] = frame_path
                    analysis["frame_index"] = i
                    all_analyses.append(analysis)
                    
                    # Track identified MPs
                    for face_detail in analysis.get("face_details", []):
                        if face_detail.get("identified_mp"):
                            mp_info = face_detail["identified_mp"]
                            member_id = mp_info.get("member_id")
                            
                            if member_id not in identified_mps:
                                identified_mps[member_id] = {
                                    "member_id": member_id,
                                    "name": mp_info.get("name", f"MP {member_id}"),
                                    "appearances": [],
                                    "max_confidence": 0,
                                    "face_locations": []
                                }
                            
                            appearance = {
                                "frame_index": i,
                                "frame_path": frame_path,
                                "confidence": mp_info.get("confidence", 0),
                                "face_location": face_detail.get("location", []),
                                "face_size": face_detail.get("size", "Unknown")
                            }
                            
                            identified_mps[member_id]["appearances"].append(appearance)
                            identified_mps[member_id]["max_confidence"] = max(
                                identified_mps[member_id]["max_confidence"],
                                mp_info.get("confidence", 0)
                            )
                            identified_mps[member_id]["face_locations"].append(face_detail.get("location", []))
            
            # Compile results
            total_faces = sum(analysis.get("total_faces", 0) for analysis in all_analyses)
            total_identified = sum(analysis.get("identified_faces", 0) for analysis in all_analyses)
            
            results = {
                "success": True,
                "total_frames_analyzed": len(frame_paths),
                "frame_analyses": all_analyses,
                "identified_mps": identified_mps,
                "summary": {
                    "total_faces_detected": total_faces,
                    "total_identified_faces": total_identified,
                    "unique_mps_identified": len(identified_mps),
                    "frames_with_faces": len([a for a in all_analyses if a.get("total_faces", 0) > 0]),
                    "frames_with_identified_mps": len([a for a in all_analyses if a.get("identified_faces", 0) > 0])
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing faces: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_face_visualization(self, frame_paths: List[str], analysis_results: Dict[str, Any]) -> str:
        """Create visualization showing detected faces and MP identifications."""
        try:
            # Create a grid showing all frames with annotations
            rows = 2
            cols = 4
            
            frame_height = 250
            annotated_frames = []
            
            for i, frame_path in enumerate(frame_paths):
                frame = cv2.imread(frame_path)
                if frame is not None:
                    resized = cv2.resize(frame, (int(frame.shape[1] * frame_height / frame.shape[0]), frame_height))
                    
                    # Add face annotations
                    frame_analysis = next((a for a in analysis_results["frame_analyses"] if a["frame_path"] == frame_path), {})
                    
                    for face_detail in frame_analysis.get("face_details", []):
                        location = face_detail["location"]
                        top, right, bottom, left = location
                        
                        # Draw face rectangle
                        if face_detail.get("identified_mp"):
                            color = (0, 255, 0)  # Green for identified
                            label_color = (0, 255, 0)
                        else:
                            color = (0, 0, 255)  # Red for unidentified
                            label_color = (0, 0, 255)
                        
                        cv2.rectangle(resized, (left, top), (right, bottom), color, 2)
                        
                        # Add label
                        label = f"Face {face_detail['face_id']}"
                        if face_detail.get("identified_mp"):
                            mp_info = face_detail["identified_mp"]
                            label += f" -> {mp_info.get('name', 'Unknown')}"
                            label += f" ({mp_info.get('confidence', 0):.2f})"
                        
                        cv2.putText(resized, label, (left, top-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_color, 2)
                    
                    # Add frame timestamp
                    timestamp = os.path.basename(frame_path).replace('frame_', '').replace('s.jpg', '')
                    cv2.putText(resized, f"Frame at {timestamp}s", (10, frame_height-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    annotated_frames.append(resized)
                else:
                    # Placeholder for failed frame
                    placeholder = np.zeros((frame_height, 400, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "FRAME LOAD FAILED", (50, frame_height//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    annotated_frames.append(placeholder)
            
            # Pad to make 8 frames (2x4 grid)
            while len(annotated_frames) < 8:
                placeholder = np.zeros((frame_height, 400, 3), dtype=np.uint8)
                annotated_frames.append(placeholder)
            
            # Create grid
            row1 = np.hstack(annotated_frames[:4])
            row2 = np.hstack(annotated_frames[4:8])
            visualization = np.vstack([row1, row2])
            
            # Add title and summary
            summary = analysis_results["summary"]
            title = f"FIXED FACE RECOGNITION TEST - {summary['unique_mps_identified']} MPs IDENTIFIED"
            cv2.putText(visualization, title, (20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            summary_text = f"Faces: {summary['total_faces_detected']} | Identified: {summary['total_identified_faces']} | Frames: {summary['frames_with_identified_mps']}/{summary['total_frames_analyzed']}"
            cv2.putText(visualization, summary_text, (20, visualization.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Save visualization
            visualization_path = self.temp_dir / "fixed_face_recognition_results.jpg"
            cv2.imwrite(str(visualization_path), visualization)
            
            logger.info(f"Created visualization: {visualization_path}")
            return str(visualization_path)
            
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            return None
    
    def run_fixed_recognition_test(self, video_path: str):
        """Run the complete fixed face recognition test."""
        logger.info(f"Starting fixed face recognition test for {video_path}")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Extract frames
        logger.info("Step 2: Extracting frames from video")
        frame_paths = self.extract_frames_from_video(video_path)
        
        if not frame_paths:
            logger.error("No frames extracted")
            return False
        
        # Step 3: Analyze faces with fixed system
        logger.info("Step 3: Analyzing faces with fixed recognition system")
        analysis_results = self.analyze_faces_with_fixed_system(frame_paths, token)
        
        if not analysis_results.get("success"):
            logger.error("Face analysis failed")
            return False
        
        # Step 4: Create visualization
        logger.info("Step 4: Creating face recognition visualization")
        visualization_path = self.create_face_visualization(frame_paths, analysis_results)
        
        # Step 5: Generate report
        logger.info("Step 5: Generating test report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "frame_paths": frame_paths,
            "analysis_results": analysis_results,
            "visualization_path": visualization_path
        }
        
        report_path = self.temp_dir / "fixed_face_recognition_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_test_summary(report)
        
        logger.info(f"Fixed face recognition test completed!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_test_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the test results."""
        print("\n" + "="*80)
        print("🔧 FIXED FACE RECOGNITION SYSTEM TEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        analysis = report['analysis_results']
        summary = analysis['summary']
        
        print(f"\n🔍 FACE RECOGNITION RESULTS:")
        print(f"   • Frames analyzed: {summary['total_frames_analyzed']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Total identified faces: {summary['total_identified_faces']}")
        print(f"   • Unique MPs identified: {summary['unique_mps_identified']}")
        print(f"   • Frames with faces: {summary['frames_with_faces']}")
        print(f"   • Frames with identified MPs: {summary['frames_with_identified_mps']}")
        
        print(f"\n👥 IDENTIFIED MPs:")
        if analysis['identified_mps']:
            for i, (member_id, mp_info) in enumerate(analysis['identified_mps'].items()):
                print(f"   {i+1}. {mp_info['name']} (ID: {member_id})")
                print(f"      → Appearances: {len(mp_info['appearances'])}")
                print(f"      → Max confidence: {mp_info['max_confidence']:.3f}")
                frames_list = [f"#{a['frame_index']}s" for a in mp_info['appearances']]
                print(f"      → Frames: {', '.join(frames_list)}")
        else:
            print("   ❌ No MPs identified - face recognition still needs work")
        
        print(f"\n📊 FRAME-BY-FRAME BREAKDOWN:")
        for i, frame_analysis in enumerate(analysis['frame_analyses']):
            frame_name = os.path.basename(frame_analysis['frame_path'])
            total_faces = frame_analysis.get('total_faces', 0)
            identified_faces = frame_analysis.get('identified_faces', 0)
            
            print(f"   Frame {i}: {frame_name}")
            print(f"      → Faces: {total_faces} | Identified: {identified_faces}")
            
            if identified_faces > 0:
                for face_detail in frame_analysis.get('face_details', []):
                    if face_detail.get('identified_mp'):
                        mp_info = face_detail['identified_mp']
                        print(f"      • {mp_info.get('name', 'Unknown')} (conf: {mp_info.get('confidence', 0):.3f})")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Visualization: {report['visualization_path']}")
        print(f"   • Detailed report: {self.temp_dir}/fixed_face_recognition_report.json")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Fixed Face Recognition System")
    parser.add_argument("--video-path", required=True, help="Path to video file")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize test
    test = FixedFaceRecognitionTest(base_url=args.base_url)
    
    try:
        # Run fixed recognition test
        result = test.run_fixed_recognition_test(
            video_path=args.video_path
        )
        
        if result:
            print(f"\n✅ Fixed face recognition test completed!")
            print(f"📁 All results saved in: {test.temp_dir}")
        else:
            print("\n❌ Test failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
