-- Change Clip Timestamps to Text
-- Migration to change start_timestamp and end_timestamp columns 
-- from TIMESTAMP WITH TIME ZONE to TEXT in parliament_member_clips table

-- First, let's check if there's existing data and convert it to text format
-- This will preserve any existing timestamp data as ISO strings

-- Add temporary columns for the new text-based timestamps
ALTER TABLE parliament_member_clips 
ADD COLUMN start_timestamp_text TEXT,
ADD COLUMN end_timestamp_text TEXT;

-- Copy existing timestamp data to text columns (converting to ISO string format)
UPDATE parliament_member_clips 
SET 
    start_timestamp_text = CASE 
        WHEN start_timestamp IS NOT NULL THEN start_timestamp::TEXT
        ELSE NULL 
    END,
    end_timestamp_text = CASE 
        WHEN end_timestamp IS NOT NULL THEN end_timestamp::TEXT
        ELSE NULL 
    END;

-- Drop the computed duration_seconds column since it depends on the timestamp columns
ALTER TABLE parliament_member_clips DROP COLUMN duration_seconds;

-- Drop the original timestamp columns
ALTER TABLE parliament_member_clips 
DROP COLUMN start_timestamp,
DROP COLUMN end_timestamp;

-- Rename the text columns to the original names
ALTER TABLE parliament_member_clips 
RENAME COLUMN start_timestamp_text TO start_timestamp;

ALTER TABLE parliament_member_clips 
RENAME COLUMN end_timestamp_text TO end_timestamp;

-- Make the columns NOT NULL since they were required before
ALTER TABLE parliament_member_clips 
ALTER COLUMN start_timestamp SET NOT NULL,
ALTER COLUMN end_timestamp SET NOT NULL;

-- Add a new duration_seconds column as a regular numeric column (not computed)
-- This will need to be populated separately based on your text timestamp format
ALTER TABLE parliament_member_clips 
ADD COLUMN duration_seconds DECIMAL(10,3);

-- Add validation constraints to ensure the text format is reasonable
-- These are basic length checks - you may want to add more specific format validation
ALTER TABLE parliament_member_clips 
ADD CONSTRAINT check_start_timestamp_length CHECK (length(start_timestamp) > 0 AND length(start_timestamp) <= 100);

ALTER TABLE parliament_member_clips 
ADD CONSTRAINT check_end_timestamp_length CHECK (length(end_timestamp) > 0 AND length(end_timestamp) <= 100);

-- Update indexes - remove timestamp-based indexes and add text-based ones
DROP INDEX IF EXISTS idx_parliament_member_clips_start_timestamp;
DROP INDEX IF EXISTS idx_parliament_member_clips_end_timestamp;

-- Create new indexes for text-based timestamps
CREATE INDEX idx_parliament_member_clips_start_timestamp_text ON parliament_member_clips(start_timestamp);
CREATE INDEX idx_parliament_member_clips_end_timestamp_text ON parliament_member_clips(end_timestamp);

-- Update column comments to reflect the new text format
COMMENT ON COLUMN parliament_member_clips.start_timestamp IS 
'Start timestamp as text string (format depends on your application needs)';

COMMENT ON COLUMN parliament_member_clips.end_timestamp IS 
'End timestamp as text string (format depends on your application needs)';

COMMENT ON COLUMN parliament_member_clips.duration_seconds IS 
'Duration of the clip in seconds. Must be calculated and set manually since timestamps are now text.';

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Parliament member clips timestamp migration completed:';
    RAISE NOTICE '- Changed start_timestamp from TIMESTAMP WITH TIME ZONE to TEXT';
    RAISE NOTICE '- Changed end_timestamp from TIMESTAMP WITH TIME ZONE to TEXT';
    RAISE NOTICE '- Preserved existing timestamp data as text strings';
    RAISE NOTICE '- Removed computed duration_seconds column - now must be set manually';
    RAISE NOTICE '- Added basic length validation constraints';
    RAISE NOTICE '- Updated indexes for text-based timestamps';
    RAISE NOTICE 'NOTE: You will need to update your application logic to handle text timestamps';
END $$; 