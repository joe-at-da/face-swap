-- Add skip_reason column to portrait_collection_evaluations table
-- This allows users to skip segments that have bad quality faces or no speaker faces

-- Create enum type for skip reasons (if it doesn't exist)
DO $$ BEGIN
    CREATE TYPE skip_reason_type AS ENUM ('bad_quality', 'no_speaker_faces');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add skip_reason column (if it doesn't exist)
DO $$ BEGIN
    ALTER TABLE portrait_collection_evaluations
    ADD COLUMN skip_reason skip_reason_type;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- Add constraint: skip_reason and member_id_selected cannot both be set
-- They can both be NULL (locked state), one can be set (completed or skipped), but not both
DO $$ BEGIN
    ALTER TABLE portrait_collection_evaluations
    ADD CONSTRAINT skip_reason_or_member_id_selected CHECK (
      NOT (skip_reason IS NOT NULL AND member_id_selected IS NOT NULL)
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Drop the existing constraint that requires selected faces
ALTER TABLE portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS must_select_at_least_one_face;

-- Add new constraint: must have selected faces if member_id_selected is set
-- Skipped segments don't need selected faces
DO $$ BEGIN
    ALTER TABLE portrait_collection_evaluations
    ADD CONSTRAINT must_select_faces_if_member_selected CHECK (
      (member_id_selected IS NULL) OR
      (member_id_selected IS NOT NULL AND array_length(selected_face_indices, 1) > 0)
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add comment
COMMENT ON COLUMN portrait_collection_evaluations.skip_reason IS
'Reason for skipping the segment: bad_quality (all faces are bad quality) or no_speaker_faces (no faces are of the speaker)';
