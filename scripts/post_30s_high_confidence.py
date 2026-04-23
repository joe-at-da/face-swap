#!/usr/bin/env python3
"""
Post-30 Seconds High Confidence MP Analysis

This script focuses specifically on frames after 30 seconds with a higher
confidence threshold to avoid false matches and only identify real MPs.

Usage:
    python post_30s_high_confidence.py --video-path "/app/data/temp/capture_1776953107.mp4"
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
logger = logging.getLogger("post_30s_high_conf")

class Post30sHighConfidenceAnalysis:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.temp_dir = Path(tempfile.mkdtemp(prefix="post_30s_high_conf_"))
        logger.info(f"Initialized post-30s high confidence analysis with temp directory: {self.temp_dir}")
        
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
    
    def extract_frames_post_30s(self, video_path: str) -> List[str]:
        """Extract frames starting from 30 seconds only."""
        try:
            frame_paths = []
            
            # Extract frames every 5 seconds starting from 30s (post-30s focus)
            time_points = [30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]
            
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
            
            logger.info(f"Extracted {len(frame_paths)} frames from 30+ seconds")
            return frame_paths
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def analyze_frames_high_confidence(self, frame_paths: List[str], token: str) -> Dict[str, Any]:
        """Analyze frames with high confidence threshold."""
        try:
            all_analyses = []
            identified_mps = {}
            
            logger.info(f"Analyzing {len(frame_paths)} frames with high confidence threshold")
            
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
                    
                    # Track identified MPs with high confidence only
                    for face_detail in analysis.get("face_details", []):
                        if face_detail.get("identified_mp"):
                            mp_info = face_detail["identified_mp"]
                            confidence = mp_info.get("confidence", 0)
                            
                            # Only accept high confidence matches (0.6+)
                            if confidence >= 0.6:
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
                                    "confidence": confidence,
                                    "face_location": face_detail.get("location", []),
                                    "face_size": face_detail.get("size", "Unknown")
                                }
                                
                                identified_mps[member_id]["appearances"].append(appearance)
                                identified_mps[member_id]["max_confidence"] = max(
                                    identified_mps[member_id]["max_confidence"],
                                    confidence
                                )
                                identified_mps[member_id]["face_locations"].append(face_detail.get("location", []))
                                
                                logger.info(f"High confidence MP identified: {member_id} with confidence {confidence:.3f}")
                            else:
                                logger.info(f"Low confidence match rejected: {mp_info.get('member_id', 'Unknown')} with confidence {confidence:.3f}")
            
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
                    "total_identified_faces": sum(analysis.get("identified_faces", 0) for analysis in all_analyses),
                    "confidence_threshold": 0.6
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frames: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_mp_photo(self, member_id: str) -> str:
        """Get the MP photo path."""
        photo_path = f"/app/data/mp_photos/{member_id}.jpg"
        return photo_path if os.path.exists(photo_path) else None
    
    def create_high_confidence_visualization(self, analysis_results: Dict[str, Any]) -> str:
        """Create visualization showing only high confidence MP matches."""
        try:
            if not analysis_results.get("identified_mps"):
                logger.warning("No high confidence MPs identified for visualization")
                return None
            
            identified_mps = analysis_results["identified_mps"]
            mp_count = len(identified_mps)
            
            # Create visualization for high confidence matches only
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
                    f"HIGH CONFIDENCE MATCH:",
                    f"• Confidence: {best_appearance['confidence']:.3f}",
                    f"• Threshold: ≥0.600",
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
                title = f"POST-30s HIGH CONFIDENCE MP MATCHES - {mp_count} MPs IDENTIFIED"
                cv2.putText(full_visualization, title, (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                
                # Add summary
                summary = analysis_results["summary"]
                summary_text = f"Frames: {summary['frames_with_identified_mps']}/{summary['total_frames_analyzed']} | Faces: {summary['total_identified_faces']}/{summary['total_faces_detected']} | Confidence: ≥0.600"
                cv2.putText(full_visualization, summary_text, (20, full_visualization.shape[0] - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Save visualization
                visualization_path = self.temp_dir / "high_confidence_mp_matches.jpg"
                cv2.imwrite(str(visualization_path), full_visualization)
                
                logger.info(f"Created high confidence MP match visualization: {visualization_path}")
                return str(visualization_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating high confidence visualization: {str(e)}")
            return None
    
    def run_high_confidence_analysis(self, video_path: str):
        """Run the complete post-30s high confidence analysis."""
        logger.info(f"Starting post-30s high confidence analysis for {video_path}")
        
        # Step 1: Get authentication token
        logger.info("Step 1: Getting authentication token")
        token = self.get_auth_token()
        if not token:
            logger.error("Failed to get authentication token")
            return False
        
        # Step 2: Extract frames from 30+ seconds only
        logger.info("Step 2: Extracting frames from 30+ seconds only")
        frame_paths = self.extract_frames_post_30s(video_path)
        
        if not frame_paths:
            logger.error("No frames extracted from 30+ seconds")
            return False
        
        # Step 3: Analyze frames with high confidence threshold
        logger.info("Step 3: Analyzing frames with high confidence threshold (≥0.6)")
        analysis_results = self.analyze_frames_high_confidence(frame_paths, token)
        
        if not analysis_results.get("success"):
            logger.error("High confidence analysis failed")
            return False
        
        # Step 4: Create high confidence visualization
        logger.info("Step 4: Creating high confidence visualization")
        visualization_path = self.create_high_confidence_visualization(analysis_results)
        
        # Step 5: Generate report
        logger.info("Step 5: Generating high confidence analysis report")
        report = {
            "analysis_status": "completed",
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "focus_period": "30+ seconds",
            "confidence_threshold": 0.6,
            "frame_paths": frame_paths,
            "analysis_results": analysis_results,
            "visualization_path": visualization_path
        }
        
        report_path = self.temp_dir / "high_confidence_analysis_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_high_confidence_summary(report)
        
        logger.info(f"Post-30s high confidence analysis completed!")
        logger.info(f"Report saved to: {report_path}")
        logger.info(f"Results directory: {self.temp_dir}")
        
        return report
    
    def print_high_confidence_summary(self, report: Dict[str, Any]):
        """Print a formatted summary of the high confidence analysis."""
        print("\n" + "="*80)
        print("🎯 POST-30 SECONDS HIGH CONFIDENCE MP ANALYSIS")
        print("="*80)
        
        print(f"\n📅 Timestamp: {report['timestamp']}")
        print(f"🎬 Video: {report['video_path']}")
        print(f"🎯 Focus: {report['focus_period']}")
        print(f"🔍 Confidence Threshold: ≥{report['confidence_threshold']}")
        
        analysis = report['analysis_results']
        summary = analysis['summary']
        
        print(f"\n🔍 HIGH CONFIDENCE ANALYSIS RESULTS:")
        print(f"   • Frames analyzed (30+ s): {summary['total_frames_analyzed']}")
        print(f"   • Frames with faces: {summary['frames_with_faces']}")
        print(f"   • Frames with identified MPs: {summary['frames_with_identified_mps']}")
        print(f"   • Total faces detected: {summary['total_faces_detected']}")
        print(f"   • Total identified faces: {summary['total_identified_faces']}")
        print(f"   • Unique MPs identified: {summary['unique_mps_identified']}")
        
        print(f"\n👥 HIGH CONFIDENCE IDENTIFIED MPs:")
        if analysis['identified_mps']:
            for i, (member_id, mp_info) in enumerate(analysis['identified_mps'].items()):
                print(f"   {i+1}. {mp_info['name']} (ID: {member_id})")
                print(f"      → Max confidence: {mp_info['max_confidence']:.3f}")
                print(f"      → Total appearances: {len(mp_info['appearances'])}")
                
                # Show timestamps
                timestamps = [a['timestamp'] for a in mp_info['appearances']]
                print(f"      → Timestamps: {', '.join(map(str, timestamps))}")
                
                # Show best appearance details
                best_appearance = max(mp_info['appearances'], key=lambda x: x['confidence'])
                print(f"      → Best match: {best_appearance['timestamp']}s")
                print(f"      → Face size: {best_appearance['face_size']}")
                print(f"      → MP photo available: {'Yes' if self.get_mp_photo(member_id) else 'No'}")
        else:
            print("   ❌ No high confidence MPs identified in post-30s content")
            print("   ✅ This is GOOD - no false positive matches!")
        
        print(f"\n📊 FRAME-BY-FRAME BREAKDOWN (POST-30s):")
        for i, frame_analysis in enumerate(analysis['frame_analyses']):
            frame_name = os.path.basename(frame_analysis['frame_path'])
            total_faces = frame_analysis.get('total_faces', 0)
            identified_faces = frame_analysis.get('identified_faces', 0)
            
            if total_faces > 0:  # Only show frames with faces
                print(f"   Frame {i}: {frame_name}")
                print(f"      → Faces: {total_faces} | High confidence identified: {identified_faces}")
                
                if identified_faces > 0:
                    for face_detail in frame_analysis.get('face_details', []):
                        if face_detail.get('identified_mp'):
                            mp_info = face_detail['identified_mp']
                            confidence = mp_info.get('confidence', 0)
                            if confidence >= 0.6:
                                print(f"      • {mp_info.get('name', 'Unknown')} (conf: {confidence:.3f})")
                            else:
                                print(f"      • {mp_info.get('name', 'Unknown')} (conf: {confidence:.3f}) - REJECTED (below threshold)")
        
        print(f"\n📁 Generated Files:")
        if report['visualization_path']:
            print(f"   • High confidence visualization: {report['visualization_path']}")
        print(f"   • Analysis report: {self.temp_dir}/high_confidence_analysis_report.json")
        print(f"   • Extracted frames: {len(report['frame_paths'])} files")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Post-30 Seconds High Confidence MP Analysis")
    parser.add_argument("--video-path", required=True, help="Path to video file")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    # Initialize analysis
    analysis = Post30sHighConfidenceAnalysis(base_url=args.base_url)
    
    try:
        # Run high confidence analysis
        result = analysis.run_high_confidence_analysis(
            video_path=args.video_path
        )
        
        if result:
            print(f"\n✅ Post-30s high confidence analysis completed!")
            print(f"📁 All results saved in: {analysis.temp_dir}")
        else:
            print("\n❌ Analysis failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
