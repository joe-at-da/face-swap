-- Make Webhook Fire-and-Forget Migration
-- This migration updates the webhook trigger to use pgmq queue instead of blocking HTTP calls
-- This prevents the trigger from waiting for API responses, making updates much faster

-- Set search_path to ensure functions are created in the public schema
SET LOCAL search_path TO public, pg_temp;

-- Ensure pgmq extension is enabled
CREATE EXTENSION IF NOT EXISTS pgmq;

-- Create webhook queue if it doesn't exist
SELECT pgmq.create('webhook_jobs');

-- Grant necessary permissions
GRANT USAGE ON SCHEMA pgmq TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pgmq TO service_role;

-- Replace notify_clip_webhook to queue the webhook call instead of making it directly
CREATE OR REPLACE FUNCTION public.notify_clip_webhook(clip_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    queue_message jsonb;
BEGIN
    -- Build queue message payload
    queue_message := jsonb_build_object(
        'webhook_type', 'parliament_clip',
        'clip_id', clip_id,
        'created_at', NOW()
    );
    
    -- Send message to the webhook jobs queue (non-blocking)
    PERFORM pgmq.send('webhook_jobs', queue_message);
    
    -- Log that we've queued the webhook
    RAISE LOG 'Queued webhook for clip ID: %', clip_id;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors but don't fail the original insert/update
        RAISE WARNING 'Failed to queue webhook for clip %: %', clip_id, SQLERRM;
        -- Don't re-raise the exception as we don't want to block the original operation
END;
$$;

-- Replace notify_user_clip_webhook to queue the webhook call instead of making it directly
CREATE OR REPLACE FUNCTION public.notify_user_clip_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    queue_message jsonb;
    user_clip_id uuid;
BEGIN
    -- Get the user clip ID from the trigger context
    user_clip_id := NEW.id;
    
    -- Build queue message payload
    queue_message := jsonb_build_object(
        'webhook_type', 'user_clip',
        'user_clip_id', user_clip_id,
        'created_at', NOW()
    );
    
    -- Send message to the webhook jobs queue (non-blocking)
    PERFORM pgmq.send('webhook_jobs', queue_message);
    
    -- Log that we've queued the webhook
    RAISE LOG 'Queued webhook for user clip ID: %', user_clip_id;
    
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors but don't fail the original insert/update
        RAISE WARNING 'Failed to queue webhook for user clip %: %', user_clip_id, SQLERRM;
        -- Don't re-raise the exception as we don't want to block the original operation
        RETURN NEW;
END;
$$;

-- Create function to process the webhook queue
CREATE OR REPLACE FUNCTION public.process_webhook_queue(
    batch_size int DEFAULT 10,
    visibility_timeout int DEFAULT 300  -- 5 minutes
)
RETURNS TABLE (
    processed_count int,
    success_count int,
    failed_count int,
    remaining_in_queue int
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    job_record RECORD;
    app_url text;
    cron_secret text;
    response_status int;
    processed int := 0;
    succeeded int := 0;
    failed int := 0;
    remaining int := 0;
BEGIN
    -- Get environment variables from vault
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Fallback if vault is not used
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000';
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'development-secret';
    END IF;
    
    -- Process messages from the queue
    FOR job_record IN 
        SELECT msg_id, message 
        FROM pgmq.read('webhook_jobs', visibility_timeout, batch_size)
    LOOP
        processed := processed + 1;
        
        BEGIN
            -- Determine webhook type and make appropriate HTTP request
            IF job_record.message->>'webhook_type' = 'parliament_clip' THEN
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
                    jsonb_build_object('clipId', job_record.message->>'clip_id')::text
                )::http_request);
                
                -- Log the result
                RAISE LOG 'Parliament clip webhook completed for clip %. Response status: %', 
                    job_record.message->>'clip_id', response_status;
                    
            ELSIF job_record.message->>'webhook_type' = 'user_clip' THEN
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
                    jsonb_build_object('userClipId', job_record.message->>'user_clip_id')::text
                )::http_request);
                
                -- Log the result
                RAISE LOG 'User clip webhook completed for clip %. Response status: %', 
                    job_record.message->>'user_clip_id', response_status;
            ELSE
                -- Unknown webhook type
                RAISE WARNING 'Unknown webhook type: %', job_record.message->>'webhook_type';
                PERFORM pgmq.delete('webhook_jobs', job_record.msg_id);
                failed := failed + 1;
                CONTINUE;
            END IF;
            
            -- Delete the successfully processed job from queue
            PERFORM pgmq.delete('webhook_jobs', job_record.msg_id);
            succeeded := succeeded + 1;
            
        EXCEPTION
            WHEN OTHERS THEN
                -- Log error but continue processing other jobs
                RAISE WARNING 'Webhook HTTP error: %', SQLERRM;
                
                -- Delete the failed job from queue (or you could implement retry logic here)
                PERFORM pgmq.delete('webhook_jobs', job_record.msg_id);
                failed := failed + 1;
        END;
    END LOOP;
    
    -- Get remaining count in queue
    SELECT COUNT(*) INTO remaining FROM pgmq.q_webhook_jobs;
    
    RETURN QUERY SELECT processed, succeeded, failed, remaining;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.process_webhook_queue TO service_role;

-- Update function comments
COMMENT ON FUNCTION public.notify_clip_webhook(uuid) IS 
'Function to queue webhook calls for parliament clip processing. Uses pgmq queue for fire-and-forget behavior - does not wait for API response.';

COMMENT ON FUNCTION public.notify_user_clip_webhook() IS 
'Function to queue webhook calls for user clip processing. Uses pgmq queue for fire-and-forget behavior - does not wait for API response.';

COMMENT ON FUNCTION public.process_webhook_queue IS 
'Function to process queued webhook jobs. Should be called periodically via cron job or scheduled task.';

-- Set up cron job to process webhook queue every minute
-- Ensure pg_cron extension is enabled
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule the webhook queue processor to run every minute
SELECT cron.schedule(
    'process-webhook-queue',
    '* * * * *', -- Every minute
    $$SELECT public.process_webhook_queue(batch_size := 50, visibility_timeout := 300)$$
);

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated webhook to be fire-and-forget:';
    RAISE NOTICE '- Created webhook_jobs queue using pgmq';
    RAISE NOTICE '- Updated notify_clip_webhook() to queue calls instead of blocking';
    RAISE NOTICE '- Updated notify_user_clip_webhook() to queue calls instead of blocking';
    RAISE NOTICE '- Created process_webhook_queue() function to process queued webhooks';
    RAISE NOTICE '- Set up cron job to process webhook queue every minute';
    RAISE NOTICE '- Webhook calls are now non-blocking and will not slow down database updates';
END $$;

