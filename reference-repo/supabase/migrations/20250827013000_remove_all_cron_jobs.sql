-- Remove all cron jobs and migrate to Coolify Scheduled Tasks
-- This removes pg_cron dependency and moves scheduling to application layer

-- Remove all existing cron jobs
SELECT cron.unschedule('parliament-daily-sync');
SELECT cron.unschedule('parliament-event-daily-sync'); 
SELECT cron.unschedule('process-embedding-queue');

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Removed all cron jobs:';
    RAISE NOTICE '- parliament-daily-sync: Moved to Coolify scheduled task';
    RAISE NOTICE '- parliament-event-daily-sync: Moved to Coolify scheduled task';
    RAISE NOTICE '- process-embedding-queue: Moved to Coolify scheduled task';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Deploy corresponding Next.js API routes';
    RAISE NOTICE '2. Configure Coolify scheduled tasks to call these API routes';
    RAISE NOTICE '3. Test each endpoint individually';
END;
$$;