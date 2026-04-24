#!/usr/bin/env python3
"""
Test Improved Face Recognition System

This script benchmarks the current system and tests the improved face recognition
with Parliament content, focusing on post-60s identification.

Usage:
    python test_improved_recognition.py --video-path "/app/data/temp/test_combined.mp4"
"""

import os
import sys
import argparse
import logging
import json
import requests
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_improved_recognition")

class ImprovedRecognitionTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="improved_recognition_test_"))
        logger.info(f"Initialized improved recognition test with temp directory: {self.temp_dir}")
        
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
    
    def benchmark_current_system(self, video_path: str, token: str) -> Dict[str, Any]:
        """Benchmark the current face recognition system."""
        try:
            logger.info("Benchmarking current face recognition system...")
            
            # Extract frames at different timestamps
            timestamps = [4, 6, 30, 45, 60]  # Mix of pre and post-60s
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
                    # Test current system
                    start_time = time.time()
                    
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
                        end_time = time.time()
                        
                        results[f"frame_{timestamp}s"] = {
                            "analysis": analysis,
                            "processing_time": end_time - start_time,
                            "timestamp": timestamp,
                            "system": "current"
                        }
                        
                        logger.info(f"Current system - Frame {timestamp}s: {analysis.get('total_faces', 0)} faces, {analysis.get('identified_faces', 0)} identified, {end_time - start_time:.3f}s")
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error benchmarking current system: {str(e)}")
            return {}
    
    def test_improved_system(self, video_path: str, token: str) -> Dict[str, Any]:
        """Test the improved face recognition system."""
        try:
            logger.info("Testing improved face recognition system...")
            
            # Extract frames at different timestamps
            timestamps = [4, 6, 30, 45, 60]  # Mix of pre and post-60s
            results = {}
            
            for timestamp in timestamps:
                frame_path = self.temp_dir / f"frame_{timestamp}s_improved.jpg"
                cmd = [
                    "ffmpeg", "-i", str(video_path), 
                    "-ss", str(timestamp), 
                    "-vframes", "1", 
                    "-q:v", "2",
                    str(frame_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    # Test improved system
                    start_time = time.time()
                    
                    headers = {"Authorization": f"Bearer {token}"}
                    with open(frame_path, 'rb') as image_file:
                        files = {'image': (os.path.basename(frame_path), image_file, 'image/jpeg')}
                        
                        # Include focus_timestamp parameter
                        params = {"focus_timestamp": timestamp}
                        
                        response = requests.post(
                            f"{self.base_url}/api/v1/face-swap/analyze-faces-improved",
                            files=files,
                            data=params,
                            headers=headers
                        )
                        response.raise_for_status()
                        
                        analysis = response.json()
                        end_time = time.time()
                        
                        results[f"frame_{timestamp}s"] = {
                            "analysis": analysis,
                            "processing_time": end_time - start_time,
                            "timestamp": timestamp,
                            "system": "improved"
                        }
                        
                        if analysis.get("skipped"):
                            logger.info(f"Improved system - Frame {timestamp}s: SKIPPED ({analysis.get('reason')})")
                        else:
                            logger.info(f"Improved system - Frame {timestamp}s: {analysis.get('total_faces', 0)} faces, {analysis.get('identified_faces', 0)} identified, {end_time - start_time:.3f}s")
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing improved system: {str(e)}")
            return {}
    
    def compare_systems(self, current_results: Dict[str, Any], improved_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare the current and improved systems."""
        try:
            logger.info("Comparing face recognition systems...")
            
            comparison = {
                "current_system": {
                    "total_frames": len(current_results),
                    "total_faces_detected": 0,
                    "total_faces_identified": 0,
                    "total_processing_time": 0,
                    "frames_with_faces": 0,
                    "frames_with_identified": 0
                },
                "improved_system": {
                    "total_frames": len(improved_results),
                    "total_faces_detected": 0,
                    "total_faces_identified": 0,
                    "total_processing_time": 0,
                    "frames_with_faces": 0,
                    "frames_with_identified": 0,
                    "frames_skipped": 0
                },
                "detailed_comparison": []
            }
            
            # Analyze current system
            for frame_key, result in current_results.items():
                analysis = result["analysis"]
                comparison["current_system"]["total_faces_detected"] += analysis.get("total_faces", 0)
                comparison["current_system"]["total_faces_identified"] += analysis.get("identified_faces", 0)
                comparison["current_system"]["total_processing_time"] += result["processing_time"]
                
                if analysis.get("total_faces", 0) > 0:
                    comparison["current_system"]["frames_with_faces"] += 1
                if analysis.get("identified_faces", 0) > 0:
                    comparison["current_system"]["frames_with_identified"] += 1
            
            # Analyze improved system
            for frame_key, result in improved_results.items():
                analysis = result["analysis"]
                if not analysis.get("skipped"):
                    comparison["improved_system"]["total_faces_detected"] += analysis.get("total_faces", 0)
                    comparison["improved_system"]["total_faces_identified"] += analysis.get("identified_faces", 0)
                    comparison["improved_system"]["total_processing_time"] += result["processing_time"]
                    
                    if analysis.get("total_faces", 0) > 0:
                        comparison["improved_system"]["frames_with_faces"] += 1
                    if analysis.get("identified_faces", 0) > 0:
                        comparison["improved_system"]["frames_with_identified"] += 1
                else:
                    comparison["improved_system"]["frames_skipped"] += 1
            
            # Calculate averages
            if comparison["current_system"]["total_frames"] > 0:
                comparison["current_system"]["avg_processing_time"] = (
                    comparison["current_system"]["total_processing_time"] / comparison["current_system"]["total_frames"]
                )
            
            if comparison["improved_system"]["total_frames"] > 0:
                comparison["improved_system"]["avg_processing_time"] = (
                    comparison["improved_system"]["total_processing_time"] / comparison["improved_system"]["total_frames"]
                )
            
            # Detailed frame-by-frame comparison
            for frame_key in current_results:
                if frame_key in improved_results:
                    current = current_results[frame_key]
                    improved = improved_results[frame_key]
                    
                    frame_comparison = {
                        "frame": frame_key,
                        "timestamp": current["timestamp"],
                        "current": {
                            "faces_detected": current["analysis"].get("total_faces", 0),
                            "faces_identified": current["analysis"].get("identified_faces", 0),
                            "processing_time": current["processing_time"]
                        },
                        "improved": {
                            "faces_detected": improved["analysis"].get("total_faces", 0) if not improved["analysis"].get("skipped") else 0,
                            "faces_identified": improved["analysis"].get("identified_faces", 0) if not improved["analysis"].get("skipped") else 0,
                            "processing_time": improved["processing_time"],
                            "skipped": improved["analysis"].get("skipped", False),
                            "reason": improved["analysis"].get("reason", "")
                        }
                    }
                    
                    comparison["detailed_comparison"].append(frame_comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing systems: {str(e)}")
            return {}
    
    def run_comprehensive_test(self, video_path: str):
        """Run comprehensive test comparing current vs improved systems."""
        logger.info(f"Starting comprehensive face recognition test for {video_path}")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Benchmark current system
        logger.info("Step 2: Benchmarking current face recognition system")
        current_results = self.benchmark_current_system(video_path, token)
        
        # Step 3: Test improved system
        logger.info("Step 3: Testing improved face recognition system")
        improved_results = self.test_improved_system(video_path, token)
        
        # Step 4: Compare systems
        logger.info("Step 4: Comparing systems")
        comparison = self.compare_systems(current_results, improved_results)
        
        # Step 5: Generate report
        logger.info("Step 5: Generating comprehensive test report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "current_system_results": current_results,
            "improved_system_results": improved_results,
            "comparison": comparison,
            "summary": self.generate_summary(comparison)
        }
        
        report_path = self.temp_dir / "improved_recognition_test_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_test_summary(report)
        
        logger.info(f"Comprehensive test completed!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def generate_summary(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the comparison."""
        try:
            current = comparison.get("current_system", {})
            improved = comparison.get("improved_system", {})
            
            summary = {
                "performance_improvement": {
                    "processing_time": {
                        "current": current.get("avg_processing_time", 0),
                        "improved": improved.get("avg_processing_time", 0),
                        "improvement_percent": 0
                    }
                },
                "accuracy_improvement": {
                    "identification_rate": {
                        "current": current.get("frames_with_identified", 0) / max(current.get("frames_with_faces", 1), 1),
                        "improved": improved.get("frames_with_identified", 0) / max(improved.get("frames_with_faces", 1), 1)
                    },
                    "total_identifications": {
                        "current": current.get("total_faces_identified", 0),
                        "improved": improved.get("total_faces_identified", 0)
                    }
                },
                "post_60s_filtering": {
                    "frames_skipped": improved.get("frames_skipped", 0),
                    "total_frames": improved.get("total_frames", 0),
                    "skip_rate": improved.get("frames_skipped", 0) / max(improved.get("total_frames", 1), 1)
                }
            }
            
            # Calculate improvement percentages
            current_time = current.get("avg_processing_time", 0)
            improved_time = improved.get("avg_processing_time", 0)
            if current_time > 0:
                summary["performance_improvement"]["processing_time"]["improvement_percent"] = (
                    ((current_time - improved_time) / current_time) * 100
                )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {}
    
    def print_test_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the test results."""
        print("\n" + "="*80)
        print("🚀 IMPROVED FACE RECOGNITION SYSTEM TEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        comparison = report['comparison']
        current = comparison['current_system']
        improved = comparison['improved_system']
        summary = report['summary']
        
        print(f"\n📊 SYSTEM COMPARISON:")
        print(f"   Current System:")
        print(f"     • Frames processed: {current['total_frames']}")
        print(f"     • Faces detected: {current['total_faces_detected']}")
        print(f"     • Faces identified: {current['total_faces_identified']}")
        print(f"     • Avg processing time: {current.get('avg_processing_time', 0):.3f}s")
        
        print(f"   Improved System:")
        print(f"     • Frames processed: {improved['total_frames']}")
        print(f"     • Frames skipped: {improved['frames_skipped']}")
        print(f"     • Faces detected: {improved['total_faces_detected']}")
        print(f"     • Faces identified: {improved['total_faces_identified']}")
        print(f"     • Avg processing time: {improved.get('avg_processing_time', 0):.3f}s")
        
        print(f"\n🎯 KEY IMPROVEMENTS:")
        perf_improvement = summary.get('performance_improvement', {}).get('processing_time', {})
        if perf_improvement.get('improvement_percent', 0) != 0:
            print(f"   • Processing time: {perf_improvement.get('improvement_percent', 0):.1f}% {'faster' if perf_improvement.get('improvement_percent', 0) > 0 else 'slower'}")
        
        post_60s = summary.get('post_60s_filtering', {})
        if post_60s.get('frames_skipped', 0) > 0:
            print(f"   • Post-60s filtering: {post_60s.get('frames_skipped', 0)} frames skipped ({post_60s.get('skip_rate', 0)*100:.1f}%)")
        
        print(f"\n📈 DETAILED FRAME COMPARISON:")
        for frame_comp in comparison['detailed_comparison']:
            timestamp = frame_comp['timestamp']
            current_data = frame_comp['current']
            improved_data = frame_comp['improved']
            
            print(f"   Frame {timestamp}s:")
            print(f"     Current: {current_data['faces_detected']} faces, {current_data['faces_identified']} identified ({current_data['processing_time']:.3f}s)")
            
            if improved_data['skipped']:
                print(f"     Improved: SKIPPED ({improved_data['reason']})")
            else:
                print(f"     Improved: {improved_data['faces_detected']} faces, {improved_data['faces_identified']} identified ({improved_data['processing_time']:.3f}s)")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Test report: {self.temp_dir}/improved_recognition_test_report.json")
        print(f"   • Extracted frames: Multiple frame files")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Improved Face Recognition System")
    parser.add_argument("--video-path", required=True, help="Path to video file for testing")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize test
    test = ImprovedRecognitionTest(base_url=args.base_url)
    
    try:
        # Run comprehensive test
        result = test.run_comprehensive_test(
            video_path=args.video_path
        )
        
        if result:
            print(f"\n✅ Improved recognition test completed!")
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
