-- Add session_date column to parliament_events table
ALTER TABLE public.parliament_events
  ADD COLUMN IF NOT EXISTS session_date DATE;

-- Create index for querying events by session date
CREATE INDEX IF NOT EXISTS idx_parliament_events_session_date 
  ON public.parliament_events(session_date);

-- Add comment for documentation
COMMENT ON COLUMN public.parliament_events.session_date IS 'Date of the parliament session/event';

