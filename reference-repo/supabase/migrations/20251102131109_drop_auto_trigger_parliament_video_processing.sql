-- Update the automatic trigger for parliament video processing
-- Changed to trigger on has_ended=true instead of status='pending'
-- This allows automatic processing when videos end, and easy reprocessing by
-- updating status to 'pending' (which will trigger again if has_ended=true)

-- First, drop the old trigger to recreate it with new conditions
DROP TRIGGER IF EXISTS auto_trigger_parliament_video_processing ON parliament_events;

-- Update the trigger function to check for has_ended=true
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
    -- Only process if has_ended is true, status is pending, and title_type is 'House of Commons'
    IF NEW.has_ended != true OR NEW.status != 'pending' OR NEW.title_type != 'House of Commons' THEN
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
        'Sending request to process parliament video (has_ended=true)'
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

-- Recreate the trigger with new conditions: fires on INSERT or UPDATE of has_ended or status
-- Only triggers when has_ended=true AND status='pending' AND title_type='House of Commons'
CREATE TRIGGER auto_trigger_parliament_video_processing
    AFTER INSERT OR UPDATE OF has_ended, status ON parliament_events
    FOR EACH ROW
    WHEN (NEW.has_ended = true AND NEW.status = 'pending' AND NEW.title_type = 'House of Commons')
    EXECUTE FUNCTION trigger_parliament_video_processing();

-- Update comment to document the new behavior
COMMENT ON FUNCTION trigger_parliament_video_processing() IS 
'Trigger function that automatically calls the RunPod video processing API endpoint when a parliament event has has_ended=true, status=pending, and title_type=House of Commons. 
Allows reprocessing by updating status to pending if has_ended is already true.';

COMMENT ON TRIGGER auto_trigger_parliament_video_processing ON parliament_events IS
'Automatically triggers video processing when has_ended=true AND status=pending AND title_type=House of Commons. 
Fires on INSERT or UPDATE of has_ended/status columns.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated automatic parliament video processing trigger:';
    RAISE NOTICE '- Modified trigger condition: has_ended=true AND status=pending AND title_type=House of Commons';
    RAISE NOTICE '- Trigger fires on INSERT or UPDATE of has_ended/status columns';
    RAISE NOTICE '- Videos are processed when they end (has_ended set to true)';
    RAISE NOTICE '- Reprocessing: UPDATE parliament_events SET status=''pending'' WHERE has_ended=true';
END;
$$;
