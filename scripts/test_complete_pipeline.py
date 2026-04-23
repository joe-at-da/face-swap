#!/usr/bin/env python3
"""
Complete Parliament TV Face Pipeline Test

This script demonstrates the complete pipeline from video capture to face swapping,
including speaker identification and targeted face enhancement.

Usage:
    python test_complete_pipeline.py --video-path "/app/data/temp/test_combined.mp4" --start-time 5
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
logger = logging.getLogger("complete_pipeline")

class CompletePipelineTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="complete_pipeline_"))
        logger.info(f"Initialized complete pipeline with temp directory: {self.temp_dir}")
        
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
    
    def extract_frames_from_video(self, video_path: str, start_time: int = 5, 
                                 frame_count: int = 3, frame_interval: int = 2) -> List[str]:
        """Extract frames from video for analysis."""
        try:
            frame_paths = []
            
            for i in range(frame_count):
                timestamp = start_time + (i * frame_interval)
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
                    logger.warning(f"Failed to extract frame at {timestamp}s: {result.stderr}")
            
            logger.info(f"Extracted {len(frame_paths)} frames")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def analyze_faces_in_frames(self, frame_paths: List[str], token: str) -> List[Dict[str, Any]]:
        """Analyze faces in multiple frames."""
        try:
            frame_analyses = []
            
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
                    frame_analyses.append(analysis)
            
            return frame_analyses
            
        except Exception as e:
            logger.error(f"Error analyzing faces: {str(e)}")
            return []
    
    def select_best_frame_and_target(self, frame_analyses: List[Dict[str, Any]], 
                                   frame_paths: List[str]) -> Tuple[str, str, Dict[str, Any]]:
        """Select the best frame and target for face swapping."""
        try:
            best_frame_index = 0
            best_face_count = 0
            identified_target = None
            
            for i, analysis in enumerate(frame_analyses):
                if analysis.get("success"):
                    face_count = analysis.get("total_faces", 0)
                    if face_count > best_face_count:
                        best_face_count = face_count
                        best_frame_index = i
                    
                    # Check if any faces are identified
                    for face_detail in analysis.get("face_details", []):
                        if face_detail.get("identified_mp"):
                            identified_target = face_detail["identified_mp"]
                            break
            
            # Use the best frame
            best_frame_path = frame_paths[best_frame_index]
            
            # Use identified target or fallback to MP 115
            if identified_target:
                target_member_id = identified_target.get("member_id", "115")
                target_name = identified_target.get("name", f"MP {target_member_id}")
                target_confidence = identified_target.get("confidence", 0)
            else:
                target_member_id = "115"
                target_name = "MP 115 (Fallback)"
                target_confidence = 0
            
            target_info = {
                "member_id": target_member_id,
                "name": target_name,
                "confidence": target_confidence,
                "is_identified": identified_target is not None,
                "face_count": best_face_count
            }
            
            logger.info(f"Selected frame {best_frame_index}: {best_frame_path}")
            logger.info(f"Target: {target_name} (ID: {target_member_id})")
            
            return best_frame_path, target_member_id, target_info
            
        except Exception as e:
            logger.error(f"Error selecting frame and target: {str(e)}")
            return None, "115", {"member_id": "115", "name": "MP 115 (Fallback)", "confidence": 0, "is_identified": False, "face_count": 0}
    
    def perform_face_enhancement_pipeline(self, frame_path: str, target_member_id: str, 
                                         target_info: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Perform the complete face enhancement pipeline."""
        try:
            enhancement_types = ["smooth", "sharpen", "beautify", "cartoon", "age"]
            results = {}
            
            logger.info(f"Starting face enhancement pipeline for {target_info['name']}")
            
            for enhancement_type in enhancement_types:
                logger.info(f"Testing {enhancement_type} enhancement")
                
                headers = {"Authorization": f"Bearer {token}"}
                
                # Copy frame to accessible location
                import shutil
                temp_frame_path = f"/tmp/pipeline_{enhancement_type}_{target_member_id}.jpg"
                shutil.copy2(frame_path, temp_frame_path)
                
                with open(temp_frame_path, 'rb') as image_file:
                    files = {
                        'image': (os.path.basename(temp_frame_path), image_file, 'image/jpeg'),
                        'target_member_id': (None, target_member_id),
                        'enhancement_type': (None, enhancement_type),
                        'target_specific': (None, 'true' if target_info['is_identified'] else 'false')
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/api/v1/face-swap/intelligent-swap",
                        files=files,
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    swap_result = response.json()
                    
                    # Copy the result to our temp directory
                    output_path = self.temp_dir / f"pipeline_{enhancement_type}_{target_member_id}.jpg"
                    try:
                        shutil.copy2(swap_result['output_path'], output_path)
                    except:
                        # Fallback to HTTP download
                        swap_response = requests.get(
                            f"{self.base_url}/api/v1/face-swap/image{swap_result['output_path']}",
                            headers=headers
                        )
                        swap_response.raise_for_status()
                        
                        with open(output_path, 'wb') as f:
                            f.write(swap_response.content)
                    
                    # Clean up
                    try:
                        os.unlink(temp_frame_path)
                    except:
                        pass
                    
                    results[enhancement_type] = {
                        "success": swap_result.get("success", False),
                        "faces_detected": swap_result.get("faces_detected", 0),
                        "target_faces_found": swap_result.get("target_faces_found", 0),
                        "faces_processed": swap_result.get("faces_processed", 0),
                        "output_path": str(output_path),
                        "message": swap_result.get("message", "")
                    }
                    
                    logger.info(f"{enhancement_type} enhancement: {results[enhancement_type]['faces_processed']} faces processed")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in face enhancement pipeline: {str(e)}")
            return {}
    
    def create_comprehensive_comparison(self, original_path: str, enhancement_results: Dict[str, Any],
                                      target_info: Dict[str, Any], frame_analyses: List[Dict[str, Any]]) -> str:
        """Create a comprehensive comparison showing the complete pipeline."""
        try:
            # Load original image
            original = cv2.imread(original_path)
            if original is None:
                logger.error("Failed to load original image")
                return None
            
            # Create a 2x3 grid layout: original + 5 enhancements
            enhancement_types = list(enhancement_results.keys())
            
            # Resize all images to same height
            target_height = 300
            original_resized = cv2.resize(original, (int(original.shape[1] * target_height / original.shape[0]), target_height))
            
            # Create grid (2 rows, 3 columns)
            row1_images = [original_resized]
            row2_images = []
            
            # Add first 2 enhancements to first row
            for enhancement_type in enhancement_types[:2]:
                result = enhancement_results[enhancement_type]
                if result.get("success") and os.path.exists(result["output_path"]):
                    enhanced = cv2.imread(result["output_path"])
                    if enhanced is not None:
                        enhanced_resized = cv2.resize(enhanced, (int(enhanced.shape[1] * target_height / enhanced.shape[0]), target_height))
                        row1_images.append(enhanced_resized)
                    else:
                        placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                        cv2.putText(placeholder, f"{enhancement_type.upper()}\nFAILED", 
                                   (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        row1_images.append(placeholder)
                else:
                    placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                    cv2.putText(placeholder, f"{enhancement_type.upper()}\nNO TARGET", 
                               (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    row1_images.append(placeholder)
            
            # Add remaining enhancements to second row
            for enhancement_type in enhancement_types[2:]:
                result = enhancement_results[enhancement_type]
                if result.get("success") and os.path.exists(result["output_path"]):
                    enhanced = cv2.imread(result["output_path"])
                    if enhanced is not None:
                        enhanced_resized = cv2.resize(enhanced, (int(enhanced.shape[1] * target_height / enhanced.shape[0]), target_height))
                        row2_images.append(enhanced_resized)
                    else:
                        placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                        cv2.putText(placeholder, f"{enhancement_type.upper()}\nFAILED", 
                                   (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        row2_images.append(placeholder)
                else:
                    placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                    cv2.putText(placeholder, f"{enhancement_type.upper()}\nNO TARGET", 
                               (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    row2_images.append(placeholder)
            
            # Add empty placeholder to make 3 columns in second row if needed
            while len(row2_images) < 3:
                placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                row2_images.append(placeholder)
            
            # Concatenate rows
            row1 = np.hstack(row1_images)
            row2 = np.hstack(row2_images)
            comparison = np.vstack([row1, row2])
            
            # Add labels for first row
            labels = ["ORIGINAL"] + [enh.upper() for enh in enhancement_types[:2]]
            label_width = comparison.shape[1] // 3
            
            for i, label in enumerate(labels):
                x_pos = i * label_width + 20
                cv2.putText(comparison, label, (x_pos, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            
            # Add labels for second row
            labels2 = [enh.upper() for enh in enhancement_types[2:3]]
            for i, label in enumerate(labels2):
                x_pos = i * label_width + 20
                cv2.putText(comparison, label, (x_pos, target_height + 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            
            # Add comprehensive information
            total_faces = sum(analysis.get("total_faces", 0) for analysis in frame_analyses)
            identified_faces = sum(analysis.get("identified_faces", 0) for analysis in frame_analyses)
            
            info_lines = [
                f"Target: {target_info['name']} (ID: {target_info['member_id']})",
                f"Identified: {'Yes' if target_info['is_identified'] else 'No'}",
                f"Faces in video: {total_faces} total, {identified_faces} identified",
                f"Enhancements: {sum(1 for r in enhancement_results.values() if r.get('success'))}/{len(enhancement_results)} successful"
            ]
            
            y_offset = comparison.shape[0] - 80
            for line in info_lines:
                cv2.putText(comparison, line, (20, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 20
            
            # Save comparison
            comparison_path = self.temp_dir / "complete_pipeline_comparison.jpg"
            cv2.imwrite(str(comparison_path), comparison)
            
            logger.info(f"Created comprehensive comparison: {comparison_path}")
            return str(comparison_path)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive comparison: {str(e)}")
            return None
    
    def run_complete_pipeline_test(self, video_path: str, start_time: int = 5):
        """Run the complete Parliament TV face pipeline test."""
        logger.info(f"Starting complete pipeline test for {video_path}")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Extract frames from video
        logger.info("Step 2: Extracting frames from video")
        frame_paths = self.extract_frames_from_video(video_path, start_time)
        
        if not frame_paths:
            logger.error("No frames extracted")
            return False
        
        # Step 3: Analyze faces in frames
        logger.info("Step 3: Analyzing faces in extracted frames")
        frame_analyses = self.analyze_faces_in_frames(frame_paths, token)
        
        # Step 4: Select best frame and target
        logger.info("Step 4: Selecting best frame and target")
        best_frame, target_member_id, target_info = self.select_best_frame_and_target(frame_analyses, frame_paths)
        
        if not best_frame:
            logger.error("No suitable frame selected")
            return False
        
        # Step 5: Perform face enhancement pipeline
        logger.info("Step 5: Performing face enhancement pipeline")
        enhancement_results = self.perform_face_enhancement_pipeline(best_frame, target_member_id, target_info, token)
        
        # Step 6: Create comprehensive comparison
        logger.info("Step 6: Creating comprehensive comparison")
        comparison_path = self.create_comprehensive_comparison(best_frame, enhancement_results, target_info, frame_analyses)
        
        # Step 7: Generate final report
        logger.info("Step 7: Generating final report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "analysis_parameters": {
                "start_time": start_time,
                "frames_extracted": len(frame_paths),
                "frame_interval": 2
            },
            "frame_analyses": frame_analyses,
            "target_selection": target_info,
            "enhancement_results": enhancement_results,
            "comparison_path": comparison_path,
            "summary": {
                "total_frames_analyzed": len(frame_analyses),
                "total_faces_detected": sum(analysis.get("total_faces", 0) for analysis in frame_analyses),
                "identified_faces": sum(analysis.get("identified_faces", 0) for analysis in frame_analyses),
                "target_member_id": target_member_id,
                "target_name": target_info["name"],
                "target_identified": target_info["is_identified"],
                "enhancements_tested": len(enhancement_results),
                "successful_enhancements": sum(1 for r in enhancement_results.values() if r.get("success")),
                "total_faces_processed": sum(r.get("faces_processed", 0) for r in enhancement_results.values())
            }
        }
        
        report_path = self.temp_dir / "complete_pipeline_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_pipeline_summary(report)
        
        logger.info(f"Complete pipeline test completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_pipeline_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the complete pipeline results."""
        print("\n" + "="*80)
        print("🎬 COMPLETE PARLIAMENT TV FACE PIPELINE RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        params = report['analysis_parameters']
        print(f"\n⚙️  Pipeline Parameters:")
        print(f"   • Start time: {params['start_time']}s")
        print(f"   • Frames extracted: {params['frames_extracted']}")
        print(f"   • Frame interval: {params['frame_interval']}s")
        
        summary = report['summary']
        print(f"\n🔍 Face Analysis Results:")
        print(f"   • Total frames analyzed: {summary['total_frames_analyzed']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Identified faces: {summary['identified_faces']}")
        
        target = report['target_selection']
        print(f"\n🎯 Target Selection:")
        print(f"   • Name: {target['name']}")
        print(f"   • Member ID: {target['member_id']}")
        print(f"   • Identified: {'Yes' if target['is_identified'] else 'No'}")
        print(f"   • Face count: {target['face_count']}")
        
        print(f"\n🎨 Enhancement Results:")
        for enhancement_type, result in report['enhancement_results'].items():
            if result.get("success"):
                print(f"   • {enhancement_type.upper()}: ✅ {result.get('faces_processed', 0)} faces processed")
            else:
                print(f"   • {enhancement_type.upper()}: ❌ {result.get('message', 'Failed')}")
        
        print(f"\n📊 Pipeline Summary:")
        print(f"   • Enhancements tested: {summary['enhancements_tested']}")
        print(f"   • Successful enhancements: {summary['successful_enhancements']}")
        print(f"   • Total faces processed: {summary['total_faces_processed']}")
        print(f"   • Target identified: {'Yes' if summary['target_identified'] else 'No (used fallback)'}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Comprehensive comparison: {report['comparison_path']}")
        print(f"   • Pipeline report: {self.temp_dir}/complete_pipeline_report.json")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Complete Parliament TV Face Pipeline Test")
    parser.add_argument("--video-path", required=True, help="Path to video file")
    parser.add_argument("--start-time", type=int, default=5, help="Start time for analysis (seconds)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize complete pipeline test
    test = CompletePipelineTest(base_url=args.base_url)
    
    try:
        # Run complete pipeline test
        result = test.run_complete_pipeline_test(
            video_path=args.video_path,
            start_time=args.start_time
        )
        
        if result:
            print(f"\n✅ Complete pipeline test finished successfully!")
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
