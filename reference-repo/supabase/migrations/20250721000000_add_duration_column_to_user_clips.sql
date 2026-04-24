-- Migration to add duration column to user_clips table
-- This migration adds a duration field to store the formatted duration (HH:MM:SS) of user clips

-- Add duration column to user_clips table
ALTER TABLE user_clips 
ADD COLUMN duration TEXT DEFAULT NULL;

-- Create index for duration column
CREATE INDEX idx_user_clips_duration
ON user_clips(duration)
WHERE duration IS NOT NULL;

-- Add column comment for documentation
COMMENT ON COLUMN user_clips.duration IS 
'Formatted duration of the clip in HH:MM:SS format (e.g., "00:02:30" for 2 minutes 30 seconds)';

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully:';
    RAISE NOTICE '- Added duration column to user_clips table';
    RAISE NOTICE '- Created index on duration column';
END $$; 