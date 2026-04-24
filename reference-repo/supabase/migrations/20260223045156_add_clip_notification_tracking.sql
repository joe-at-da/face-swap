-- Add notification tracking for new clips email notifications

-- Add notification_sent_at to parliament_member_clips
ALTER TABLE public.parliament_member_clips
ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ;

-- Backfill ALL existing clips so they don't trigger notifications
UPDATE public.parliament_member_clips
SET notification_sent_at = NOW()
WHERE notification_sent_at IS NULL;

-- Per-user+clip notification tracking for precise retry on failure
CREATE TABLE public.clip_notification_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  clip_id UUID NOT NULL REFERENCES public.parliament_member_clips(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(clip_id, user_id)
);

CREATE INDEX idx_clip_notification_log_clip_id ON public.clip_notification_log(clip_id);

-- RLS enabled, service_role only (cron job uses admin client)
ALTER TABLE public.clip_notification_log ENABLE ROW LEVEL SECURITY;

GRANT ALL ON TABLE public.clip_notification_log TO postgres;
GRANT ALL ON TABLE public.clip_notification_log TO service_role;
