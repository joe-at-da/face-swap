-- Add statistics tracking columns to parliament_events table
ALTER TABLE public.parliament_events
  ADD COLUMN IF NOT EXISTS segments_found integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS db_rows_created integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS segments_mp_identified integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS segments_transcribed integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS segments_uploaded integer DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN public.parliament_events.segments_found IS 'Total number of segments found during processing';
COMMENT ON COLUMN public.parliament_events.db_rows_created IS 'Number of database rows created for segments';
COMMENT ON COLUMN public.parliament_events.segments_mp_identified IS 'Number of segments where MP was successfully identified';
COMMENT ON COLUMN public.parliament_events.segments_transcribed IS 'Number of segments with successful transcription';
COMMENT ON COLUMN public.parliament_events.segments_uploaded IS 'Number of segments successfully uploaded to storage';

-- Create index for querying events by processing statistics
CREATE INDEX IF NOT EXISTS idx_parliament_events_processing_stats 
  ON public.parliament_events(segments_found, db_rows_created, segments_mp_identified, segments_transcribed, segments_uploaded)
  WHERE status = 'processed';