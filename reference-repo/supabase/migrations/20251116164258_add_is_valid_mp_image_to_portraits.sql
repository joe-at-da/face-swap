-- Add is_valid_mp_image column to parliament_member_portraits table
-- This field tracks whether an image has been validated as a correct MP image
-- Defaults to false for all existing and new records

ALTER TABLE parliament_member_portraits
ADD COLUMN is_valid_mp_image BOOLEAN DEFAULT false NOT NULL;

-- Add comment to document the column
COMMENT ON COLUMN parliament_member_portraits.is_valid_mp_image IS 
'Flag indicating if the image has been validated as a correct MP image. false = not yet validated, true = validated as correct';

-- Create index for better query performance when filtering by validation status
CREATE INDEX idx_parliament_member_portraits_valid_mp_image
ON parliament_member_portraits(member_id, is_valid_mp_image)
WHERE is_deleted = false;




