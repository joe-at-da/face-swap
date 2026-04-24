-- Fix timeout issues with embedding queue processing
-- Increase statement timeout and optimize the function

-- Update the process_embedding_queue function with better timeout handling
CREATE OR REPLACE FUNCTION public.process_embedding_queue(
    batch_size int DEFAULT 100,
    visibility_timeout int DEFAULT 300
)
RETURNS TABLE (
    processed_count int,
    success_count int,
    failed_count int,
    remaining_in_queue int
)
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '10min'  -- Increase timeout to 10 minutes
AS $$
DECLARE
    job_record RECORD;
    app_url text;
    cron_secret text;
    request_body text;
    clip_id_param text;
    processed int := 0;
    succeeded int := 0;
    failed int := 0;
    remaining int := 0;
    http_response http_response;
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
        cron_secret := 'your-secret-cron-key';
    END IF;
    
    -- Process messages from the queue with smaller batches for HTTP calls
    FOR job_record IN 
        SELECT msg_id, message 
        FROM pgmq.read('embedding_jobs', visibility_timeout, batch_size)
    LOOP
        processed := processed + 1;
        
        BEGIN
            -- Determine the correct parameter based on table
            IF job_record.message->>'table_name' = 'parliament_member_clips' THEN
                clip_id_param := 'parliament_clip_id';
            ELSIF job_record.message->>'table_name' = 'user_clips' THEN
                clip_id_param := 'user_clip_id';
            ELSE
                -- Log error and mark as failed
                UPDATE transcript_embedding_logs 
                SET status = 'failed',
                    error_message = 'Unknown table name: ' || (job_record.message->>'table_name'),
                    notes = 'Processed from PGMQ queue'
                WHERE clip_id = (job_record.message->>'clip_id')::uuid
                AND status = 'queued';
                
                -- Delete the invalid job from queue
                PERFORM pgmq.delete('embedding_jobs', job_record.msg_id);
                failed := failed + 1;
                CONTINUE;
            END IF;
            
            -- Build request body
            request_body := json_build_object(
                clip_id_param, 
                job_record.message->>'clip_id'
            )::text;
            
            -- Make HTTP POST request with timeout
            SELECT * INTO http_response FROM http((
                'POST',
                app_url || '/api/embeddings/transcript',
                ARRAY[
                    http_header('Authorization', 'Bearer ' || cron_secret)
                ],
                'application/json',
                request_body,
                5000  -- 5 second timeout per request
            )::http_request);
            
            -- Check response status
            IF http_response.status = 200 THEN
                -- Success
                UPDATE transcript_embedding_logs 
                SET status = 'success',
                    response_status = 200,
                    notes = 'Processed successfully from PGMQ queue'
                WHERE clip_id = (job_record.message->>'clip_id')::uuid
                AND status = 'queued';
                
                -- Delete the processed job from queue
                PERFORM pgmq.delete('embedding_jobs', job_record.msg_id);
                succeeded := succeeded + 1;
            ELSE
                -- HTTP error
                UPDATE transcript_embedding_logs 
                SET status = 'failed',
                    response_status = http_response.status,
                    error_message = 'HTTP ' || http_response.status,
                    notes = 'Failed with HTTP error from PGMQ queue'
                WHERE clip_id = (job_record.message->>'clip_id')::uuid
                AND status = 'queued';
                
                -- Delete failed job (don't retry HTTP errors)
                PERFORM pgmq.delete('embedding_jobs', job_record.msg_id);
                failed := failed + 1;
            END IF;
            
            -- Small delay between requests
            PERFORM pg_sleep(0.05); -- 50ms delay
            
        EXCEPTION
            WHEN OTHERS THEN
                -- Update log with failure status
                UPDATE transcript_embedding_logs 
                SET status = 'failed',
                    error_message = SQLERRM,
                    notes = 'Failed during PGMQ queue processing'
                WHERE clip_id = (job_record.message->>'clip_id')::uuid
                AND status = 'queued';
                
                -- Delete the job if it's a timeout or connection error
                IF SQLERRM LIKE '%timeout%' OR SQLERRM LIKE '%connection%' THEN
                    PERFORM pgmq.delete('embedding_jobs', job_record.msg_id);
                END IF;
                
                failed := failed + 1;
        END;
        
        -- Exit early if we've processed enough to avoid overall timeout
        IF processed >= 20 THEN
            EXIT;
        END IF;
    END LOOP;
    
    -- Get remaining queue count
    SELECT queue_length INTO remaining
    FROM pgmq.metrics('embedding_jobs');
    
    RETURN QUERY SELECT processed, succeeded, failed, COALESCE(remaining, 0);
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.process_embedding_queue(int, int) TO service_role;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Optimized embedding queue processing:';
    RAISE NOTICE '- Added statement_timeout of 10 minutes';
    RAISE NOTICE '- Added 5 second timeout per HTTP request';
    RAISE NOTICE '- Limited to 20 items per execution to avoid timeouts';
    RAISE NOTICE '- Improved error handling for HTTP responses';
    RAISE NOTICE '- Delete failed jobs to prevent retry loops';
END;
$$;