# Speaker Attribution Improvements

## Problem
Speakers were being incorrectly attributed due to a very low confidence threshold (0.1) in the face matching process, resulting in many faces being matched to the same member ID with low confidence.

## Solution
We've implemented the following improvements:

1. **Increased Confidence Threshold**
   - Raised from 0.1 to 0.45 in `MultimodalRecognitionService.identify_speaker_in_frame` and face extraction methods
   - This prevents low-confidence matches that lead to incorrect attributions

2. **Confidence Gap Analysis**
   - Added tracking of second-best match confidence in `ParliamentMemberMatcher`
   - Calculate confidence gap between best and second-best match
   - Log warnings when confidence gap is too small (< 0.1)
   - Include confidence gap in match results for better decision making

3. **Enhanced Timeline-based Speaker Analysis**
   - Updated sorting criteria to consider confidence gap along with center-frame priority and quality score
   - This ensures more reliable speaker continuity across segments

## Testing
Use the `test_speaker_attribution_docker.py` script to test these improvements with a real Parliament TV video in the Docker container. The script will:

1. Process a video with the improved speaker attribution
2. Analyze the member ID distribution in recognition events
3. Save results to a JSON file for further analysis
4. Log detailed information about the matching process

## Running the Test
```bash
docker exec -it parliament-tv python /app/backend/scripts/test_speaker_attribution_docker.py
```

## Expected Results
- Multiple member IDs in recognition events (not just 4621)
- Higher confidence scores for matches
- Significant confidence gaps between best and second-best matches
- Better speaker attribution with enhanced center-frame prioritization
