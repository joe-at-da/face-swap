-- Fix Webhook Trigger Function Syntax
-- This migration fixes the PostgreSQL trigger function syntax errors

-- Replace the broken notify_clip_webhook function with a proper one
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
    -- Get environment variables from vault
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Use localhost for development/testing
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000';
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'development-secret';
    END IF;
    
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

-- Fix the trigger function to properly handle NEW and OLD records
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
        IF OLD.status IS DISTINCT FROM NEW.status AND NEW.status = 'completed'::parliament_clip_status THEN
            PERFORM notify_clip_webhook(NEW.id);
        -- Call webhook if completed clip has key field changes
        ELSIF NEW.status = 'completed'::parliament_clip_status AND (
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

-- Drop and recreate the webhook_debug_logs table if it exists
DROP TABLE IF EXISTS webhook_debug_logs;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed webhook trigger function syntax:';
    RAISE NOTICE '- Separated notify_clip_webhook() to accept clip_id parameter properly';
    RAISE NOTICE '- Fixed handle_clip_webhook() to properly use NEW and OLD records';
    RAISE NOTICE '- Webhook will call for all INSERT operations';
    RAISE NOTICE '- Using development URL: http://host.docker.internal:3000';
    RAISE NOTICE '- Ready to test with /api/test endpoint';
END $$; 