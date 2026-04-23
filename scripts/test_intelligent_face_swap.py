#!/usr/bin/env python3
"""
Intelligent Face Swap Demonstration

This script demonstrates the improved face swapping system that:
1. Identifies specific faces using face recognition
2. Targets only the matching person instead of all faces
3. Applies enhancement filters instead of replacement
4. Shows detailed face analysis and confidence scores

Usage:
    python test_intelligent_face_swap.py --video-path "/app/data/temp/test_combined.mp4" --target-member-id "115"
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
logger = logging.getLogger("intelligent_demo")

class IntelligentFaceSwapDemo:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="intelligent_demo_"))
        logger.info(f"Initialized intelligent demo with temp directory: {self.temp_dir}")
        
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
    
    def extract_frame_for_analysis(self, video_path: str, timestamp: int = 5) -> str:
        """Extract a frame for face analysis."""
        try:
            output_path = self.temp_dir / f"analysis_frame_{timestamp}s.jpg"
            
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
            
            logger.info(f"Extracted frame for analysis: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error extracting frame: {str(e)}")
            return None
    
    def analyze_faces_detailed(self, image_path: str, token: str) -> Dict[str, Any]:
        """Perform detailed face analysis using the intelligent API."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            with open(image_path, 'rb') as image_file:
                files = {'image': (os.path.basename(image_path), image_file, 'image/jpeg')}
                
                response = requests.post(
                    f"{self.base_url}/api/v1/face-swap/analyze-faces",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                analysis = response.json()
                logger.info(f"Face analysis completed: {analysis.get('total_faces', 0)} faces found")
                return analysis
                
        except Exception as e:
            logger.error(f"Failed to analyze faces: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def perform_intelligent_face_swap(self, image_path: str, target_member_id: str, 
                                    enhancement_type: str, target_specific: bool, token: str) -> Dict[str, Any]:
        """Perform intelligent face swapping with enhancement."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Copy image to accessible location
            import shutil
            temp_image_path = f"/tmp/intelligent_{target_member_id}.jpg"
            shutil.copy2(image_path, temp_image_path)
            
            with open(temp_image_path, 'rb') as image_file:
                files = {
                    'image': (os.path.basename(temp_image_path), image_file, 'image/jpeg'),
                    'target_member_id': (None, target_member_id),
                    'enhancement_type': (None, enhancement_type),
                    'target_specific': (None, str(target_specific))
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/face-swap/intelligent-swap",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                swap_result = response.json()
                
                # Copy the result to our temp directory
                output_path = self.temp_dir / f"intelligent_{enhancement_type}_{target_member_id}.jpg"
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
                    os.unlink(temp_image_path)
                except:
                    pass
                
                logger.info(f"Intelligent face swap completed: {swap_result.get('faces_processed', 0)} faces processed")
                return swap_result
                
        except Exception as e:
            logger.error(f"Failed to perform intelligent face swap: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_comparison_visualization(self, original_path: str, enhanced_path: str, 
                                     enhancement_type: str, analysis: Dict) -> str:
        """Create a detailed comparison visualization with annotations."""
        try:
            # Load images
            original = cv2.imread(original_path)
            enhanced = cv2.imread(enhanced_path)
            
            if original is None or enhanced is None:
                logger.error("Failed to load images for comparison")
                return None
            
            # Ensure images have the same height
            height = max(original.shape[0], enhanced.shape[0])
            original = cv2.resize(original, (int(original.shape[1] * height / original.shape[0]), height))
            enhanced = cv2.resize(enhanced, (int(enhanced.shape[1] * height / enhanced.shape[0]), height))
            
            # Create side-by-side comparison
            comparison = np.hstack([original, enhanced])
            
            # Add labels and annotations
            cv2.putText(comparison, "ORIGINAL", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(comparison, f"ENHANCED ({enhancement_type.upper()})", (original.shape[1] + 20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            # Add face analysis information
            y_offset = 80
            cv2.putText(comparison, f"Faces Detected: {analysis.get('total_faces', 0)}", 
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            y_offset += 30
            cv2.putText(comparison, f"Identified: {analysis.get('identified_faces', 0)}", 
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            y_offset += 30
            cv2.putText(comparison, f"Unidentified: {analysis.get('unidentified_faces', 0)}", 
                       (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add face details on the right side
            y_offset = 80
            for i, face_detail in enumerate(analysis.get('face_details', [])[:3]):
                face_text = f"Face {i+1}: {face_detail.get('size', 'Unknown')}"
                if face_detail.get('identified_mp'):
                    mp_info = face_detail['identified_mp']
                    face_text += f" -> {mp_info.get('name', 'Unknown')} ({mp_info.get('confidence', 0):.2f})"
                else:
                    face_text += " -> Unidentified"
                
                cv2.putText(comparison, face_text, 
                           (original.shape[1] + 20, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                y_offset += 25
            
            # Save comparison
            comparison_path = self.temp_dir / f"intelligent_comparison_{enhancement_type}.jpg"
            cv2.imwrite(str(comparison_path), comparison)
            
            logger.info(f"Created intelligent comparison: {comparison_path}")
            return str(comparison_path)
            
        except Exception as e:
            logger.error(f"Error creating comparison: {str(e)}")
            return None
    
    def run_intelligent_demo(self, video_path: str, target_member_id: str):
        """Run the complete intelligent face swapping demonstration."""
        logger.info("Starting intelligent face swapping demonstration")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Extract frame for analysis
        logger.info("Step 2: Extracting frame for analysis")
        analysis_frame = self.extract_frame_for_analysis(video_path)
        if not analysis_frame:
            logger.error("Failed to extract frame for analysis")
            return False
        
        # Step 3: Perform detailed face analysis
        logger.info("Step 3: Performing detailed face analysis")
        face_analysis = self.analyze_faces_detailed(analysis_frame, token)
        
        if not face_analysis.get("success"):
            logger.error("Face analysis failed")
            return False
        
        # Step 4: Test different enhancement types
        enhancement_types = ["smooth", "sharpen", "beautify", "cartoon", "age"]
        results = {}
        
        for enhancement_type in enhancement_types:
            logger.info(f"Step 4.{enhancement_types.index(enhancement_type) + 1}: Testing {enhancement_type} enhancement")
            
            swap_result = self.perform_intelligent_face_swap(
                analysis_frame, target_member_id, enhancement_type, True, token
            )
            
            if swap_result.get("success"):
                # Create comparison visualization
                comparison_path = self.create_comparison_visualization(
                    analysis_frame, swap_result["output_path"], enhancement_type, face_analysis
                )
                
                results[enhancement_type] = {
                    "swap_result": swap_result,
                    "comparison_path": comparison_path,
                    "success": True
                }
            else:
                results[enhancement_type] = {
                    "swap_result": swap_result,
                    "success": False
                }
        
        # Step 5: Generate comprehensive report
        logger.info("Step 5: Generating comprehensive report")
        report = {
            "demonstration_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "target_member_id": target_member_id,
            "face_analysis": face_analysis,
            "enhancement_results": results,
            "summary": {
                "total_faces": face_analysis.get("total_faces", 0),
                "identified_faces": face_analysis.get("identified_faces", 0),
                "target_faces_found": sum(1 for r in results.values() 
                                        if r.get("success") and r.get("swap_result", {}).get("target_faces_found", 0) > 0),
                "successful_enhancements": sum(1 for r in results.values() if r.get("success"))
            }
        }
        
        report_path = self.temp_dir / "intelligent_demo_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print detailed summary
        self.print_intelligent_demo_summary(report)
        
        logger.info(f"Intelligent demo completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return True
    
    def print_intelligent_demo_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the intelligent demonstration results."""
        print("\n" + "="*80)
        print("🧠 INTELLIGENT FACE SWAPPING DEMONSTRATION RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        print(f"🎯 Target MP: {report['target_member_id']}")
        
        analysis = report['face_analysis']
        print(f"\n🔍 FACE ANALYSIS RESULTS:")
        print(f"   • Total faces detected: {analysis.get('total_faces', 0)}")
        print(f"   • Identified faces: {analysis.get('identified_faces', 0)}")
        print(f"   • Unidentified faces: {analysis.get('unidentified_faces', 0)}")
        
        print(f"\n👥 FACE DETAILS:")
        for i, face_detail in enumerate(analysis.get('face_details', [])[:3]):
            print(f"   • Face {i+1}: Size {face_detail.get('size', 'Unknown')}")
            if face_detail.get('identified_mp'):
                mp_info = face_detail['identified_mp']
                print(f"     → Identified as: {mp_info.get('name', 'Unknown')}")
                print(f"     → Confidence: {mp_info.get('confidence', 0):.3f}")
                print(f"     → Member ID: {mp_info.get('member_id', 'Unknown')}")
            else:
                print(f"     → Status: Unidentified")
        
        print(f"\n🎨 ENHANCEMENT RESULTS:")
        for enhancement_type, result in report['enhancement_results'].items():
            if result.get("success"):
                swap_result = result["swap_result"]
                print(f"   • {enhancement_type.upper()}: ✅ Success")
                print(f"     → Faces detected: {swap_result.get('faces_detected', 0)}")
                print(f"     → Target faces found: {swap_result.get('target_faces_found', 0)}")
                print(f"     → Faces processed: {swap_result.get('faces_processed', 0)}")
                print(f"     → Comparison: {result.get('comparison_path', 'N/A')}")
            else:
                print(f"   • {enhancement_type.upper()}: ❌ Failed")
                print(f"     → Error: {result.get('swap_result', {}).get('error', 'Unknown')}")
        
        summary = report['summary']
        print(f"\n📊 SUMMARY:")
        print(f"   • Total faces in frame: {summary['total_faces']}")
        print(f"   • Successfully identified: {summary['identified_faces']}")
        print(f"   • Target faces found: {summary['target_faces_found']}")
        print(f"   • Successful enhancements: {summary['successful_enhancements']}/5")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Analysis frame: {self.temp_dir}/analysis_frame_5s.jpg")
        for enhancement_type, result in report['enhancement_results'].items():
            if result.get("success") and result.get("comparison_path"):
                print(f"   • {enhancement_type} comparison: {result['comparison_path']}")
        
        print(f"\n📋 Complete report: {self.temp_dir}/intelligent_demo_report.json")
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Intelligent Face Swapping Demonstration")
    parser.add_argument("--video-path", required=True, help="Path to existing captured video file")
    parser.add_argument("--target-member-id", required=True, help="Target MP member ID for face enhancement")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize demo
    demo = IntelligentFaceSwapDemo(base_url=args.base_url)
    
    try:
        # Run intelligent demonstration
        success = demo.run_intelligent_demo(
            video_path=args.video_path,
            target_member_id=args.target_member_id
        )
        
        if success:
            print(f"\n✅ Intelligent demonstration completed successfully!")
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
