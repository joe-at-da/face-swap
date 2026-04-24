-- Add new skip reason 'already_added_similar_pictures' to skip_reason_type enum
-- This allows users to skip segments when they've already added similar pictures to the MP

-- Add new enum value (only if it doesn't already exist)
DO $$ 
BEGIN
    -- Check if the enum value already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'already_added_similar_pictures' 
        AND enumtypid = 'skip_reason_type'::regtype
    ) THEN
        ALTER TYPE skip_reason_type ADD VALUE 'already_added_similar_pictures';
    END IF;
END $$;

-- Update comment to include the new skip reason
COMMENT ON COLUMN portrait_collection_evaluations.skip_reason IS
'Reason for skipping the segment: bad_quality (all faces are bad quality), no_speaker_faces (no faces are of the speaker), or already_added_similar_pictures (already added similar pictures to this MP)';
