-- Fix dedupe index: PostgreSQL treats NULLs as distinct in unique indexes,
-- so after ON DELETE SET NULL sets user_clip_id to NULL, multiple pending
-- reports for the same fingerprint+reason bypass dedup.
--
-- Use a partial index that only enforces uniqueness when user_clip_id
-- IS NOT NULL.  Reports whose clip has been deleted (user_clip_id = NULL)
-- fall outside the index entirely, which is correct -- there is nothing
-- left to deduplicate for a deleted clip.

DROP INDEX IF EXISTS public_clip_reports_open_dedupe_idx;

CREATE UNIQUE INDEX public_clip_reports_open_dedupe_idx
  ON public.public_clip_reports (user_clip_id, reporter_fingerprint, reason)
  WHERE review_status = 'pending' AND user_clip_id IS NOT NULL;
