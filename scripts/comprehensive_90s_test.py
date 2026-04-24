#!/usr/bin/env python3
"""
Comprehensive 90-Second Parliament TV Face Recognition Test

This script captures 90 seconds of Parliament TV and performs comprehensive
face recognition analysis to identify MPs throughout the video.

Usage:
    python comprehensive_90s_test.py --duration 90 --output-name "parliament_90s_test"
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
logger = logging.getLogger("comprehensive_90s")

class Comprehensive90sTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="comprehensive_90s_"))
        logger.info(f"Initialized 90s test with temp directory: {self.temp_dir}")
        
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
    
    def capture_parliament_tv(self, duration: int = 90, output_name: str = "parliament_90s_test"):
        """Capture Parliament TV for specified duration."""
        try:
            parliament_url = "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7"
            headers = {"Authorization": f"Bearer {self.get_auth_token()}"}
            
            capture_data = {
                "source_url": parliament_url,
                "title": f"Parliament TV {duration}s Comprehensive Test - {output_name}",
                "description": f"Comprehensive Parliament TV capture for MP identification - {duration} seconds",
                "duration": duration
            }
            
            logger.info(f"Starting {duration}-second Parliament TV capture")
            response = requests.post(
                f"{self.base_url}/api/v1/capture",
                json=capture_data,
                headers=headers
            )
            response.raise_for_status()
            
            capture_result = response.json()
            capture_id = capture_result["id"]
            
            logger.info(f"Capture started with ID: {capture_id}")
            
            # Wait for capture to complete
            return self.wait_for_capture_completion(capture_id, headers, duration)
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return None
    
    def wait_for_capture_completion(self, capture_id: int, headers: Dict, expected_duration: int):
        """Wait for capture to complete."""
        try:
            max_wait_time = expected_duration + 60  # Add buffer time
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < max_wait_time:
                response = requests.get(
                    f"{self.base_url}/api/v1/capture/{capture_id}",
                    headers=headers
                )
                response.raise_for_status()
                
                capture_status = response.json()
                status = capture_status.get("status")
                
                logger.info(f"Capture status: {status}")
                
                if status == "completed":
                    video_path = capture_status.get("file_path")
                    if video_path:
                        logger.info(f"Capture completed: {video_path}")
                        return {
                            "success": True,
                            "capture_id": capture_id,
                            "video_path": video_path,
                            "metadata": capture_status
                        }
                
                # Wait before checking again
                import time
                time.sleep(10)
            
            logger.error("Capture timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for capture: {str(e)}")
            return None
    
    def extract_comprehensive_frames(self, video_path: str) -> List[str]:
        """Extract frames throughout the entire video duration."""
        try:
            frame_paths = []
            
            # Extract frames at regular intervals throughout 90 seconds
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
    
    def analyze_all_faces(self, frame_paths: List[str], token: str) -> Dict[str, Any]:
        """Analyze faces in all frames and compile comprehensive results."""
        try:
            all_analyses = []
            all_detected_faces = []
            identified_mps = {}
            
            logger.info(f"Analyzing faces in {len(frame_paths)} frames")
            
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
                    
                    # Collect all detected faces
                    for face_detail in analysis.get("face_details", []):
                        face_info = {
                            "frame_index": i,
                            "frame_path": frame_path,
                            "face_id": face_detail["face_id"],
                            "location": face_detail["location"],
                            "size": face_detail["size"],
                            "identified_mp": face_detail.get("identified_mp"),
                            "confidence": face_detail.get("confidence", 0)
                        }
                        all_detected_faces.append(face_info)
                        
                        # Track identified MPs
                        if face_detail.get("identified_mp"):
                            mp_info = face_detail["identified_mp"]
                            member_id = mp_info.get("member_id")
                            if member_id not in identified_mps:
                                identified_mps[member_id] = {
                                    "member_id": member_id,
                                    "name": mp_info.get("name", f"MP {member_id}"),
                                    "appearances": [],
                                    "max_confidence": 0
                                }
                            
                            identified_mps[member_id]["appearances"].append(face_info)
                            identified_mps[member_id]["max_confidence"] = max(
                                identified_mps[member_id]["max_confidence"],
                                mp_info.get("confidence", 0)
                            )
            
            # Compile comprehensive results
            results = {
                "success": True,
                "total_frames_analyzed": len(frame_paths),
                "frame_analyses": all_analyses,
                "all_detected_faces": all_detected_faces,
                "identified_mps": identified_mps,
                "summary": {
                    "total_faces_detected": len(all_detected_faces),
                    "unique_mps_identified": len(identified_mps),
                    "frames_with_faces": len([a for a in all_analyses if a.get("total_faces", 0) > 0]),
                    "frames_with_identified_mps": len([a for a in all_analyses if a.get("identified_faces", 0) > 0])
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing faces: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_face_comparison_visualization(self, frame_paths: List[str], analysis_results: Dict[str, Any]) -> str:
        """Create a comprehensive visualization showing all detected faces and MP matches."""
        try:
            # Create a grid layout showing all frames with face annotations
            rows = 2
            cols = 4  # 7 frames + 1 info panel
            
            # Load and resize all frames
            frame_height = 200
            resized_frames = []
            
            for frame_path in frame_paths:
                frame = cv2.imread(frame_path)
                if frame is not None:
                    resized = cv2.resize(frame, (int(frame.shape[1] * frame_height / frame.shape[0]), frame_height))
                    
                    # Add face detection annotations
                    frame_analysis = next((a for a in analysis_results["frame_analyses"] if a["frame_path"] == frame_path), {})
                    
                    for face_detail in frame_analysis.get("face_details", []):
                        location = face_detail["location"]
                        top, right, bottom, left = location
                        
                        # Draw face rectangle
                        color = (0, 255, 0) if face_detail.get("identified_mp") else (0, 0, 255)
                        cv2.rectangle(resized, (left, top), (right, bottom), color, 2)
                        
                        # Add label
                        label = f"Face {face_detail['face_id']}"
                        if face_detail.get("identified_mp"):
                            mp_info = face_detail["identified_mp"]
                            label += f" -> {mp_info.get('name', 'Unknown')}"
                            label += f" ({mp_info.get('confidence', 0):.2f})"
                        
                        cv2.putText(resized, label, (left, top-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    
                    resized_frames.append(resized)
                else:
                    # Create placeholder for failed frame
                    placeholder = np.zeros((frame_height, 300, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "FRAME LOAD FAILED", (50, frame_height//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    resized_frames.append(placeholder)
            
            # Add info panel
            info_panel = np.zeros((frame_height, 300, 3), dtype=np.uint8)
            
            # Add summary information
            summary = analysis_results["summary"]
            info_lines = [
                f"COMPREHENSIVE 90s TEST RESULTS",
                f"",
                f"Frames Analyzed: {summary['total_frames_analyzed']}",
                f"Total Faces: {summary['total_faces_detected']}",
                f"MPs Identified: {summary['unique_mps_identified']}",
                f"Frames with Faces: {summary['frames_with_faces']}",
                f"Frames with MPs: {summary['frames_with_identified_mps']}",
                f"",
                f"IDENTIFIED MPs:"
            ]
            
            y_offset = 20
            for line in info_lines:
                cv2.putText(info_panel, line, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 20
            
            # Add identified MPs list
            for i, (member_id, mp_info) in enumerate(analysis_results["identified_mps"].items()):
                if i >= 5:  # Limit to 5 MPs to fit
                    break
                mp_line = f"• {mp_info['name']} ({mp_info['max_confidence']:.2f})"
                cv2.putText(info_panel, mp_line, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                y_offset += 15
            
            resized_frames.append(info_panel)
            
            # Arrange frames in grid
            # Pad to make 8 frames (2x4 grid)
            while len(resized_frames) < 8:
                placeholder = np.zeros((frame_height, 300, 3), dtype=np.uint8)
                resized_frames.append(placeholder)
            
            # Create rows
            row1 = np.hstack(resized_frames[:4])
            row2 = np.hstack(resized_frames[4:8])
            comparison = np.vstack([row1, row2])
            
            # Save comparison
            comparison_path = self.temp_dir / "comprehensive_90s_comparison.jpg"
            cv2.imwrite(str(comparison_path), comparison)
            
            logger.info(f"Created comprehensive comparison: {comparison_path}")
            return str(comparison_path)
            
        except Exception as e:
            logger.error(f"Error creating comparison: {str(e)}")
            return None
    
    def run_comprehensive_test(self, duration: int = 90, output_name: str = "parliament_90s_test"):
        """Run the complete 90-second comprehensive test."""
        logger.info(f"Starting comprehensive {duration}s Parliament TV test")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Capture Parliament TV
        logger.info("Step 2: Capturing Parliament TV")
        capture_result = self.capture_parliament_tv(duration, output_name)
        
        if not capture_result:
            logger.error("Capture failed")
            return False
        
        video_path = capture_result["video_path"]
        logger.info(f"Video captured: {video_path}")
        
        # Step 3: Extract comprehensive frames
        logger.info("Step 3: Extracting frames throughout video")
        frame_paths = self.extract_comprehensive_frames(video_path)
        
        if not frame_paths:
            logger.error("No frames extracted")
            return False
        
        # Step 4: Analyze all faces
        logger.info("Step 4: Analyzing faces in all frames")
        analysis_results = self.analyze_all_faces(frame_paths, token)
        
        if not analysis_results.get("success"):
            logger.error("Face analysis failed")
            return False
        
        # Step 5: Create visualization
        logger.info("Step 5: Creating comprehensive visualization")
        comparison_path = self.create_face_comparison_visualization(frame_paths, analysis_results)
        
        # Step 6: Generate report
        logger.info("Step 6: Generating comprehensive report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "output_name": output_name,
            "capture_result": capture_result,
            "frame_paths": frame_paths,
            "analysis_results": analysis_results,
            "comparison_path": comparison_path
        }
        
        report_path = self.temp_dir / "comprehensive_90s_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_comprehensive_summary(report)
        
        logger.info(f"Comprehensive test completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_comprehensive_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the comprehensive test results."""
        print("\n" + "="*80)
        print("🎬 COMPREHENSIVE 90-SECOND PARLIAMENT TV TEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Duration: {report['duration']} seconds")
        print(f"📹 Video: {report['capture_result']['video_path']}")
        
        analysis = report['analysis_results']
        summary = analysis['summary']
        
        print(f"\n🔍 FACE ANALYSIS SUMMARY:")
        print(f"   • Frames analyzed: {summary['total_frames_analyzed']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Unique MPs identified: {summary['unique_mps_identified']}")
        print(f"   • Frames with faces: {summary['frames_with_faces']}/{summary['total_frames_analyzed']}")
        print(f"   • Frames with identified MPs: {summary['frames_with_identified_mps']}")
        
        print(f"\n👥 IDENTIFIED MPs:")
        if analysis['identified_mps']:
            for i, (member_id, mp_info) in enumerate(analysis['identified_mps'].items()):
                print(f"   {i+1}. {mp_info['name']} (ID: {member_id})")
                print(f"      → Appearances: {len(mp_info['appearances'])}")
                print(f"      → Max confidence: {mp_info['max_confidence']:.3f}")
                print(f"      → Frames: {', '.join([f"#{a['frame_index']}" for a in mp_info['appearances'][:3]])}{'...' if len(mp_info['appearances']) > 3 else ''}")
        else:
            print("   ❌ No MPs identified in the video")
        
        print(f"\n📊 FRAME-BY-FRAME ANALYSIS:")
        for i, frame_analysis in enumerate(analysis['frame_analyses']):
            frame_name = os.path.basename(frame_analysis['frame_path'])
            total_faces = frame_analysis.get('total_faces', 0)
            identified_faces = frame_analysis.get('identified_faces', 0)
            
            print(f"   Frame {i}: {frame_name}")
            print(f"      → Faces detected: {total_faces}")
            print(f"      → Identified: {identified_faces}")
            
            if identified_faces > 0:
                for face_detail in frame_analysis.get('face_details', []):
                    if face_detail.get('identified_mp'):
                        mp_info = face_detail['identified_mp']
                        print(f"      • {mp_info.get('name', 'Unknown')} (confidence: {mp_info.get('confidence', 0):.3f})")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Comprehensive comparison: {report['comparison_path']}")
        print(f"   • Detailed report: {self.temp_dir}/comprehensive_90s_report.json")
        print(f"   • Extracted frames: {len(report['frame_paths'])} files")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive 90-Second Parliament TV Test")
    parser.add_argument("--duration", type=int, default=90, help="Capture duration in seconds")
    parser.add_argument("--output-name", default="parliament_90s_test", help="Output name for the test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize comprehensive test
    test = Comprehensive90sTest(base_url=args.base_url)
    
    try:
        # Run comprehensive test
        result = test.run_comprehensive_test(
            duration=args.duration,
            output_name=args.output_name
        )
        
        if result:
            print(f"\n✅ Comprehensive test completed successfully!")
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
