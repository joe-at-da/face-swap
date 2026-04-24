-- Add 'failed' status to parliament_event_processing_status enum and error_message column
-- This migration extends the parliament_events table to support error tracking

-- Add 'failed' value to the existing enum
ALTER TYPE parliament_event_processing_status ADD VALUE 'failed';

-- Add error_message column to store error details when processing fails
ALTER TABLE parliament_events 
ADD COLUMN error_message TEXT DEFAULT NULL;

-- Add column comment for documentation
COMMENT ON COLUMN parliament_events.error_message IS 
'Error message details when parliament event processing fails. NULL when processing is successful.';

-- Update status column comment to include the new 'failed' value
COMMENT ON COLUMN parliament_events.status IS 
'Processing status: pending (default), processing, processed, failed';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated parliament_events table:';
    RAISE NOTICE '- Added "failed" value to parliament_event_processing_status enum';
    RAISE NOTICE '- Added error_message column for error tracking';
    RAISE NOTICE '- Updated column documentation';
    RAISE NOTICE 'Note: Indexes for failed events can be created in a subsequent transaction if needed';
END $$;