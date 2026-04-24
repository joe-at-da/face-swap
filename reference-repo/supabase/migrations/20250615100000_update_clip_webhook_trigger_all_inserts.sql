-- Update Clip Webhook Trigger for All Inserts Migration
-- Migration to update the parliament member clips webhook trigger to fire on ALL inserts,
-- not just completed clips. This allows processing to start immediately when clips are added.

-- Update the trigger function to call webhook on any INSERT operation
CREATE OR REPLACE FUNCTION handle_clip_webhook()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- For INSERT operations: call webhook for ALL new clips (regardless of status)
    IF TG_OP = 'INSERT' THEN
        PERFORM notify_clip_webhook();
    -- For UPDATE operations: call webhook if status becomes completed OR if key fields changed on completed clips
    ELSIF TG_OP = 'UPDATE' THEN
        -- Check if status changed to completed
        IF NEW.status = 'completed'::parliament_clip_status AND OLD.status != 'completed'::parliament_clip_status THEN
            PERFORM notify_clip_webhook();
        -- Check if key fields changed on already completed clips
        ELSIF NEW.status = 'completed'::parliament_clip_status AND OLD.status = 'completed'::parliament_clip_status THEN
            -- Check if start_timestamp, end_timestamp, or transcript changed
            IF (OLD.start_timestamp IS DISTINCT FROM NEW.start_timestamp) OR
               (OLD.end_timestamp IS DISTINCT FROM NEW.end_timestamp) OR
               (OLD.transcript IS DISTINCT FROM NEW.transcript) THEN
                PERFORM notify_clip_webhook();
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Grant necessary permissions (in case they were lost)
GRANT EXECUTE ON FUNCTION handle_clip_webhook TO service_role;

-- Update the function comment to reflect the new behavior
COMMENT ON FUNCTION handle_clip_webhook IS 
'Trigger function that calls webhook for: ALL new clips (any status), status changes to completed, or when start_timestamp/end_timestamp/transcript change on completed clips';

-- Log successful migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated parliament member clips webhook trigger:';
    RAISE NOTICE '- Now calls webhook on ALL INSERT operations (regardless of status)';
    RAISE NOTICE '- Maintains existing UPDATE logic for completed clips';
    RAISE NOTICE '- This allows immediate processing when clips are added to the database';
    RAISE NOTICE '- Webhook endpoint: /api/webhooks/create-clip';
END $$; 