-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS http;

-- Create logging table for RunPod processing attempts
CREATE TABLE IF NOT EXISTS runpod_processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    endpoint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('triggered', 'success', 'failed')),
    response_status INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

-- Create index for better query performance on logging table
CREATE INDEX IF NOT EXISTS idx_runpod_processing_logs_created_at 
ON runpod_processing_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_runpod_processing_logs_record_id 
ON runpod_processing_logs(record_id);

-- Function to trigger parliament video processing
CREATE OR REPLACE FUNCTION trigger_parliament_video_processing()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    request_body text;
    processing_endpoint text := '/api/runpod/process-video';
BEGIN
    -- Only process if status is pending and title_type is 'House of Commons'
    IF NEW.status != 'pending' OR NEW.title_type != 'House of Commons' THEN
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
    
    -- Build request body JSON
    request_body := json_build_object('parliament_event_id', NEW.id)::text;
    
    -- Log that we're triggering the processing
    INSERT INTO runpod_processing_logs (
        table_name, 
        record_id, 
        endpoint,
        status, 
        notes
    ) VALUES (
        'parliament_events',
        NEW.id,
        processing_endpoint,
        'triggered',
        'Sending request to process parliament video'
    );
    
    -- Make HTTP POST request to the RunPod processing endpoint (fire and forget)
    BEGIN
        PERFORM http((
            'POST',
            app_url || processing_endpoint,
            ARRAY[
                http_header('Content-Type', 'application/json'),
                http_header('Authorization', 'Bearer ' || cron_secret)
            ],
            'application/json',
            request_body
        )::http_request);
        
        -- If we get here, the request was sent successfully
        -- Update the log with success status
        UPDATE runpod_processing_logs 
        SET status = 'success', 
            response_status = 200,
            notes = 'HTTP request sent successfully (async processing)'
        WHERE table_name = 'parliament_events' 
        AND record_id = NEW.id 
        AND endpoint = processing_endpoint
        AND status = 'triggered'
        AND created_at = (
            SELECT MAX(created_at) 
            FROM runpod_processing_logs 
            WHERE table_name = 'parliament_events' 
            AND record_id = NEW.id
            AND endpoint = processing_endpoint
        );
        
    EXCEPTION
        WHEN OTHERS THEN
            -- If there's an error sending the request, log it but continue
            -- Update the log with failure status
            UPDATE runpod_processing_logs 
            SET status = 'failed', 
                response_status = 0,
                error_message = SQLERRM,
                notes = 'Failed to send HTTP request'
            WHERE table_name = 'parliament_events' 
            AND record_id = NEW.id 
            AND endpoint = processing_endpoint
            AND status = 'triggered'
            AND created_at = (
                SELECT MAX(created_at) 
                FROM runpod_processing_logs 
                WHERE table_name = 'parliament_events' 
                AND record_id = NEW.id
                AND endpoint = processing_endpoint
            );
    END;
    
    -- Always return NEW to not interfere with the original operation
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log any unexpected errors
        INSERT INTO runpod_processing_logs (
            table_name, 
            record_id, 
            endpoint,
            status, 
            error_message,
            notes
        ) VALUES (
            'parliament_events',
            COALESCE(NEW.id, uuid_generate_v4()),
            processing_endpoint,
            'failed',
            SQLERRM,
            'Unexpected error in trigger function'
        );
        
        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- Function to trigger user clip processing
CREATE OR REPLACE FUNCTION trigger_user_clip_processing()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    request_body text;
    processing_endpoint text := '/api/runpod/create-clip';
