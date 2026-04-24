-- Expose PGMQ Queues via PostgREST Migration
-- Migration to grant service role full access to PGMQ queues

-- Ensure service role has full access to PGMQ schema and all operations
GRANT ALL PRIVILEGES ON SCHEMA pgmq TO service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA pgmq TO service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA pgmq TO service_role;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA pgmq TO service_role;

-- Grant service role access to queue tables directly
GRANT ALL ON pgmq.q_video_processing TO service_role;
GRANT ALL ON pgmq.a_video_processing TO service_role;
GRANT ALL ON pgmq.q_clip_creation TO service_role;
GRANT ALL ON pgmq.a_clip_creation TO service_role;

-- Grant access to existing queue info view
GRANT SELECT ON public.queue_info TO service_role;

-- Log successful permissions grant
DO $$
BEGIN
    RAISE NOTICE 'Service role granted full access to PGMQ queues:';
    RAISE NOTICE '- Full privileges on pgmq schema';
    RAISE NOTICE '- Access to all queue tables and functions';
    RAISE NOTICE '- Access to queue monitoring views';
END $$; 