-- Fix Missing Circular Foreign Key Constraints for pg_dump
-- This migration makes additional foreign key constraints deferrable that were
-- identified from the live database but not yet applied.
-- This complements the previous migration 20251106175333_fix_all_circular_foreign_key_constraints.sql

-- ============================================================================
-- PARLIAMENT MEMBER RELATED FOREIGN KEYS
-- ============================================================================

-- parliament_member_contacts.member_id -> parliament_members(member_id)
ALTER TABLE public.parliament_member_contacts
DROP CONSTRAINT IF EXISTS parliament_member_contacts_member_id_fkey;

ALTER TABLE public.parliament_member_contacts
ADD CONSTRAINT parliament_member_contacts_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT parliament_member_contacts_member_id_fkey ON public.parliament_member_contacts IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- parliament_member_portraits.member_id -> parliament_members(member_id)
ALTER TABLE public.parliament_member_portraits
DROP CONSTRAINT IF EXISTS parliament_member_portraits_member_id_fkey;

ALTER TABLE public.parliament_member_portraits
ADD CONSTRAINT parliament_member_portraits_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT parliament_member_portraits_member_id_fkey ON public.parliament_member_portraits IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- parliament_member_voting_history.member_id -> parliament_members(member_id)
ALTER TABLE public.parliament_member_voting_history
DROP CONSTRAINT IF EXISTS parliament_member_voting_history_member_id_fkey;

ALTER TABLE public.parliament_member_voting_history
ADD CONSTRAINT parliament_member_voting_history_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT parliament_member_voting_history_member_id_fkey ON public.parliament_member_voting_history IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- TEAMS SYSTEM FOREIGN KEYS (if not already applied)
-- ============================================================================

-- teams.owner_id -> auth.users(id)
ALTER TABLE public.teams
DROP CONSTRAINT IF EXISTS teams_owner_id_fkey;

