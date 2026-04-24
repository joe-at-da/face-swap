-- Fix embedding generation for bulk inserts from RunPod (300-700 clips at once)
-- Detects bulk operations and queues them for batch processing instead of flooding with HTTP requests

-- Add new status type for queued embeddings
DO $$
BEGIN
    -- Check if 'queued' status already exists in the check constraint
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'transcript_embedding_logs_status_check'
    ) THEN
        -- If constraint doesn't exist, we need to add it
        NULL; -- Table already has the constraint
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        NULL; -- Ignore if already exists
END;
$$;

-- Drop and recreate the check constraint to include 'queued' status
ALTER TABLE transcript_embedding_logs 
DROP CONSTRAINT IF EXISTS transcript_embedding_logs_status_check;

ALTER TABLE transcript_embedding_logs 
ADD CONSTRAINT transcript_embedding_logs_status_check 
CHECK (status IN ('triggered', 'success', 'failed', 'skipped', 'queued'));

-- Create improved embedding generation function that handles bulk inserts
CREATE OR REPLACE FUNCTION generate_transcript_embedding()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    http_response_status int;
    request_body text;
    clip_id_param text;
    transcript_text text;
    transcript_len int;
    recent_insert_count int;
    is_bulk_operation boolean := false;
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
    
    -- CRITICAL: Detect bulk insert operations (RunPod typically inserts 300-700 clips)
    -- Check how many clips were inserted in the last 2 seconds
    SELECT COUNT(*) INTO recent_insert_count
    FROM parliament_member_clips
    WHERE created_at >= NOW() - INTERVAL '2 seconds'
      AND created_at <= NOW();
    
    -- If more than 10 inserts in 2 seconds, this is likely a bulk operation
    IF recent_insert_count > 10 THEN
        is_bulk_operation := true;
    END IF;
    
    -- For bulk operations, just queue for later processing
    IF is_bulk_operation THEN
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
            'Queued for batch processing (bulk insert detected: ' || recent_insert_count || ' recent clips)'
        );
        -- Don't make HTTP calls during bulk insert
        RETURN NEW;
    END IF;
    
    -- For single inserts, continue with immediate processing
    -- Get environment variables from vault (preferred approach)
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
    
    -- Determine the correct parameter based on table
    IF TG_TABLE_NAME = 'parliament_member_clips' THEN
        clip_id_param := 'parliament_clip_id';
    ELSIF TG_TABLE_NAME = 'user_clips' THEN
        clip_id_param := 'user_clip_id';
    ELSE
        -- Log error for unknown table
        INSERT INTO transcript_embedding_logs (
            table_name, 
            clip_id, 
            status, 
            transcript_length,
            error_message
        ) VALUES (
            TG_TABLE_NAME,
            NEW.id,
            'failed',
            transcript_len,
            'Unknown table name: ' || TG_TABLE_NAME
        );
        RETURN NEW;
    END IF;
    
    -- Build request body JSON
    request_body := json_build_object(clip_id_param, NEW.id)::text;
    
    -- Log that we're triggering the embedding generation
    INSERT INTO transcript_embedding_logs (
        table_name, 
        clip_id, 
        status, 
        transcript_length,
        notes
    ) VALUES (
        TG_TABLE_NAME,
        NEW.id,
        'triggered',
        transcript_len,
        'Sending immediate request to generate embedding (single insert)'
    );
    
    -- Make HTTP POST request for single inserts only
    BEGIN
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
        http_response_status := 200;
        
        -- Update the log with success status
        UPDATE transcript_embedding_logs 
        SET status = 'success', 
            response_status = http_response_status,
            notes = 'HTTP request sent successfully (single insert processing)'
        WHERE table_name = TG_TABLE_NAME 
        AND clip_id = NEW.id 
        AND status = 'triggered'
        AND created_at = (
            SELECT MAX(created_at) 
            FROM transcript_embedding_logs 
            WHERE table_name = TG_TABLE_NAME 
            AND clip_id = NEW.id
        );
        
    EXCEPTION
        WHEN OTHERS THEN
            -- If there's an error sending the request, log it but continue
            http_response_status := 0;
            
            -- Update the log with failure status
            UPDATE transcript_embedding_logs 
            SET status = 'failed', 
                response_status = http_response_status,
                error_message = SQLERRM,
                notes = 'Failed to send HTTP request (single insert)'
            WHERE table_name = TG_TABLE_NAME 
            AND clip_id = NEW.id 
            AND status = 'triggered'
            AND created_at = (
                SELECT MAX(created_at) 
                FROM transcript_embedding_logs 
                WHERE table_name = TG_TABLE_NAME 
                AND clip_id = NEW.id
            );
    END;
    
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
            'Unexpected error in trigger function (non-blocking)'
        );
        
        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- Create function to process queued embeddings in batches
