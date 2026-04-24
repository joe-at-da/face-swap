-- Fix the ambiguous column reference in the trigger function
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
        'Sending request to generate embedding'
    );
    
    -- Make HTTP POST request to the transcript embedding endpoint (fire and forget)
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
        http_response_status := 200; -- Assume success since request was sent
        
        -- Update the log with success status
        UPDATE transcript_embedding_logs 
        SET status = 'success', 
            response_status = http_response_status,
            notes = 'HTTP request sent successfully (async processing)'
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
                notes = 'Failed to send HTTP request'
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
        -- Log any unexpected errors
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
            'Unexpected error in trigger function'
        );
        
        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;