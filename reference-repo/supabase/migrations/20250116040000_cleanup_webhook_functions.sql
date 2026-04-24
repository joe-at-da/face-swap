-- Cleanup and Fix Webhook Functions Migration
-- This migration drops all existing webhook functions and recreates them correctly

-- Drop the trigger first (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parliament_member_clips') THEN
        DROP TRIGGER IF EXISTS parliament_member_clips_webhook_trigger ON parliament_member_clips;
    END IF;
END $$;

-- Now drop all existing webhook functions
DROP FUNCTION IF EXISTS notify_clip_webhook();
DROP FUNCTION IF EXISTS notify_clip_webhook(uuid);
DROP FUNCTION IF EXISTS handle_clip_webhook();

-- Create the clean notify_clip_webhook function that takes clip_id as parameter
CREATE OR REPLACE FUNCTION notify_clip_webhook(clip_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status int;
BEGIN
    -- Use localhost for development/testing
    app_url := 'http://host.docker.internal:3000';
    cron_secret := 'development-secret';
    
    -- Log start of webhook call
    RAISE LOG 'Calling clip webhook for clip ID: %. URL: %', clip_id, app_url;
    
    -- Make HTTP POST request to the create-clip webhook endpoint
    BEGIN
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
        
        RAISE LOG 'Clip webhook completed for clip %. Response status: %', clip_id, response_status;
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE WARNING 'Webhook HTTP error for clip %: %', clip_id, SQLERRM;
    END;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Clip webhook failed for clip %: %', clip_id, SQLERRM;
END;
$$;

-- Create the clean trigger function
CREATE OR REPLACE FUNCTION handle_clip_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- For INSERT operations: call webhook for ALL new clips (regardless of status)
    IF TG_OP = 'INSERT' THEN
        PERFORM notify_clip_webhook(NEW.id);
        RETURN NEW;
    END IF;
    
    -- For UPDATE operations: call webhook if status becomes completed OR if key fields changed on completed clips
    IF TG_OP = 'UPDATE' THEN
        -- Call webhook if status changed to completed
        IF OLD.status IS DISTINCT FROM NEW.status AND NEW.status::text = 'completed' THEN
            PERFORM notify_clip_webhook(NEW.id);
        -- Call webhook if completed clip has key field changes
        ELSIF NEW.status::text = 'completed' AND (
            OLD.clip_url IS DISTINCT FROM NEW.clip_url OR
            OLD.start_timestamp IS DISTINCT FROM NEW.start_timestamp OR
            OLD.end_timestamp IS DISTINCT FROM NEW.end_timestamp
        ) THEN
            PERFORM notify_clip_webhook(NEW.id);
        END IF;
        RETURN NEW;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Recreate the trigger (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parliament_member_clips') THEN
        CREATE TRIGGER parliament_member_clips_webhook_trigger
            AFTER INSERT OR UPDATE ON parliament_member_clips
            FOR EACH ROW
            EXECUTE FUNCTION handle_clip_webhook();
    END IF;
END $$;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Cleaned up webhook functions:';
    RAISE NOTICE '- Dropped trigger and all existing webhook functions';
    RAISE NOTICE '- Created clean notify_clip_webhook(uuid) function';
    RAISE NOTICE '- Created clean handle_clip_webhook() trigger function';
    RAISE NOTICE '- Recreated trigger parliament_member_clips_webhook_trigger';
    RAISE NOTICE '- Ready to test webhook system';
END $$; 