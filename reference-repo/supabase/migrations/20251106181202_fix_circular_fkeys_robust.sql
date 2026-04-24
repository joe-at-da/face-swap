-- Fix Circular Foreign Key Constraints - Robust Approach
-- This migration uses a more robust method to ensure all foreign key constraints
-- are made deferrable by explicitly handling each constraint

-- ============================================================================
-- PARLIAMENT MEMBER RELATED FOREIGN KEYS
-- ============================================================================

-- parliament_member_contacts.member_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'parliament_member_contacts_member_id_fkey'
        AND conrelid = 'public.parliament_member_contacts'::regclass
    ) THEN
        ALTER TABLE public.parliament_member_contacts
        DROP CONSTRAINT parliament_member_contacts_member_id_fkey;
    END IF;
END $$;

ALTER TABLE public.parliament_member_contacts
ADD CONSTRAINT parliament_member_contacts_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- parliament_member_portraits.member_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'parliament_member_portraits_member_id_fkey'
        AND conrelid = 'public.parliament_member_portraits'::regclass
    ) THEN
        ALTER TABLE public.parliament_member_portraits
        DROP CONSTRAINT parliament_member_portraits_member_id_fkey;
    END IF;
END $$;

ALTER TABLE public.parliament_member_portraits
ADD CONSTRAINT parliament_member_portraits_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- parliament_member_voting_history.member_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'parliament_member_voting_history_member_id_fkey'
        AND conrelid = 'public.parliament_member_voting_history'::regclass
    ) THEN
        ALTER TABLE public.parliament_member_voting_history
        DROP CONSTRAINT parliament_member_voting_history_member_id_fkey;
    END IF;
END $$;

ALTER TABLE public.parliament_member_voting_history
ADD CONSTRAINT parliament_member_voting_history_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- parliament_member_face_encodings.member_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'parliament_member_face_encodings_member_id_fkey'
        AND conrelid = 'public.parliament_member_face_encodings'::regclass
    ) THEN
        ALTER TABLE public.parliament_member_face_encodings
        DROP CONSTRAINT parliament_member_face_encodings_member_id_fkey;
    END IF;
END $$;

ALTER TABLE public.parliament_member_face_encodings
ADD CONSTRAINT parliament_member_face_encodings_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- parliament_member_face_encodings.portrait_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'parliament_member_face_encodings_portrait_id_fkey'
        AND conrelid = 'public.parliament_member_face_encodings'::regclass
    ) THEN
        ALTER TABLE public.parliament_member_face_encodings
        DROP CONSTRAINT parliament_member_face_encodings_portrait_id_fkey;
    END IF;
END $$;

ALTER TABLE public.parliament_member_face_encodings
ADD CONSTRAINT parliament_member_face_encodings_portrait_id_fkey
FOREIGN KEY (portrait_id)
REFERENCES parliament_member_portraits(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- TEAMS SYSTEM FOREIGN KEYS
-- ============================================================================

-- teams.owner_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'teams_owner_id_fkey'
        AND conrelid = 'public.teams'::regclass
    ) THEN
        ALTER TABLE public.teams
        DROP CONSTRAINT teams_owner_id_fkey;
    END IF;
END $$;

ALTER TABLE public.teams
ADD CONSTRAINT teams_owner_id_fkey
FOREIGN KEY (owner_id)
REFERENCES auth.users(id)
ON DELETE RESTRICT
DEFERRABLE INITIALLY DEFERRED;

-- team_members.team_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_members_team_id_fkey'
        AND conrelid = 'public.team_members'::regclass
    ) THEN
        ALTER TABLE public.team_members
        DROP CONSTRAINT team_members_team_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_members.user_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_members_user_id_fkey'
        AND conrelid = 'public.team_members'::regclass
    ) THEN
        ALTER TABLE public.team_members
        DROP CONSTRAINT team_members_user_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_members.invited_by
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_members_invited_by_fkey'
        AND conrelid = 'public.team_members'::regclass
    ) THEN
        ALTER TABLE public.team_members
        DROP CONSTRAINT team_members_invited_by_fkey;
    END IF;
END $$;

ALTER TABLE public.team_members
ADD CONSTRAINT team_members_invited_by_fkey
FOREIGN KEY (invited_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

-- team_invitations.team_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_invitations_team_id_fkey'
        AND conrelid = 'public.team_invitations'::regclass
    ) THEN
        ALTER TABLE public.team_invitations
        DROP CONSTRAINT team_invitations_team_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_invitations.invited_by
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_invitations_invited_by_fkey'
        AND conrelid = 'public.team_invitations'::regclass
    ) THEN
        ALTER TABLE public.team_invitations
        DROP CONSTRAINT team_invitations_invited_by_fkey;
    END IF;
