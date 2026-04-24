-- Add new_clips_available notification preference to user_roles table
-- Enabled by default so MPs get notified when followed MP speaks in Parliament

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS new_clips_available BOOLEAN NOT NULL DEFAULT true;

COMMENT ON COLUMN public.user_roles.new_clips_available IS 'MP preference for new clips available notifications when followed MP speaks in Parliament';
