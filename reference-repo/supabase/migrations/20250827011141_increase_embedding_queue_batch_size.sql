-- Increase embedding queue batch size to process more messages per run
-- This improves throughput for bulk RunPod insertions (300-700 clips)

-- Update the process_embedding_queue function with larger default batch size
CREATE OR REPLACE FUNCTION public.process_embedding_queue(
    batch_size int DEFAULT 100,  -- Increased from 10 to 100
    visibility_timeout int DEFAULT 300  -- Keep at 5 minutes
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
    request_body text;
    clip_id_param text;
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
        cron_secret := 'your-secret-cron-key';
    END IF;
    
    -- Process messages from the queue
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
            
            -- Make HTTP POST request to embedding endpoint
            PERFORM http((
                'POST',
                app_url || '/api/embeddings/transcript',
                ARRAY[
                    http_header('Content-Type', 'application/json'),
                    http_header('Authorization', 'Bearer ' || cron_secret)
                ],
                'application/json',
                request_body
            )::http_request);
            
            -- If we get here, the request was sent successfully
            UPDATE transcript_embedding_logs 
            SET status = 'success',
                response_status = 200,
                notes = 'Processed successfully from PGMQ queue'
            WHERE clip_id = (job_record.message->>'clip_id')::uuid
            AND status = 'queued';
            
            -- Delete the processed job from queue
            PERFORM pgmq.delete('embedding_jobs', job_record.msg_id);
            succeeded := succeeded + 1;
            
            -- Small delay between requests to avoid overwhelming the API
            PERFORM pg_sleep(0.1);
            
        EXCEPTION
            WHEN OTHERS THEN
                -- Update log with failure status
                UPDATE transcript_embedding_logs 
                SET status = 'failed',
                    error_message = SQLERRM,
                    notes = 'Failed during PGMQ queue processing'
                WHERE clip_id = (job_record.message->>'clip_id')::uuid
                AND status = 'queued';
                
                -- Don't delete the job - let it retry via visibility timeout
                failed := failed + 1;
        END;
    END LOOP;
    
    -- Get remaining queue count
    SELECT queue_length INTO remaining
    FROM pgmq.metrics('embedding_jobs');
    
    RETURN QUERY SELECT processed, succeeded, failed, COALESCE(remaining, 0);
END;
$$;

-- Update the cron job to use larger batch size (keeping same schedule)
SELECT cron.unschedule('process-embedding-queue');
SELECT cron.schedule(
    'process-embedding-queue',
    '*/30 * * * * *',  -- Every 30 seconds
    'SELECT process_embedding_queue(100, 300);'  -- Updated to use 100 batch size
);

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated embedding queue processing:';
    RAISE NOTICE '- Increased default batch_size from 10 to 100';
    RAISE NOTICE '- Kept visibility_timeout at 300 seconds (5 minutes)';
    RAISE NOTICE '- Updated cron job to use new batch size';
    RAISE NOTICE '- System can now process up to 100 messages per 30-second cycle';
    RAISE NOTICE '- Better throughput for RunPod bulk insertions (300-700 clips)';
END;
$$;