-- Fix: user_clips.user_id was NOT NULL but FK uses ON DELETE SET NULL.
-- If an auth user is deleted, Postgres tries SET NULL on a NOT NULL column → error.
-- Dropping NOT NULL allows SET NULL to succeed. Data integrity is maintained by the
-- cleanup_orphaned_personal_clips trigger (migration 20251001131153) which deletes
-- personal clips before the SET NULL fires.
ALTER TABLE public.user_clips ALTER COLUMN user_id DROP NOT NULL;
