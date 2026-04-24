CREATE TABLE public.public_clip_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_clip_id UUID NULL
    REFERENCES public.user_clips(id)
    ON DELETE SET NULL,
  clip_public_url TEXT NOT NULL,
  clip_title_snapshot TEXT NULL,
  reporter_user_id UUID NULL
    REFERENCES auth.users(id)
    ON DELETE SET NULL,
  reporter_fingerprint TEXT NOT NULL,
  reason TEXT NOT NULL CHECK (
    reason IN (
      'wrong_clip',
      'misleading',
      'copyright_or_privacy',
      'harmful_or_abusive',
      'other'
    )
  ),
  details TEXT NULL CHECK (
    details IS NULL OR char_length(btrim(details)) <= 2000
  ),
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK (
    review_status IN ('pending', 'reviewed_keep', 'reviewed_remove')
  ),
  notification_status TEXT NOT NULL DEFAULT 'pending' CHECK (
    notification_status IN ('pending', 'sent', 'failed')
  ),
  notification_attempts INTEGER NOT NULL DEFAULT 0 CHECK (
    notification_attempts >= 0
  ),
  notification_last_error TEXT NULL,
  admin_notified_at TIMESTAMPTZ NULL,
  reviewed_at TIMESTAMPTZ NULL,
  reviewed_by UUID NULL
    REFERENCES auth.users(id)
    ON DELETE SET NULL,
  review_notes TEXT NULL CHECK (
    review_notes IS NULL OR char_length(btrim(review_notes)) <= 2000
  ),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.public_clip_reports IS
'Stores public reports submitted against publicly visible user clips for manual moderation review.';

COMMENT ON COLUMN public.public_clip_reports.clip_public_url IS
'Snapshot of the public clip URL at the time the report was submitted.';

COMMENT ON COLUMN public.public_clip_reports.reporter_fingerprint IS
'Server-generated hashed fingerprint used for dedupe and throttling without storing raw IP addresses.';

CREATE UNIQUE INDEX public_clip_reports_open_dedupe_idx
  ON public.public_clip_reports (user_clip_id, reporter_fingerprint, reason)
  WHERE review_status = 'pending';

CREATE INDEX public_clip_reports_pending_queue_idx
  ON public.public_clip_reports (created_at DESC, id)
  WHERE review_status = 'pending';

CREATE INDEX public_clip_reports_user_clip_history_idx
  ON public.public_clip_reports (user_clip_id, created_at DESC);

CREATE INDEX public_clip_reports_reporter_fingerprint_created_at_idx
  ON public.public_clip_reports (reporter_fingerprint, created_at DESC);

CREATE INDEX public_clip_reports_reporter_user_id_created_at_idx
  ON public.public_clip_reports (reporter_user_id, created_at DESC)
  WHERE reporter_user_id IS NOT NULL;

CREATE TRIGGER update_public_clip_reports_updated_at
  BEFORE UPDATE ON public.public_clip_reports
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- No RLS policies: access restricted to service_role only (bypasses RLS).
-- If browser-client access is needed later, add user-scoped SELECT policy.
ALTER TABLE public.public_clip_reports ENABLE ROW LEVEL SECURITY;

GRANT ALL ON TABLE public.public_clip_reports TO postgres;
GRANT ALL ON TABLE public.public_clip_reports TO service_role;