ALTER TABLE public.teams
ADD CONSTRAINT teams_owner_id_fkey
FOREIGN KEY (owner_id)
REFERENCES auth.users(id)
ON DELETE RESTRICT
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT teams_owner_id_fkey ON public.teams IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_members.team_id -> teams(id)
ALTER TABLE public.team_members
DROP CONSTRAINT IF EXISTS team_members_team_id_fkey;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_members_team_id_fkey ON public.team_members IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_members.user_id -> auth.users(id)
ALTER TABLE public.team_members
DROP CONSTRAINT IF EXISTS team_members_user_id_fkey;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_members_user_id_fkey ON public.team_members IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_members.invited_by -> auth.users(id)
ALTER TABLE public.team_members
DROP CONSTRAINT IF EXISTS team_members_invited_by_fkey;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_invited_by_fkey
FOREIGN KEY (invited_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_members_invited_by_fkey ON public.team_members IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_invitations.team_id -> teams(id)
ALTER TABLE public.team_invitations
DROP CONSTRAINT IF EXISTS team_invitations_team_id_fkey;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_invitations_team_id_fkey ON public.team_invitations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_invitations.invited_by -> auth.users(id)
ALTER TABLE public.team_invitations
DROP CONSTRAINT IF EXISTS team_invitations_invited_by_fkey;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_invited_by_fkey
FOREIGN KEY (invited_by)
REFERENCES auth.users(id)
ON DELETE RESTRICT
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_invitations_invited_by_fkey ON public.team_invitations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_invitations.accepted_by -> auth.users(id)
ALTER TABLE public.team_invitations
DROP CONSTRAINT IF EXISTS team_invitations_accepted_by_fkey;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_accepted_by_fkey
FOREIGN KEY (accepted_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_invitations_accepted_by_fkey ON public.team_invitations IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_mp_follows.team_id -> teams(id)
ALTER TABLE public.team_mp_follows
DROP CONSTRAINT IF EXISTS team_mp_follows_team_id_fkey;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_mp_follows_team_id_fkey ON public.team_mp_follows IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_mp_follows.member_id -> parliament_members(member_id)
ALTER TABLE public.team_mp_follows
DROP CONSTRAINT IF EXISTS team_mp_follows_member_id_fkey;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_mp_follows_member_id_fkey ON public.team_mp_follows IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_mp_follows.followed_by -> auth.users(id)
ALTER TABLE public.team_mp_follows
DROP CONSTRAINT IF EXISTS team_mp_follows_followed_by_fkey;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_followed_by_fkey
FOREIGN KEY (followed_by)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_mp_follows_followed_by_fkey ON public.team_mp_follows IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_notification_preferences.team_id -> teams(id)
ALTER TABLE public.team_notification_preferences
DROP CONSTRAINT IF EXISTS team_notification_preferences_team_id_fkey;

ALTER TABLE public.team_notification_preferences
ADD CONSTRAINT team_notification_preferences_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_notification_preferences_team_id_fkey ON public.team_notification_preferences IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- team_notification_preferences.user_id -> auth.users(id)
ALTER TABLE public.team_notification_preferences
DROP CONSTRAINT IF EXISTS team_notification_preferences_user_id_fkey;

ALTER TABLE public.team_notification_preferences
ADD CONSTRAINT team_notification_preferences_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT team_notification_preferences_user_id_fkey ON public.team_notification_preferences IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- USER CLIPS FOREIGN KEYS (if not already applied)
-- ============================================================================

-- user_clips.user_id -> auth.users(id)
ALTER TABLE public.user_clips
DROP CONSTRAINT IF EXISTS user_clips_user_id_fkey;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT user_clips_user_id_fkey ON public.user_clips IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups. SET NULL on delete to allow trigger-based cleanup of orphaned personal clips.';

-- user_clips.team_id -> teams(id)
ALTER TABLE public.user_clips
DROP CONSTRAINT IF EXISTS user_clips_team_id_fkey;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT user_clips_team_id_fkey ON public.user_clips IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups. CASCADE on delete to remove team clips when team is deleted.';

-- user_clips.clip_id -> parliament_member_clips(id)
ALTER TABLE public.user_clips
DROP CONSTRAINT IF EXISTS user_clips_clip_id_fkey;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_clip_id_fkey
FOREIGN KEY (clip_id)
REFERENCES parliament_member_clips(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT user_clips_clip_id_fkey ON public.user_clips IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- VIDEO JOBS FOREIGN KEYS (if not already applied)
-- ============================================================================

-- video_jobs.user_id -> auth.users(id)
ALTER TABLE public.video_jobs
DROP CONSTRAINT IF EXISTS video_jobs_user_id_fkey;

ALTER TABLE public.video_jobs
ADD CONSTRAINT video_jobs_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT video_jobs_user_id_fkey ON public.video_jobs IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- video_jobs.user_clip_id -> user_clips(id)
ALTER TABLE public.video_jobs
DROP CONSTRAINT IF EXISTS video_jobs_user_clip_id_fkey;

ALTER TABLE public.video_jobs
ADD CONSTRAINT video_jobs_user_clip_id_fkey
FOREIGN KEY (user_clip_id)
REFERENCES user_clips(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT video_jobs_user_clip_id_fkey ON public.video_jobs IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- PARLIAMENT MEMBER FACE ENCODINGS FOREIGN KEYS (if not already applied)
-- ============================================================================

-- parliament_member_face_encodings.member_id -> parliament_members(member_id)
ALTER TABLE public.parliament_member_face_encodings
DROP CONSTRAINT IF EXISTS parliament_member_face_encodings_member_id_fkey;

ALTER TABLE public.parliament_member_face_encodings
ADD CONSTRAINT parliament_member_face_encodings_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT parliament_member_face_encodings_member_id_fkey ON public.parliament_member_face_encodings IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- parliament_member_face_encodings.portrait_id -> parliament_member_portraits(id)
ALTER TABLE public.parliament_member_face_encodings
DROP CONSTRAINT IF EXISTS parliament_member_face_encodings_portrait_id_fkey;

ALTER TABLE public.parliament_member_face_encodings
ADD CONSTRAINT parliament_member_face_encodings_portrait_id_fkey
FOREIGN KEY (portrait_id)
REFERENCES parliament_member_portraits(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

COMMENT ON CONSTRAINT parliament_member_face_encodings_portrait_id_fkey ON public.parliament_member_face_encodings IS
'Deferrable constraint to prevent circular dependency issues during pg_dump backups';

-- ============================================================================
-- VERIFICATION AND LOGGING
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Missing circular foreign key constraints fix completed:';
    RAISE NOTICE '- Made all parliament_member related foreign keys deferrable (contacts, portraits, voting_history, face_encodings)';
    RAISE NOTICE '- Made all teams system foreign keys deferrable';
    RAISE NOTICE '- Made all user_clips foreign keys deferrable';
    RAISE NOTICE '- Made all video_jobs foreign keys deferrable';
    RAISE NOTICE '- All constraints are now DEFERRABLE INITIALLY DEFERRED';
    RAISE NOTICE '- This should resolve pg_dump circular dependency warnings';
END $$;

