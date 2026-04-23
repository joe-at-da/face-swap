#!/usr/bin/env python3
"""
Complete Parliament TV Face Swap Workflow Test using Existing Video

This script demonstrates the complete end-to-end workflow using an existing captured video:
1. Use existing captured Parliament TV video
2. Extract frames from the video
3. Perform face recognition to identify speakers
4. Swap faces with target MP faces
5. Generate final face-swapped content

Usage:
    python test_existing_workflow.py --video-path "/app/data/temp/capture_1776946643.mp4" --target-member-id "115"
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("existing_workflow")

class ParliamentTVFaceSwapWorkflow:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.temp_dir = Path(tempfile.mkdtemp(prefix="parliament_workflow_"))
        logger.info(f"Initialized workflow with temp directory: {self.temp_dir}")
        
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
    
    def extract_frame_from_video(self, video_path, timestamp=5):
        """Extract a frame from the captured video at the specified timestamp."""
        try:
            output_path = self.temp_dir / f"frame_{timestamp}s.jpg"
            
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
            
            logger.info(f"Extracted frame from video at {timestamp}s: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error extracting frame: {str(e)}")
            return None
    
    def perform_face_recognition(self, video_path, token=None):
        """Perform face recognition on the video."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            data = {
                "video_path": video_path,
                "output_format": "json"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/facial-recognition/test",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            recognition_data = response.json()
            logger.info(f"Face recognition completed: {recognition_data}")
            return recognition_data
            
        except Exception as e:
            logger.error(f"Failed to perform face recognition: {str(e)}")
            return None
    
    def perform_face_swap(self, image_path, target_member_id, token=None):
        """Perform face swapping on the extracted frame."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Copy the image to a temporary location accessible by the API
            import shutil
            temp_image_path = f"/tmp/workface_{target_member_id}.jpg"
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
                logger.info(f"Face swap completed: {swap_data}")
                
                # Copy the swapped image directly from container temp location
                output_path = self.temp_dir / f"face_swapped_{target_member_id}.jpg"
                try:
                    shutil.copy2(swap_data['output_path'], output_path)
                    logger.info(f"Copied face-swapped image from: {swap_data['output_path']}")
                except Exception as copy_error:
                    logger.warning(f"Could not copy directly, trying HTTP download: {copy_error}")
                    # Fallback to HTTP download
                    swap_response = requests.get(
                        f"{self.base_url}/api/v1/face-swap/image{swap_data['output_path']}",
                        headers=headers
                    )
                    swap_response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(swap_response.content)
                
                # Clean up temporary file
                try:
                    os.unlink(temp_image_path)
                except:
                    pass
                
                logger.info(f"Downloaded face-swapped image: {output_path}")
                return str(output_path), swap_data
                
        except Exception as e:
            logger.error(f"Failed to perform face swap: {str(e)}")
            return None, None
    
    def run_complete_workflow(self, video_path, target_member_id):
        """Run the complete Parliament TV face swap workflow using existing video."""
        logger.info("Starting complete Parliament TV face swap workflow with existing video")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Verify video exists
        logger.info("Step 2: Verifying captured video exists")
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        logger.info(f"Using existing captured video: {video_path}")
        
        # Step 3: Perform face recognition on the video
        logger.info("Step 3: Performing face recognition on video")
        recognition_results = self.perform_face_recognition(video_path, token)
        if recognition_results:
            logger.info(f"Face recognition results: {len(recognition_results.get('recognized_speakers', []))} speakers identified")
        else:
            logger.warning("Face recognition failed, continuing with face swap test")
        
        # Step 4: Extract frame from video
        logger.info("Step 4: Extracting frame from video")
        frame_path = self.extract_frame_from_video(video_path)
        if not frame_path:
            logger.error("Failed to extract frame from video")
            return False
        
        # Step 5: Perform face swapping
        logger.info("Step 5: Performing face swapping")
        swapped_path, swap_data = self.perform_face_swap(frame_path, target_member_id, token)
        if not swapped_path:
            logger.error("Failed to perform face swapping")
            return False
        
        # Step 6: Generate workflow report
        logger.info("Step 6: Generating workflow report")
        report = {
            "workflow_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "target_member_id": target_member_id,
            "frame_path": frame_path,
            "swapped_path": swapped_path,
            "face_recognition_results": recognition_results,
            "face_swap_results": swap_data,
            "temp_directory": str(self.temp_dir)
        }
        
        report_path = self.temp_dir / "workflow_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Complete workflow finished successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Original frame: {frame_path}")
        logger.info(f"Face-swapped image: {swapped_path}")
        
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Complete Parliament TV Face Swap Workflow using Existing Video")
    parser.add_argument("--video-path", required=True, help="Path to existing captured video file")
    parser.add_argument("--target-member-id", required=True, help="Target MP member ID for face swapping")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize workflow
    workflow = ParliamentTVFaceSwapWorkflow(base_url=args.base_url)
    
    try:
        # Run complete workflow
        success = workflow.run_complete_workflow(
            video_path=args.video_path,
            target_member_id=args.target_member_id
        )
        
        if success:
            print("\n✅ Complete workflow finished successfully!")
            print(f"📁 Results saved in: {workflow.temp_dir}")
            print(f"🎯 Target member ID: {args.target_member_id}")
            print(f"📹 Video file: {args.video_path}")
            print(f"🖼️ Face-swapped image available")
        else:
            print("\n❌ Workflow failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
