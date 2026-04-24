-- Fix circular foreign key constraints for Coolify backup issues
-- This migration makes foreign key constraints deferrable to avoid pg_dump warnings
-- about circular dependencies during backup operations

-- Make the user_roles -> parliament_members foreign key constraint deferrable
-- This allows the constraint check to be deferred until transaction commit
ALTER TABLE public.user_roles
DROP CONSTRAINT IF EXISTS user_roles_member_id_fkey;

ALTER TABLE public.user_roles
ADD CONSTRAINT user_roles_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

-- Make auth.users foreign key constraint deferrable as well
ALTER TABLE public.user_roles
DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey;

ALTER TABLE public.user_roles
ADD CONSTRAINT user_roles_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- For any other tables that reference parliament_members
-- Check parliament_member_clips table
ALTER TABLE public.parliament_member_clips
DROP CONSTRAINT IF EXISTS parliament_member_clips_member_id_fkey;

ALTER TABLE public.parliament_member_clips
ADD CONSTRAINT parliament_member_clips_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- For user_clips table if it has any foreign keys
ALTER TABLE public.user_clips
DROP CONSTRAINT IF EXISTS user_clips_user_id_fkey;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- For video_jobs table if it has any foreign keys
ALTER TABLE public.video_jobs
DROP CONSTRAINT IF EXISTS video_jobs_user_id_fkey;

ALTER TABLE public.video_jobs
ADD CONSTRAINT video_jobs_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- Add a comment to document why these constraints are deferrable
COMMENT ON CONSTRAINT user_roles_member_id_fkey ON public.user_roles IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

COMMENT ON CONSTRAINT user_roles_user_id_fkey ON public.user_roles IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';