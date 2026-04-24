-- Add session_start_time column to parliament_events table
ALTER TABLE public.parliament_events
  ADD COLUMN IF NOT EXISTS session_start_time TEXT;

-- Create index for querying events by start time
CREATE INDEX IF NOT EXISTS idx_parliament_events_session_start_time 
  ON public.parliament_events(session_start_time) WHERE session_start_time IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN public.parliament_events.session_start_time IS 'Start time of the parliament session in HH:MM:SS format (24-hour)';
