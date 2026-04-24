-- Change embedding queue processing schedule from every 30 seconds to every 1 minute
-- This reduces database load while maintaining good processing throughput

-- Update the cron job schedule
SELECT cron.unschedule('process-embedding-queue');
SELECT cron.schedule(
    'process-embedding-queue',
    '0 * * * * *',  -- Every minute (at 0 seconds)
    'SELECT process_embedding_queue(100, 300);'
);

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Updated embedding queue cron schedule:';
    RAISE NOTICE '- Changed from every 30 seconds to every 1 minute';
    RAISE NOTICE '- Still processes 100 messages per batch';
    RAISE NOTICE '- Reduced database load while maintaining throughput';
    RAISE NOTICE '- Max capacity: 100 messages/minute = 6000 messages/hour';
END;
$$;