#!/usr/bin/env python3
"""
Targeted Face Swapping Test for Identified Speaker

This script performs face swapping specifically on the identified speaker
from the Parliament TV video analysis.

Usage:
    python test_targeted_face_swap.py --identification-report "/path/to/speaker_identification_report.json"
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
logger = logging.getLogger("targeted_face_swap")

class TargetedFaceSwapTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="targeted_face_swap_"))
        logger.info(f"Initialized targeted face swap with temp directory: {self.temp_dir}")
        
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
    
    def load_identification_report(self, report_path: str) -> Dict[str, Any]:
        """Load the speaker identification report."""
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)
            logger.info(f"Loaded identification report: {report_path}")
            return report
        except Exception as e:
            logger.error(f"Failed to load identification report: {str(e)}")
            return {}
    
    def extract_best_frame_for_target(self, video_path: str, target_speaker: Dict[str, Any]) -> str:
        """Extract the best frame showing the target speaker."""
        try:
            # Find the frame with the highest confidence for the target speaker
            best_appearance = None
            best_confidence = 0
            
            for appearance in target_speaker.get("appearances", []):
                if appearance.get("confidence", 0) > best_confidence:
                    best_confidence = appearance["confidence"]
                    best_appearance = appearance
            
            if not best_appearance:
                logger.error("No good appearance found for target speaker")
                return None
            
            timestamp = best_appearance["timestamp"]
            output_path = self.temp_dir / f"target_frame_{timestamp}s.jpg"
            
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
                logger.error(f"Failed to extract frame at {timestamp}s: {result.stderr}")
                return None
            
            logger.info(f"Extracted best target frame at {timestamp}s: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error extracting best frame: {str(e)}")
            return None
    
    def perform_targeted_face_swap(self, frame_path: str, target_member_id: str, 
                                 enhancement_types: List[str], token: str) -> Dict[str, Any]:
        """Perform face swapping with multiple enhancement types on the target."""
        try:
            results = {}
            
            for enhancement_type in enhancement_types:
                logger.info(f"Performing {enhancement_type} enhancement for MP {target_member_id}")
                
                headers = {"Authorization": f"Bearer {token}"}
                
                # Copy frame to accessible location
                import shutil
                temp_frame_path = f"/tmp/target_{enhancement_type}_{target_member_id}.jpg"
                shutil.copy2(frame_path, temp_frame_path)
                
                with open(temp_frame_path, 'rb') as image_file:
                    files = {
                        'image': (os.path.basename(temp_frame_path), image_file, 'image/jpeg'),
                        'target_member_id': (None, target_member_id),
                        'enhancement_type': (None, enhancement_type),
                        'target_specific': (None, 'true')
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/api/v1/face-swap/intelligent-swap",
                        files=files,
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    swap_result = response.json()
                    
                    # Copy the result to our temp directory
                    output_path = self.temp_dir / f"target_{enhancement_type}_{target_member_id}.jpg"
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
                    
                    logger.info(f"{enhancement_type} enhancement completed: {results[enhancement_type]}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing targeted face swap: {str(e)}")
            return {}
    
    def create_comprehensive_comparison(self, original_path: str, enhancement_results: Dict[str, Any],
                                      target_speaker: Dict[str, Any]) -> str:
        """Create a comprehensive comparison showing all enhancements."""
        try:
            # Load original image
            original = cv2.imread(original_path)
            if original is None:
                logger.error("Failed to load original image")
                return None
            
            # Create a grid layout: original + all enhancements
            enhancement_types = list(enhancement_results.keys())
            cols = len(enhancement_types) + 1  # +1 for original
            rows = 1
            
            # Resize all images to same height
            target_height = 400
            original_resized = cv2.resize(original, (int(original.shape[1] * target_height / original.shape[0]), target_height))
            
            # Create row with original and enhancements
            row_images = [original_resized]
            
            for enhancement_type in enhancement_types:
                result = enhancement_results[enhancement_type]
                if result.get("success") and os.path.exists(result["output_path"]):
                    enhanced = cv2.imread(result["output_path"])
                    if enhanced is not None:
                        enhanced_resized = cv2.resize(enhanced, (int(enhanced.shape[1] * target_height / enhanced.shape[0]), target_height))
                        row_images.append(enhanced_resized)
                    else:
                        # Create placeholder if image loading failed
                        placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                        cv2.putText(placeholder, f"{enhancement_type.upper()}\nFAILED", 
                                   (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        row_images.append(placeholder)
                else:
                    # Create placeholder for failed enhancement
                    placeholder = np.zeros((target_height, original_resized.shape[1], 3), dtype=np.uint8)
                    cv2.putText(placeholder, f"{enhancement_type.upper()}\nNO TARGET", 
                               (50, target_height//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    row_images.append(placeholder)
            
            # Concatenate horizontally
            comparison = np.hstack(row_images)
            
            # Add labels
            labels = ["ORIGINAL"] + [enh.upper() for enh in enhancement_types]
            label_width = comparison.shape[1] // len(labels)
            
            for i, label in enumerate(labels):
                x_pos = i * label_width + 20
                cv2.putText(comparison, label, (x_pos, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            
            # Add speaker information
            speaker_info = f"Target: {target_speaker.get('name', 'Unknown')} (ID: {target_speaker.get('member_id', 'Unknown')})"
            cv2.putText(comparison, speaker_info, (20, comparison.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Save comparison
            comparison_path = self.temp_dir / "comprehensive_target_comparison.jpg"
            cv2.imwrite(str(comparison_path), comparison)
            
            logger.info(f"Created comprehensive comparison: {comparison_path}")
            return str(comparison_path)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive comparison: {str(e)}")
            return None
    
    def run_targeted_face_swap_test(self, identification_report_path: str):
        """Run the complete targeted face swapping test."""
        logger.info(f"Starting targeted face swap test using report: {identification_report_path}")
        
        # Step 1: Load identification report
        logger.info("Step 1: Loading speaker identification report")
        identification_report = self.load_identification_report(identification_report_path)
        
        if not identification_report:
            logger.error("Failed to load identification report")
            return False
        
        # Step 2: Extract target speaker information
        logger.info("Step 2: Extracting target speaker information")
        target_selection = identification_report.get("target_selection", {})
        
        if not target_selection.get("success"):
            logger.error("No target speaker selected in identification report")
            return False
        
        target_speaker = target_selection["selected_speaker"]
        target_member_id = target_speaker["member_id"]
        video_path = identification_report["video_path"]
        
        logger.info(f"Target speaker: {target_speaker['name']} (ID: {target_member_id})")
        
        # Step 3: Extract best frame showing target speaker
        logger.info("Step 3: Extracting best frame showing target speaker")
        target_frame = self.extract_best_frame_for_target(video_path, target_speaker)
        
        if not target_frame:
            logger.error("Failed to extract target frame")
            return False
        
        # Step 4: Get authentication token
        logger.info("Step 4: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 5: Perform targeted face swapping
        logger.info("Step 5: Performing targeted face swapping")
        enhancement_types = ["smooth", "sharpen", "beautify", "cartoon", "age"]
        enhancement_results = self.perform_targeted_face_swap(
            target_frame, target_member_id, enhancement_types, token
        )
        
        # Step 6: Create comprehensive comparison
        logger.info("Step 6: Creating comprehensive comparison")
        comparison_path = self.create_comprehensive_comparison(
            target_frame, enhancement_results, target_speaker
        )
        
        # Step 7: Generate final report
        logger.info("Step 7: Generating final report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "identification_report": identification_report_path,
            "target_speaker": target_speaker,
            "target_frame": target_frame,
            "enhancement_results": enhancement_results,
            "comparison_path": comparison_path,
            "summary": {
                "target_member_id": target_member_id,
                "target_name": target_speaker.get("name", "Unknown"),
                "enhancements_tested": len(enhancement_types),
                "successful_enhancements": sum(1 for r in enhancement_results.values() if r.get("success")),
                "target_faces_processed": sum(r.get("faces_processed", 0) for r in enhancement_results.values())
            }
        }
        
        report_path = self.temp_dir / "targeted_face_swap_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_targeted_swap_summary(report)
        
        logger.info(f"Targeted face swap test completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_targeted_swap_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the targeted face swap results."""
        print("\n" + "="*80)
        print("🎭 TARGETED FACE SWAPPING TEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Source video: {report['identification_report']}")
        
        target = report['target_speaker']
        print(f"\n🎯 TARGET SPEAKER:")
        print(f"   • Name: {target.get('name', 'Unknown')}")
        print(f"   • Member ID: {target.get('member_id', 'Unknown')}")
        print(f"   • Max confidence: {target.get('max_confidence', 0):.3f}")
        print(f"   • Appearances: {len(target.get('appearances', []))}")
        
        print(f"\n🎨 ENHANCEMENT RESULTS:")
        for enhancement_type, result in report['enhancement_results'].items():
            if result.get("success"):
                print(f"   • {enhancement_type.upper()}: ✅ Success")
                print(f"     → Faces detected: {result.get('faces_detected', 0)}")
                print(f"     → Target faces found: {result.get('target_faces_found', 0)}")
                print(f"     → Faces processed: {result.get('faces_processed', 0)}")
            else:
                print(f"   • {enhancement_type.upper()}: ❌ Failed")
                print(f"     → Message: {result.get('message', 'Unknown error')}")
        
        summary = report['summary']
        print(f"\n📊 SUMMARY:")
        print(f"   • Enhancements tested: {summary['enhancements_tested']}")
        print(f"   • Successful enhancements: {summary['successful_enhancements']}")
        print(f"   • Total faces processed: {summary['target_faces_processed']}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Target frame: {report['target_frame']}")
        print(f"   • Comprehensive comparison: {report['comparison_path']}")
        print(f"   • Test report: {self.temp_dir}/targeted_face_swap_report.json")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Targeted Face Swapping Test")
    parser.add_argument("--identification-report", required=True, 
                       help="Path to speaker identification report JSON file")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize targeted face swap test
    test = TargetedFaceSwapTest(base_url=args.base_url)
    
    try:
        # Run targeted face swap test
        result = test.run_targeted_face_swap_test(
            identification_report=args.identification_report
        )
        
        if result:
            print(f"\n✅ Targeted face swap test completed successfully!")
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
