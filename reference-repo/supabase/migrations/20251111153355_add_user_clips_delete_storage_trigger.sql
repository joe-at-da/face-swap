-- Simple AFTER DELETE Trigger for User Clips Storage Deletion
-- This trigger calls the API endpoint to delete video files from DO Spaces (via Supabase Storage)
-- when user_clips records are deleted from the database.

-- Enable http extension if not already enabled
CREATE EXTENSION IF NOT EXISTS http;

-- Create trigger function to call storage deletion API
CREATE OR REPLACE FUNCTION public.delete_user_clip_storage()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    response_status int;
BEGIN
    -- Get environment variables from vault
    SELECT decrypted_secret INTO app_url
    FROM vault.decrypted_secrets
    WHERE name = 'project_url';

    -- Fallback for local development
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000';
    END IF;

    -- Call the storage deletion API endpoint
    BEGIN
        SELECT status INTO response_status
        FROM http((
            'POST',
            app_url || '/api/webhooks/delete-user-clip-storage',
            ARRAY[
                http_header('Content-Type', 'application/json')
            ],
            'application/json',
            jsonb_build_object(
                'userId', OLD.user_id,
                'clipId', OLD.id
            )::text
        )::http_request);

        RAISE LOG 'Storage deletion triggered for clip %. Response status: %', OLD.id, response_status;

    EXCEPTION
        WHEN OTHERS THEN
            -- Log error but don't fail the deletion
            RAISE WARNING 'Failed to trigger storage deletion for clip %: %', OLD.id, SQLERRM;
    END;

    RETURN OLD;
END;
$$;

-- Create trigger on user_clips table
-- Fires AFTER DELETE so it only runs after successful database deletion
CREATE TRIGGER user_clips_delete_storage_trigger
    AFTER DELETE ON user_clips
    FOR EACH ROW
    EXECUTE FUNCTION public.delete_user_clip_storage();

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION public.delete_user_clip_storage TO service_role;

-- Add comment
COMMENT ON FUNCTION public.delete_user_clip_storage() IS
'Trigger function that calls the storage deletion API endpoint when user_clips are deleted. Makes HTTP POST to /api/webhooks/delete-user-clip-storage with userId and clipId.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Created simple AFTER DELETE storage trigger:';
    RAISE NOTICE '- Trigger function: delete_user_clip_storage()';
    RAISE NOTICE '- Trigger: user_clips_delete_storage_trigger';
    RAISE NOTICE '- Calls: POST /api/webhooks/delete-user-clip-storage';
    RAISE NOTICE '- Deletes files from DO Spaces via Supabase Storage API';
END $$;