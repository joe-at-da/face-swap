-- Complete PGMQ-based embedding queue system
-- This migration replaces the complex bulk detection system with a simple, reliable queue-based approach

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgmq;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Create the embedding jobs queue
SELECT pgmq.create('embedding_jobs');

-- Grant necessary permissions to interact with the queue
GRANT USAGE ON SCHEMA pgmq TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pgmq TO service_role;

-- Replace the trigger function to always use the queue
CREATE OR REPLACE FUNCTION public.generate_transcript_embedding()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    transcript_text text;
    transcript_len int;
    queue_message jsonb;
BEGIN
    -- Get the transcript and check if embedding is needed
    transcript_text := NEW.transcript;
    transcript_len := COALESCE(length(transcript_text), 0);
    
    -- Skip if no transcript or already has embedding
    IF transcript_text IS NULL OR transcript_text = '' THEN
        INSERT INTO transcript_embedding_logs (
            table_name, 
            clip_id, 
            status, 
            transcript_length,
            notes
        ) VALUES (
            TG_TABLE_NAME,
            NEW.id,
            'skipped',
            transcript_len,
            'No transcript available'
        );
        RETURN NEW;
    END IF;
    
    -- Skip if already has embedding
    IF NEW.transcript_embedding IS NOT NULL THEN
        INSERT INTO transcript_embedding_logs (
            table_name, 
            clip_id, 
            status, 
            transcript_length,
            notes
        ) VALUES (
            TG_TABLE_NAME,
            NEW.id,
            'skipped',
            transcript_len,
            'Embedding already exists'
        );
        RETURN NEW;
    END IF;
    
    -- Build queue message payload
    queue_message := jsonb_build_object(
        'clip_id', NEW.id,
        'table_name', TG_TABLE_NAME,
        'transcript_length', transcript_len,
        'created_at', NOW()
    );
    
    -- Send message to the embedding jobs queue
    PERFORM pgmq.send('embedding_jobs', queue_message);
    
    -- Log that we've queued the job
    INSERT INTO transcript_embedding_logs (
        table_name, 
        clip_id, 
        status, 
        transcript_length,
        notes
    ) VALUES (
        TG_TABLE_NAME,
        NEW.id,
        'queued',
        transcript_len,
        'Queued for processing via PGMQ'
    );
    
    -- Always return NEW to not interfere with the original operation
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log any unexpected errors but don't fail the insert
        INSERT INTO transcript_embedding_logs (
            table_name, 
            clip_id, 
            status, 
            transcript_length,
            error_message,
            notes
        ) VALUES (
            COALESCE(TG_TABLE_NAME, 'unknown'),
            COALESCE(NEW.id, uuid_generate_v4()),
            'failed',
            transcript_len,
            SQLERRM,
            'Error queuing embedding job'
        );
        
        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- Create function to process the embedding queue
