-- Add skip_reason column to portrait_collection_evaluations table
-- This allows users to skip segments that have bad quality faces or no speaker faces

-- Add skip_reason column with enum values
CREATE TYPE skip_reason_type AS ENUM ('bad_quality', 'no_speaker_faces');

ALTER TABLE portrait_collection_evaluations
ADD COLUMN skip_reason skip_reason_type;

-- Add constraint: skip_reason and member_id_selected cannot both be set
-- They can both be NULL (locked state), one can be set (completed or skipped), but not both
ALTER TABLE portrait_collection_evaluations
ADD CONSTRAINT skip_reason_or_member_id_selected CHECK (
  NOT (skip_reason IS NOT NULL AND member_id_selected IS NOT NULL)
);

-- Drop the existing constraint that requires selected faces
ALTER TABLE portrait_collection_evaluations
DROP CONSTRAINT IF EXISTS must_select_at_least_one_face;

-- Add new constraint: must have selected faces if member_id_selected is set
-- Skipped segments don't need selected faces
ALTER TABLE portrait_collection_evaluations
ADD CONSTRAINT must_select_faces_if_member_selected CHECK (
  (member_id_selected IS NULL) OR
  (member_id_selected IS NOT NULL AND array_length(selected_face_indices, 1) > 0)
);

-- Add comment
COMMENT ON COLUMN portrait_collection_evaluations.skip_reason IS
'Reason for skipping the segment: bad_quality (all faces are bad quality) or no_speaker_faces (no faces are of the speaker)';
