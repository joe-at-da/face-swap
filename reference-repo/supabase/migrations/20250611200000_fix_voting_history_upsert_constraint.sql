-- Fix Parliament Voting History Unique Constraint for Upsert Operations
-- Migration to allow upsert operations on parliament_member_voting_history table
-- 
-- The issue: PostgreSQL's ON CONFLICT clause cannot use partial unique indexes
-- (those with WHERE clauses) which was preventing upsert operations.
--
-- Solution: Replace the partial unique index with a full unique constraint
-- and handle soft deletion at the application level.

-- Drop the existing partial unique index
DROP INDEX IF EXISTS idx_parliament_voting_history_upsert;

-- Create a new unique constraint without WHERE clause that works with ON CONFLICT
-- Include is_deleted in the constraint to handle soft deletion properly
-- This allows multiple "deleted" records but only one active record per member/division
CREATE UNIQUE INDEX idx_parliament_voting_history_upsert_full
ON parliament_member_voting_history(member_id, division_id, is_deleted);

-- Create a separate partial index for active records only (for query performance)
-- This maintains the performance benefits of the original index
CREATE INDEX idx_parliament_voting_history_active_only
ON parliament_member_voting_history(member_id, division_id)
WHERE is_deleted = FALSE AND division_id IS NOT NULL;

-- Add comments to document the changes
COMMENT ON INDEX idx_parliament_voting_history_upsert_full IS 
'Full unique constraint for parliament voting history upsert operations. Includes is_deleted to allow soft deletion while maintaining uniqueness.';

COMMENT ON INDEX idx_parliament_voting_history_active_only IS 
'Performance index for active (non-deleted) voting history records with non-null division_id.';

-- Note: This allows:
-- 1. Upsert operations using ON CONFLICT (member_id, division_id, is_deleted)
-- 2. Multiple soft-deleted records for the same member/division
-- 3. Only one active record per member/division combination
-- 4. NULL division_id values (which PostgreSQL treats as unique)

-- Note: The application layer should filter out records with NULL division_id 
-- before attempting upsert operations, as done in the current sync service. 