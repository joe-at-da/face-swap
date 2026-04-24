-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Enable http extension for making HTTP requests
CREATE EXTENSION IF NOT EXISTS http;

-- Grant necessary permissions to run cron jobs
GRANT USAGE ON SCHEMA cron TO postgres;

-- Create a function to call the Parliament sync endpoint
CREATE OR REPLACE FUNCTION call_parliament_sync_endpoint()
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
    RAISE LOG 'Starting Parliament sync. App URL: %', app_url;
    
    -- Make HTTP POST request to the sync endpoint (fire and forget)
    -- We don't wait for the response since sync can take a long time
    BEGIN
        PERFORM http((
            'POST',
            app_url || '/api/cron/parliament-sync',
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
        'Triggered via pg_cron (async, not waiting for completion)'
    );
    
    -- Log completion of trigger (not the actual sync)
    RAISE LOG 'Parliament sync trigger completed. Request sent status: %', response_status;
    
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
            'Triggered via pg_cron',
            SQLERRM
        );
        
        RAISE LOG 'Parliament sync trigger failed with error: %', SQLERRM;
        -- Don't re-raise to avoid failing the cron job
        -- RAISE;
END;
$$;

-- Create a simple logging table for cron executions
CREATE TABLE IF NOT EXISTS parliament_sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type parliament_sync_type NOT NULL,
    status parliament_sync_status_enum NOT NULL,
    response_status INTEGER,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    error_message TEXT
);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_parliament_sync_logs_executed_at 
ON parliament_sync_logs(executed_at DESC);

-- Schedule the cron job to run daily at 2 AM UTC
-- This will call the Parliament sync endpoint every day
SELECT cron.schedule(
    'parliament-daily-sync',           -- job name
    '0 2 * * *',                      -- cron expression (daily at 2 AM UTC)
    'SELECT call_parliament_sync_endpoint();'  -- SQL to execute
);

-- -- Optional: Schedule a daily voting history sync (limited)
-- SELECT cron.schedule(
--     'parliament-daily-voting-sync',    -- job name
--     '0 3 * * *',                      -- cron expression (daily at 3 AM UTC)
--     'SELECT call_parliament_sync_endpoint_with_voting();'  -- SQL to execute
-- );

-- Create function for daily voting history sync
CREATE OR REPLACE FUNCTION call_parliament_sync_endpoint_with_voting()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status int;
BEGIN
    -- Get environment variables using best practice vault approach
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Fallback values
    IF app_url IS NULL THEN
        app_url := 'https://your-app.vercel.app'; -- Replace with your actual app URL
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'your-secret-cron-key'; -- Replace with your actual secret
    END IF;
    
    -- Log start of function execution
    RAISE LOG 'Starting Parliament voting history sync (limited to 50 members)';
    
    -- Make HTTP POST request for voting history sync (fire and forget)
    -- We don't wait for the response since sync can take a long time
    BEGIN
        PERFORM http((
            'POST',
            app_url || '/api/cron/parliament-sync?type=voting-history&limit=50',
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
        'voting_history'::parliament_sync_type,
        CASE 
            WHEN response_status = 200 THEN 'running'::parliament_sync_status_enum
            ELSE 'failed'::parliament_sync_status_enum
        END,
        response_status,
        NOW(),
        'Daily voting history sync via pg_cron (async, limited to 50 members)'
    );
    
    -- Log completion of trigger (not the actual sync)
    RAISE LOG 'Parliament daily voting history sync trigger completed. Request sent status: %', response_status;
    
EXCEPTION
    WHEN OTHERS THEN
        INSERT INTO parliament_sync_logs (
            sync_type,
            status,
            response_status,
            executed_at,
            notes,
            error_message
        ) VALUES (
            'voting_history'::parliament_sync_type,
            'failed'::parliament_sync_status_enum,
            NULL,
            NOW(),
            'Daily voting history sync via pg_cron',
            SQLERRM
        );
        
        RAISE LOG 'Parliament daily voting history sync trigger failed with error: %', SQLERRM;
        -- Don't re-raise to avoid failing the cron job
        -- RAISE;
END;
$$;

-- Enable Row Level Security on the logs table
ALTER TABLE parliament_sync_logs ENABLE ROW LEVEL SECURITY;

-- Create policy for authenticated users to view logs
CREATE POLICY "Parliament sync logs are viewable by authenticated users" 
ON parliament_sync_logs
FOR SELECT 
USING (auth.role() = 'authenticated');

-- Grant permissions for service role
GRANT ALL ON parliament_sync_logs TO service_role;

-- Function to view current cron jobs
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

-- Function to manually trigger sync (for testing)
CREATE OR REPLACE FUNCTION trigger_parliament_sync_manually()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    PERFORM call_parliament_sync_endpoint();
    RETURN 'Parliament sync triggered manually. Check parliament_sync_logs for results.';
END;
$$; 