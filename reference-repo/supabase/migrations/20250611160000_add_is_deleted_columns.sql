-- Add is_deleted columns to support soft deletion instead of hard deletion
-- This preserves all historical data while tracking what's currently active

-- Add is_deleted column to parliament_member_contacts
ALTER TABLE parliament_member_contacts 
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add is_deleted column to parliament_member_portraits  
ALTER TABLE parliament_member_portraits
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add is_deleted column to parliament_member_voting_history
ALTER TABLE parliament_member_voting_history
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Create indexes for better query performance on is_deleted filters
CREATE INDEX idx_parliament_member_contacts_active 
ON parliament_member_contacts(member_id, is_deleted) 
WHERE is_deleted = FALSE;

CREATE INDEX idx_parliament_member_portraits_active
ON parliament_member_portraits(member_id, is_deleted)
WHERE is_deleted = FALSE;

CREATE INDEX idx_parliament_member_voting_history_active
ON parliament_member_voting_history(member_id, is_deleted)
WHERE is_deleted = FALSE;

-- Add composite indexes for upsert operations
-- For contacts: we'll upsert based on member_id + contact_type + contact details
CREATE INDEX idx_parliament_contacts_upsert 
ON parliament_member_contacts(member_id, contact_type, COALESCE(email, ''), COALESCE(phone, ''), COALESCE(website_url, ''));

-- For portraits: we'll upsert based on member_id + crop_type + web_version
CREATE UNIQUE INDEX idx_parliament_portraits_upsert
ON parliament_member_portraits(member_id, crop_type, web_version)
WHERE is_deleted = FALSE;

-- For voting history: we'll upsert based on member_id + division_id
-- We need a unique constraint for this to work properly
CREATE UNIQUE INDEX idx_parliament_voting_history_upsert
ON parliament_member_voting_history(member_id, division_id)
WHERE division_id IS NOT NULL AND is_deleted = FALSE;

-- Add comments to document the new columns
COMMENT ON COLUMN parliament_member_contacts.is_deleted IS 
'Soft deletion flag. FALSE = active record, TRUE = no longer exists in Parliament API';

COMMENT ON COLUMN parliament_member_contacts.deleted_at IS 
'Timestamp when this record was marked as deleted during sync. NULL = never deleted';

COMMENT ON COLUMN parliament_member_portraits.is_deleted IS 
'Soft deletion flag. FALSE = active record, TRUE = no longer exists in Parliament API';

COMMENT ON COLUMN parliament_member_portraits.deleted_at IS 
'Timestamp when this record was marked as deleted during sync. NULL = never deleted';

COMMENT ON COLUMN parliament_member_voting_history.is_deleted IS 
'Soft deletion flag. FALSE = active record, TRUE = no longer exists in Parliament API';

COMMENT ON COLUMN parliament_member_voting_history.deleted_at IS 
'Timestamp when this record was marked as deleted during sync. NULL = never deleted'; 