BEGIN
    -- Only process if status is pending_review
    IF NEW.status != 'pending_review' THEN
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
    
    -- Build request body JSON
    request_body := json_build_object('user_clip_id', NEW.id)::text;
    
    -- Log that we're triggering the processing
    INSERT INTO runpod_processing_logs (
        table_name, 
        record_id, 
        endpoint,
        status, 
        notes
    ) VALUES (
        'user_clips',
        NEW.id,
        processing_endpoint,
        'triggered',
        'Sending request to create user clip'
    );
    
    -- Make HTTP POST request to the RunPod processing endpoint (fire and forget)
    BEGIN
        PERFORM http((
            'POST',
            app_url || processing_endpoint,
            ARRAY[
                http_header('Content-Type', 'application/json'),
                http_header('Authorization', 'Bearer ' || cron_secret)
            ],
            'application/json',
            request_body
        )::http_request);
        
        -- If we get here, the request was sent successfully
        -- Update the log with success status
        UPDATE runpod_processing_logs 
        SET status = 'success', 
            response_status = 200,
            notes = 'HTTP request sent successfully (async processing)'
        WHERE table_name = 'user_clips' 
        AND record_id = NEW.id 
        AND endpoint = processing_endpoint
        AND status = 'triggered'
        AND created_at = (
            SELECT MAX(created_at) 
            FROM runpod_processing_logs 
            WHERE table_name = 'user_clips' 
            AND record_id = NEW.id
            AND endpoint = processing_endpoint
        );
        
    EXCEPTION
        WHEN OTHERS THEN
            -- If there's an error sending the request, log it but continue
            -- Update the log with failure status
            UPDATE runpod_processing_logs 
            SET status = 'failed', 
                response_status = 0,
                error_message = SQLERRM,
                notes = 'Failed to send HTTP request'
            WHERE table_name = 'user_clips' 
            AND record_id = NEW.id 
            AND endpoint = processing_endpoint
            AND status = 'triggered'
            AND created_at = (
                SELECT MAX(created_at) 
                FROM runpod_processing_logs 
                WHERE table_name = 'user_clips' 
                AND record_id = NEW.id
                AND endpoint = processing_endpoint
            );
    END;
    
    -- Always return NEW to not interfere with the original operation
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log any unexpected errors
        INSERT INTO runpod_processing_logs (
            table_name, 
            record_id, 
            endpoint,
            status, 
            error_message,
            notes
        ) VALUES (
            'user_clips',
            COALESCE(NEW.id, uuid_generate_v4()),
            processing_endpoint,
            'failed',
            SQLERRM,
            'Unexpected error in trigger function'
        );
        
        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- Create trigger for parliament_events table
-- Trigger on INSERT or UPDATE of status field when status is pending and title_type is 'House of Commons'
DROP TRIGGER IF EXISTS auto_trigger_parliament_video_processing ON parliament_events;
CREATE TRIGGER auto_trigger_parliament_video_processing
    AFTER INSERT OR UPDATE OF status ON parliament_events
    FOR EACH ROW
    WHEN (NEW.status = 'pending' AND NEW.title_type = 'House of Commons')
    EXECUTE FUNCTION trigger_parliament_video_processing();

-- Create trigger for user_clips table
-- Trigger on INSERT or UPDATE of status field when status is pending_review
DROP TRIGGER IF EXISTS auto_trigger_user_clip_processing ON user_clips;
CREATE TRIGGER auto_trigger_user_clip_processing
    AFTER INSERT OR UPDATE OF status ON user_clips
    FOR EACH ROW
    WHEN (NEW.status = 'pending_review')
    EXECUTE FUNCTION trigger_user_clip_processing();

-- Create function to manually trigger processing (for testing/debugging)
CREATE OR REPLACE FUNCTION trigger_runpod_processing_manually(
    record_id_param UUID,
    table_name_param TEXT,
    endpoint_param TEXT DEFAULT NULL
)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result_message text;
    record_exists boolean;
