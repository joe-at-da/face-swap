-- Replace all uuid_generate_v4() usage with PostgreSQL built-in gen_random_uuid()
-- The uuid-ossp extension is not available in the current database environment.
-- gen_random_uuid() is built into PostgreSQL (since v13) and requires no extension.

-- =============================================================================
-- Section 1: Update all table column defaults
-- =============================================================================

ALTER TABLE parliament_members ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_member_contacts ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_member_portraits ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_member_voting_history ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_sync_status ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_member_clips ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE user_clips ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_member_face_encodings ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_events ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE transcript_embedding_logs ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE runpod_processing_logs ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE parliament_sync_logs ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- =============================================================================
-- Section 2: Update trigger functions that use uuid_generate_v4() in EXCEPTION blocks
-- =============================================================================

-- 2a) generate_transcript_embedding() - latest version from 20260107012615
CREATE OR REPLACE FUNCTION public.generate_transcript_embedding()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    transcript_text text;
    transcript_len int;
    queue_message jsonb;
    should_process boolean := false;
BEGIN
    transcript_text := NEW.transcript;
    transcript_len := COALESCE(length(transcript_text), 0);

    -- Skip if no transcript
    IF transcript_text IS NULL OR transcript_text = '' THEN
        INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, notes)
        VALUES (TG_TABLE_NAME, NEW.id, 'skipped', transcript_len, 'No transcript available');
        RETURN NEW;
    END IF;

    -- Determine if we should process
    IF TG_OP = 'INSERT' THEN
        -- New row with transcript: process if no embedding yet
        IF NEW.transcript_embedding IS NULL THEN
            should_process := true;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Update: process if transcript actually changed
        IF OLD.transcript IS DISTINCT FROM NEW.transcript THEN
            should_process := true;
            -- Clear existing embeddings so they'll be regenerated
            -- This works because we're now a BEFORE trigger
            NEW.transcript_embedding := NULL;
            NEW.description_embedding := NULL;
            NEW.description := NULL;
            -- For user_clips, also clear title fields
            IF TG_TABLE_NAME = 'user_clips' THEN
                NEW.title := NULL;
                NEW.title_embedding := NULL;
            END IF;
        END IF;
    END IF;

    -- If no processing needed, skip
    IF NOT should_process THEN
        INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, notes)
        VALUES (TG_TABLE_NAME, NEW.id, 'skipped', transcript_len,
            CASE
                WHEN TG_OP = 'INSERT' THEN 'Embedding already exists on insert'
                ELSE 'No transcript change detected'
            END);
        RETURN NEW;
    END IF;

    -- Queue the job
    queue_message := jsonb_build_object(
        'clip_id', NEW.id,
        'table_name', TG_TABLE_NAME,
        'transcript_length', transcript_len,
        'created_at', NOW()
    );

    PERFORM pgmq.send('embedding_jobs', queue_message);

    INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, notes)
    VALUES (TG_TABLE_NAME, NEW.id, 'queued', transcript_len, 'Queued for processing via PGMQ');

    RETURN NEW;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO transcript_embedding_logs (table_name, clip_id, status, transcript_length, error_message, notes)
    VALUES (COALESCE(TG_TABLE_NAME, 'unknown'), COALESCE(NEW.id, gen_random_uuid()), 'failed', transcript_len, SQLERRM, 'Error queuing embedding job');
    RETURN NEW;
END;
$$;

-- 2b) trigger_parliament_video_processing() - latest version from 20251102131109
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
            COALESCE(NEW.id, gen_random_uuid()),
            processing_endpoint,
            'failed',
            SQLERRM,
            'Unexpected error in trigger function'
        );

        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- 2c) trigger_user_clip_processing() - from 20250825140000
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
            COALESCE(NEW.id, gen_random_uuid()),
            processing_endpoint,
            'failed',
            SQLERRM,
            'Unexpected error in trigger function'
        );

        -- Don't re-raise to avoid failing the original operation
        RETURN NEW;
END;
$$;

-- =============================================================================
-- Section 3: Drop the uuid-ossp extension (no longer needed)
-- Wrapped in exception handler so a failure here cannot roll back the
-- critical gen_random_uuid() changes above.
-- =============================================================================

DO $$
BEGIN
    DROP EXTENSION IF EXISTS "uuid-ossp";
EXCEPTION WHEN dependent_objects_still_exist THEN
    RAISE WARNING 'uuid-ossp extension not dropped: dependent objects still exist. This is non-critical since all defaults now use gen_random_uuid().';
END;
$$;
