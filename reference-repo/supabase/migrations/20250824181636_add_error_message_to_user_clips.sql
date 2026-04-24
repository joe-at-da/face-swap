-- Add error_message field to user_clips table
-- This migration adds error tracking capability to user clips

-- Add error_message column to store error details when clip processing fails
ALTER TABLE user_clips 
ADD COLUMN error_message TEXT DEFAULT NULL;

-- Create index for efficient queries on clips with errors
CREATE INDEX idx_user_clips_with_errors 
ON user_clips(user_id, status) 
WHERE error_message IS NOT NULL;

-- Add column comment for documentation
COMMENT ON COLUMN user_clips.error_message IS 
'Error message details when user clip processing fails. NULL when processing is successful.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated user_clips table:';
    RAISE NOTICE '- Added error_message column for error tracking';
    RAISE NOTICE '- Created index for efficient error queries';
    RAISE NOTICE '- Updated column documentation';
END $$;