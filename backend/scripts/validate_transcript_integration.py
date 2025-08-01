#!/usr/bin/env python3
"""
Transcript Integration Validation Script

This script validates the transcript integration by analyzing the parliament_clips database
to check for placeholder transcripts and verify diarization-driven segmentation.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranscriptValidator:
    """Validator for transcript integration in parliament clips."""
    
    def __init__(self):
        """Initialize the transcript validator."""
        # Define database paths
        self.docker_db_path = "/app/backend/parliament_clips.db"
        self.local_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                         "backend/parliament_clips.db")
        
        # Use the path that exists
        if os.path.exists(self.docker_db_path):
            self.db_path = self.docker_db_path
        elif os.path.exists(self.local_db_path):
            self.db_path = self.local_db_path
        else:
            raise FileNotFoundError("Parliament clips database not found")
        
        logger.info(f"Using database at: {self.db_path}")
    
    def validate_video_clips(self, video_id: int) -> Dict[str, Any]:
        """
        Validate transcript integration for clips of a specific video.
        
        Args:
            video_id: ID of the video to validate
            
        Returns:
            Dict with validation results
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all clips for the video
            cursor.execute(
                "SELECT id, member_id, transcript, start_timestamp, end_timestamp, speech_group_id, metadata "
                "FROM parliament_clips WHERE json_extract(metadata, '$.video_id') = ?",
                (video_id,)
            )
            clips = cursor.fetchall()
            
            if not clips:
                return {"success": False, "error": f"No clips found for video ID {video_id}"}
            
            # Analyze clips
            total_clips = len(clips)
            placeholder_count = 0
            speech_groups = set()
            
            for clip in clips:
                clip_id, member_id, transcript, start_time, end_time, speech_group_id, metadata_json = clip
                
                # Check if transcript is a placeholder
                if transcript and transcript.startswith("Speech segment from"):
                    placeholder_count += 1
                
                # Track speech groups
                if speech_group_id:
                    speech_groups.add(speech_group_id)
            
            # Calculate statistics
            placeholder_percentage = (placeholder_count / total_clips) * 100 if total_clips > 0 else 0
            avg_clips_per_group = total_clips / len(speech_groups) if speech_groups else 0
            
            # Analyze speech group distribution
            group_sizes = {}
            for group_id in speech_groups:
                cursor.execute(
                    "SELECT COUNT(*) FROM parliament_clips WHERE speech_group_id = ?",
                    (group_id,)
                )
                group_size = cursor.fetchone()[0]
                group_sizes[group_id] = group_size
            
            # Determine if segmentation is correct (one clip per speaker turn)
            segmentation_correct = avg_clips_per_group <= 1.2  # Allow slight variance
            
            return {
                "success": True,
                "video_id": video_id,
                "total_clips": total_clips,
                "placeholder_count": placeholder_count,
                "placeholder_percentage": placeholder_percentage,
                "speech_group_count": len(speech_groups),
                "avg_clips_per_group": avg_clips_per_group,
                "segmentation_correct": segmentation_correct,
                "group_sizes": group_sizes
            }
            
        except Exception as e:
            logger.error(f"Error validating clips: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                conn.close()
    
    def validate_all_videos(self) -> Dict[str, Any]:
        """
        Validate transcript integration for all videos in the database.
        
        Returns:
            Dict with validation results for all videos
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all unique video IDs
            cursor.execute(
                "SELECT DISTINCT json_extract(metadata, '$.video_id') FROM parliament_clips"
            )
            video_ids = [row[0] for row in cursor.fetchall() if row[0] is not None]
            
            results = {}
            for video_id in video_ids:
                results[str(video_id)] = self.validate_video_clips(video_id)
            
            return {
                "success": True,
                "video_count": len(video_ids),
                "results_by_video": results
            }
            
        except Exception as e:
            logger.error(f"Error validating all videos: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                conn.close()

def main():
    """Main function to run the validation."""
    validator = TranscriptValidator()
    
    if len(sys.argv) > 1:
        # Validate specific video
        video_id = int(sys.argv[1])
        logger.info(f"Validating transcript integration for video ID: {video_id}")
        results = validator.validate_video_clips(video_id)
    else:
        # Validate all videos
        logger.info("Validating transcript integration for all videos")
        results = validator.validate_all_videos()
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Provide summary
    if results.get("success", False):
        if "results_by_video" in results:
            # All videos summary
            total_placeholder_percentage = 0
            video_count = 0
            
            for video_id, video_results in results["results_by_video"].items():
                if video_results.get("success", False):
                    total_placeholder_percentage += video_results.get("placeholder_percentage", 0)
                    video_count += 1
            
            avg_placeholder_percentage = total_placeholder_percentage / video_count if video_count > 0 else 0
            logger.info(f"Average placeholder percentage across {video_count} videos: {avg_placeholder_percentage:.1f}%")
        else:
            # Single video summary
            logger.info(f"Placeholder percentage: {results.get('placeholder_percentage', 0):.1f}%")
            logger.info(f"Segmentation correct: {results.get('segmentation_correct', False)}")
    else:
        logger.error(f"Validation failed: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
