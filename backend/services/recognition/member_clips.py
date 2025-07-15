"""
Enhanced member clips processing for Parliament TV
This module provides functions to create member clips from recognition results,
including support for unidentified speakers.
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import ParliamentTranscription
from backend.services.integration.supabase_client import SupabaseService
from backend.services.utils import make_json_serializable

logger = logging.getLogger(__name__)

def save_member_clips_to_supabase(
    db: Session,
    video_id: int,
    full_video_url: str,
    recognition_results: Dict[str, Any],
    video_metadata: Dict[str, Any],
    supabase_service: SupabaseService,
    video_path: Optional[str] = None,
    audio_path: Optional[str] = None,
    use_diarization: bool = False
) -> Dict[str, Any]:
    """
    Process recognition results and save individual member clips to the Supabase parliament_member_clips table.
    
    This function:
    1. Processes recognition results to identify speaker segments
    2. Merges segments by the same speaker if they are close together (less than 60 seconds apart)
    3. Creates detailed clip metadata including timestamps, transcript segments, and confidence scores
    4. Saves clips to the Supabase parliament_member_clips table
    5. Handles unidentified speakers by assigning temporary IDs
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        full_video_url: URL to the full video in Supabase storage
        recognition_results: Recognition results from facial and voice recognition
        video_metadata: Metadata about the video
        supabase_service: Initialized Supabase service with appropriate permissions
        video_path: Optional path to the video file for diarization
        audio_path: Optional path to the audio file for diarization
        use_diarization: Whether to use speaker diarization to enhance speaker segments
        
    Returns:
        Dictionary with results of the clip saving process
    """
    logger.info(f"Processing member clips for video ID: {video_id}")
    
    # Get session information from metadata
    session_info = {
        "title": video_metadata.get("title", f"Parliament TV Session {video_id}"),
        "date": video_metadata.get("capture_date", datetime.now().isoformat()),
        "description": video_metadata.get("description", ""),
        "original_url": video_metadata.get("original_url", "")
    }
    
    # Apply speaker diarization if enabled and audio path is available
    if use_diarization and audio_path and os.path.exists(audio_path):
        logger.info(f"Using speaker diarization for video ID: {video_id}")
        recognition_results = enhance_segments_with_diarization(
            audio_path=audio_path,
            recognition_results=recognition_results,
            video_path=video_path
        )
        logger.info("Speaker diarization completed")
    elif use_diarization:
        logger.warning(f"Speaker diarization requested but audio path not available or invalid: {audio_path}")
    
    
    # Get transcription data if available
    transcription = db.query(ParliamentTranscription).filter(
        ParliamentTranscription.capture_session_id == video_id,
        ParliamentTranscription.status == "completed"
    ).order_by(ParliamentTranscription.created_at.desc()).first()
    
    transcript_data = None
    if transcription and transcription.output_file and os.path.exists(transcription.output_file):
        try:
            with open(transcription.output_file, 'r') as f:
                transcript_data = json.load(f)
            logger.info(f"Loaded transcription data from {transcription.output_file}")
        except Exception as e:
            logger.error(f"Error loading transcription file: {str(e)}")
    
    # Extract speaker segments from recognition results
    speaker_segments = []
    
    # Process identified speakers from facial recognition
    if "identified_speakers" in recognition_results:
        for speaker in recognition_results["identified_speakers"]:
            speaker_id = speaker.get("mp_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id or not speaker_name:
                continue
                
            for segment in speaker.get("segments", []):
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "facial",
                    "transcript": ""
                })
    
    # Process diarized speaker segments if available
    if "diarized_speaker_segments" in recognition_results and recognition_results["diarized_speaker_segments"]:
        logger.info("Processing diarized speaker segments")
        for segment in recognition_results["diarized_speaker_segments"]:
            speaker_segments.append({
                "speaker_id": segment["speaker_id"],
                "speaker_name": segment["speaker_name"],
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "confidence": segment.get("confidence", 0.7),
                "recognition_method": "diarizer",
                "transcript": segment.get("transcript", "")
            })
    
    # Process speaker segments from voice recognition if available
    elif transcript_data and "speakers" in transcript_data:
        for speaker in transcript_data["speakers"]:
            speaker_id = speaker.get("profile_id") or speaker.get("profileId")
            speaker_name = speaker.get("name")
            
            if not speaker_id:
                continue
                
            for segment in speaker.get("segments", []):
                # Find corresponding transcript text
                transcript_text = ""
                if "segments" in transcript_data:
                    for transcript_segment in transcript_data["segments"]:
                        if (transcript_segment["start"] >= segment["start_time"] and 
                            transcript_segment["end"] <= segment["end_time"]):
                            transcript_text += " " + transcript_segment["text"]
                
                speaker_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name or "Unknown Speaker",
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment.get("confidence", 0.0),
                    "recognition_method": "voice",
                    "transcript": transcript_text.strip()
                })
    
    # Process recognition events if no identified speakers were found
    if len(speaker_segments) == 0 and "recognition_events" in recognition_results:
        logger.info("No identified speakers found. Processing recognition events to create unidentified speaker segments.")
        
        # Group recognition events by time to create segments
        events = recognition_results["recognition_events"]
        if isinstance(events, list):
            # Sort events by time
            events.sort(key=lambda x: x.get("time", 0))
            
            # Create segments from recognition events
            current_segment = None
            unidentified_count = 0
            
            for event in events:
                event_time = event.get("time", 0)
                event_text = event.get("segment_text", "")
                
                if not current_segment:
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,  # Default 5 second segment
                        "confidence": 0.5,  # Medium confidence for unidentified speakers
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
                elif event_time - current_segment["end_time"] <= 60:  # If within 60 seconds
                    # Extend the current segment
                    current_segment["end_time"] = event_time + 5
                    current_segment["transcript"] += " " + event_text
                    current_segment["events"].append(event)
                else:
                    # Finalize the current segment and start a new one
                    speaker_segments.append({
                        "speaker_id": current_segment["speaker_id"],
                        "speaker_name": current_segment["speaker_name"],
                        "start_time": current_segment["start_time"],
                        "end_time": current_segment["end_time"],
                        "confidence": current_segment["confidence"],
                        "recognition_method": current_segment["recognition_method"],
                        "transcript": current_segment["transcript"].strip()
                    })
                    
                    # Start a new segment
                    unidentified_count += 1
                    temp_id = f"unidentified_{video_id}_{unidentified_count}"
                    current_segment = {
                        "speaker_id": temp_id,
                        "speaker_name": f"Unidentified Speaker {unidentified_count}",
                        "start_time": event_time,
                        "end_time": event_time + 5,
                        "confidence": 0.5,
                        "recognition_method": "unidentified",
                        "transcript": event_text,
                        "events": [event]
                    }
            
            # Add the last segment if there is one
            if current_segment:
                speaker_segments.append({
                    "speaker_id": current_segment["speaker_id"],
                    "speaker_name": current_segment["speaker_name"],
                    "start_time": current_segment["start_time"],
                    "end_time": current_segment["end_time"],
                    "confidence": current_segment["confidence"],
                    "recognition_method": current_segment["recognition_method"],
                    "transcript": current_segment["transcript"].strip()
                })
    
    # If still no segments, create a single segment for the entire video
    if len(speaker_segments) == 0:
        logger.info("No speaker segments found. Creating a single segment for the entire video.")
        
        # Get video duration from metadata or default to 60 seconds
        duration = video_metadata.get("duration", 60)
        
        # Log the full_video_url to help with debugging
        logger.info(f"Using full_video_url: {full_video_url} for unidentified speaker clip")
        
        speaker_segments.append({
            "speaker_id": f"unidentified_{video_id}_full",
            "speaker_name": "Unidentified Speaker",
            "start_time": 0,
            "end_time": duration,
            "confidence": 0.3,  # Low confidence
            "recognition_method": "default",
            "transcript": "No transcript available"
        })
    
    # Sort segments by start time
    speaker_segments.sort(key=lambda x: x["start_time"])
    
    # Helper function to check if a transcript appears to end with sentence-ending punctuation
    def is_sentence_complete(text):
        """Check if text appears to end with sentence-ending punctuation."""
        if not text:
            return False
        # Strip whitespace and check for sentence-ending punctuation
        text = text.strip()
        if not text:
            return False
        return text[-1] in ['.', '!', '?', ':', '"']
        
    # Helper function to assess transcript coherence
    def assess_transcript_coherence(text):
        """Assess the semantic coherence of a transcript segment.
        Returns a value between 0-1 where higher values indicate more coherent, complete thoughts."""
        if not text:
            return 0.0
            
        text = text.strip()
        if not text:
            return 0.0
            
        # Basic coherence indicators
        score = 0.5  # Start with neutral score
        
        # Length-based indicators (longer texts tend to be more coherent)
        words = text.split()
        if len(words) < 3:
            score -= 0.2  # Very short segments are less likely to be coherent
        elif len(words) > 10:
            score += 0.2  # Longer segments are more likely to be complete thoughts
            
        # Sentence completion indicators
        if is_sentence_complete(text):
            score += 0.2  # Complete sentences are more coherent
        else:
            score -= 0.1  # Incomplete sentences may need merging
            
        # Check for sentence starters
        sentence_starters = ['i', 'we', 'they', 'he', 'she', 'it', 'the', 'a', 'an', 'this', 'that', 'these', 'those']
        if words and words[0].lower() in sentence_starters:
            score += 0.1  # Proper sentence starters indicate coherence
            
        # Check for conjunctions at the end
        conjunctions = ['and', 'but', 'or', 'nor', 'for', 'yet', 'so', 'if', 'when', 'because']
        if words and words[-1].lower() in conjunctions:
            score -= 0.3  # Ending with conjunction suggests incomplete thought
            
        # Normalize score to 0-1 range
        return max(0.0, min(1.0, score))
    
    # Merge segments by the same speaker if they are close together (less than 60 seconds apart)
    # or if the previous segment's transcript doesn't end with sentence-ending punctuation
    MAX_GAP_SECONDS = 60
    EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE = 120  # 2 minutes for incomplete sentences
    merged_segments = []
    
    current_segment = None
    for segment in speaker_segments:
        if current_segment is None:
            current_segment = segment.copy()
            continue
            
        # Determine if current segment's transcript is a complete sentence
        sentence_complete = is_sentence_complete(current_segment["transcript"])
        
        # Use extended gap threshold for incomplete sentences
        threshold = EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE if not sentence_complete else MAX_GAP_SECONDS
        
        # If same speaker and either gap is small enough OR sentence is incomplete, merge segments
        if (segment["speaker_id"] == current_segment["speaker_id"] and 
            (segment["start_time"] - current_segment["end_time"] <= threshold or not sentence_complete)):
            
            # Merge transcripts if available
            if segment["transcript"] and current_segment["transcript"]:
                current_segment["transcript"] += " " + segment["transcript"]
            elif segment["transcript"]:
                current_segment["transcript"] = segment["transcript"]
                
            # Update end time and confidence (use max confidence)
            current_segment["end_time"] = segment["end_time"]
            current_segment["confidence"] = max(current_segment["confidence"], segment["confidence"])
        else:
            # Different speaker or gap too large, add current segment and start a new one
            merged_segments.append(current_segment)
            current_segment = segment.copy()
    
    # Add the last segment if there is one
    if current_segment is not None:
        merged_segments.append(current_segment)
        
    # Post-process segments to further avoid splitting sentences
    def post_process_segments(segments):
        """Post-process segments to avoid splitting sentences and create more coherent clips."""
        result = []
        i = 0
        while i < len(segments) - 1:
            current = segments[i]
            next_seg = segments[i + 1]
            
            should_merge = False
            merge_reason = ""
            
            # Calculate coherence scores
            current_coherence = assess_transcript_coherence(current["transcript"])
            next_coherence = assess_transcript_coherence(next_seg["transcript"])
            
            # Case 1: Same speaker with incomplete sentence
            if (current["speaker_id"] == next_seg["speaker_id"] and 
                not is_sentence_complete(current["transcript"])):
                
                # Merge with next segment if gap is reasonable (within 2 minutes)
                if next_seg["start_time"] - current["end_time"] <= EXTENDED_GAP_FOR_INCOMPLETE_SENTENCE:
                    should_merge = True
                    merge_reason = "incomplete sentence"
            
            # Case 2: Check for sentence continuity between segments
            elif (current["speaker_id"] == next_seg["speaker_id"] and
                  next_seg["start_time"] - current["end_time"] <= MAX_GAP_SECONDS):
                  
                # Check if they might be part of the same speech (look for sentence continuity)
                if current["transcript"] and next_seg["transcript"]:
                    # If the next segment doesn't start with a capital letter, it's likely a continuation
                    if len(next_seg["transcript"]) > 0 and not next_seg["transcript"].strip()[0].isupper():
                        should_merge = True
                        merge_reason = "sentence continuity"
                    # Check for short segments that might be part of the same thought
                    elif len(current["transcript"].split()) < 5 or len(next_seg["transcript"].split()) < 5:
                        should_merge = True
                        merge_reason = "short segment"
                    # Check if the current segment ends with a conjunction or preposition
                    elif any(current["transcript"].strip().lower().endswith(word) for word in ["and", "but", "or", "nor", "for", "yet", "so", "if", "to", "with", "by", "as"]):
                        should_merge = True
                        merge_reason = "ending with conjunction"
                    # Use coherence scores to make better merging decisions
                    elif current_coherence < 0.4 and next_coherence < 0.6:
                        # Both segments have low-to-medium coherence, likely part of same thought
                        should_merge = True
                        merge_reason = "low coherence segments"
            
            # Case 3: Check for very short pauses between segments of the same speaker
            elif (current["speaker_id"] == next_seg["speaker_id"] and
                  next_seg["start_time"] - current["end_time"] <= 2.0):  # 2 second pause threshold
                should_merge = True
                merge_reason = "short pause"
                
            # Case 4: Check for semantic continuity using coherence scores
            elif (current["speaker_id"] == next_seg["speaker_id"] and 
                  next_seg["start_time"] - current["end_time"] <= 5.0 and  # 5 second threshold for semantic continuity
                  current_coherence < 0.3):  # Current segment has very low coherence
                should_merge = True
                merge_reason = "semantic continuity"
                
            if should_merge:
                logger.debug(f"Merging segments due to {merge_reason}: {current['transcript']} + {next_seg['transcript']}")
                merged = current.copy()
                merged["end_time"] = next_seg["end_time"]
                if next_seg["transcript"]:
                    if merged["transcript"]:
                        # Add proper spacing between merged segments
                        if is_sentence_complete(merged["transcript"]):
                            merged["transcript"] += " " + next_seg["transcript"]
                        else:
                            # If the first segment doesn't end with punctuation, add a space
                            merged["transcript"] += " " + next_seg["transcript"]
                    else:
                        merged["transcript"] = next_seg["transcript"]
                merged["confidence"] = max(current["confidence"], next_seg["confidence"])
                
                result.append(merged)
                i += 2  # Skip both segments as they're now merged
                continue
                    
            result.append(current)
            i += 1
            
        # Add the last segment if we didn't merge it
        if i == len(segments) - 1:
            result.append(segments[i])
            
        return result

    # Apply post-processing to further merge segments with incomplete sentences
    merged_segments = post_process_segments(merged_segments)
    
    # Split overly long segments at natural pause points
    def split_long_segments(segments, max_duration=60):
        """Split segments that are too long at natural pause points or sentence boundaries."""
        result = []
        
        for segment in segments:
            duration = segment["end_time"] - segment["start_time"]
            
            # If segment is not too long, keep it as is
            if duration <= max_duration:
                result.append(segment)
                continue
                
            # Try to split at sentence boundaries for long segments
            transcript = segment["transcript"]
            if not transcript or len(transcript) < 20:  # Skip if transcript is too short
                result.append(segment)
                continue
                
            # Look for sentence-ending punctuation to find natural split points
            sentence_endings = []
            for i, char in enumerate(transcript):
                if char in ['.', '!', '?'] and (i+1 >= len(transcript) or transcript[i+1] == ' '):
                    sentence_endings.append(i)
            
            # If no sentence endings found, don't split
            if not sentence_endings:
                result.append(segment)
                continue
                
            # Calculate ideal split points based on duration
            num_splits = int(duration / max_duration) + 1
            ideal_split_points = []
            
            for i in range(1, num_splits):
                ideal_time = segment["start_time"] + (i * duration / num_splits)
                ideal_position = int(len(transcript) * (i / num_splits))
                
                # Find the closest sentence ending to this ideal position
                closest_idx = min(range(len(sentence_endings)), 
                                key=lambda j: abs(sentence_endings[j] - ideal_position)) if sentence_endings else -1
                
                if closest_idx >= 0:
                    ideal_split_points.append(sentence_endings[closest_idx])
            
            # Sort split points and remove duplicates
            ideal_split_points = sorted(set(ideal_split_points))
            
            # Create sub-segments
            if not ideal_split_points:
                # No good split points found
                result.append(segment)
                continue
                
            # Create the sub-segments
            sub_segments = []
            start_idx = 0
            start_time = segment["start_time"]
            
            for split_idx in ideal_split_points:
                # Calculate proportional time for this split point
                split_ratio = (split_idx + 1) / len(transcript)
                split_time = segment["start_time"] + (duration * split_ratio)
                
                # Create sub-segment
                sub_segment = segment.copy()
                sub_segment["start_time"] = start_time
                sub_segment["end_time"] = split_time
                sub_segment["transcript"] = transcript[start_idx:split_idx+1].strip()
                sub_segments.append(sub_segment)
                
                # Update for next segment
                start_idx = split_idx + 1
                start_time = split_time
            
            # Add final sub-segment if needed
            if start_idx < len(transcript):
                sub_segment = segment.copy()
                sub_segment["start_time"] = start_time
                sub_segment["end_time"] = segment["end_time"]
                sub_segment["transcript"] = transcript[start_idx:].strip()
                sub_segments.append(sub_segment)
            
            # Add all sub-segments to result
            result.extend(sub_segments)
            logger.info(f"Split long segment ({duration:.1f}s) into {len(sub_segments)} sub-segments")
        
        return result
    
    # Split segments that are too long (over 60 seconds)
    merged_segments = split_long_segments(merged_segments, max_duration=60)
    
    # Create clips for Supabase parliament_member_clips table
    member_clips = []
    for segment in merged_segments:
        # Generate a unique clip ID
        clip_id = str(uuid.uuid4())
        
        # Calculate duration
        duration = segment["end_time"] - segment["start_time"]
        
        # Format timestamps as HH:MM:SS
        def format_timestamp(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
        
        start_timestamp = format_timestamp(segment["start_time"])
        end_timestamp = format_timestamp(segment["end_time"])
        
        # Get speaker_id - we'll validate it later when inserting to Supabase
        speaker_id = segment["speaker_id"]
        # We'll keep the original speaker_id here and validate/filter when inserting to Supabase
        # This allows us to still create the clip data for local processing
        if isinstance(speaker_id, str) and speaker_id.startswith("unidentified_"):
            # Keep as is for now, we'll handle this during insertion
            pass
        else:
            try:
                speaker_id = int(speaker_id)
            except (ValueError, TypeError):
                # Keep as is for now, we'll handle this during insertion
                pass
        
        # Create clip metadata - simplified to match the actual Supabase schema
        clip_data = {
            "id": clip_id,
            # Removed video_id as it's not in the Supabase schema
            "member_id": speaker_id,  # Now guaranteed to be an integer
            # Removed member_name as it's not in the Supabase schema
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "duration_seconds": duration,
            "transcript": segment["transcript"],
            "full_video_url": full_video_url if full_video_url else "pending_combined_av_upload",
            # Removed session_title as it's not in the Supabase schema
            "created_at": datetime.now().isoformat()
            # Removed is_unidentified as it's not in the Supabase schema
        }
        
        member_clips.append(clip_data)
    
    # Save clips to Supabase parliament_member_clips table
    saved_clips = []
    failed_clips = []
    
    for clip in member_clips:
        try:
            # Ensure clip data is serializable and matches the Supabase schema
            try:
                # Create a clean serializable version of the clip
                # Ensure member_id is an integer and skip unidentified speakers
                member_id = clip.get("member_id")
                if isinstance(member_id, str) and member_id.startswith("unidentified_"):
                    # Skip unidentified speakers instead of using member_id = 0
                    logger.warning(f"Skipping unidentified speaker clip {clip.get('id')} - cannot be inserted due to foreign key constraints")
                    failed_clips.append({"clip_id": clip.get("id"), "warn": "Skipped unidentified speaker"})
                    continue
                else:
                    try:
                        member_id = int(member_id)
                        # Skip if member_id is 0 or negative
                        if member_id <= 0:
                            logger.warning(f"Skipping clip {clip.get('id')} with invalid member_id {member_id} - must be positive integer")
                            failed_clips.append({"clip_id": clip.get("id"), "error": f"Invalid member_id: {member_id}"})
                            continue
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping clip {clip.get('id')} with non-integer member_id {member_id}")
                        failed_clips.append({"clip_id": clip.get("id"), "error": f"Non-integer member_id: {member_id}"})
                        continue
                
                serializable_clip = {
                    "id": clip.get("id"),
                    # Removed video_id as it's not in the Supabase schema
                    "member_id": member_id,  # Now guaranteed to be a positive integer
                    # Removed member_name as it's not in the Supabase schema
                    "start_timestamp": str(clip.get("start_time", 0)),  # Convert to string for Supabase
                    "end_timestamp": str(clip.get("end_time", 0)),  # Convert to string for Supabase
                    "duration_seconds": float(clip.get("duration_seconds", 0)),
                    "transcript": (clip.get("transcript", "") or "")[:1000],  # Truncate long transcripts
                    "full_video_path": clip.get("full_video_url", "").replace("host.docker.internal", "localhost") if clip.get("full_video_url") else "",
                    # Removed session_title as it's not in the Supabase schema
                    "created_at": datetime.now().isoformat()
                    # Removed is_unidentified as it's not in the Supabase schema
                }
                
                # Log the clip data we're about to insert
                logger.info(f"Inserting clip for member ID {serializable_clip['member_id']} with ID {serializable_clip['id']}")
                
                # Insert clip into parliament_member_clips table
                response = supabase_service.client.table('parliament_member_clips').insert(serializable_clip).execute()
                
                if response and hasattr(response, 'data') and response.data:
                    saved_clips.append(clip["id"])
                    logger.info(f"Saved clip {clip['id']} for member ID {clip['member_id']} to Supabase")
                else:
                    failed_clips.append({
                        "clip_id": clip["id"],
                        "error": "No data returned from Supabase"
                    })
                    logger.warning(f"No data returned when saving clip {clip['id']} to Supabase")
            except Exception as e:
                logger.error(f"Error inserting clip {clip.get('id', 'unknown')}: {str(e)}")
                failed_clips.append({
                    "clip_id": clip["id"],
                    "error": str(e)
                })
        except Exception as e:
            failed_clips.append({
                "clip_id": clip["id"],
                "error": str(e)
            })
            logger.error(f"Error saving clip {clip['id']} to Supabase: {str(e)}")
    
    return {
        "success": True,
        "video_id": video_id,
        "clip_count": len(saved_clips),
        "saved_clips": saved_clips,
        "failed_clips": failed_clips
    }


def enhance_segments_with_diarization(
    audio_path: str, 
    recognition_results: Dict[str, Any],
    video_path: Optional[str] = None,
    max_duration: int = 1800
) -> Dict[str, Any]:
    """
    Use speaker diarization to enhance the accuracy of speaker segments without necessarily
    identifying the MP. This focuses on distinguishing different speakers based on voice characteristics.
    
    Args:
        audio_path: Path to the audio file
        recognition_results: Current recognition results
        video_path: Optional path to the video file
        max_duration: Maximum duration in seconds for the diarization process
        
    Returns:
        Enhanced recognition results with improved speaker segmentation
    """
    logger.info(f"Enhancing speaker segments with diarization for audio: {audio_path}")
    
    try:
        # Import the speaker diarizer
        from backend.utils.speaker_diarizer import SpeakerDiarizer
    except ImportError:
        logger.error("Could not import SpeakerDiarizer. Make sure the module is installed.")
        return recognition_results
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return recognition_results
    
    try:
        # Extract transcription data from recognition results
        transcription = {"segments": []}
        
        # Convert recognition events to transcription format expected by diarizer
        if "recognition_events" in recognition_results:
            events = recognition_results["recognition_events"]
            if isinstance(events, list):
                # Sort events by time
                events.sort(key=lambda x: x.get("time", 0))
                
                for event in events:
                    event_time = event.get("time", 0)
                    event_text = event.get("segment_text", "")
                    
                    if event_text:  # Only add events with text
                        # Estimate segment duration (2 seconds is a reasonable default)
                        transcription["segments"].append({
                            "start": event_time,
                            "end": event_time + 2.0,
                            "text": event_text
                        })
        
        # If we have a transcription file, use that instead
        if "transcription_file" in recognition_results:
            transcription_file = recognition_results["transcription_file"]
            if os.path.exists(transcription_file):
                try:
                    with open(transcription_file, 'r') as f:
                        file_transcription = json.load(f)
                    if "segments" in file_transcription and file_transcription["segments"]:
                        transcription = file_transcription
                        logger.info(f"Using transcription from file: {transcription_file}")
                except Exception as e:
                    logger.error(f"Error loading transcription file: {str(e)}")
        
        # If we don't have any segments, we can't perform diarization
        if not transcription["segments"]:
            logger.warning("No transcription segments found for diarization")
            return recognition_results
        
        # Initialize the speaker diarizer
        diarizer = SpeakerDiarizer()
        
        # Run diarization on the audio file
        # We're using a simple timeout mechanism to prevent hanging
        import threading
        import time
        
        result = None
        error = None
        
        def run_diarization():
            nonlocal result, error
            try:
                # Use basic speaker identification without requiring voice profiles
                result = diarizer.diarize(audio_path, transcription, video_path)
            except Exception as e:
                error = str(e)
        
        # Start diarization in a separate thread
        thread = threading.Thread(target=run_diarization)
        thread.daemon = True
        thread.start()
        
        # Wait for the thread to finish or timeout
        thread.join(timeout=max_duration)
        
        if thread.is_alive():
            logger.error(f"Speaker diarization timed out after {max_duration} seconds")
            return recognition_results
        
        if error:
            logger.error(f"Error in speaker diarization: {error}")
            return recognition_results
        
        if not result:
            logger.error("Speaker diarization returned no results")
            return recognition_results
        
        # Process the diarization results
        diarized_segments = []
        speaker_segments = {}
        
        # First pass: Group segments by speaker
        for segment in result.get("segments", []):
            if "speaker" not in segment:
                continue
                
            speaker_info = segment["speaker"]
            speaker_id = speaker_info.get("name", "")  # Use name as ID for anonymous speakers
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "")
            confidence = speaker_info.get("confidence", 0.7)
            
            # Initialize speaker dict if not exists
            if speaker_id not in speaker_segments:
                speaker_segments[speaker_id] = []
            
            # Add this segment to the speaker's list
            speaker_segments[speaker_id].append({
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
                "confidence": confidence
            })
        
        logger.info(f"Found {len(speaker_segments)} unique speakers in diarization results")
        
        # Second pass: Merge adjacent segments by speaker with small gaps
        MAX_MERGE_GAP = 2.0  # Maximum gap in seconds to merge segments
        
        for speaker_id, segments in speaker_segments.items():
            # Sort segments by start time
            segments.sort(key=lambda x: x["start_time"])
            
            # Merge adjacent segments with small gaps
            merged_segments = []
            current_segment = None
            
            for segment in segments:
                if current_segment is None:
                    current_segment = segment.copy()
                    continue
                
                # If gap is small enough, merge segments
                if segment["start_time"] - current_segment["end_time"] <= MAX_MERGE_GAP:
                    # Extend current segment
                    current_segment["end_time"] = segment["end_time"]
                    if segment["text"]:
                        if current_segment["text"]:
                            current_segment["text"] += " " + segment["text"]
                        else:
                            current_segment["text"] = segment["text"]
                    # Use max confidence
                    current_segment["confidence"] = max(current_segment["confidence"], segment["confidence"])
                else:
                    # Add current segment and start a new one
                    merged_segments.append(current_segment)
                    current_segment = segment.copy()
            
            # Add the last segment
            if current_segment:
                merged_segments.append(current_segment)
            
            # Create final speaker segments
            for segment in merged_segments:
                diarized_segments.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_id,  # For now, just use the speaker ID as the name
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "confidence": segment["confidence"],
                    "recognition_method": "diarizer",
                    "transcript": segment["text"]
                })
            
            logger.info(f"Speaker {speaker_id}: {len(segments)} raw segments merged into {len(merged_segments)} coherent segments")
        
        # Create enhanced recognition results
        enhanced_results = recognition_results.copy()
        
        # Replace or merge speaker segments
        if diarized_segments:
            logger.info(f"Found {len(diarized_segments)} diarized speaker segments")
            
            # For now, we'll completely replace the speaker segments with diarized ones
            # Later, we could implement a more sophisticated merging strategy
            enhanced_results["diarized_speaker_segments"] = diarized_segments
            
            return enhanced_results
        
        return recognition_results
    
    except Exception as e:
        logger.exception(f"Error enhancing segments with diarization: {str(e)}")
        return recognition_results