CREATE OR REPLACE FUNCTION process_queued_embeddings(
    batch_size int DEFAULT 10,
    table_filter text DEFAULT NULL
)
RETURNS TABLE (
    processed_count int,
    success_count int,
    failed_count int,
    remaining_queued int
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    clip_record RECORD;
    processed int := 0;
    succeeded int := 0;
    failed int := 0;
    remaining int := 0;
    request_body text;
    clip_id_param text;
BEGIN
    -- Get environment variables
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
    
    -- Process queued embeddings in batches
    FOR clip_record IN 
        SELECT DISTINCT ON (tel.clip_id) 
            tel.clip_id,
            tel.table_name,
            tel.transcript_length
        FROM transcript_embedding_logs tel
        WHERE tel.status = 'queued'
        AND (table_filter IS NULL OR tel.table_name = table_filter)
        ORDER BY tel.clip_id, tel.created_at DESC
        LIMIT batch_size
    LOOP
        processed := processed + 1;
        
        -- Determine the correct parameter based on table
        IF clip_record.table_name = 'parliament_member_clips' THEN
            clip_id_param := 'parliament_clip_id';
        ELSIF clip_record.table_name = 'user_clips' THEN
            clip_id_param := 'user_clip_id';
        ELSE
            failed := failed + 1;
            CONTINUE;
        END IF;
        
        -- Build request body
        request_body := json_build_object(clip_id_param, clip_record.clip_id)::text;
        
        -- Try to send HTTP request
        BEGIN
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
            
            -- Success - update log
            UPDATE transcript_embedding_logs 
            SET status = 'success',
                response_status = 200,
                notes = 'Processed from queue batch'
            WHERE clip_id = clip_record.clip_id
            AND status = 'queued';
            
            succeeded := succeeded + 1;
            
            -- Small delay between requests to avoid overwhelming the API
            PERFORM pg_sleep(0.1);
            
        EXCEPTION
            WHEN OTHERS THEN
                -- Failed - update log
                UPDATE transcript_embedding_logs 
                SET status = 'failed',
                    error_message = SQLERRM,
                    notes = 'Failed during batch processing'
                WHERE clip_id = clip_record.clip_id
                AND status = 'queued';
                
                failed := failed + 1;
        END;
    END LOOP;
    
    -- Count remaining queued items
    SELECT COUNT(DISTINCT clip_id) INTO remaining
    FROM transcript_embedding_logs
    WHERE status = 'queued'
    AND (table_filter IS NULL OR table_name = table_filter);
    
    RETURN QUERY SELECT processed, succeeded, failed, remaining;
END;
$$;

-- Create function to manually process all clips missing embeddings
CREATE OR REPLACE FUNCTION generate_missing_embeddings_batch(
    table_name_param text DEFAULT 'parliament_member_clips',
    limit_param int DEFAULT 50
)
RETURNS TABLE (
    clips_found int,
    clips_queued int,
    clips_processed int,
    success_count int,
    failed_count int
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    found_count int := 0;
    queued_count int := 0;
    process_result RECORD;
BEGIN
    -- Find clips missing embeddings and queue them
    IF table_name_param = 'parliament_member_clips' THEN
        INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, notes)
        SELECT 
            'parliament_member_clips',
            id,
            'queued',
            length(transcript),
            'Queued for batch embedding generation'
        FROM parliament_member_clips
        WHERE transcript IS NOT NULL 
        AND transcript != ''
        AND transcript_embedding IS NULL
        AND id NOT IN (
            SELECT clip_id FROM transcript_embedding_logs 
            WHERE status IN ('queued', 'triggered')
            AND table_name = 'parliament_member_clips'
        )
        LIMIT limit_param;
        
        GET DIAGNOSTICS queued_count = ROW_COUNT;
        
        SELECT COUNT(*) INTO found_count
        FROM parliament_member_clips
        WHERE transcript IS NOT NULL 
        AND transcript != ''
        AND transcript_embedding IS NULL;
        
    ELSIF table_name_param = 'user_clips' THEN
        INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, notes)
        SELECT 
            'user_clips',
            id,
            'queued',
            length(transcript),
            'Queued for batch embedding generation'
        FROM user_clips
        WHERE transcript IS NOT NULL 
        AND transcript != ''
        AND transcript_embedding IS NULL
        AND id NOT IN (
            SELECT clip_id FROM transcript_embedding_logs 
            WHERE status IN ('queued', 'triggered')
            AND table_name = 'user_clips'
        )
        LIMIT limit_param;
        
        GET DIAGNOSTICS queued_count = ROW_COUNT;
        
        SELECT COUNT(*) INTO found_count
        FROM user_clips
        WHERE transcript IS NOT NULL 
        AND transcript != ''
        AND transcript_embedding IS NULL;
    END IF;
    
    -- Process the queued items
    SELECT * INTO process_result
    FROM process_queued_embeddings(10, table_name_param);
    
    RETURN QUERY 
    SELECT 
        found_count,
        queued_count,
        process_result.processed_count,
        process_result.success_count,
        process_result.failed_count;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION process_queued_embeddings(int, text) TO service_role;
GRANT EXECUTE ON FUNCTION generate_missing_embeddings_batch(text, int) TO service_role;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Bulk insert embedding fix applied:';
    RAISE NOTICE '- Modified generate_transcript_embedding() to detect bulk inserts';
    RAISE NOTICE '- Bulk inserts (>10 clips in 2 seconds) are queued instead of processed immediately';
    RAISE NOTICE '- Added process_queued_embeddings() function for batch processing';
    RAISE NOTICE '- Added generate_missing_embeddings_batch() for manual batch generation';
    RAISE NOTICE '- Single inserts still processed immediately';
    RAISE NOTICE '- This prevents HTTP request flooding during RunPod bulk insertions';
END;
$$;