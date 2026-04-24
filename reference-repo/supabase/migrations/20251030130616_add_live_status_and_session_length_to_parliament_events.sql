-- Add is_live, has_ended, and session_length_seconds columns to parliament_events table
ALTER TABLE public.parliament_events
  ADD COLUMN IF NOT EXISTS is_live BOOLEAN DEFAULT FALSE NOT NULL,
  ADD COLUMN IF NOT EXISTS has_ended BOOLEAN DEFAULT FALSE NOT NULL,
  ADD COLUMN IF NOT EXISTS session_length_seconds INTEGER;

-- Create index for querying live events
CREATE INDEX IF NOT EXISTS idx_parliament_events_is_live 
  ON public.parliament_events(is_live) WHERE is_live = TRUE;

-- Create index for querying ended events
CREATE INDEX IF NOT EXISTS idx_parliament_events_has_ended 
  ON public.parliament_events(has_ended) WHERE has_ended = TRUE;

-- Create index for querying events by session length
CREATE INDEX IF NOT EXISTS idx_parliament_events_session_length_seconds 
  ON public.parliament_events(session_length_seconds) WHERE session_length_seconds IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN public.parliament_events.is_live IS 'Whether the parliament session is currently live/broadcasting';
COMMENT ON COLUMN public.parliament_events.has_ended IS 'Whether the parliament session has ended';
COMMENT ON COLUMN public.parliament_events.session_length_seconds IS 'Length of the parliament session in seconds';

