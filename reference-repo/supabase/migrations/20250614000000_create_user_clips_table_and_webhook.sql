-- Create User Clips Table and Webhook Migration
-- Migration to:
-- 1. Create user_clips table with foreign key references
-- 2. Remove social media post ID columns from parliament_member_clips table
-- 3. Setup webhook to call /api/webhooks/create-user-clip when user clips are created or updated

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create user_clips table
CREATE TABLE user_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User reference (automatically set using RLS and auth.uid())
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Reference to parliament_member_clips
    clip_id UUID NOT NULL REFERENCES parliament_member_clips(id) ON DELETE CASCADE,
    
    -- Timestamp fields as text (consistent with parliament_member_clips)
    start_timestamp TEXT NOT NULL,
    end_timestamp TEXT NOT NULL,
    
    -- Media file information
    clip_url TEXT,
    full_video_path TEXT,
    
    -- Processing status (reusing existing enum)
    status parliament_clip_status DEFAULT 'pending_review',
    
    -- Social media post IDs (moved from parliament_member_clips)
    facebook_post_id TEXT DEFAULT NULL,
    twitter_post_id TEXT DEFAULT NULL,
    tiktok_post_id TEXT DEFAULT NULL,
    instagram_post_id TEXT DEFAULT NULL,
    
    -- Soft deletion support
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_timestamp_length CHECK (
        length(start_timestamp) > 0 AND length(start_timestamp) <= 100 AND
        length(end_timestamp) > 0 AND length(end_timestamp) <= 100
    )
);

