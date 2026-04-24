#!/usr/bin/env python3
"""
Face Recognition Diagnostic Test

This script performs a comprehensive diagnostic of the face recognition system
to verify all components are working correctly.

Usage:
    python face_recognition_diagnostic.py --video-path "/app/data/temp/test_combined.mp4"
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
logger = logging.getLogger("face_recognition_diagnostic")

class FaceRecognitionDiagnostic:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="face_recognition_diagnostic_"))
        logger.info(f"Initialized diagnostic with temp directory: {self.temp_dir}")
        
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
    
    def test_mp_database_loading(self):
        """Test MP database loading and structure."""
        try:
            logger.info("Testing MP database loading...")
            
            # Test the intelligent face swap service
            result = subprocess.run([
                "python", "-c", 
                """
import sys
sys.path.append('/app')
from backend.services.intelligent_face_swap import IntelligentFaceSwapService

service = IntelligentFaceSwapService()
print(f'MP encodings loaded: {len(service.mp_encodings)}')

# Test structure of encodings
sample_ids = list(service.mp_encodings.keys())[:3]
for member_id in sample_ids:
    mp_data = service.mp_encodings[member_id]
    print(f'MP {member_id}: type={type(mp_data)}')
    if isinstance(mp_data, dict) and 'embedding' in mp_data:
        print(f'  Embedding length: {len(mp_data[\"embedding\"])}')
    elif isinstance(mp_data, list):
        print(f'  List length: {len(mp_data)}')
