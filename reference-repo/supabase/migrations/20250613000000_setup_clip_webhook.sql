-- Setup Database Webhook for Parliament Member Clips
-- Migration to create a webhook that calls /api/webhooks/create-clip
-- every time a new clip row is added or updated in parliament_member_clips table
-- with CRON_SECRET authentication
-- Also adds social media post ID columns to parliament_member_clips table

-- Add social media post ID columns to parliament_member_clips table
ALTER TABLE parliament_member_clips 
ADD COLUMN facebook_post_id TEXT DEFAULT NULL,
ADD COLUMN twitter_post_id TEXT DEFAULT NULL,
ADD COLUMN tiktok_post_id TEXT DEFAULT NULL,
ADD COLUMN instagram_post_id TEXT DEFAULT NULL;

-- Add indexes for social media post IDs for better query performance
CREATE INDEX idx_parliament_member_clips_facebook_post_id ON parliament_member_clips(facebook_post_id) WHERE facebook_post_id IS NOT NULL;
CREATE INDEX idx_parliament_member_clips_twitter_post_id ON parliament_member_clips(twitter_post_id) WHERE twitter_post_id IS NOT NULL;
CREATE INDEX idx_parliament_member_clips_tiktok_post_id ON parliament_member_clips(tiktok_post_id) WHERE tiktok_post_id IS NOT NULL;
CREATE INDEX idx_parliament_member_clips_instagram_post_id ON parliament_member_clips(instagram_post_id) WHERE instagram_post_id IS NOT NULL;

-- Add comments to document the new columns
COMMENT ON COLUMN parliament_member_clips.facebook_post_id IS 
'Facebook post ID when this clip is shared to Facebook. NULL if not shared.';

COMMENT ON COLUMN parliament_member_clips.twitter_post_id IS 
'Twitter/X post ID when this clip is shared to Twitter. NULL if not shared.';

COMMENT ON COLUMN parliament_member_clips.tiktok_post_id IS 
'TikTok post ID when this clip is shared to TikTok. NULL if not shared.';

COMMENT ON COLUMN parliament_member_clips.instagram_post_id IS 
'Instagram post ID when this clip is shared to Instagram. NULL if not shared.';

-- Create function to call the create-clip webhook endpoint
CREATE OR REPLACE FUNCTION notify_clip_webhook()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    clip_id uuid;
    response_status int;
BEGIN
    -- Get the clip ID from the trigger context (NEW record)
    clip_id := NEW.id;
    
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
    RAISE LOG 'Calling clip webhook for clip ID: %', clip_id;
    
    -- Make HTTP POST request to the create-clip webhook endpoint
    SELECT status INTO response_status
    FROM http((
        'POST',
        app_url || '/api/webhooks/create-clip',
        ARRAY[
            http_header('Content-Type', 'application/json'),
            http_header('Authorization', 'Bearer ' || cron_secret)
        ],
        'application/json',
        jsonb_build_object('clipId', clip_id)::text
    )::http_request);
    
    -- Log the result
    RAISE LOG 'Clip webhook completed for clip %. Response status: %', clip_id, response_status;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors but don't fail the original insert/update
        RAISE WARNING 'Clip webhook failed for clip %: %', clip_id, SQLERRM;
        -- Don't re-raise the exception as we don't want to block the original operation
END;
$$;

-- Create the trigger function that will be called by the database trigger
CREATE OR REPLACE FUNCTION handle_clip_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- For INSERT operations: only call webhook for completed clips
    IF TG_OP = 'INSERT' THEN
        IF NEW.status = 'completed'::parliament_clip_status THEN
            PERFORM notify_clip_webhook();
        END IF;
    -- For UPDATE operations: call webhook if status becomes completed OR if key fields changed on completed clips
    ELSIF TG_OP = 'UPDATE' THEN
        -- Check if status changed to completed
        IF NEW.status = 'completed'::parliament_clip_status AND OLD.status != 'completed'::parliament_clip_status THEN
            PERFORM notify_clip_webhook();
        -- Check if key fields changed on already completed clips
        ELSIF NEW.status = 'completed'::parliament_clip_status AND OLD.status = 'completed'::parliament_clip_status THEN
            -- Check if start_timestamp, end_timestamp, or transcript changed
            IF (OLD.start_timestamp IS DISTINCT FROM NEW.start_timestamp) OR
               (OLD.end_timestamp IS DISTINCT FROM NEW.end_timestamp) OR
               (OLD.transcript IS DISTINCT FROM NEW.transcript) THEN
                PERFORM notify_clip_webhook();
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create the trigger on parliament_member_clips table
-- This will fire after INSERT or UPDATE operations
CREATE TRIGGER parliament_member_clips_webhook_trigger
    AFTER INSERT OR UPDATE ON parliament_member_clips
    FOR EACH ROW
    EXECUTE FUNCTION handle_clip_webhook();

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION notify_clip_webhook() TO service_role;
GRANT EXECUTE ON FUNCTION handle_clip_webhook() TO service_role;

-- Add comments to document the webhook setup
COMMENT ON FUNCTION notify_clip_webhook() IS 
'Function to call the /api/webhooks/create-clip endpoint with authentication when clips are processed';

COMMENT ON FUNCTION handle_clip_webhook() IS 
'Trigger function that calls webhook for: new completed clips, status changes to completed, or when start_timestamp/end_timestamp/transcript change on completed clips';

COMMENT ON TRIGGER parliament_member_clips_webhook_trigger ON parliament_member_clips IS 
'Triggers webhook call to /api/webhooks/create-clip when clips are added or updated with completed status';

-- Log successful setup
DO $$
BEGIN
    RAISE NOTICE 'Parliament member clips webhook setup completed:';
    RAISE NOTICE '- Added social media post ID columns: facebook_post_id, twitter_post_id, tiktok_post_id, instagram_post_id';
    RAISE NOTICE '- notify_clip_webhook(): Function to call webhook endpoint with CRON_SECRET';
    RAISE NOTICE '- handle_clip_webhook(): Trigger function that filters for completed clips';
    RAISE NOTICE '- parliament_member_clips_webhook_trigger: Trigger on INSERT/UPDATE operations';
    RAISE NOTICE '- Webhook will call: /api/webhooks/create-clip with clipId and Authorization header';
END $$; 