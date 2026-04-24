-- Migration: Add title, title_embedding, and view_count to user_clips
-- Purpose: Enable user-friendly titles with semantic search and view tracking

-- Ensure vector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Add title column
ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS title TEXT DEFAULT NULL;

-- Add title_embedding column for vector similarity search
ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS title_embedding VECTOR(1536) DEFAULT NULL;

-- Add view_count column to track clip views
ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0 NOT NULL;

-- Create IVFFlat index on title_embedding for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_user_clips_title_embedding
ON user_clips USING ivfflat (title_embedding vector_cosine_ops)
WITH (lists = 100);

-- Create GIN index for full-text search on title
CREATE INDEX IF NOT EXISTS idx_user_clips_title_gin
ON user_clips USING gin(to_tsvector('english', COALESCE(title, '')));

-- Create B-tree index on view_count for efficient sorting by popularity
CREATE INDEX IF NOT EXISTS idx_user_clips_view_count
ON user_clips(view_count);

-- Add column comments for documentation
COMMENT ON COLUMN user_clips.title IS
'User-friendly title for the clip. Can be set by user or auto-generated.';

COMMENT ON COLUMN user_clips.title_embedding IS
'Vector embedding of the title for semantic similarity search. Generated using text-embedding-3-small model (1536 dimensions).';

COMMENT ON COLUMN user_clips.view_count IS
'Number of times this clip has been viewed. Defaults to 0.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Successfully added title, title_embedding, and view_count columns to user_clips';
    RAISE NOTICE 'Created ivfflat index on title_embedding for vector similarity search';
    RAISE NOTICE 'Created GIN index on title for full-text search';
    RAISE NOTICE 'Created B-tree index on view_count for popularity sorting';
END;
$$;