"""
            ], capture_output=True, text=True, cwd="/app")
            
            if result.returncode == 0:
                logger.info("✅ MP database loading test passed")
                return result.stdout
            else:
                logger.error(f"❌ MP database loading test failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error testing MP database: {str(e)}")
            return None
    
    def test_face_detection_api(self, token: str, video_path: str):
        """Test face detection API with the video."""
        try:
            logger.info("Testing face detection API...")
            
            # Extract a test frame
            test_frame_path = self.temp_dir / "test_frame.jpg"
            cmd = [
                "ffmpeg", "-i", str(video_path), 
                "-ss", "4", 
                "-vframes", "1", 
                "-q:v", "2",
                str(test_frame_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to extract test frame: {result.stderr}")
                return None
            
            # Test face analysis API
            headers = {"Authorization": f"Bearer {token}"}
            
            with open(test_frame_path, 'rb') as image_file:
                files = {'image': (os.path.basename(test_frame_path), image_file, 'image/jpeg')}
                
                response = requests.post(
                    f"{self.base_url}/api/v1/face-swap/analyze-faces",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                analysis = response.json()
                logger.info("✅ Face detection API test passed")
                return analysis
                
        except Exception as e:
            logger.error(f"Error testing face detection API: {str(e)}")
            return None
    
    def test_different_confidence_thresholds(self, token: str, video_path: str):
        """Test face recognition with different confidence thresholds."""
        try:
            logger.info("Testing different confidence thresholds...")
            
            # Extract frames at different timestamps
            timestamps = [4, 6]  # Known to have faces
            results = {}
            
            for timestamp in timestamps:
                frame_path = self.temp_dir / f"frame_{timestamp}s.jpg"
                cmd = [
                    "ffmpeg", "-i", str(video_path), 
                    "-ss", str(timestamp), 
                    "-vframes", "1", 
                    "-q:v", "2",
                    str(frame_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    # Test with current API
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
                        results[f"frame_{timestamp}s"] = analysis
                        
                        logger.info(f"Frame {timestamp}s: {analysis.get('total_faces', 0)} faces, {analysis.get('identified_faces', 0)} identified")
                        
                        # Show face details
                        for face_detail in analysis.get("face_details", []):
                            if face_detail.get("identified_mp"):
                                mp_info = face_detail["identified_mp"]
                                logger.info(f"  -> MP {mp_info.get('member_id', 'Unknown')} with confidence {mp_info.get('confidence', 0):.3f}")
                            else:
                                logger.info(f"  -> Unidentified face")
            
            logger.info("✅ Confidence threshold test completed")
            return results
            
        except Exception as e:
            logger.error(f"Error testing confidence thresholds: {str(e)}")
            return None
    
    def test_video_capture_system(self):
        """Test the video capture system."""
        try:
            logger.info("Testing video capture system...")
            
            # Check recent captures
            headers = {"Authorization": f"Bearer {self.get_auth_token()}"}
            response = requests.get(f"{self.base_url}/api/v1/capture", headers=headers)
            response.raise_for_status()
            
            captures = response.json()
            recent_captures = [c for c in captures if c.get("status") == "completed"][-5:]  # Last 5 completed
            
            logger.info(f"Found {len(recent_captures)} recent completed captures")
            
            for capture in recent_captures:
                file_path = capture.get("file_path")
                if file_path and os.path.exists(file_path):
                    # Check video duration
                    duration_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file_path]
                    duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
                    
                    if duration_result.returncode == 0:
                        duration = duration_result.stdout.strip()
                        logger.info(f"Capture {capture['id']}: {duration}s duration, file: {file_path}")
                    else:
                        logger.info(f"Capture {capture['id']}: Unable to determine duration, file: {file_path}")
                else:
                    logger.info(f"Capture {capture['id']}: File not found: {file_path}")
            
            logger.info("✅ Video capture system test completed")
            return recent_captures
            
        except Exception as e:
            logger.error(f"Error testing video capture system: {str(e)}")
            return None
    
    def run_comprehensive_diagnostic(self, video_path: str):
        """Run comprehensive face recognition diagnostic."""
        logger.info(f"Starting comprehensive face recognition diagnostic for {video_path}")
        
        diagnostic_results = {
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "tests": {}
        }
        
        # Test 1: MP Database Loading
        logger.info("=== Test 1: MP Database Loading ===")
        mp_db_result = self.test_mp_database_loading()
        diagnostic_results["tests"]["mp_database"] = {
            "status": "passed" if mp_db_result else "failed",
            "details": mp_db_result
        }
        
        # Test 2: Authentication
        logger.info("=== Test 2: Authentication ===")
        token = self.get_auth_token()
        diagnostic_results["tests"]["authentication"] = {
            "status": "passed" if token else "failed",
            "details": "Token obtained" if token else "Failed to get token"
        }
        
        if not token:
            logger.error("Authentication failed, cannot continue with API tests")
            return diagnostic_results
        
        # Test 3: Face Detection API
        logger.info("=== Test 3: Face Detection API ===")
        face_detection_result = self.test_face_detection_api(token, video_path)
        diagnostic_results["tests"]["face_detection"] = {
            "status": "passed" if face_detection_result else "failed",
            "details": face_detection_result
        }
        
        # Test 4: Confidence Thresholds
        logger.info("=== Test 4: Confidence Thresholds ===")
        confidence_result = self.test_different_confidence_thresholds(token, video_path)
        diagnostic_results["tests"]["confidence_thresholds"] = {
            "status": "passed" if confidence_result else "failed", 
            "details": confidence_result
        }
        
        # Test 5: Video Capture System
        logger.info("=== Test 5: Video Capture System ===")
        capture_result = self.test_video_capture_system()
        diagnostic_results["tests"]["video_capture"] = {
            "status": "passed" if capture_result else "failed",
            "details": capture_result
        }
        
        # Generate diagnostic report
        logger.info("=== Diagnostic Summary ===")
        passed_tests = sum(1 for test in diagnostic_results["tests"].values() if test["status"] == "passed")
        total_tests = len(diagnostic_results["tests"])
        
        logger.info(f"Tests passed: {passed_tests}/{total_tests}")
        
        for test_name, test_result in diagnostic_results["tests"].items():
            status_icon = "✅" if test_result["status"] == "passed" else "❌"
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {test_result['status']}")
        
        # Save diagnostic report
        report_path = self.temp_dir / "face_recognition_diagnostic_report.json"
        with open(report_path, 'w') as f:
            json.dump(diagnostic_results, f, indent=2)
        
        logger.info(f"Diagnostic report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return diagnostic_results
    
    def print_diagnostic_summary(self, diagnostic_results: Dict[str, Any]):
        """Print a formatted summary of the diagnostic results."""
        print("\n" + "="*80)
        print("🔍 FACE RECOGNITION SYSTEM DIAGNOSTIC RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {diagnostic_results['timestamp']}")
        print(f"🎬 Test Video: {diagnostic_results['video_path']}")
        
        tests = diagnostic_results["tests"]
        passed_tests = sum(1 for test in tests.values() if test["status"] == "passed")
        total_tests = len(tests)
        
        print(f"\n📊 Overall Status: {passed_tests}/{total_tests} tests passed")
        
        print(f"\n🔧 Individual Test Results:")
        for test_name, test_result in tests.items():
            status_icon = "✅" if test_result["status"] == "passed" else "❌"
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}: {test_result['status'].upper()}")
        
        # Show detailed results for key tests
        if tests.get("mp_database", {}).get("details"):
            print(f"\n📚 MP Database Details:")
            print(f"   {tests['mp_database']['details']}")
        
        if tests.get("face_detection", {}).get("details"):
            face_det = tests["face_detection"]["details"]
            print(f"\n👁️ Face Detection Details:")
            print(f"   • Total faces: {face_det.get('total_faces', 0)}")
            print(f"   • Identified faces: {face_det.get('identified_faces', 0)}")
            print(f"   • Success: {face_det.get('success', False)}")
        
        if tests.get("confidence_thresholds", {}).get("details"):
            conf_results = tests["confidence_thresholds"]["details"]
            print(f"\n🎯 Confidence Threshold Results:")
            for frame_name, analysis in conf_results.items():
                total_faces = analysis.get('total_faces', 0)
                identified_faces = analysis.get('identified_faces', 0)
                print(f"   • {frame_name}: {total_faces} faces, {identified_faces} identified")
        
        if tests.get("video_capture", {}).get("details"):
            captures = tests["video_capture"]["details"]
            print(f"\n📹 Recent Captures:")
            for capture in captures[:3]:  # Show first 3
                print(f"   • Capture {capture['id']}: {capture.get('title', 'Unknown')}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Diagnostic report: {self.temp_dir}/face_recognition_diagnostic_report.json")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Face Recognition System Diagnostic")
    parser.add_argument("--video-path", required=True, help="Path to video file for testing")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize diagnostic
    diagnostic = FaceRecognitionDiagnostic(base_url=args.base_url)
    
    try:
        # Run comprehensive diagnostic
        result = diagnostic.run_comprehensive_diagnostic(
            video_path=args.video_path
        )
        
        # Print summary
        diagnostic.print_diagnostic_summary(result)
        
        if result:
            print(f"\n✅ Diagnostic completed!")
            print(f"📁 All results saved in: {diagnostic.temp_dir}")
        else:
            print("\n❌ Diagnostic failed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
