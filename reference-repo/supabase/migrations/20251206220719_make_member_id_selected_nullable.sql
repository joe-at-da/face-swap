-- Make member_id_selected nullable to allow NULL as placeholder before evaluation
-- This fixes the foreign key constraint violation when locking segments

-- Drop the foreign key constraint
ALTER TABLE portrait_collection_evaluations
DROP CONSTRAINT portrait_collection_evaluations_member_id_selected_fkey;

-- Make member_id_selected nullable
ALTER TABLE portrait_collection_evaluations
ALTER COLUMN member_id_selected DROP NOT NULL;

-- Re-add the foreign key constraint (now allows NULL)
ALTER TABLE portrait_collection_evaluations
ADD CONSTRAINT portrait_collection_evaluations_member_id_selected_fkey
FOREIGN KEY (member_id_selected)
REFERENCES parliament_members(member_id);

-- Update existing placeholder records (if any) from 0 to NULL
UPDATE portrait_collection_evaluations
SET member_id_selected = NULL
WHERE member_id_selected = 0;
