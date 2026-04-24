-- Fix All Non-Deferrable Foreign Key Constraints - Direct Approach
-- This migration directly fixes each constraint without using dynamic SQL
-- This is more reliable and easier to debug

-- ============================================================================
-- TEAMS SYSTEM
-- ============================================================================

ALTER TABLE public.teams DROP CONSTRAINT IF EXISTS teams_owner_id_fkey;
ALTER TABLE public.teams ADD CONSTRAINT teams_owner_id_fkey 
    FOREIGN KEY (owner_id) REFERENCES auth.users(id) ON DELETE RESTRICT 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_members DROP CONSTRAINT IF EXISTS team_members_team_id_fkey;
ALTER TABLE public.team_members ADD CONSTRAINT team_members_team_id_fkey 
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_members DROP CONSTRAINT IF EXISTS team_members_user_id_fkey;
ALTER TABLE public.team_members ADD CONSTRAINT team_members_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_members DROP CONSTRAINT IF EXISTS team_members_invited_by_fkey;
ALTER TABLE public.team_members ADD CONSTRAINT team_members_invited_by_fkey 
    FOREIGN KEY (invited_by) REFERENCES auth.users(id) ON DELETE SET NULL 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_invitations DROP CONSTRAINT IF EXISTS team_invitations_team_id_fkey;
ALTER TABLE public.team_invitations ADD CONSTRAINT team_invitations_team_id_fkey 
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_invitations DROP CONSTRAINT IF EXISTS team_invitations_invited_by_fkey;
ALTER TABLE public.team_invitations ADD CONSTRAINT team_invitations_invited_by_fkey 
    FOREIGN KEY (invited_by) REFERENCES auth.users(id) ON DELETE RESTRICT 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_invitations DROP CONSTRAINT IF EXISTS team_invitations_accepted_by_fkey;
ALTER TABLE public.team_invitations ADD CONSTRAINT team_invitations_accepted_by_fkey 
    FOREIGN KEY (accepted_by) REFERENCES auth.users(id) ON DELETE SET NULL 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_mp_follows DROP CONSTRAINT IF EXISTS team_mp_follows_team_id_fkey;
ALTER TABLE public.team_mp_follows ADD CONSTRAINT team_mp_follows_team_id_fkey 
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_mp_follows DROP CONSTRAINT IF EXISTS team_mp_follows_member_id_fkey;
ALTER TABLE public.team_mp_follows ADD CONSTRAINT team_mp_follows_member_id_fkey 
    FOREIGN KEY (member_id) REFERENCES parliament_members(member_id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_mp_follows DROP CONSTRAINT IF EXISTS team_mp_follows_followed_by_fkey;
ALTER TABLE public.team_mp_follows ADD CONSTRAINT team_mp_follows_followed_by_fkey 
    FOREIGN KEY (followed_by) REFERENCES auth.users(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_notification_preferences DROP CONSTRAINT IF EXISTS team_notification_preferences_team_id_fkey;
ALTER TABLE public.team_notification_preferences ADD CONSTRAINT team_notification_preferences_team_id_fkey 
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.team_notification_preferences DROP CONSTRAINT IF EXISTS team_notification_preferences_user_id_fkey;
ALTER TABLE public.team_notification_preferences ADD CONSTRAINT team_notification_preferences_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- USER CLIPS
-- ============================================================================

ALTER TABLE public.user_clips DROP CONSTRAINT IF EXISTS user_clips_user_id_fkey;
ALTER TABLE public.user_clips ADD CONSTRAINT user_clips_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.user_clips DROP CONSTRAINT IF EXISTS user_clips_team_id_fkey;
ALTER TABLE public.user_clips ADD CONSTRAINT user_clips_team_id_fkey 
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.user_clips DROP CONSTRAINT IF EXISTS user_clips_clip_id_fkey;
ALTER TABLE public.user_clips ADD CONSTRAINT user_clips_clip_id_fkey 
    FOREIGN KEY (clip_id) REFERENCES parliament_member_clips(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- VIDEO JOBS
-- ============================================================================

ALTER TABLE public.video_jobs DROP CONSTRAINT IF EXISTS video_jobs_user_clip_id_fkey;
ALTER TABLE public.video_jobs ADD CONSTRAINT video_jobs_user_clip_id_fkey 
    FOREIGN KEY (user_clip_id) REFERENCES user_clips(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- PARLIAMENT MEMBER TABLES
-- ============================================================================

ALTER TABLE public.parliament_member_contacts DROP CONSTRAINT IF EXISTS parliament_member_contacts_member_id_fkey;
ALTER TABLE public.parliament_member_contacts ADD CONSTRAINT parliament_member_contacts_member_id_fkey 
    FOREIGN KEY (member_id) REFERENCES parliament_members(member_id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.parliament_member_portraits DROP CONSTRAINT IF EXISTS parliament_member_portraits_member_id_fkey;
ALTER TABLE public.parliament_member_portraits ADD CONSTRAINT parliament_member_portraits_member_id_fkey 
    FOREIGN KEY (member_id) REFERENCES parliament_members(member_id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.parliament_member_voting_history DROP CONSTRAINT IF EXISTS parliament_member_voting_history_member_id_fkey;
ALTER TABLE public.parliament_member_voting_history ADD CONSTRAINT parliament_member_voting_history_member_id_fkey 
    FOREIGN KEY (member_id) REFERENCES parliament_members(member_id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.parliament_member_face_encodings DROP CONSTRAINT IF EXISTS parliament_member_face_encodings_member_id_fkey;
ALTER TABLE public.parliament_member_face_encodings ADD CONSTRAINT parliament_member_face_encodings_member_id_fkey 
    FOREIGN KEY (member_id) REFERENCES parliament_members(member_id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.parliament_member_face_encodings DROP CONSTRAINT IF EXISTS parliament_member_face_encodings_portrait_id_fkey;
ALTER TABLE public.parliament_member_face_encodings ADD CONSTRAINT parliament_member_face_encodings_portrait_id_fkey 
    FOREIGN KEY (portrait_id) REFERENCES parliament_member_portraits(id) ON DELETE CASCADE 
    DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    non_deferrable_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO non_deferrable_count
    FROM pg_constraint con
    JOIN pg_class t ON con.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE con.contype = 'f'
        AND n.nspname = 'public'
        AND NOT con.condeferrable
        AND t.relname IN (
            'teams', 'team_members', 'team_invitations', 'team_mp_follows',
            'team_notification_preferences', 'user_clips', 'video_jobs',
            'parliament_member_contacts', 'parliament_member_portraits',
            'parliament_member_voting_history', 'parliament_member_face_encodings'
        );
    
    IF non_deferrable_count > 0 THEN
        RAISE WARNING 'Still have % non-deferrable foreign key constraints!', non_deferrable_count;
    ELSE
        RAISE NOTICE 'SUCCESS: All foreign key constraints are now deferrable!';
    END IF;
END $$;

