-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS http;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create logging table for transcript embedding generation attempts
CREATE TABLE IF NOT EXISTS transcript_embedding_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name TEXT NOT NULL,
    clip_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('triggered', 'success', 'failed', 'skipped')),
    response_status INTEGER,
    error_message TEXT,
    transcript_length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

-- Create index for better query performance on logging table
CREATE INDEX IF NOT EXISTS idx_transcript_embedding_logs_created_at 
ON transcript_embedding_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transcript_embedding_logs_clip_id 
ON transcript_embedding_logs(clip_id);

-- Create function to automatically generate transcript embeddings
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

-- Create trigger for parliament_member_clips table
-- Only trigger on INSERT or UPDATE of transcript field when embedding is null
DROP TRIGGER IF EXISTS auto_generate_parliament_clip_embedding ON parliament_member_clips;
CREATE TRIGGER auto_generate_parliament_clip_embedding
    AFTER INSERT OR UPDATE OF transcript ON parliament_member_clips
    FOR EACH ROW
    WHEN (NEW.transcript IS NOT NULL AND NEW.transcript <> '' AND NEW.transcript_embedding IS NULL)
    EXECUTE FUNCTION generate_transcript_embedding();

-- Create trigger for user_clips table
-- Only trigger on INSERT or UPDATE of transcript field when embedding is null
DROP TRIGGER IF EXISTS auto_generate_user_clip_embedding ON user_clips;
CREATE TRIGGER auto_generate_user_clip_embedding
    AFTER INSERT OR UPDATE OF transcript ON user_clips
    FOR EACH ROW
    WHEN (NEW.transcript IS NOT NULL AND NEW.transcript <> '' AND NEW.transcript_embedding IS NULL)
    EXECUTE FUNCTION generate_transcript_embedding();

-- Create function to manually trigger embedding generation (for testing/debugging)
CREATE OR REPLACE FUNCTION trigger_embedding_generation_manually(
    clip_id_param UUID,
    table_name_param TEXT DEFAULT 'parliament_member_clips'
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result_message text;
    record_exists boolean;
BEGIN
    -- Validate table name
    IF table_name_param NOT IN ('parliament_member_clips', 'user_clips') THEN
        RETURN 'Error: Invalid table name. Must be either ''parliament_member_clips'' or ''user_clips''';
    END IF;
    
    -- Check if the clip exists
    IF table_name_param = 'parliament_member_clips' THEN
        SELECT EXISTS(SELECT 1 FROM parliament_member_clips WHERE id = clip_id_param) INTO record_exists;
    ELSE
        SELECT EXISTS(SELECT 1 FROM user_clips WHERE id = clip_id_param) INTO record_exists;
    END IF;
    
    IF NOT record_exists THEN
        RETURN 'Error: Clip with ID ' || clip_id_param || ' not found in table ' || table_name_param;
    END IF;
    
    -- Trigger the embedding generation by updating the transcript field to itself
    -- This will fire the trigger if conditions are met
    IF table_name_param = 'parliament_member_clips' THEN
        UPDATE parliament_member_clips 
        SET transcript = transcript, updated_at = NOW()
        WHERE id = clip_id_param;
    ELSE
        UPDATE user_clips 
        SET transcript = transcript, updated_at = NOW()
        WHERE id = clip_id_param;
    END IF;
    
    -- Return success message
    result_message := 'Embedding generation triggered manually for ' || table_name_param || ' with ID: ' || clip_id_param || '. Check transcript_embedding_logs for results.';
    
    RETURN result_message;
END;
$$;

-- Create function to get embedding generation status for a clip
CREATE OR REPLACE FUNCTION get_embedding_generation_status(clip_id_param UUID)
RETURNS TABLE (
    table_name TEXT,
    clip_id UUID,
    status TEXT,
    response_status INTEGER,
    transcript_length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    notes TEXT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        t.table_name,
        t.clip_id,
        t.status,
        t.response_status,
        t.transcript_length,
        t.created_at,
        t.error_message,
        t.notes
    FROM transcript_embedding_logs t
    WHERE t.clip_id = clip_id_param
    ORDER BY t.created_at DESC;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION generate_transcript_embedding() TO service_role;
GRANT EXECUTE ON FUNCTION trigger_embedding_generation_manually(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION get_embedding_generation_status(UUID) TO service_role;

-- Grant table permissions
GRANT INSERT, SELECT, UPDATE ON transcript_embedding_logs TO service_role;
GRANT USAGE ON SCHEMA public TO service_role;

-- Add comments to document the setup
COMMENT ON FUNCTION generate_transcript_embedding() IS 
'Trigger function that automatically calls the transcript embedding API endpoint when a clip with transcript is inserted or updated';

COMMENT ON FUNCTION trigger_embedding_generation_manually(UUID, TEXT) IS 
'Manual function to trigger embedding generation for a specific clip ID and table for testing/debugging purposes';

COMMENT ON FUNCTION get_embedding_generation_status(UUID) IS 
'Function to retrieve the embedding generation status and history for a specific clip ID';

COMMENT ON TABLE transcript_embedding_logs IS 
'Logs all attempts to generate transcript embeddings, including successes, failures, and skipped attempts';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Transcript embedding automation setup complete:';
    RAISE NOTICE '- Created transcript_embedding_logs table for tracking attempts';
    RAISE NOTICE '- Created generate_transcript_embedding() trigger function';
    RAISE NOTICE '- Added triggers for both parliament_member_clips and user_clips tables';
    RAISE NOTICE '- Added manual trigger function for testing';
    RAISE NOTICE '- Added status checking function';
    RAISE NOTICE '- Granted necessary permissions to service_role';
    RAISE NOTICE '- Triggers will only fire when transcript exists and embedding is null';
END;
$$;