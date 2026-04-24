-- Automate Video Sync on Storage Changes Migration
-- Migration to automatically trigger video sync when files are added or removed from the full_videos bucket
-- This ensures the temp folder stays in sync with Supabase storage without manual intervention

-- Ensure http extension is enabled for making HTTP requests
CREATE EXTENSION IF NOT EXISTS http;

-- Create function to call the video sync endpoint for a specific file
CREATE OR REPLACE FUNCTION call_video_sync_endpoint(file_name text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status int;
    request_id bigint;
    request_body jsonb;
BEGIN
    -- Get environment variables from vault (preferred approach)
    -- These should be set in your Supabase project settings under "Vault"
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Use localhost for development/testing
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000';
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'development-secret';
    END IF;
    
    -- Build request body with specific file if provided
    IF file_name IS NOT NULL THEN
        request_body := jsonb_build_object('file', file_name);
        RAISE LOG 'Calling video sync endpoint for specific file: %. URL: %', file_name, app_url;
    ELSE
        request_body := jsonb_build_object();
        RAISE LOG 'Calling video sync endpoint for full sync. URL: %', app_url;
    END IF;
    
    -- Make HTTP POST request to the video sync endpoint
    BEGIN
        SELECT net.http_post(
            url := app_url || '/api/sync-videos',
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'Authorization', 'Bearer ' || cron_secret
            ),
            body := request_body
        ) INTO request_id;
        
        RAISE LOG 'Video sync request initiated. Request ID: %, File: %', request_id, COALESCE(file_name, 'all');
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE WARNING 'Video sync HTTP error for file %: %', COALESCE(file_name, 'all'), SQLERRM;
    END;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Video sync failed for file %: %', COALESCE(file_name, 'all'), SQLERRM;
END;
$$;

-- Create trigger function for storage object changes
CREATE OR REPLACE FUNCTION handle_video_storage_changes()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Only trigger for changes in the full_videos bucket
    IF COALESCE(NEW.bucket_id, OLD.bucket_id) = 'full_videos' THEN
        -- For INSERT: new file added to full_videos bucket
        IF TG_OP = 'INSERT' THEN
            -- Only sync .mp4 files
            IF NEW.name LIKE '%.mp4' THEN
                RAISE LOG 'File added to full_videos bucket: %', NEW.name;
                PERFORM call_video_sync_endpoint(NEW.name);
            END IF;
            RETURN NEW;
        END IF;
        
        -- For DELETE: file removed from full_videos bucket
        IF TG_OP = 'DELETE' THEN
            -- Trigger full sync when files are deleted (to clean up local files)
            IF OLD.name LIKE '%.mp4' THEN
                RAISE LOG 'File removed from full_videos bucket: %', OLD.name;
                PERFORM call_video_sync_endpoint(); -- Full sync to clean up
            END IF;
            RETURN OLD;
        END IF;
        
        -- For UPDATE: file modified in full_videos bucket (e.g., metadata changes)
        IF TG_OP = 'UPDATE' THEN
            -- Only trigger if the file name changed (actual file changes)
            IF OLD.name IS DISTINCT FROM NEW.name AND (OLD.name LIKE '%.mp4' OR NEW.name LIKE '%.mp4') THEN
                RAISE LOG 'File modified in full_videos bucket: % -> %', OLD.name, NEW.name;
                -- Trigger full sync when files are renamed (to handle cleanup properly)
                PERFORM call_video_sync_endpoint();
            END IF;
            RETURN NEW;
        END IF;
    END IF;
    
    -- Return appropriate record based on operation
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$;

-- Create trigger on storage.objects table for full_videos bucket changes
DROP TRIGGER IF EXISTS video_storage_sync_trigger ON storage.objects;

CREATE TRIGGER video_storage_sync_trigger
    AFTER INSERT OR UPDATE OR DELETE ON storage.objects
    FOR EACH ROW
    EXECUTE FUNCTION handle_video_storage_changes();

-- Create a function to manually trigger video sync (for testing)
CREATE OR REPLACE FUNCTION trigger_video_sync_manually(file_name text DEFAULT NULL)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    PERFORM call_video_sync_endpoint(file_name);
    IF file_name IS NOT NULL THEN
        RETURN 'Video sync triggered manually for file: ' || file_name || '. Check application logs for results.';
    ELSE
        RETURN 'Full video sync triggered manually. Check application logs for results.';
    END IF;
END;
$$;

-- Create a view to monitor recent video storage changes (for debugging)
CREATE OR REPLACE VIEW video_storage_activity AS
SELECT 
    o.name,
    o.bucket_id,
    o.created_at,
    o.updated_at,
    o.metadata,
    CASE 
        WHEN o.created_at = o.updated_at THEN 'CREATED'
        ELSE 'UPDATED'
    END as action_type
FROM storage.objects o
WHERE o.bucket_id = 'full_videos'
ORDER BY o.updated_at DESC
LIMIT 100;

-- Grant necessary permissions for service role
GRANT EXECUTE ON FUNCTION call_video_sync_endpoint(text) TO service_role;
GRANT EXECUTE ON FUNCTION handle_video_storage_changes() TO service_role;
GRANT EXECUTE ON FUNCTION trigger_video_sync_manually(text) TO service_role;
GRANT SELECT ON video_storage_activity TO service_role;

-- Grant permissions for authenticated users to view activity (read-only)
GRANT SELECT ON video_storage_activity TO authenticated;

-- Add comments to document the new functions and trigger
COMMENT ON FUNCTION call_video_sync_endpoint(text) IS 
'Function to call the /api/sync-videos endpoint with authentication. Pass filename for specific file sync or NULL for full sync';

COMMENT ON FUNCTION handle_video_storage_changes() IS 
'Trigger function that monitors storage.objects changes for full_videos bucket and calls video sync for specific files';

COMMENT ON FUNCTION trigger_video_sync_manually(text) IS 
'Manual function to trigger video sync for testing. Pass filename for specific file or NULL for full sync';

-- Note: Cannot comment on system table triggers due to ownership restrictions
-- video_storage_sync_trigger: Triggers automatic video sync when files are added, updated, or removed from full_videos bucket

COMMENT ON VIEW video_storage_activity IS 
'Monitoring view showing recent activity in the full_videos storage bucket';

-- Log successful setup
DO $$
BEGIN
    RAISE NOTICE 'Automated video sync on storage changes setup completed:';
    RAISE NOTICE '- call_video_sync_endpoint(filename): Function to call /api/sync-videos endpoint for specific files';
    RAISE NOTICE '- handle_video_storage_changes(): Trigger function for storage.objects changes';
    RAISE NOTICE '- video_storage_sync_trigger: Trigger on INSERT/UPDATE/DELETE in storage.objects';
    RAISE NOTICE '- trigger_video_sync_manually(filename): Manual trigger function for testing';
    RAISE NOTICE '- video_storage_activity: Monitoring view for full_videos bucket activity';
    RAISE NOTICE '- NEW FILES: Automatic targeted sync when .mp4 files are added to full_videos bucket';
    RAISE NOTICE '- DELETED FILES: Full sync triggered to clean up local files';
    RAISE NOTICE '- PREVENTS CONCURRENT DOWNLOADS: Queue system prevents duplicate downloads';
    RAISE NOTICE '- PRESERVES FILENAMES: Uses original filenames instead of hash-based names';
    RAISE NOTICE '- Using development URL: http://host.docker.internal:3000';
    RAISE NOTICE '- Test manually: SELECT trigger_video_sync_manually(); or SELECT trigger_video_sync_manually(''filename.mp4'');';
END $$; 