#!/usr/bin/env python3
"""
Complete Parliament TV Face Swap Workflow Test

This script demonstrates the complete end-to-end workflow:
1. Capture video from Parliament TV
2. Extract frames from the video
3. Perform face recognition to identify speakers
4. Swap faces with target MP faces
5. Generate final face-swapped content

Usage:
    python test_complete_workflow.py --parliament-url "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7" --target-member-id "115" --duration 30
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
logger = logging.getLogger("complete_workflow")

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
    
    def capture_parliament_video(self, parliament_url, duration=30, token=None):
        """Capture video from Parliament TV URL."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            data = {
                "title": "Complete Workflow Test Capture",
                "description": "Testing complete Parliament TV face swap workflow",
                "source_url": parliament_url,
                "duration": duration
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/capture",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            capture_data = response.json()
            capture_id = capture_data["id"]
            logger.info(f"Started Parliament TV capture with ID: {capture_id}")
            
            # Wait for capture to complete
            import time
            max_wait_time = duration + 60  # Wait for capture duration + buffer
            
            for i in range(max_wait_time):
                try:
                    status_response = requests.get(
                        f"{self.base_url}/api/v1/capture/{capture_id}",
                        headers=headers
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    if status_data["status"] == "completed":
                        logger.info(f"Capture completed successfully")
                        return status_data
                    elif status_data["status"] == "failed":
                        logger.error(f"Capture failed")
                        return None
                    
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Error checking capture status: {str(e)}")
                    time.sleep(1)
            
            logger.warning(f"Capture timed out after {max_wait_time} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Failed to capture Parliament TV video: {str(e)}")
            return None
    
    def extract_frame_from_video(self, video_path, timestamp=5):
        """Extract a frame from the captured video at the specified timestamp."""
        try:
            output_path = self.temp_dir / f"frame_{timestamp}s.jpg"
            
            cmd = [
                "ffmpeg", "-i", str(video_path), 
                "-ss", str(timestamp), 
                "-vframes", "1", 
                "-q:v", "2",
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
    
    def perform_face_swap(self, image_path, target_member_id, token=None):
        """Perform face swapping on the extracted frame."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            with open(image_path, 'rb') as image_file:
                files = {
                    'image': image_file,
                    'target_member_id': target_member_id,
                    'blend_factor': '0.7'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/face-swap/image",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                swap_data = response.json()
                logger.info(f"Face swap completed: {swap_data}")
                
                # Download the swapped image
                output_path = self.temp_dir / f"face_swapped_{target_member_id}.jpg"
                swap_response = requests.get(
                    f"{self.base_url}/api/v1/face-swap/image/{swap_data['output_path']}",
                    headers=headers
                )
                swap_response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(swap_response.content)
                
                logger.info(f"Downloaded face-swapped image: {output_path}")
                return str(output_path), swap_data
                
        except Exception as e:
            logger.error(f"Failed to perform face swap: {str(e)}")
            return None, None
    
    def run_complete_workflow(self, parliament_url, target_member_id, duration=30):
        """Run the complete Parliament TV face swap workflow."""
        logger.info("Starting complete Parliament TV face swap workflow")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Capture video from Parliament TV
        logger.info("Step 2: Capturing video from Parliament TV")
        capture_data = self.capture_parliament_video(parliament_url, duration, token)
        if not capture_data:
            logger.error("Failed to capture Parliament TV video")
            return False
        
        video_path = capture_data.get("file_path")
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        logger.info(f"Video captured successfully: {video_path}")
        
        # Step 3: Extract frame from video
        logger.info("Step 3: Extracting frame from video")
        frame_path = self.extract_frame_from_video(video_path)
        if not frame_path:
            logger.error("Failed to extract frame from video")
            return False
        
        # Step 4: Perform face swapping
        logger.info("Step 4: Performing face swapping")
        swapped_path, swap_data = self.perform_face_swap(frame_path, target_member_id, token)
        if not swapped_path:
            logger.error("Failed to perform face swapping")
            return False
        
        # Step 5: Generate workflow report
        logger.info("Step 5: Generating workflow report")
        report = {
            "workflow_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "parliament_url": parliament_url,
            "target_member_id": target_member_id,
            "duration": duration,
            "video_path": video_path,
            "frame_path": frame_path,
            "swapped_path": swapped_path,
            "face_swap_results": swap_data,
            "temp_directory": str(self.temp_dir)
        }
        
        report_path = self.temp_dir / "workflow_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Complete workflow finished successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Face-swapped image: {swapped_path}")
        
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Complete Parliament TV Face Swap Workflow")
    parser.add_argument("--parliament-url", required=True, help="Parliament TV URL to capture")
    parser.add_argument("--target-member-id", required=True, help="Target MP member ID for face swapping")
    parser.add_argument("--duration", type=int, default=30, help="Video capture duration in seconds")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize workflow
    workflow = ParliamentTVFaceSwapWorkflow(base_url=args.base_url)
    
    try:
        # Run complete workflow
        success = workflow.run_complete_workflow(
            parliament_url=args.parliament_url,
            target_member_id=args.target_member_id,
            duration=args.duration
        )
        
        if success:
            print("\n✅ Complete workflow finished successfully!")
            print(f"📁 Results saved in: {workflow.temp_dir}")
            print(f"🎯 Target member ID: {args.target_member_id}")
            print(f"📹 Capture duration: {args.duration} seconds")
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
