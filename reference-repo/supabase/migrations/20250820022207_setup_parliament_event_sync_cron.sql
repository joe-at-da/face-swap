-- Create a function to call the Parliament event sync endpoint
CREATE OR REPLACE FUNCTION call_parliament_event_sync_endpoint()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status int;
BEGIN
    -- Get environment variables from vault (preferred approach)
    -- These should be set in your Supabase project settings under "Vault"
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Fallback if vault is not used - replace with your actual URL
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000'; -- Replace with your actual app URL
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'your-secret-cron-key'; -- Replace with your actual secret
    END IF;
    
    -- Log start of function execution
    RAISE LOG 'Starting Parliament event sync. App URL: %', app_url;
    
    -- Make HTTP POST request to the event sync endpoint (fire and forget)
    -- We don't wait for the response since sync can take a long time
    BEGIN
        PERFORM http((
            'POST',
            app_url || '/api/cron/parliament-event-sync',
            ARRAY[
                http_header('Content-Type', 'application/json'),
                http_header('Authorization', 'Bearer ' || cron_secret)
            ],
            'application/json',
            '{}'
        )::http_request);
        
        -- If we get here, the request was sent successfully
        response_status := 200; -- Assume success since request was sent
        
    EXCEPTION
        WHEN OTHERS THEN
            -- If there's an error sending the request, log it but continue
            RAISE LOG 'Failed to send HTTP request: %', SQLERRM;
            response_status := 0; -- Indicate request failed to send
    END;
    
    -- Log that we triggered the sync (not that it completed)
    INSERT INTO parliament_sync_logs (
        sync_type,
        status,
        response_status,
        executed_at,
        notes
    ) VALUES (
        'cron_trigger'::parliament_sync_type,
        CASE 
            WHEN response_status = 200 THEN 'running'::parliament_sync_status_enum
            ELSE 'failed'::parliament_sync_status_enum
        END,
        response_status,
        NOW(),
        'Parliament event sync triggered via pg_cron (async, not waiting for completion)'
    );
    
    -- Log completion of trigger (not the actual sync)
    RAISE LOG 'Parliament event sync trigger completed. Request sent status: %', response_status;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors with more detail
        INSERT INTO parliament_sync_logs (
            sync_type,
            status,
            response_status,
            executed_at,
            notes,
            error_message
        ) VALUES (
            'cron_trigger'::parliament_sync_type,
            'failed'::parliament_sync_status_enum,
            NULL,
            NOW(),
            'Parliament event sync trigger failed via pg_cron',
            SQLERRM
        );
        
        RAISE LOG 'Parliament event sync trigger failed with error: %', SQLERRM;
        -- Don't re-raise to avoid failing the cron job
        -- RAISE;
END;
$$;

-- Schedule the cron job to run daily at 3:30 AM UTC
-- This will call the Parliament event sync endpoint every day
SELECT cron.schedule(
    'parliament-event-daily-sync',           -- job name
    '30 3 * * *',                           -- cron expression (daily at 3:30 AM UTC)
    'SELECT call_parliament_event_sync_endpoint();'  -- SQL to execute
);

-- Function to manually trigger event sync (for testing)
CREATE OR REPLACE FUNCTION trigger_parliament_event_sync_manually()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    PERFORM call_parliament_event_sync_endpoint();
    RETURN 'Parliament event sync triggered manually. Check parliament_sync_logs for results.';
END;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION call_parliament_event_sync_endpoint() TO service_role;
GRANT EXECUTE ON FUNCTION trigger_parliament_event_sync_manually() TO service_role;

-- Update the existing function to show both parliament sync jobs
CREATE OR REPLACE FUNCTION get_parliament_cron_jobs()
RETURNS TABLE (
    job_id bigint,
    job_name text,
    schedule text,
    command text,
    active boolean
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        jobid,
        jobname::text,
        schedule::text,
        command::text,
        active
    FROM cron.job 
    WHERE jobname LIKE 'parliament-%'
    ORDER BY jobname;
$$;
