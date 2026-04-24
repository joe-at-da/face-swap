-- Migration: Fix segment_evaluations to allow nullable is_correct during locking phase

-- Drop the old CHECK constraint
ALTER TABLE segment_evaluations
DROP CONSTRAINT IF EXISTS error_reason_required_when_incorrect;

-- Make is_correct nullable (it was previously NOT NULL)
ALTER TABLE segment_evaluations
ALTER COLUMN is_correct DROP NOT NULL;

-- Add the new CHECK constraint that allows null during locking
ALTER TABLE segment_evaluations
ADD CONSTRAINT error_reason_required_when_incorrect CHECK (
  (is_correct IS NULL) OR  -- Allow null during locking phase
  (is_correct = true AND error_reason IS NULL) OR
  (is_correct = false AND error_reason IS NOT NULL)
);

-- Update the column comment to reflect the change
COMMENT ON COLUMN segment_evaluations.is_correct IS 'Whether the auto-detected MP identification was correct (null during locking phase, set when evaluation is submitted)';
