# Speaker Attribution Consistency

## Overview

This document describes the implementation of speaker attribution consistency in the Parliament TV transcription system. The feature ensures that continuous speech segments from the same speaker are consistently attributed to the speaker with the highest confidence score, even if facial recognition initially identified different speakers for some segments.

## Problem Statement

In parliamentary video processing, facial recognition may incorrectly attribute different parts of the same continuous speech to different MPs due to:

1. Camera angle changes
2. Face detection failures in some frames
3. MPs with similar appearances
4. Varying lighting conditions
5. MPs turning away from the camera temporarily

This inconsistency creates problems for:
- Transcription accuracy
- Speech segment grouping
- Export quality
- User experience

## Solution

The implemented solution normalizes speaker IDs across temporally contiguous segments by:

1. Grouping segments that are close together in time (within 1.5 seconds)
2. Finding the speaker ID with the highest confidence score in each group
3. Assigning that speaker ID to all segments in the group
4. Creating a unique speech group ID for each continuous speech block
5. Updating both in-memory segments and the SQLite database

## Implementation Details

### Key Components

1. **Segment Grouping Logic**
   - Segments are sorted by start time
   - Segments with gaps less than 1.5 seconds are considered part of the same continuous speech
   - Each continuous block becomes a speech group

2. **Speaker Normalization**
   - Within each speech group, the speaker with the highest confidence score is selected
   - All segments in the group are updated to use this speaker ID
   - A unique speech group ID is assigned to all segments in the group

3. **Database Integration**
   - The SQLite database schema was extended with a `speech_group_id` column
   - Normalized speaker IDs and speech group IDs are persisted to the database
   - Updates are performed using parameterized SQL for security and efficiency

### Key Functions

#### `normalize_speaker_ids(segments)`

Groups segments into continuous speech blocks and normalizes speaker IDs:

```python
def normalize_speaker_ids(segments):
    """
    Ensure consistent speaker attribution across continuous speech segments.
    
    For segments that are close together in time (likely part of the same continuous speech),
    use the speaker ID with the highest confidence score for all segments in that continuous block.
    
    Args:
        segments: List of speaker segments
        
    Returns:
        Tuple of (normalized_segments, speech_groups)
    """
    # Implementation details...
```

#### `update_sqlite_with_normalized_speakers(db, video_id, speech_groups, member_id_mapping)`

Updates the SQLite database with normalized speaker IDs:

```python
def update_sqlite_with_normalized_speakers(db, video_id, speech_groups, member_id_mapping):
    """
    Update the SQLite database with normalized speaker IDs.
    
    Args:
        db: Database session
        video_id: ID of the video in the database
        speech_groups: List of speech groups with segment IDs and normalized speaker IDs
        member_id_mapping: Dictionary mapping speaker IDs to member IDs
        
    Returns:
        Number of segments updated in the database
    """
    # Implementation details...
```

## Integration

The speaker normalization is integrated into the main processing pipeline in `save_member_clips_to_supabase`:

1. After collecting all speaker segments but before merging and sorting
2. Member ID mappings are fetched from the database
3. Normalized speaker IDs and speech group IDs are updated in both memory and the database
4. Error handling ensures pipeline continuity even if normalization fails

## Benefits

1. **Improved Accuracy**: Ensures consistent speaker attribution based on highest confidence scores
2. **Better User Experience**: Prevents confusing speaker changes in the middle of continuous speech
3. **Enhanced Data Quality**: Provides reliable speaker data for exports and analytics
4. **Simplified Processing**: Groups related segments with speech group IDs for easier downstream processing

## Future Enhancements

1. **Confidence Threshold Tuning**: Optimize the confidence threshold for speaker normalization
2. **Voice Recognition Integration**: Combine facial and voice recognition for even better speaker identification
3. **Manual Override**: Allow users to manually correct speaker attributions when needed
4. **Performance Optimization**: Improve the efficiency of database updates for large videos