END $$;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_invited_by_fkey
FOREIGN KEY (invited_by)
REFERENCES auth.users(id)
ON DELETE RESTRICT
DEFERRABLE INITIALLY DEFERRED;

-- team_invitations.accepted_by
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_invitations_accepted_by_fkey'
        AND conrelid = 'public.team_invitations'::regclass
    ) THEN
        ALTER TABLE public.team_invitations
        DROP CONSTRAINT team_invitations_accepted_by_fkey;
    END IF;
END $$;

ALTER TABLE public.team_invitations
ADD CONSTRAINT team_invitations_accepted_by_fkey
FOREIGN KEY (accepted_by)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

-- team_mp_follows.team_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_mp_follows_team_id_fkey'
        AND conrelid = 'public.team_mp_follows'::regclass
    ) THEN
        ALTER TABLE public.team_mp_follows
        DROP CONSTRAINT team_mp_follows_team_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_mp_follows.member_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_mp_follows_member_id_fkey'
        AND conrelid = 'public.team_mp_follows'::regclass
    ) THEN
        ALTER TABLE public.team_mp_follows
        DROP CONSTRAINT team_mp_follows_member_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_member_id_fkey
FOREIGN KEY (member_id)
REFERENCES parliament_members(member_id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_mp_follows.followed_by
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_mp_follows_followed_by_fkey'
        AND conrelid = 'public.team_mp_follows'::regclass
    ) THEN
        ALTER TABLE public.team_mp_follows
        DROP CONSTRAINT team_mp_follows_followed_by_fkey;
    END IF;
END $$;

ALTER TABLE public.team_mp_follows
ADD CONSTRAINT team_mp_follows_followed_by_fkey
FOREIGN KEY (followed_by)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_notification_preferences.team_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_notification_preferences_team_id_fkey'
        AND conrelid = 'public.team_notification_preferences'::regclass
    ) THEN
        ALTER TABLE public.team_notification_preferences
        DROP CONSTRAINT team_notification_preferences_team_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_notification_preferences
ADD CONSTRAINT team_notification_preferences_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- team_notification_preferences.user_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'team_notification_preferences_user_id_fkey'
        AND conrelid = 'public.team_notification_preferences'::regclass
    ) THEN
        ALTER TABLE public.team_notification_preferences
        DROP CONSTRAINT team_notification_preferences_user_id_fkey;
    END IF;
END $$;

ALTER TABLE public.team_notification_preferences
ADD CONSTRAINT team_notification_preferences_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- USER CLIPS FOREIGN KEYS
-- ============================================================================

-- user_clips.user_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_clips_user_id_fkey'
        AND conrelid = 'public.user_clips'::regclass
    ) THEN
        ALTER TABLE public.user_clips
        DROP CONSTRAINT user_clips_user_id_fkey;
    END IF;
END $$;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES auth.users(id)
ON DELETE SET NULL
DEFERRABLE INITIALLY DEFERRED;

-- user_clips.team_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_clips_team_id_fkey'
        AND conrelid = 'public.user_clips'::regclass
    ) THEN
        ALTER TABLE public.user_clips
        DROP CONSTRAINT user_clips_team_id_fkey;
    END IF;
END $$;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_team_id_fkey
FOREIGN KEY (team_id)
REFERENCES teams(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- user_clips.clip_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_clips_clip_id_fkey'
        AND conrelid = 'public.user_clips'::regclass
    ) THEN
        ALTER TABLE public.user_clips
        DROP CONSTRAINT user_clips_clip_id_fkey;
    END IF;
END $$;

ALTER TABLE public.user_clips
ADD CONSTRAINT user_clips_clip_id_fkey
FOREIGN KEY (clip_id)
REFERENCES parliament_member_clips(id)
ON DELETE CASCADE
DEFERRABLE INITIALLY DEFERRED;

-- ============================================================================
-- VIDEO JOBS FOREIGN KEYS
-- ============================================================================

-- video_jobs.user_clip_id
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'video_jobs_user_clip_id_fkey'
        AND conrelid = 'public.video_jobs'::regclass
    ) THEN
        ALTER TABLE public.video_jobs
        DROP CONSTRAINT video_jobs_user_clip_id_fkey;
    END IF;
END $$;

ALTER TABLE public.video_jobs
ADD CONSTRAINT video_jobs_user_clip_id_fkey
FOREIGN KEY (user_clip_id)
REFERENCES user_clips(id)
ON DELETE CASCADE
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
        RAISE WARNING 'Still have % non-deferrable foreign key constraints', non_deferrable_count;
    ELSE
        RAISE NOTICE 'All foreign key constraints are now deferrable!';
    END IF;
END $$;

