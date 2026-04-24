-- Migration: Add description and description_embedding fields to parliament_member_clips
-- Purpose: Enable AI-generated descriptions for video clips with semantic search

-- Ensure vector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Add description column
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL;

-- Add description_embedding column for vector similarity search
ALTER TABLE parliament_member_clips
ADD COLUMN IF NOT EXISTS description_embedding VECTOR(1536) DEFAULT NULL;

-- Create index on description_embedding for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_description_embedding
ON parliament_member_clips USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);

-- Create GIN index for full-text search on description
CREATE INDEX IF NOT EXISTS idx_parliament_member_clips_description_gin
ON parliament_member_clips USING gin(to_tsvector('english', COALESCE(description, '')));

-- Add comment to description column
COMMENT ON COLUMN parliament_member_clips.description IS
'AI-generated description of the clip content, used for display and search. Generated from transcript and member info.';

-- Add comment to description_embedding column
COMMENT ON COLUMN parliament_member_clips.description_embedding IS
'Vector embedding of the description for semantic similarity search. Generated using text-embedding-3-small model (1536 dimensions).';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully added description and description_embedding columns to parliament_member_clips';
    RAISE NOTICE 'Created ivfflat index on description_embedding for vector similarity search';
    RAISE NOTICE 'Created GIN index on description for full-text search';
END;
$$;
