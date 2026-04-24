-- Migration: Add is_false_positive field to parliament_member_clips
-- Purpose: Flag clips that were incorrectly identified or processed

-- Add is_false_positive column to track incorrectly identified clips
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS is_false_positive BOOLEAN DEFAULT FALSE NOT NULL;

-- Create B-tree index for efficient filtering of false positive clips
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_is_false_positive
ON parliament_member_clips(is_false_positive);

-- Create composite index for filtering active, non-false-positive clips (common query)
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_active_valid
ON parliament_member_clips(is_deleted, is_false_positive)
WHERE is_deleted = FALSE AND is_false_positive = FALSE;

-- Add column comment for documentation
COMMENT ON COLUMN parliament_member_clips.is_false_positive IS
'Flag to mark clips that were incorrectly identified or processed. FALSE = valid clip, TRUE = false positive that should be excluded from search results.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully added is_false_positive column to parliament_member_clips';
    RAISE NOTICE 'Created index on is_false_positive for efficient filtering';
    RAISE NOTICE 'Created composite index for active and valid clips';
END;
$$;
