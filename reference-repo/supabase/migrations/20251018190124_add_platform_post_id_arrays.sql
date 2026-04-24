-- Migration: Add platform post ID columns as arrays to support multiple posts over time
-- This migration:
-- 1. Converts existing text columns to text arrays
-- 2. Adds missing platform columns from supportedPlatforms.ts
-- 3. Adds appropriate indexes for array columns

-- Step 1: Convert existing post ID columns from text to text[]
-- Migrate existing data by wrapping non-null values in arrays

-- Rename existing columns temporarily
ALTER TABLE user_clips RENAME COLUMN facebook_post_id TO facebook_post_id_old;
ALTER TABLE user_clips RENAME COLUMN twitter_post_id TO twitter_post_id_old;
ALTER TABLE user_clips RENAME COLUMN tiktok_post_id TO tiktok_post_id_old;
ALTER TABLE user_clips RENAME COLUMN instagram_post_id TO instagram_post_id_old;

-- Add new array columns
ALTER TABLE user_clips ADD COLUMN facebook_post_ids text[];
ALTER TABLE user_clips ADD COLUMN twitter_post_ids text[];
ALTER TABLE user_clips ADD COLUMN tiktok_post_ids text[];
ALTER TABLE user_clips ADD COLUMN instagram_post_ids text[];

-- Migrate existing data
UPDATE user_clips
SET facebook_post_ids = ARRAY[facebook_post_id_old]
WHERE facebook_post_id_old IS NOT NULL;

UPDATE user_clips
SET twitter_post_ids = ARRAY[twitter_post_id_old]
WHERE twitter_post_id_old IS NOT NULL;

UPDATE user_clips
SET tiktok_post_ids = ARRAY[tiktok_post_id_old]
WHERE tiktok_post_id_old IS NOT NULL;

UPDATE user_clips
SET instagram_post_ids = ARRAY[instagram_post_id_old]
WHERE instagram_post_id_old IS NOT NULL;

-- Drop old columns
ALTER TABLE user_clips DROP COLUMN facebook_post_id_old;
ALTER TABLE user_clips DROP COLUMN twitter_post_id_old;
ALTER TABLE user_clips DROP COLUMN tiktok_post_id_old;
ALTER TABLE user_clips DROP COLUMN instagram_post_id_old;

-- Step 2: Add missing platform columns from supportedPlatforms.ts
ALTER TABLE user_clips ADD COLUMN linkedin_post_ids text[];
ALTER TABLE user_clips ADD COLUMN linkedin_page_post_ids text[];
ALTER TABLE user_clips ADD COLUMN instagram_standalone_post_ids text[];
ALTER TABLE user_clips ADD COLUMN threads_post_ids text[];
ALTER TABLE user_clips ADD COLUMN youtube_post_ids text[];
ALTER TABLE user_clips ADD COLUMN mastodon_post_ids text[];
ALTER TABLE user_clips ADD COLUMN bluesky_post_ids text[];

-- Step 3: Drop old indexes for renamed columns
DROP INDEX IF EXISTS idx_user_clips_facebook_post_id;
DROP INDEX IF EXISTS idx_user_clips_twitter_post_id;
DROP INDEX IF EXISTS idx_user_clips_tiktok_post_id;
DROP INDEX IF EXISTS idx_user_clips_instagram_post_id;

-- Step 4: Add GIN indexes for array columns to enable efficient searches
CREATE INDEX idx_user_clips_facebook_post_ids ON user_clips USING GIN (facebook_post_ids) WHERE facebook_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_twitter_post_ids ON user_clips USING GIN (twitter_post_ids) WHERE twitter_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_tiktok_post_ids ON user_clips USING GIN (tiktok_post_ids) WHERE tiktok_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_instagram_post_ids ON user_clips USING GIN (instagram_post_ids) WHERE instagram_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_linkedin_post_ids ON user_clips USING GIN (linkedin_post_ids) WHERE linkedin_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_linkedin_page_post_ids ON user_clips USING GIN (linkedin_page_post_ids) WHERE linkedin_page_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_instagram_standalone_post_ids ON user_clips USING GIN (instagram_standalone_post_ids) WHERE instagram_standalone_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_threads_post_ids ON user_clips USING GIN (threads_post_ids) WHERE threads_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_youtube_post_ids ON user_clips USING GIN (youtube_post_ids) WHERE youtube_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_mastodon_post_ids ON user_clips USING GIN (mastodon_post_ids) WHERE mastodon_post_ids IS NOT NULL;
CREATE INDEX idx_user_clips_bluesky_post_ids ON user_clips USING GIN (bluesky_post_ids) WHERE bluesky_post_ids IS NOT NULL;

-- Step 5: Add comment for documentation
COMMENT ON COLUMN user_clips.facebook_post_ids IS 'Array of Facebook post IDs for this clip';
COMMENT ON COLUMN user_clips.twitter_post_ids IS 'Array of Twitter/X post IDs for this clip';
COMMENT ON COLUMN user_clips.tiktok_post_ids IS 'Array of TikTok post IDs for this clip';
COMMENT ON COLUMN user_clips.instagram_post_ids IS 'Array of Instagram (Facebook Business) post IDs for this clip';
COMMENT ON COLUMN user_clips.linkedin_post_ids IS 'Array of LinkedIn post IDs for this clip';
COMMENT ON COLUMN user_clips.linkedin_page_post_ids IS 'Array of LinkedIn Page post IDs for this clip';
COMMENT ON COLUMN user_clips.instagram_standalone_post_ids IS 'Array of Instagram (Standalone) post IDs for this clip';
COMMENT ON COLUMN user_clips.threads_post_ids IS 'Array of Threads post IDs for this clip';
COMMENT ON COLUMN user_clips.youtube_post_ids IS 'Array of YouTube post IDs for this clip';
COMMENT ON COLUMN user_clips.mastodon_post_ids IS 'Array of Mastodon post IDs for this clip';
COMMENT ON COLUMN user_clips.bluesky_post_ids IS 'Array of Bluesky post IDs for this clip';
