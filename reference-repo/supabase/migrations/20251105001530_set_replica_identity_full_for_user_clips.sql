-- Set REPLICA IDENTITY FULL for user_clips table
-- This is required for Supabase Realtime to properly track UPDATE events
-- Without this, realtime subscriptions may not receive UPDATE payloads with full row data

ALTER TABLE user_clips REPLICA IDENTITY FULL;

-- Log successful setup
DO $$
BEGIN
    RAISE NOTICE 'Set REPLICA IDENTITY FULL on user_clips table for realtime UPDATE events';
END $$;

