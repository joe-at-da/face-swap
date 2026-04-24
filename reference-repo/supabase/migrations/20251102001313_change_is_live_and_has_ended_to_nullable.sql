-- Change is_live and has_ended columns to be nullable with NULL default
-- instead of NOT NULL with FALSE default

ALTER TABLE public.parliament_events
  ALTER COLUMN is_live DROP NOT NULL,
  ALTER COLUMN is_live DROP DEFAULT,
  ALTER COLUMN is_live SET DEFAULT NULL,
  ALTER COLUMN has_ended DROP NOT NULL,
  ALTER COLUMN has_ended DROP DEFAULT,
  ALTER COLUMN has_ended SET DEFAULT NULL;

-- Update comments to reflect nullable status
COMMENT ON COLUMN public.parliament_events.is_live IS 'Whether the parliament session is currently live/broadcasting. NULL indicates unknown status.';
COMMENT ON COLUMN public.parliament_events.has_ended IS 'Whether the parliament session has ended. NULL indicates unknown status.';

