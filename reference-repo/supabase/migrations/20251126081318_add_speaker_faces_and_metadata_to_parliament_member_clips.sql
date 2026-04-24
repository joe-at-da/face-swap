-- Migration: Add speaker faces array and metadata fields to parliament_member_clips
-- Purpose: Store face detection data, unidentified speaker flags, and additional metadata

-- Add speaker_faces column (array of JSONB objects)
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS speaker_faces jsonb[] DEFAULT NULL;

-- Add is_unidentified column (boolean flag)
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS is_unidentified BOOLEAN DEFAULT FALSE NOT NULL;

-- Add asd_meta column (JSONB for additional metadata)
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS asd_meta JSONB DEFAULT NULL;

-- Add mp_id_meta column (JSONB for member identification metadata)
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS mp_id_meta JSONB DEFAULT NULL;

-- Create GIN index on speaker_faces for efficient array queries
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_speaker_faces
ON parliament_member_clips USING GIN (speaker_faces)
WHERE speaker_faces IS NOT NULL;

-- Create B-tree index on is_unidentified for filtering queries
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_is_unidentified
ON parliament_member_clips(is_unidentified);

-- Create GIN index on asd_meta for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_asd_meta
ON parliament_member_clips USING GIN (asd_meta)
WHERE asd_meta IS NOT NULL;

-- Create GIN index on mp_id_meta for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_mp_id_meta
ON parliament_member_clips USING GIN (mp_id_meta)
WHERE mp_id_meta IS NOT NULL;

-- Add column comments for documentation
COMMENT ON COLUMN parliament_member_clips.speaker_faces IS
'Array of JSONB objects containing face detection and recognition data for each detected face in the clip. Each object may contain face coordinates, confidence scores, and identification information.';

COMMENT ON COLUMN parliament_member_clips.is_unidentified IS
'Flag to mark clips where the speaker could not be identified. FALSE = speaker identified, TRUE = speaker unidentified.';

COMMENT ON COLUMN parliament_member_clips.asd_meta IS
'Additional metadata in JSON format for the clip. Stores supplementary information related to audio/speech detection and processing.';

COMMENT ON COLUMN parliament_member_clips.mp_id_meta IS
'Metadata related to member identification in JSON format. Contains information about the identification process, confidence scores, and related data.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully added speaker_faces, is_unidentified, asd_meta, and mp_id_meta columns to parliament_member_clips';
    RAISE NOTICE 'Created GIN index on speaker_faces array for efficient queries';
    RAISE NOTICE 'Created B-tree index on is_unidentified for filtering';
    RAISE NOTICE 'Created GIN indexes on asd_meta and mp_id_meta for JSONB queries';
END;
$$;

