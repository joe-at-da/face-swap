# Speaker Attribution Enhancements

## Overview

This document describes the enhancements made to the Parliament TV speaker identification and transcript attribution pipeline. These improvements focus on better leveraging center-frame detection and implementing timeline-based speaker analysis to more accurately attribute transcripts to the correct speakers.

## Key Enhancements

### 1. Enhanced Center-Frame Prioritization

We've improved the face extraction process to give higher priority to faces that appear in the center of the frame, which are more likely to be the active speaker in Parliament TV footage:

- Increased the weight of center-frame positioning in the quality score calculation from 30% to 50%
- Implemented a sharper falloff for faces away from the center (2.5x distance penalty vs 2.0x previously)
- Reduced the sampling interval from 1.0s to 0.5s for more frequent frame analysis
- Added explicit center-frame priority flags to recognition events

### 2. Timeline-Based Speaker Analysis

We've implemented a new timeline-based speaker analysis system that:

- Groups faces by segment for better speaker attribution
- Selects the best face for each segment based on quality score and center-frame positioning
- Analyzes speaker transitions across adjacent segments
- Maintains speaker continuity when appropriate (within 2-second gaps)
- Updates speaker attributions based on timeline context

### 3. Improved Logging and Transparency

- Added detailed logging for center-frame detection and quality scores
- Included quality score metrics in recognition events
- Added flags to indicate when speaker attribution was updated by timeline analysis
- Preserved all recognition data for debugging and analysis

### 4. Clip Preservation

- Modified the export process to preserve clips in the SQLite database after successful export to Supabase
- This allows for better debugging, re-exporting if needed, and analysis of the recognition results

## Implementation Details

### Face Quality Scoring

The quality score for each detected face is now calculated with the following weights:

- Size component: 30% (previously 40%)
- Center proximity: 50% (previously 30%)
- Sharpness: 20% (previously 30%)

This prioritizes faces in the center of the frame, which are more likely to be the active speaker in Parliament TV footage.

### Speaker Attribution Process

1. Extract high-quality faces from the video with enhanced center-frame prioritization
2. Group faces by segment and collect quality scores
3. Select the best face for each segment based on quality score and center-frame positioning
4. Identify speakers in the selected faces
5. Perform timeline-based speaker analysis to improve attribution
6. Update speaker attributions based on timeline context
7. Save recognition events to parliament clips

## Testing

A test script (`test_center_frame_detection.py`) has been provided to verify the enhanced center-frame detection and timeline-based speaker analysis. This script:

1. Tests face extraction with center-frame prioritization
2. Tests the full recognition pipeline with timeline-based speaker analysis
3. Verifies integration with the ParliamentClipsIntegrationService
4. Logs detailed information about the recognition process

## Usage

To use the enhanced speaker attribution pipeline, simply use the existing API endpoint:

```
/api/v1/supabase-automation/process-parliament-tv
```

The enhancements are integrated into the existing pipeline and require no changes to the API usage.