BEGIN
    -- Validate table name and set default endpoint
    IF table_name_param = 'parliament_events' THEN
        IF endpoint_param IS NULL THEN
            endpoint_param := '/api/runpod/process-video';
        END IF;
        SELECT EXISTS(SELECT 1 FROM parliament_events WHERE id = record_id_param) INTO record_exists;
    ELSIF table_name_param = 'user_clips' THEN
        IF endpoint_param IS NULL THEN
            endpoint_param := '/api/runpod/create-clip';
        END IF;
        SELECT EXISTS(SELECT 1 FROM user_clips WHERE id = record_id_param) INTO record_exists;
    ELSE
        RETURN 'Error: Invalid table name. Must be either ''parliament_events'' or ''user_clips''';
    END IF;
    
    IF NOT record_exists THEN
        RETURN 'Error: Record with ID ' || record_id_param || ' not found in table ' || table_name_param;
    END IF;
    
    -- Trigger the processing by updating the status field to itself
    -- This will fire the trigger if conditions are met
    IF table_name_param = 'parliament_events' THEN
        UPDATE parliament_events 
        SET status = status, updated_at = NOW()
        WHERE id = record_id_param;
    ELSE
        UPDATE user_clips 
        SET status = status, updated_at = NOW()
        WHERE id = record_id_param;
    END IF;
    
    -- Return success message
    result_message := 'RunPod processing triggered manually for ' || table_name_param || ' with ID: ' || record_id_param || ' (endpoint: ' || endpoint_param || '). Check runpod_processing_logs for results.';
    
    RETURN result_message;
END;
$$;

-- Create function to get processing status for a record
CREATE OR REPLACE FUNCTION get_runpod_processing_status(record_id_param UUID)
RETURNS TABLE (
    table_name TEXT,
    record_id UUID,
    endpoint TEXT,
    status TEXT,
    response_status INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    notes TEXT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        r.table_name,
        r.record_id,
        r.endpoint,
        r.status,
        r.response_status,
        r.created_at,
        r.error_message,
        r.notes
    FROM runpod_processing_logs r
    WHERE r.record_id = record_id_param
    ORDER BY r.created_at DESC;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION trigger_parliament_video_processing() TO service_role;
GRANT EXECUTE ON FUNCTION trigger_user_clip_processing() TO service_role;
GRANT EXECUTE ON FUNCTION trigger_runpod_processing_manually(UUID, TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION get_runpod_processing_status(UUID) TO service_role;

-- Grant table permissions
GRANT INSERT, SELECT, UPDATE ON runpod_processing_logs TO service_role;
GRANT USAGE ON SCHEMA public TO service_role;

-- Add comments to document the setup
COMMENT ON FUNCTION trigger_parliament_video_processing() IS 
'Trigger function that automatically calls the RunPod video processing API endpoint when a parliament event with status pending and title_type House of Commons is inserted or updated';

COMMENT ON FUNCTION trigger_user_clip_processing() IS 
'Trigger function that automatically calls the RunPod clip creation API endpoint when a user clip with status pending_review is inserted or updated';

COMMENT ON FUNCTION trigger_runpod_processing_manually(UUID, TEXT, TEXT) IS 
'Manual function to trigger RunPod processing for a specific record ID and table for testing/debugging purposes';

COMMENT ON FUNCTION get_runpod_processing_status(UUID) IS 
'Function to retrieve the RunPod processing status and history for a specific record ID';

COMMENT ON TABLE runpod_processing_logs IS 
'Logs all attempts to trigger RunPod processing, including successes, failures, and triggered attempts';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'RunPod processing automation setup complete:';
    RAISE NOTICE '- Created runpod_processing_logs table for tracking attempts';
    RAISE NOTICE '- Created trigger_parliament_video_processing() function';
    RAISE NOTICE '- Created trigger_user_clip_processing() function';
    RAISE NOTICE '- Added triggers for both parliament_events and user_clips tables';
    RAISE NOTICE '- Added manual trigger function for testing';
    RAISE NOTICE '- Added status checking function';
    RAISE NOTICE '- Granted necessary permissions to service_role';
    RAISE NOTICE '- Parliament events: triggers when status=pending AND title_type=House of Commons';
    RAISE NOTICE '- User clips: triggers when status=pending_review';
END;
$$;