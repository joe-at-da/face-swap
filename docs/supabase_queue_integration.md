# Supabase Queue Integration - Phase 1

This document outlines the data requirements and implementation approach for Phase 1 integration between the Parliament TV system and the MPAI NextJS Supabase project using Supabase's queue system.

## Supabase Queue Overview

Based on the architecture diagrams, the Supabase project uses two main queues:

1. **clip_creation** - For creating clips from Parliament TV videos
2. **video_processing** - For processing video content

## Data Requirements for Queue Integration

### For `video_processing` Queue

When a Parliament TV video is captured and processed, we need to provide:

```json
{
  "video_id": "string",          // Unique identifier for the video in Parliament TV system
  "title": "string",             // Title of the video
  "description": "string",       // Description of the video
  "capture_date": "ISO-8601",    // When the video was captured
  "duration": "number",          // Duration in seconds
  "video_url": "string",         // URL to the video file
  "audio_url": "string",         // URL to the audio file (separate from video)
  "thumbnail_url": "string",     // URL to the video thumbnail (optional)
  "status": "string",            // Processing status
  "metadata": {                  // Additional metadata
    "source": "parliament_tv",
    "stream_type": "string",     // Type of stream (committee, debate, etc.)
    "parliament_tv_url": "string" // Original Parliament TV URL
  }
}
```

### For `clip_creation` Queue

When facial recognition identifies speakers and segments, we need to provide:

```json
{
  "video_id": "string",          // Reference to the parent video
  "start_time": "number",        // Start time in seconds
  "end_time": "number",          // End time in seconds
  "speaker_id": "string",        // MP identifier (if recognized)
  "speaker_name": "string",      // MP name (if recognized)
  "confidence": "number",        // Recognition confidence score
  "transcript": "string",        // Transcript of this segment (if available)
  "face_image_url": "string",    // URL to extracted face image (optional)
  "metadata": {                  // Additional metadata
    "recognition_method": "facial", // Method used for recognition
    "unidentified_face_id": "string" // ID for unidentified faces
  }
}
```

## Implementation Approach

### 1. Data Export Function

Add a function to export recognition results in the format required by Supabase queues:

```python
# backend/services/integration/supabase_export.py

import json
import os
from typing import Dict, List, Any, Optional

def format_video_for_supabase(
    video_id: str,
    title: str,
    description: str,
    capture_date: str,
    duration: float,
    video_url: str,
    audio_url: str,
    thumbnail_url: Optional[str] = None,
    status: str = "processed",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format video data for Supabase video_processing queue"""
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "capture_date": capture_date,
        "duration": duration,
        "video_url": video_url,
        "audio_url": audio_url,
        "thumbnail_url": thumbnail_url,
        "status": status,
        "metadata": metadata or {
            "source": "parliament_tv"
        }
    }

def format_clips_for_supabase(
    video_id: str,
    recognition_results: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Format recognition results for Supabase clip_creation queue"""
    clips = []
    
    # Process identified speakers
    for speaker in recognition_results.get("identified_speakers", []):
        for segment in speaker.get("segments", []):
            clips.append({
                "video_id": video_id,
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "speaker_id": speaker["mp_id"],
                "speaker_name": speaker["name"],
                "confidence": segment.get("confidence", 0.0),
                "transcript": segment.get("transcript", ""),
                "face_image_url": segment.get("face_image_url", ""),
                "metadata": {
                    "recognition_method": "facial",
                }
            })
    
    # Process unidentified faces
    for face in recognition_results.get("unidentified_faces", []):
        for appearance in face.get("appearances", []):
            clips.append({
                "video_id": video_id,
                "start_time": appearance.get("start_time", 0),
                "end_time": appearance.get("end_time", 0),
                "speaker_id": None,
                "speaker_name": "Unknown",
                "confidence": 0.0,
                "transcript": "",
                "face_image_url": face.get("image_url", ""),
                "metadata": {
                    "recognition_method": "facial",
                    "unidentified_face_id": face.get("id", "")
                }
            })
    
    return clips

def export_to_json(data: Dict[str, Any], output_path: str) -> None:
    """Export data to JSON file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
```

### 2. Integration with Recognition Process

Update the facial recognition service to export data for Supabase queues:

```python
# Add to backend/services/recognition/facial_recognition.py

from backend.services.integration.supabase_export import (
    format_video_for_supabase,
    format_clips_for_supabase,
    export_to_json
)

def identify_speakers(self, video_path: str, output_file: Optional[str] = None, store_unidentified: bool = True) -> Dict:
    # ... existing code ...
    
    # After successful recognition, export data for Supabase integration
    if results and results.get("success"):
        video_id = os.path.basename(video_path).split('.')[0]
        
        # Get video metadata from database or file
        video_metadata = self._get_video_metadata(video_path)
        
        # Format data for Supabase queues
        video_data = format_video_for_supabase(
            video_id=video_id,
            title=video_metadata.get("title", f"Parliament TV Video {video_id}"),
            description=video_metadata.get("description", ""),
            capture_date=video_metadata.get("capture_date", datetime.now().isoformat()),
            duration=video_metadata.get("duration", 0),
            video_url=f"/media/videos/{os.path.basename(video_path)}",
            audio_url=video_metadata.get("audio_url", ""),
            status="processed",
            metadata={
                "source": "parliament_tv",
                "parliament_tv_url": video_metadata.get("source_url", "")
            }
        )
        
        clips_data = format_clips_for_supabase(video_id, results)
        
        # Export to JSON files for Supabase integration
        export_dir = os.path.join(os.path.dirname(output_file), "supabase_export")
        export_to_json(video_data, os.path.join(export_dir, f"{video_id}_video.json"))
        export_to_json({"clips": clips_data}, os.path.join(export_dir, f"{video_id}_clips.json"))
        
        # Add export paths to results
        results["supabase_export"] = {
            "video_data": os.path.join(export_dir, f"{video_id}_video.json"),
            "clips_data": os.path.join(export_dir, f"{video_id}_clips.json")
        }
    
    return results
```

## Data Flow

1. Parliament TV system captures and processes video
2. Facial recognition identifies speakers and segments
3. Integration module formats data for Supabase queues
4. Data is exported to JSON files in a standardized format
5. Files are manually imported to Supabase or accessed via shared storage

## Next Steps

1. Implement the data export functionality
2. Test with sample recognition results
3. Verify the exported data format matches Supabase queue requirements
4. Document the file locations and import process for the Supabase team

## Future Enhancements (Phase 2+)

1. Direct API integration to push data to Supabase queues
2. Webhook notifications when new data is available
3. Automated synchronization between systems
