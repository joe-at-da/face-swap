#!/usr/bin/env python3
"""
Capture 1 Minute of Parliament TV for Speaker Identification Test

This script captures a full minute of Parliament TV content for comprehensive
speaker identification and face swapping testing.

Usage:
    python capture_minute_parliament.py --duration 60 --output-name "parliament_test_minute"
"""

import os
import sys
import argparse
import logging
import json
import requests
import tempfile
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parliament_capture")

class ParliamentTVCapture:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="parliament_capture_"))
        logger.info(f"Initialized capture with temp directory: {self.temp_dir}")
        
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
    
    def get_parliament_url(self):
        """Get a Parliament TV URL for capturing."""
        # Use a known Parliament TV URL for testing
        return "https://parliamentlive.tv/Event/Index/2b0b9b50-ee08-42b3-b6b9-655175fbe6d7"
    
    def start_capture(self, token: str, duration: int = 60, output_name: str = "parliament_test_minute"):
        """Start capturing Parliament TV for specified duration."""
        try:
            parliament_url = self.get_parliament_url()
            headers = {"Authorization": f"Bearer {token}"}
            
            capture_data = {
                "source_url": parliament_url,
                "title": f"Parliament TV {duration}s Test - {output_name}",
                "description": f"Parliament TV capture for speaker identification test - {duration} seconds",
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
            return self.wait_for_capture_completion(capture_id, token, duration)
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            return None
    
    def wait_for_capture_completion(self, capture_id: int, token: str, expected_duration: int):
        """Wait for capture to complete and return the video path."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            max_wait_time = expected_duration + 30  # Add buffer time
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
                        logger.info(f"Capture completed successfully: {video_path}")
                        return {
                            "success": True,
                            "capture_id": capture_id,
                            "video_path": video_path,
                            "duration": capture_status.get("duration"),
                            "file_size": capture_status.get("file_size"),
                            "metadata": capture_status
                        }
                    else:
                        logger.error("Capture completed but no file path available")
                        return None
                elif status == "failed":
                    logger.error(f"Capture failed: {capture_status}")
                    return None
                
                # Wait before checking again
                import time
                time.sleep(5)
            
            logger.error("Capture timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for capture completion: {str(e)}")
            return None
    
    def run_capture_test(self, duration: int = 60, output_name: str = "parliament_test_minute"):
        """Run the complete Parliament TV capture test."""
        logger.info(f"Starting Parliament TV capture test: {duration}s")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Start capture
        logger.info("Step 2: Starting Parliament TV capture")
        capture_result = self.start_capture(token, duration, output_name)
        
        if not capture_result:
            logger.error("Capture failed")
            return False
        
        # Step 3: Generate capture report
        logger.info("Step 3: Generating capture report")
        report = {
            "capture_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "output_name": output_name,
            "capture_result": capture_result,
            "parliament_url": self.get_parliament_url()
        }
        
        report_path = self.temp_dir / f"capture_report_{output_name}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Capture test completed successfully!")
        logger.info(f"Video path: {capture_result['video_path']}")
        logger.info(f"Report saved to: {report_path}")
        
        return capture_result

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Capture 1 Minute of Parliament TV")
    parser.add_argument("--duration", type=int, default=60, help="Capture duration in seconds")
    parser.add_argument("--output-name", default="parliament_test_minute", help="Output name for the capture")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize capture
    capture = ParliamentTVCapture(base_url=args.base_url)
    
    try:
        # Run capture test
        result = capture.run_capture_test(
            duration=args.duration,
            output_name=args.output_name
        )
        
        if result:
            print(f"\n✅ Parliament TV capture completed successfully!")
            print(f"📹 Video: {result['video_path']}")
            print(f"⏱️  Duration: {result['duration']} seconds")
            print(f"📁 Results: {capture.temp_dir}")
            print(f"\n🎯 Next step: Run speaker identification on this video")
        else:
            print("\n❌ Capture failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Capture interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
