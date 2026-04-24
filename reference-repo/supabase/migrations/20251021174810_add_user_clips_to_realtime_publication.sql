-- Add user_clips table to Supabase Realtime publication
-- This enables client-side realtime subscriptions to receive UPDATE, INSERT, DELETE events
-- This migration is idempotent: it checks if the table is already in the publication before adding it

DO $$
BEGIN
    -- Check if user_clips is already in the supabase_realtime publication
    IF NOT EXISTS (
        SELECT 1
        FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
        AND schemaname = 'public'
        AND tablename = 'user_clips'
    ) THEN
        -- Add the table to the publication
        ALTER PUBLICATION supabase_realtime ADD TABLE user_clips;
        RAISE NOTICE 'Added user_clips table to supabase_realtime publication';
        RAISE NOTICE 'Client-side realtime subscriptions will now receive database change events for user_clips';
    ELSE
        RAISE NOTICE 'user_clips table is already in supabase_realtime publication, skipping';
    END IF;
END $$;
