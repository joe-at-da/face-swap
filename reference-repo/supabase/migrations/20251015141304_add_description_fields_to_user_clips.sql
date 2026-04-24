-- Add description and description_embedding columns to user_clips table
-- Follows same pattern as parliament_member_clips

ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL;

ALTER TABLE user_clips
ADD COLUMN IF NOT EXISTS description_embedding VECTOR(1536) DEFAULT NULL;

-- Create ivfflat index for efficient similarity search on description embeddings
CREATE INDEX IF NOT EXISTS idx_user_clips_description_embedding
ON user_clips USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON COLUMN user_clips.description IS 'AI-generated description of the clip content for display purposes';
COMMENT ON COLUMN user_clips.description_embedding IS 'Vector embedding of the description for semantic search';
