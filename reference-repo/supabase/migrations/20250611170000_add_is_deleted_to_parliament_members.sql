-- Add is_deleted columns to parliament_members table
-- This was missing from the previous soft deletion migration

-- Add is_deleted column to parliament_members
ALTER TABLE parliament_members 
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Create index for better query performance on is_deleted filters
CREATE INDEX idx_parliament_members_active 
ON parliament_members(member_id, is_deleted) 
WHERE is_deleted = FALSE;

-- Add composite index for member sync operations
CREATE INDEX idx_parliament_members_sync
ON parliament_members(member_id, is_deleted, last_synced_at)
WHERE is_deleted = FALSE;

-- Add comments to document the new columns
COMMENT ON COLUMN parliament_members.is_deleted IS 
'Soft deletion flag. FALSE = active member, TRUE = no longer a current member in Parliament API';

COMMENT ON COLUMN parliament_members.deleted_at IS 
'Timestamp when this member was marked as deleted during sync. NULL = never deleted'; 