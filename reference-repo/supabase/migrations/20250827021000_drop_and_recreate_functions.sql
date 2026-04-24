-- Drop and recreate functions with proper timeout settings

-- Drop existing functions first
DROP FUNCTION IF EXISTS public.call_parliament_sync_endpoint();
DROP FUNCTION IF EXISTS public.call_parliament_event_sync_endpoint();

-- Recreate parliament sync function with timeout
CREATE FUNCTION public.call_parliament_sync_endpoint()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '10min'
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response jsonb;
BEGIN
    SELECT decrypted_secret INTO app_url FROM vault.decrypted_secrets WHERE name = 'project_url';
    SELECT decrypted_secret INTO cron_secret FROM vault.decrypted_secrets WHERE name = 'cron_secret';
    
    IF app_url IS NULL THEN app_url := 'http://host.docker.internal:3000'; END IF;
    IF cron_secret IS NULL THEN cron_secret := 'your-secret-cron-key'; END IF;
    
    BEGIN
        SELECT content::jsonb INTO response
        FROM http((
            'POST',
            app_url || '/api/cron/parliament-sync',
            ARRAY[http_header('Authorization', 'Bearer ' || cron_secret)],
            'application/json',
            '{}'
        )::http_request);
        RETURN response;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'timestamp', NOW());
    END;
END;
$$;

-- Recreate parliament event sync function with timeout
CREATE FUNCTION public.call_parliament_event_sync_endpoint()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '10min'
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response jsonb;
BEGIN
    SELECT decrypted_secret INTO app_url FROM vault.decrypted_secrets WHERE name = 'project_url';
    SELECT decrypted_secret INTO cron_secret FROM vault.decrypted_secrets WHERE name = 'cron_secret';
    
    IF app_url IS NULL THEN app_url := 'http://host.docker.internal:3000'; END IF;
    IF cron_secret IS NULL THEN cron_secret := 'your-secret-cron-key'; END IF;
    
    BEGIN
        SELECT content::jsonb INTO response
        FROM http((
            'POST',
            app_url || '/api/cron/parliament-sync',
            ARRAY[http_header('Authorization', 'Bearer ' || cron_secret)],
            'application/json',
            json_build_object('event_sync', true)::text
        )::http_request);
        RETURN response;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'timestamp', NOW());
    END;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.call_parliament_sync_endpoint() TO service_role;
GRANT EXECUTE ON FUNCTION public.call_parliament_event_sync_endpoint() TO service_role;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Recreated parliament sync functions with timeouts:';
    RAISE NOTICE '- Dropped old functions';
    RAISE NOTICE '- Created new functions with 10 minute timeout';
    RAISE NOTICE '- Added error handling';
END;
$$;