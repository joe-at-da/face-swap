-- Fix: Increase service_role statement timeout from 8s (inherited) to 5 minutes
-- The 8s timeout was causing batch inserts of parliament_member_clips via PostgREST
-- to fail with error 57014 when triggers (especially notify_mp_identification_email
-- which makes HTTP POST per row) cause the statement to exceed the timeout
ALTER ROLE service_role SET statement_timeout = '300s';

-- Disable the per-row email notification trigger on parliament_member_clips
-- This trigger fires AFTER INSERT FOR EACH ROW and makes HTTP POST requests
-- to send individual email notifications. For batch inserts of 500+ clips,
-- this causes massive overhead and contributes to statement timeouts.
-- A Coolify cron job already handles new clip notifications hourly via
-- the /api/cron/new-clips-notification endpoint, making this trigger redundant.
ALTER TABLE public.parliament_member_clips DISABLE TRIGGER trigger_notify_mp_identification_email;
