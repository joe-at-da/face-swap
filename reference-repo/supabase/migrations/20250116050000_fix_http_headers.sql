-- Fix HTTP Headers for Webhook Function
-- This migration fixes the HTTP request format to work with the pg_http extension

CREATE OR REPLACE FUNCTION notify_clip_webhook(clip_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status int;
    request_id bigint;
BEGIN
    -- Use localhost for development/testing
    app_url := 'http://host.docker.internal:3000';
    cron_secret := 'development-secret';
    
    -- Log start of webhook call
    RAISE LOG 'Calling clip webhook for clip ID: %. URL: %', clip_id, app_url;
    
    -- Make HTTP POST request using the correct syntax for pg_http
    BEGIN
        SELECT net.http_post(
            url := app_url || '/api/webhooks/create-clip',
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || cron_secret
            ),
            body := jsonb_build_object('clipId', clip_id)
        ) INTO request_id;
        
        RAISE LOG 'Clip webhook initiated for clip %. Request ID: %', clip_id, request_id;
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE WARNING 'Webhook HTTP error for clip %: %', clip_id, SQLERRM;
    END;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Clip webhook failed for clip %: %', clip_id, SQLERRM;
END;
$$;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed HTTP headers for webhook function:';
    RAISE NOTICE '- Updated notify_clip_webhook to use net.http_post';
    RAISE NOTICE '- Fixed header format to use jsonb_build_object';
    RAISE NOTICE '- Using development URL: http://host.docker.internal:3000';
    RAISE NOTICE '- Ready to test webhook system';
END $$; 