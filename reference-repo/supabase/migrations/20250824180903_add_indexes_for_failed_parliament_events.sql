-- Add indexes for efficient queries on failed parliament events
-- This migration creates indexes for the 'failed' enum value added in the previous migration

-- Create index for efficient queries on failed events
CREATE INDEX idx_parliament_events_failed_status 
ON parliament_events(status) 
WHERE status = 'failed';

-- Create composite index for failed events with error messages
CREATE INDEX idx_parliament_events_failed_with_errors 
ON parliament_events(status, error_message) 
WHERE status = 'failed' AND error_message IS NOT NULL;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Added indexes for parliament_events table:';
    RAISE NOTICE '- Created index for failed status queries';
    RAISE NOTICE '- Created composite index for failed events with error messages';
END $$;