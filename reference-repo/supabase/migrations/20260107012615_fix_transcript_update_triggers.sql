-- Fix the generate_transcript_embedding() function and triggers to handle transcript updates
-- This migration fixes a bug where embeddings/descriptions weren't regenerated when transcript changed
--
-- Issues fixed:
-- 1. Triggers were AFTER triggers - modifying NEW had no effect
-- 2. WHEN clause required transcript_embedding IS NULL, blocking updates on clips with existing embeddings
-- 3. Function tried to modify NEW in AFTER trigger context

-- First, update the function to work as a BEFORE trigger
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
    VALUES (COALESCE(TG_TABLE_NAME, 'unknown'), COALESCE(NEW.id, uuid_generate_v4()), 'failed', transcript_len, SQLERRM, 'Error queuing embedding job');
    RETURN NEW;
END;
$$;

-- Recreate triggers as BEFORE triggers without restrictive WHEN clause
-- The function now handles all the logic internally

-- Drop existing AFTER triggers
DROP TRIGGER IF EXISTS auto_generate_parliament_clip_embedding ON parliament_member_clips;
DROP TRIGGER IF EXISTS auto_generate_user_clip_embedding ON user_clips;

-- Create new BEFORE triggers
-- These fire on INSERT or UPDATE of transcript, letting the function decide whether to process
CREATE TRIGGER auto_generate_parliament_clip_embedding
    BEFORE INSERT OR UPDATE OF transcript ON parliament_member_clips
    FOR EACH ROW
    WHEN (NEW.transcript IS NOT NULL AND NEW.transcript <> '')
    EXECUTE FUNCTION generate_transcript_embedding();

CREATE TRIGGER auto_generate_user_clip_embedding
    BEFORE INSERT OR UPDATE OF transcript ON user_clips
    FOR EACH ROW
    WHEN (NEW.transcript IS NOT NULL AND NEW.transcript <> '')
    EXECUTE FUNCTION generate_transcript_embedding();

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed transcript embedding triggers:';
    RAISE NOTICE '- Changed from AFTER to BEFORE triggers (allows modifying NEW)';
    RAISE NOTICE '- Removed transcript_embedding IS NULL from WHEN clause';
    RAISE NOTICE '- Function now detects transcript changes and clears embeddings';
    RAISE NOTICE '- For user_clips: clears title/title_embedding when transcript changes';
    RAISE NOTICE '- Embeddings will now regenerate when transcript content is updated';
END;
$$;