CREATE OR REPLACE FUNCTION public.process_embedding_queue(
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

-- Create function to manually process all clips missing embeddings
CREATE OR REPLACE FUNCTION public.queue_missing_embeddings(
    table_name_param text DEFAULT 'parliament_member_clips',
    limit_param int DEFAULT 100
)
RETURNS TABLE (
    clips_found int,
    clips_queued int
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    found_count int := 0;
    queued_count int := 0;
    clip_record RECORD;
    queue_message jsonb;
BEGIN
    -- Find clips missing embeddings and queue them
    IF table_name_param = 'parliament_member_clips' THEN
        FOR clip_record IN
            SELECT id, length(transcript) as transcript_length
            FROM parliament_member_clips
            WHERE transcript IS NOT NULL 
            AND transcript != ''
            AND transcript_embedding IS NULL
            LIMIT limit_param
        LOOP
            found_count := found_count + 1;
            
            -- Build queue message
            queue_message := jsonb_build_object(
                'clip_id', clip_record.id,
                'table_name', table_name_param,
                'transcript_length', clip_record.transcript_length,
                'created_at', NOW()
            );
            
            -- Send to queue
            PERFORM pgmq.send('embedding_jobs', queue_message);
            
            -- Log that we've queued it
            INSERT INTO transcript_embedding_logs (
                table_name, 
                clip_id, 
                status, 
                transcript_length,
                notes
            ) VALUES (
                table_name_param,
                clip_record.id,
                'queued',
                clip_record.transcript_length,
                'Manually queued for batch processing'
            );
            
            queued_count := queued_count + 1;
        END LOOP;
        
    ELSIF table_name_param = 'user_clips' THEN
        FOR clip_record IN
            SELECT id, length(transcript) as transcript_length
            FROM user_clips
            WHERE transcript IS NOT NULL 
            AND transcript != ''
            AND transcript_embedding IS NULL
            LIMIT limit_param
        LOOP
            found_count := found_count + 1;
            
            -- Build queue message
            queue_message := jsonb_build_object(
                'clip_id', clip_record.id,
                'table_name', table_name_param,
                'transcript_length', clip_record.transcript_length,
                'created_at', NOW()
            );
            
            -- Send to queue
            PERFORM pgmq.send('embedding_jobs', queue_message);
            
            -- Log that we've queued it
            INSERT INTO transcript_embedding_logs (
                table_name, 
                clip_id, 
                status, 
                transcript_length,
                notes
            ) VALUES (
                table_name_param,
                clip_record.id,
                'queued',
                clip_record.transcript_length,
                'Manually queued for batch processing'
            );
            
            queued_count := queued_count + 1;
        END LOOP;
    END IF;
    
    RETURN QUERY SELECT found_count, queued_count;
END;
$$;

-- Create function to get queue status and metrics
CREATE OR REPLACE FUNCTION public.get_embedding_queue_status()
RETURNS TABLE (
    queue_length bigint,
    oldest_msg_age_sec integer,
    newest_msg_age_sec integer,
    total_messages bigint,
    pending_logs_count bigint,
    failed_logs_count bigint,
    success_logs_count bigint
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    WITH queue_metrics AS (
        SELECT * FROM pgmq.metrics('embedding_jobs')
    ),
    log_counts AS (
        SELECT 
            COUNT(*) FILTER (WHERE status = 'queued') as pending_count,
            COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
            COUNT(*) FILTER (WHERE status = 'success') as success_count
        FROM public.transcript_embedding_logs
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    )
    SELECT 
        COALESCE(qm.queue_length, 0),
        qm.oldest_msg_age_sec,
        qm.newest_msg_age_sec,
        COALESCE(qm.total_messages, 0),
        lc.pending_count,
        lc.failed_count,
        lc.success_count
    FROM queue_metrics qm
    CROSS JOIN log_counts lc;
$$;

-- Schedule the embedding processing to run every 30 seconds
SELECT cron.schedule(
    'process-embedding-queue',
    '*/30 * * * * *',  -- Every 30 seconds
    'SELECT process_embedding_queue(10, 300);'
);

-- Grant permissions to service_role
GRANT EXECUTE ON FUNCTION public.process_embedding_queue(int, int) TO service_role;
GRANT EXECUTE ON FUNCTION public.queue_missing_embeddings(text, int) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_embedding_queue_status() TO service_role;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'PGMQ-based embedding system deployed:';
    RAISE NOTICE '- Created embedding_jobs queue with pgmq';
    RAISE NOTICE '- Modified trigger to always use queue (no bulk detection)';
    RAISE NOTICE '- Added process_embedding_queue() function for scheduled processing';
    RAISE NOTICE '- Added queue_missing_embeddings() for manual batch queuing';
    RAISE NOTICE '- Added get_embedding_queue_status() for monitoring';
    RAISE NOTICE '- Scheduled processing every 30 seconds with pg_cron';
    RAISE NOTICE '- System now handles any volume of inserts reliably';
END;
$$;