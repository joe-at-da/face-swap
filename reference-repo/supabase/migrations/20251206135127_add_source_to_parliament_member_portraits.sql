-- Add source field to parliament_member_portraits to track portrait origin
-- This distinguishes between official Parliament API portraits and user-collected portraits

-- Add source column with constraint
ALTER TABLE parliament_member_portraits
ADD COLUMN source TEXT DEFAULT 'parliament_api' NOT NULL
CHECK (source IN ('parliament_api', 'user_uploaded'));

-- Create index for querying user-uploaded portraits
CREATE INDEX idx_parliament_member_portraits_source
ON parliament_member_portraits(source)
WHERE source = 'user_uploaded';

-- Add comment for documentation
COMMENT ON COLUMN parliament_member_portraits.source IS
'Source of the portrait: parliament_api (official from Parliament.uk) or user_uploaded (collected from portrait collection tool)';
