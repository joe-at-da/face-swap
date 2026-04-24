-- Fix User Clips Cascade Deletion Behavior
-- Migration to properly handle deletion of user accounts and teams:
-- 1. Personal clips (no team_id) -> Deleted when user deletes account
-- 2. Team clips (team_id set) -> Preserved when user deletes account
-- 3. Team clips -> Deleted when team is deleted
-- 4. Prevent orphaned clips (must have user_id OR team_id)

-- Step 1: Drop existing foreign key constraints
ALTER TABLE user_clips
DROP CONSTRAINT IF EXISTS user_clips_user_id_fkey,
DROP CONSTRAINT IF EXISTS user_clips_team_id_fkey;

-- Step 2: Add new foreign key constraint for user_id with SET NULL
-- This allows us to handle deletion logic via trigger
ALTER TABLE user_clips
ADD CONSTRAINT user_clips_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES auth.users(id)
    ON DELETE SET NULL;

-- Step 3: Add new foreign key constraint for team_id with CASCADE
-- When team is deleted, all team clips should be deleted
ALTER TABLE user_clips
ADD CONSTRAINT user_clips_team_id_fkey
    FOREIGN KEY (team_id)
    REFERENCES teams(id)
    ON DELETE CASCADE;

-- Step 4: Add CHECK constraint to prevent orphaned clips
-- Every clip must have EITHER a user_id OR a team_id (or both)
ALTER TABLE user_clips
ADD CONSTRAINT user_clips_must_have_owner
    CHECK (user_id IS NOT NULL OR team_id IS NOT NULL);

-- Step 5: Create function to handle user_id becoming NULL (from SET NULL cascade)
-- This deletes clips that have no team (orphaned personal clips)
CREATE OR REPLACE FUNCTION cleanup_orphaned_personal_clips()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- If user_id was set to NULL and there's no team_id, delete the clip
    -- This happens when a user deletes their account and they had personal clips
    IF NEW.user_id IS NULL AND NEW.team_id IS NULL THEN
        -- Delete this orphaned personal clip
        DELETE FROM user_clips WHERE id = NEW.id;
        RAISE LOG 'Deleted orphaned personal clip % after user deletion', NEW.id;
        RETURN NULL; -- Prevent the UPDATE since we're deleting
    END IF;

    RETURN NEW;
END;
$$;

-- Step 6: Create trigger on user_clips table BEFORE UPDATE
-- This runs when the foreign key SET NULL updates user_id to NULL
CREATE TRIGGER cleanup_orphaned_clips_trigger
    BEFORE UPDATE OF user_id ON user_clips
    FOR EACH ROW
    WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL)
    EXECUTE FUNCTION cleanup_orphaned_personal_clips();

-- Step 7: Add comments for documentation
COMMENT ON CONSTRAINT user_clips_user_id_fkey ON user_clips IS
'User reference with SET NULL on delete. Trigger deletes personal clips (team_id IS NULL) and preserves team clips.';

COMMENT ON CONSTRAINT user_clips_team_id_fkey ON user_clips IS
'Team reference with CASCADE on delete. Team clips are deleted when team is deleted.';

COMMENT ON CONSTRAINT user_clips_must_have_owner ON user_clips IS
'Ensures every clip has either a user_id or team_id (or both). Prevents orphaned clips.';

COMMENT ON FUNCTION cleanup_orphaned_personal_clips IS
'Deletes clips when user_id becomes NULL and team_id is also NULL (orphaned personal clips from user deletion).';

COMMENT ON TRIGGER cleanup_orphaned_clips_trigger ON user_clips IS
'Runs when user_id is set to NULL to delete orphaned personal clips while preserving team clips.';

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'User clips cascade deletion fix completed:';
    RAISE NOTICE '- Personal clips (no team_id) will be deleted when user deletes account';
    RAISE NOTICE '- Team clips (with team_id) will be preserved when user deletes account';
    RAISE NOTICE '- Team clips will be deleted when team is deleted';
    RAISE NOTICE '- CHECK constraint prevents orphaned clips (must have user_id OR team_id)';
    RAISE NOTICE '- Trigger: cleanup_orphaned_clips_trigger on user_clips BEFORE UPDATE of user_id';
    RAISE NOTICE '- Function: cleanup_orphaned_personal_clips() implements deletion logic';
END $$;
