-- Add asd_skip_info column to event_processing_segments table
-- This column stores information about why segments were skipped during processing
-- NULL for processed segments
-- JSON object for skipped segments with structure:
-- {
--   "skipped": true,
--   "reason": "below_speaking_threshold" | other reasons,
--   "speaking_score_info": {"best_avg_score": 0.18, "threshold": 0.25, ...},
--   "debug_why": "..."
-- }

ALTER TABLE event_processing_segments
ADD COLUMN asd_skip_info JSONB;

-- Add index for querying skipped segments efficiently
CREATE INDEX idx_event_processing_segments_asd_skip_info
ON event_processing_segments
USING GIN (asd_skip_info)
WHERE asd_skip_info IS NOT NULL;

-- Add index for querying by skip reason
CREATE INDEX idx_event_processing_segments_skip_reason
ON event_processing_segments ((asd_skip_info->>'reason'))
WHERE asd_skip_info IS NOT NULL;

-- Add comment to the column
COMMENT ON COLUMN event_processing_segments.asd_skip_info IS
'Stores information about why segments were skipped during ASD processing. NULL for processed segments, JSON object for skipped segments containing skip reason and debug information.';