-- Create indexes for better query performance
CREATE INDEX idx_user_clips_user_id ON user_clips(user_id);
CREATE INDEX idx_user_clips_clip_id ON user_clips(clip_id);
CREATE INDEX idx_user_clips_start_timestamp ON user_clips(start_timestamp);
CREATE INDEX idx_user_clips_end_timestamp ON user_clips(end_timestamp);
CREATE INDEX idx_user_clips_status ON user_clips(status);
CREATE INDEX idx_user_clips_active ON user_clips(user_id, is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_user_clips_created_at ON user_clips(created_at);
CREATE INDEX idx_user_clips_facebook_post_id ON user_clips(facebook_post_id) WHERE facebook_post_id IS NOT NULL;
CREATE INDEX idx_user_clips_twitter_post_id ON user_clips(twitter_post_id) WHERE twitter_post_id IS NOT NULL;
CREATE INDEX idx_user_clips_tiktok_post_id ON user_clips(tiktok_post_id) WHERE tiktok_post_id IS NOT NULL;
CREATE INDEX idx_user_clips_instagram_post_id ON user_clips(instagram_post_id) WHERE instagram_post_id IS NOT NULL;

-- Create composite index for common queries (user + clip + status)
CREATE INDEX idx_user_clips_user_clip_status 
ON user_clips(user_id, clip_id, status) 
WHERE is_deleted = FALSE;

-- Create updated_at trigger for user_clips
CREATE TRIGGER update_user_clips_updated_at 
    BEFORE UPDATE ON user_clips 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE user_clips ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_clips
-- Users can only see their own clips
CREATE POLICY "Users can view their own clips" 
ON user_clips
FOR SELECT 
USING (auth.uid() = user_id);

-- Users can insert their own clips (user_id will be set automatically)
CREATE POLICY "Users can insert their own clips" 
ON user_clips
FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Users can update their own clips
CREATE POLICY "Users can update their own clips" 
ON user_clips
FOR UPDATE 
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can delete their own clips
CREATE POLICY "Users can delete their own clips" 
ON user_clips
FOR DELETE 
USING (auth.uid() = user_id);

-- Grant permissions for service role (for webhooks and API operations)
GRANT ALL ON user_clips TO service_role;

-- Grant permissions for authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON user_clips TO authenticated;

-- Remove social media post ID columns from parliament_member_clips
-- These columns were added in the previous migration, now moving to user_clips
ALTER TABLE parliament_member_clips 
DROP COLUMN IF EXISTS facebook_post_id,
DROP COLUMN IF EXISTS twitter_post_id,
DROP COLUMN IF EXISTS tiktok_post_id,
DROP COLUMN IF EXISTS instagram_post_id;

-- Drop the indexes for social media post IDs from parliament_member_clips
DROP INDEX IF EXISTS idx_parliament_member_clips_facebook_post_id;
DROP INDEX IF EXISTS idx_parliament_member_clips_twitter_post_id;
DROP INDEX IF EXISTS idx_parliament_member_clips_tiktok_post_id;
DROP INDEX IF EXISTS idx_parliament_member_clips_instagram_post_id;

-- Create function to call the create-user-clip webhook endpoint
CREATE OR REPLACE FUNCTION notify_user_clip_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    user_clip_id uuid;
    response_status int;
BEGIN
    -- Get the user clip ID from the trigger context
    user_clip_id := NEW.id;
    
    -- Get environment variables from vault
    -- These should be set in your Supabase project settings under "Vault"
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Fallback if vault is not used - replace with your actual URL
    IF app_url IS NULL THEN
        app_url := 'https://your-app.vercel.app'; -- Replace with your actual app URL
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'your-secret-cron-key'; -- Replace with your actual secret
    END IF;
    
    -- Log start of webhook call
    RAISE LOG 'Calling user clip webhook for user clip ID: %', user_clip_id;
    
    -- Make HTTP POST request to the create-user-clip webhook endpoint
    SELECT status INTO response_status
    FROM http((
        'POST',
        app_url || '/api/webhooks/create-user-clip',
        ARRAY[
            http_header('Content-Type', 'application/json'),
            http_header('Authorization', 'Bearer ' || cron_secret)
        ],
        'application/json',
        jsonb_build_object('userClipId', user_clip_id)::text
    )::http_request);
    
    -- Log the result
    RAISE LOG 'User clip webhook completed for clip %. Response status: %', user_clip_id, response_status;
    
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors but don't fail the original insert/update
        RAISE WARNING 'User clip webhook failed for clip %: %', user_clip_id, SQLERRM;
        -- Don't re-raise the exception as we don't want to block the original operation
        RETURN NEW;
END;
$$;

-- Create trigger on user_clips table
-- This will fire after INSERT or UPDATE operations when:
-- 1. A new user clip is created
-- 2. start_timestamp or end_timestamp are updated
CREATE TRIGGER user_clips_webhook_trigger
    AFTER INSERT OR UPDATE OF start_timestamp, end_timestamp ON user_clips
    FOR EACH ROW
    EXECUTE FUNCTION notify_user_clip_webhook();

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION notify_user_clip_webhook TO service_role;

-- Add table and column comments for documentation
COMMENT ON TABLE user_clips IS 
'Stores user-created clips from parliament member clips with their own social media post tracking';

COMMENT ON COLUMN user_clips.user_id IS 
'Reference to auth.users.id - the user who created this clip';

COMMENT ON COLUMN user_clips.clip_id IS 
'Reference to parliament_member_clips.id - the source clip this user clip is based on';

COMMENT ON COLUMN user_clips.start_timestamp IS 
'Start timestamp as text string for the user clip (can be different from source clip)';

COMMENT ON COLUMN user_clips.end_timestamp IS 
'End timestamp as text string for the user clip (can be different from source clip)';

COMMENT ON COLUMN user_clips.clip_url IS 
'Direct URL to the user-specific processed video clip file';

COMMENT ON COLUMN user_clips.full_video_path IS 
'Path to the full video file from which this user clip was extracted';

COMMENT ON COLUMN user_clips.status IS 
'Processing status of the user clip (processing, completed, failed, pending_review)';

COMMENT ON COLUMN user_clips.facebook_post_id IS 
'Facebook post ID when this user clip is shared to Facebook. NULL if not shared.';

COMMENT ON COLUMN user_clips.twitter_post_id IS 
'Twitter/X post ID when this user clip is shared to Twitter. NULL if not shared.';

COMMENT ON COLUMN user_clips.tiktok_post_id IS 
'TikTok post ID when this user clip is shared to TikTok. NULL if not shared.';

COMMENT ON COLUMN user_clips.instagram_post_id IS 
'Instagram post ID when this user clip is shared to Instagram. NULL if not shared.';

COMMENT ON COLUMN user_clips.is_deleted IS 
'Soft deletion flag. FALSE = active clip, TRUE = deleted';

COMMENT ON COLUMN user_clips.deleted_at IS 
'Timestamp when this user clip was marked as deleted. NULL = never deleted';

COMMENT ON FUNCTION notify_user_clip_webhook IS 
'Function to call the /api/webhooks/create-user-clip endpoint with authentication when user clips are created or updated';

COMMENT ON TRIGGER user_clips_webhook_trigger ON user_clips IS 
'Triggers webhook call to /api/webhooks/create-user-clip when user clips are created or when start_timestamp/end_timestamp are updated';

-- Log successful setup
DO $$
BEGIN
    RAISE NOTICE 'User clips table and webhook setup completed:';
    RAISE NOTICE '- Created user_clips table with foreign key references to auth.users and parliament_member_clips';
    RAISE NOTICE '- Added social media post ID columns: facebook_post_id, twitter_post_id, tiktok_post_id, instagram_post_id';
    RAISE NOTICE '- Removed social media post ID columns from parliament_member_clips table';
    RAISE NOTICE '- Created RLS policies for user-specific access control';
    RAISE NOTICE '- notify_user_clip_webhook(): Function to call webhook endpoint with CRON_SECRET';
    RAISE NOTICE '- user_clips_webhook_trigger: Trigger on INSERT and UPDATE of timestamps';
    RAISE NOTICE '- Webhook will call: /api/webhooks/create-user-clip with userClipId and Authorization header';
END $$; 