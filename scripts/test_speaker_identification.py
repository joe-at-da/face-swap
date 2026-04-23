#!/usr/bin/env python3
"""
Speaker Identification Test for Parliament TV Video

This script analyzes a captured Parliament TV video to identify speakers
after the 30-second mark and matches them to the MP database.

Usage:
    python test_speaker_identification.py --video-path "/app/data/temp/parliament_test_minute.mp4" --start-time 30
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
logger = logging.getLogger("speaker_identification")

class SpeakerIdentificationTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="speaker_identification_"))
        logger.info(f"Initialized speaker identification with temp directory: {self.temp_dir}")
        
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
    
    def extract_frames_from_video(self, video_path: str, start_time: int = 30, 
                                 duration: int = 30, frame_interval: int = 2) -> List[str]:
        """
        Extract frames from video starting from specified time.
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            duration: Duration to analyze in seconds
            frame_interval: Extract frame every N seconds
            
        Returns:
            List of extracted frame paths
        """
        try:
            frame_paths = []
            end_time = start_time + duration
            
            for timestamp in range(start_time, end_time, frame_interval):
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
            
            logger.info(f"Extracted {len(frame_paths)} frames from {start_time}s to {end_time}s")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def analyze_faces_in_frame(self, frame_path: str, token: str) -> Dict[str, Any]:
        """Analyze faces in a single frame using the intelligent API."""
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
    
    def consolidate_speaker_data(self, frame_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate speaker data from multiple frames."""
        try:
            speaker_appearances = {}
            total_faces_detected = 0
            identified_faces = 0
            
            for i, analysis in enumerate(frame_analyses):
                if not analysis.get("success"):
                    continue
                
                frame_timestamp = 30 + (i * 2)  # Calculate timestamp based on frame index
                total_faces_detected += analysis.get("total_faces", 0)
                identified_faces += analysis.get("identified_faces", 0)
                
                for face_detail in analysis.get("face_details", []):
                    if face_detail.get("identified_mp"):
                        mp_info = face_detail["identified_mp"]
                        member_id = mp_info.get("member_id")
                        
                        if member_id not in speaker_appearances:
                            speaker_appearances[member_id] = {
                                "member_id": member_id,
                                "name": mp_info.get("name", f"MP {member_id}"),
                                "appearances": [],
                                "max_confidence": 0,
                                "face_sizes": [],
                                "timestamps": []
                            }
                        
                        # Record this appearance
                        appearance = {
                            "frame_index": i,
                            "timestamp": frame_timestamp,
                            "confidence": mp_info.get("confidence", 0),
                            "face_size": face_detail.get("size", "Unknown"),
                            "face_location": face_detail.get("location", [])
                        }
                        
                        speaker_appearances[member_id]["appearances"].append(appearance)
                        speaker_appearances[member_id]["max_confidence"] = max(
                            speaker_appearances[member_id]["max_confidence"],
                            mp_info.get("confidence", 0)
                        )
                        speaker_appearances[member_id]["face_sizes"].append(face_detail.get("size", "Unknown"))
                        speaker_appearances[member_id]["timestamps"].append(frame_timestamp)
            
            # Sort speakers by confidence and number of appearances
            ranked_speakers = sorted(
                speaker_appearances.values(),
                key=lambda x: (x["max_confidence"], len(x["appearances"])),
                reverse=True
            )
            
            return {
                "success": True,
                "total_frames_analyzed": len(frame_analyses),
                "total_faces_detected": total_faces_detected,
                "identified_faces": identified_faces,
                "unique_speakers": len(speaker_appearances),
                "ranked_speakers": ranked_speakers,
                "speaker_appearances": speaker_appearances
            }
            
        except Exception as e:
            logger.error(f"Error consolidating speaker data: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def select_best_target_speaker(self, consolidated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best target speaker for face swapping."""
        try:
            if not consolidated_data.get("success") or not consolidated_data.get("ranked_speakers"):
                return {"success": False, "error": "No speakers identified"}
            
            ranked_speakers = consolidated_data["ranked_speakers"]
            
            # Select the top-ranked speaker (highest confidence + most appearances)
            best_speaker = ranked_speakers[0]
            
            # Calculate a composite score
            confidence_score = best_speaker["max_confidence"]
            appearance_score = min(len(best_speaker["appearances"]) / 10, 1.0)  # Normalize to 0-1
            composite_score = (confidence_score * 0.7) + (appearance_score * 0.3)
            
            return {
                "success": True,
                "selected_speaker": best_speaker,
                "selection_criteria": {
                    "max_confidence": confidence_score,
                    "appearances_count": len(best_speaker["appearances"]),
                    "composite_score": composite_score,
                    "selection_reason": "Highest confidence with good appearance frequency"
                }
            }
            
        except Exception as e:
            logger.error(f"Error selecting target speaker: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def run_speaker_identification_test(self, video_path: str, start_time: int = 30):
        """Run the complete speaker identification test."""
        logger.info(f"Starting speaker identification test for {video_path}")
        logger.info(f"Analyzing frames from {start_time}s onwards")
        
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
        
        # Step 3: Analyze faces in each frame
        logger.info("Step 3: Analyzing faces in extracted frames")
        frame_analyses = []
        
        for i, frame_path in enumerate(frame_paths):
            logger.info(f"Analyzing frame {i+1}/{len(frame_paths)}: {os.path.basename(frame_path)}")
            analysis = self.analyze_faces_in_frame(frame_path, token)
            frame_analyses.append(analysis)
        
        # Step 4: Consolidate speaker data
        logger.info("Step 4: Consolidating speaker identification data")
        consolidated_data = self.consolidate_speaker_data(frame_analyses)
        
        # Step 5: Select best target speaker
        logger.info("Step 5: Selecting best target speaker for face swapping")
        target_selection = self.select_best_target_speaker(consolidated_data)
        
        # Step 6: Generate comprehensive report
        logger.info("Step 6: Generating comprehensive report")
        report = {
            "test_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "analysis_parameters": {
                "start_time": start_time,
                "frame_interval": 2,
                "total_frames_analyzed": len(frame_paths)
            },
            "frame_analyses": frame_analyses,
            "consolidated_data": consolidated_data,
            "target_selection": target_selection,
            "extracted_frames": frame_paths
        }
        
        report_path = self.temp_dir / "speaker_identification_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_identification_summary(report)
        
        logger.info(f"Speaker identification test completed successfully!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_identification_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the speaker identification results."""
        print("\n" + "="*80)
        print("🎤 PARLIAMENT TV SPEAKER IDENTIFICATION RESULTS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        params = report['analysis_parameters']
        print(f"\n⚙️  Analysis Parameters:")
        print(f"   • Start time: {params['start_time']}s")
        print(f"   • Frame interval: {params['frame_interval']}s")
        print(f"   • Total frames analyzed: {params['total_frames_analyzed']}")
        
        consolidated = report['consolidated_data']
        if consolidated.get("success"):
            print(f"\n🔍 Face Analysis Results:")
            print(f"   • Total faces detected: {consolidated['total_faces_detected']}")
            print(f"   • Identified faces: {consolidated['identified_faces']}")
            print(f"   • Unique speakers: {consolidated['unique_speakers']}")
            
            print(f"\n👥 Ranked Speakers (by confidence):")
            for i, speaker in enumerate(consolidated['ranked_speakers'][:5]):
                print(f"   {i+1}. {speaker['name']} (ID: {speaker['member_id']})")
                print(f"      → Appearances: {len(speaker['appearances'])}")
                print(f"      → Max confidence: {speaker['max_confidence']:.3f}")
                print(f"      → Timestamps: {', '.join(map(str, speaker['timestamps'][:3]))}{'...' if len(speaker['timestamps']) > 3 else ''}")
        else:
            print(f"\n❌ Speaker identification failed: {consolidated.get('error', 'Unknown')}")
        
        target = report['target_selection']
        if target.get("success"):
            selected = target['selected_speaker']
            criteria = target['selection_criteria']
            print(f"\n🎯 SELECTED TARGET SPEAKER:")
            print(f"   • Name: {selected['name']}")
            print(f"   • Member ID: {selected['member_id']}")
            print(f"   • Confidence: {criteria['max_confidence']:.3f}")
            print(f"   • Appearances: {criteria['appearances_count']}")
            print(f"   • Composite score: {criteria['composite_score']:.3f}")
            print(f"   • Reason: {criteria['selection_reason']}")
        else:
            print(f"\n❌ No target speaker selected: {target.get('error', 'Unknown')}")
        
        print(f"\n📁 Generated Files:")
        print(f"   • Extracted frames: {len(report['extracted_frames'])} files")
        print(f"   • Analysis report: {self.temp_dir}/speaker_identification_report.json")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Speaker Identification Test")
    parser.add_argument("--video-path", required=True, help="Path to captured video file")
    parser.add_argument("--start-time", type=int, default=30, help="Start time for analysis (seconds)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize speaker identification test
    test = SpeakerIdentificationTest(base_url=args.base_url)
    
    try:
        # Run speaker identification test
        result = test.run_speaker_identification_test(
            video_path=args.video_path,
            start_time=args.start_time
        )
        
        if result:
            print(f"\n✅ Speaker identification test completed successfully!")
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
