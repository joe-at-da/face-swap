#!/usr/bin/env python3
"""
Simple Face Recognition Test

This script tests the fixed face recognition system with the existing video
to demonstrate that MPs can now be identified correctly.

Usage:
    python simple_face_recognition_test.py --video-path "/app/data/temp/test_combined.mp4"
"""

import os
import sys
import argparse
import logging
import json
import requests
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_face_test")

class SimpleFaceRecognitionTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="simple_face_test_"))
        logger.info(f"Initialized simple test with temp directory: {self.temp_dir}")
        
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
        """Extract frames from video at appropriate time points."""
        try:
            frame_paths = []
            
            # For a 10-second video, extract frames every 2 seconds
            time_points = [0, 2, 4, 6, 8]
            
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
    
    def analyze_single_frame(self, frame_path: str, token: str) -> Dict[str, Any]:
        """Analyze faces in a single frame."""
        try:
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
                return analysis
                
        except Exception as e:
            logger.error(f"Failed to analyze faces in {frame_path}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def run_simple_test(self, video_path: str):
        """Run the simple face recognition test."""
        logger.info(f"Starting simple face recognition test for {video_path}")
        
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
        
        # Step 3: Analyze each frame
        logger.info("Step 3: Analyzing faces in each frame")
        all_analyses = []
        identified_mps = {}
        
        for i, frame_path in enumerate(frame_paths):
            logger.info(f"Analyzing frame {i+1}/{len(frame_paths)}: {os.path.basename(frame_path)}")
            
            analysis = self.analyze_single_frame(frame_path, token)
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
                            "max_confidence": 0
                        }
                    
                    appearance = {
                        "frame_index": i,
                        "frame_path": frame_path,
                        "confidence": mp_info.get("confidence", 0),
                        "face_size": face_detail.get("size", "Unknown")
                    }
                    
                    identified_mps[member_id]["appearances"].append(appearance)
                    identified_mps[member_id]["max_confidence"] = max(
                        identified_mps[member_id]["max_confidence"],
                        mp_info.get("confidence", 0)
                    )
        
        # Step 4: Generate report
        logger.info("Step 4: Generating test report")
        
        total_faces = sum(analysis.get("total_faces", 0) for analysis in all_analyses)
        total_identified = sum(analysis.get("identified_faces", 0) for analysis in all_analyses)
        
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "frame_analyses": all_analyses,
            "identified_mps": identified_mps,
            "summary": {
                "total_frames_analyzed": len(frame_paths),
                "total_faces_detected": total_faces,
                "total_identified_faces": total_identified,
                "unique_mps_identified": len(identified_mps),
                "frames_with_faces": len([a for a in all_analyses if a.get("total_faces", 0) > 0]),
                "frames_with_identified_mps": len([a for a in all_analyses if a.get("identified_faces", 0) > 0])
            }
        }
        
        report_path = self.temp_dir / "simple_face_recognition_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_simple_summary(report)
        
        logger.info(f"Simple face recognition test completed!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_simple_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the test results."""
        print("\n" + "="*80)
        print("🔧 SIMPLE FACE RECOGNITION TEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        summary = report['summary']
        
        print(f"\n🔍 FACE RECOGNITION RESULTS:")
        print(f"   • Frames analyzed: {summary['total_frames_analyzed']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Total identified faces: {summary['total_identified_faces']}")
        print(f"   • Unique MPs identified: {summary['unique_mps_identified']}")
        print(f"   • Frames with faces: {summary['frames_with_faces']}")
        print(f"   • Frames with identified MPs: {summary['frames_with_identified_mps']}")
        
        print(f"\n👥 IDENTIFIED MPs:")
        if report['identified_mps']:
            for i, (member_id, mp_info) in enumerate(report['identified_mps'].items()):
                print(f"   {i+1}. {mp_info['name']} (ID: {member_id})")
                print(f"      → Appearances: {len(mp_info['appearances'])}")
                print(f"      → Max confidence: {mp_info['max_confidence']:.3f}")
                frames_list = [f"#{a['frame_index']}" for a in mp_info['appearances']]
                print(f"      → Frames: {', '.join(frames_list)}")
        else:
            print("   ❌ No MPs identified in this video")
        
        print(f"\n📊 FRAME-BY-FRAME RESULTS:")
        for i, frame_analysis in enumerate(report['frame_analyses']):
            frame_name = os.path.basename(frame_analysis['frame_path'])
            total_faces = frame_analysis.get('total_faces', 0)
            identified_faces = frame_analysis.get('identified_faces', 0)
            
            print(f"   Frame {i}: {frame_name}")
            print(f"      → Faces detected: {total_faces}")
            print(f"      → Faces identified: {identified_faces}")
            
            if identified_faces > 0:
                for face_detail in frame_analysis.get('face_details', []):
                    if face_detail.get('identified_mp'):
                        mp_info = face_detail['identified_mp']
                        print(f"      • {mp_info.get('name', 'Unknown')} (confidence: {mp_info.get('confidence', 0):.3f})")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Report: {self.temp_dir}/simple_face_recognition_report.json")
        print(f"   • Extracted frames: {len(report['frame_analyses'])} files")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Simple Face Recognition Test")
    parser.add_argument("--video-path", required=True, help="Path to video file")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize test
    test = SimpleFaceRecognitionTest(base_url=args.base_url)
    
    try:
        # Run simple test
        result = test.run_simple_test(
            video_path=args.video_path
        )
        
        if result:
            print(f"\n✅ Simple face recognition test completed!")
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
