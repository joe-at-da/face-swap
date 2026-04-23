#!/usr/bin/env python3
"""
Show MP Photo Matches for Identified Faces

This script shows the actual MP photos that match the identified faces
in the video, demonstrating the face recognition accuracy.

Usage:
    python show_mp_matches.py --video-path "/app/data/temp/test_combined.mp4"
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
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mp_matches")

class MPMatchVisualization:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mp_matches_"))
        logger.info(f"Initialized MP match visualization with temp directory: {self.temp_dir}")
        
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
        """Extract frames from video for analysis."""
        try:
            frame_paths = []
            
            # Extract frames throughout the 10-second video
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
    
    def analyze_faces_and_identify_mps(self, frame_paths: List[str], token: str) -> Dict[str, Any]:
        """Analyze faces and identify MPs."""
        try:
            all_analyses = []
            identified_mps = {}
            
            logger.info(f"Analyzing {len(frame_paths)} frames for MP identification")
            
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
                                    "max_confidence": 0,
                                    "face_locations": []
                                }
                            
                            appearance = {
                                "frame_index": i,
                                "frame_path": frame_path,
                                "timestamp": int(os.path.basename(frame_path).replace('frame_', '').replace('s.jpg', '')),
                                "confidence": mp_info.get("confidence", 0),
                                "face_location": face_detail.get("location", []),
                                "face_size": face_detail.get("size", "Unknown")
                            }
                            
                            identified_mps[member_id]["appearances"].append(appearance)
                            identified_mps[member_id]["max_confidence"] = max(
                                identified_mps[member_id]["max_confidence"],
                                mp_info.get("confidence", 0)
                            )
                            identified_mps[member_id]["face_locations"].append(face_detail.get("location", []))
            
            return {
                "success": True,
                "frame_analyses": all_analyses,
                "identified_mps": identified_mps,
                "summary": {
                    "total_frames_analyzed": len(frame_paths),
                    "frames_with_faces": len([a for a in all_analyses if a.get("total_faces", 0) > 0]),
                    "frames_with_identified_mps": len([a for a in all_analyses if a.get("identified_faces", 0) > 0]),
                    "unique_mps_identified": len(identified_mps),
                    "total_faces_detected": sum(analysis.get("total_faces", 0) for analysis in all_analyses),
                    "total_identified_faces": sum(analysis.get("identified_faces", 0) for analysis in all_analyses)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frames: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_mp_photo(self, member_id: str) -> str:
        """Get the MP photo path."""
        photo_path = f"/app/data/mp_photos/{member_id}.jpg"
        return photo_path if os.path.exists(photo_path) else None
    
    def create_detailed_match_visualization(self, analysis_results: Dict[str, Any]) -> str:
        """Create detailed visualization showing detected faces with their MP photo matches."""
        try:
            if not analysis_results.get("identified_mps"):
                logger.warning("No MPs identified for visualization")
                return None
            
            identified_mps = analysis_results["identified_mps"]
            mp_count = len(identified_mps)
            
            # Create a detailed comparison for each identified MP
            comparison_height = 300
            mp_visualizations = []
            
            for member_id, mp_info in identified_mps.items():
                # Get the best appearance (highest confidence)
                best_appearance = max(mp_info["appearances"], key=lambda x: x["confidence"])
                frame_path = best_appearance["frame_path"]
                face_location = best_appearance["face_location"]
                
                # Create a row for this MP: detected face | MP photo | comparison info
                row_images = []
                
                # 1. Load and crop the detected face
                frame = cv2.imread(frame_path)
                if frame is not None:
                    top, right, bottom, left = face_location
                    detected_face = frame[top:bottom, left:right]
                    detected_face_resized = cv2.resize(detected_face, (200, 200))
                    
                    # Add border and label
                    cv2.rectangle(detected_face_resized, (0, 0), (199, 199), (0, 255, 0), 3)
                    cv2.putText(detected_face_resized, "DETECTED FACE", (10, 25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(detected_face_resized, f"at {best_appearance['timestamp']}s", (10, 180), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(detected_face_resized, f"Size: {best_appearance['face_size']}", (10, 195), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                else:
                    detected_face_resized = np.zeros((200, 200, 3), dtype=np.uint8)
                    cv2.putText(detected_face_resized, "DETECTED FACE\nLOAD FAILED", (10, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                row_images.append(detected_face_resized)
                
                # 2. Load MP photo
                mp_photo_path = self.get_mp_photo(member_id)
                if mp_photo_path and os.path.exists(mp_photo_path):
                    mp_photo = cv2.imread(mp_photo_path)
                    if mp_photo is not None:
                        mp_photo_resized = cv2.resize(mp_photo, (200, 200))
                        
                        # Add border and label
                        cv2.rectangle(mp_photo_resized, (0, 0), (199, 199), (255, 0, 0), 3)
                        cv2.putText(mp_photo_resized, "MP DATABASE PHOTO", (10, 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                        cv2.putText(mp_photo_resized, f"ID: {member_id}", (10, 180), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(mp_photo_resized, f"Conf: {best_appearance['confidence']:.3f}", (10, 195), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    else:
                        mp_photo_resized = np.zeros((200, 200, 3), dtype=np.uint8)
                        cv2.putText(mp_photo_resized, "MP PHOTO\nLOAD FAILED", (10, 100), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                else:
                    mp_photo_resized = np.zeros((200, 200, 3), dtype=np.uint8)
                    cv2.putText(mp_photo_resized, "MP PHOTO\nNOT FOUND", (10, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                row_images.append(mp_photo_resized)
                
                # 3. Create comparison info panel
                info_panel = np.zeros((200, 300, 3), dtype=np.uint8)
                
                # Add MP name and details
                info_lines = [
                    f"MP: {mp_info['name']}",
                    f"ID: {member_id}",
                    f"",
                    f"Match Details:",
                    f"• Confidence: {best_appearance['confidence']:.3f}",
                    f"• Timestamp: {best_appearance['timestamp']}s",
                    f"• Face Size: {best_appearance['face_size']}",
                    f"• Appearances: {len(mp_info['appearances'])}",
                    f"",
                    f"All Timestamps:",
                ]
                
                # Add timestamps
                timestamps = [str(a['timestamp']) + 's' for a in mp_info['appearances']]
                for ts in timestamps[:3]:  # Show first 3 timestamps
                    info_lines.append(f"  • {ts}")
                if len(timestamps) > 3:
                    info_lines.append(f"  • ... and {len(timestamps)-3} more")
                
                y_offset = 20
                for line in info_lines:
                    cv2.putText(info_panel, line, (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    y_offset += 18
                
                row_images.append(info_panel)
                mp_visualizations.append(np.hstack(row_images))
            
            # Stack all MP visualizations
            if mp_visualizations:
                full_visualization = np.vstack(mp_visualizations)
                
                # Add title
                title = f"MP FACE RECOGNITION MATCHES - {mp_count} MPs IDENTIFIED"
                cv2.putText(full_visualization, title, (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                
                # Add summary
                summary = analysis_results["summary"]
                summary_text = f"Frames: {summary['frames_with_identified_mps']}/{summary['total_frames_analyzed']} | Faces: {summary['total_identified_faces']}/{summary['total_faces_detected']} | MPs: {summary['unique_mps_identified']}"
                cv2.putText(full_visualization, summary_text, (20, full_visualization.shape[0] - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Save visualization
                visualization_path = self.temp_dir / "detailed_mp_matches.jpg"
                cv2.imwrite(str(visualization_path), full_visualization)
                
                logger.info(f"Created detailed MP match visualization: {visualization_path}")
                return str(visualization_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating detailed visualization: {str(e)}")
            return None
    
    def run_mp_match_visualization(self, video_path: str):
        """Run the complete MP match visualization."""
        logger.info(f"Starting MP match visualization for {video_path}")
        
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
        
        # Step 3: Analyze faces and identify MPs
        logger.info("Step 3: Analyzing faces and identifying MPs")
        analysis_results = self.analyze_faces_and_identify_mps(frame_paths, token)
        
        if not analysis_results.get("success"):
            logger.error("Face analysis failed")
            return False
        
        # Step 4: Create detailed visualization
        logger.info("Step 4: Creating detailed MP match visualization")
        visualization_path = self.create_detailed_match_visualization(analysis_results)
        
        # Step 5: Generate report
        logger.info("Step 5: Generating MP match report")
        report = {
            "visualization_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "frame_paths": frame_paths,
            "analysis_results": analysis_results,
            "visualization_path": visualization_path
        }
        
        report_path = self.temp_dir / "mp_match_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_match_summary(report)
        
        logger.info(f"MP match visualization completed!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_match_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the MP match results."""
        print("\n" + "="*80)
        print("🎭 MP FACE RECOGNITION MATCH VISUALIZATION")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        
        analysis = report['analysis_results']
        summary = analysis['summary']
        
        print(f"\n🔍 FACE RECOGNITION RESULTS:")
        print(f"   • Frames analyzed: {summary['total_frames_analyzed']}")
        print(f"   • Frames with faces: {summary['frames_with_faces']}")
        print(f"   • Frames with identified MPs: {summary['frames_with_identified_mps']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Total identified faces: {summary['total_identified_faces']}")
        print(f"   • Unique MPs identified: {summary['unique_mps_identified']}")
        
        print(f"\n👥 IDENTIFIED MPs WITH MATCHES:")
        if analysis['identified_mps']:
            for i, (member_id, mp_info) in enumerate(analysis['identified_mps'].items()):
                print(f"   {i+1}. {mp_info['name']} (ID: {member_id})")
                print(f"      → Max confidence: {mp_info['max_confidence']:.3f}")
                print(f"      → Total appearances: {len(mp_info['appearances'])}")
                
                # Show all timestamps
                timestamps = [a['timestamp'] for a in mp_info['appearances']]
                print(f"      → Timestamps: {', '.join(map(str, timestamps))}")
                
                # Show best appearance details
                best_appearance = max(mp_info['appearances'], key=lambda x: x['confidence'])
                print(f"      → Best match: {best_appearance['timestamp']}s")
                print(f"      → Face size: {best_appearance['face_size']}")
                print(f"      → MP photo available: {'Yes' if self.get_mp_photo(member_id) else 'No'}")
        else:
            print("   ❌ No MPs identified in the video")
        
        print(f"\n📁 Generated Files:")
        if report['visualization_path']:
            print(f"   • Detailed MP match visualization: {report['visualization_path']}")
        print(f"   • Analysis report: {self.temp_dir}/mp_match_report.json")
        print(f"   • Extracted frames: {len(report['frame_paths'])} files")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Show MP Photo Matches for Identified Faces")
    parser.add_argument("--video-path", required=True, help="Path to video file")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize visualization
    viz = MPMatchVisualization(base_url=args.base_url)
    
    try:
        # Run MP match visualization
        result = viz.run_mp_match_visualization(
            video_path=args.video_path
        )
        
        if result:
            print(f"\n✅ MP match visualization completed!")
            print(f"📁 All results saved in: {viz.temp_dir}")
        else:
            print("\n❌ Visualization failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Visualization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
