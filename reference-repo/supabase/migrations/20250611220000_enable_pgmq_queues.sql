-- Enable PGMQ Queues Migration
-- Migration to enable the pgmq extension and create queues for video processing workflow:
-- 1. video_processing: Queue for video upload and processing jobs
-- 2. clip_creation: Queue for extracting clips from processed videos
-- 
-- This migration follows Supabase best practices with proper RLS policies

-- Create enum for queue job status
CREATE TYPE public.queue_job_status AS ENUM (
    'pending',
    'running', 
    'completed',
    'failed'
);

-- Enable the pgmq extension for message queues
CREATE EXTENSION IF NOT EXISTS pgmq;

-- Grant usage on the pgmq schema to necessary roles
GRANT USAGE ON SCHEMA pgmq TO postgres, supabase_auth_admin, service_role;

-- Create video_processing queue for handling video upload and processing jobs
SELECT pgmq.create('video_processing');

-- Create clip_creation queue for handling clip extraction jobs
SELECT pgmq.create('clip_creation');

-- Create a view to list all queues for monitoring purposes
CREATE OR REPLACE VIEW public.queue_info AS
SELECT 
    queue_name,
    created_at,
    is_partitioned,
    is_unlogged
FROM pgmq.list_queues()
ORDER BY created_at DESC;

-- Grant permissions on the queue_info view
GRANT SELECT ON public.queue_info TO service_role;

-- Enable Row Level Security (RLS) on PGMQ tables
-- PGMQ creates tables for each queue, we need to enable RLS on them

-- Enable RLS on the video_processing queue table
ALTER TABLE pgmq.q_video_processing ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgmq.a_video_processing ENABLE ROW LEVEL SECURITY;

-- Enable RLS on the clip_creation queue table  
ALTER TABLE pgmq.q_clip_creation ENABLE ROW LEVEL SECURITY;
ALTER TABLE pgmq.a_clip_creation ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for video_processing queue (service_role only)
CREATE POLICY "service_role_access_video_processing_queue" ON pgmq.q_video_processing
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_access_video_processing_archive" ON pgmq.a_video_processing
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Create RLS policies for clip_creation queue (service_role only)
CREATE POLICY "service_role_access_clip_creation_queue" ON pgmq.q_clip_creation
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_access_clip_creation_archive" ON pgmq.a_clip_creation
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Revoke direct access to pgmq functions from authenticated users
-- They should use our wrapper functions instead
REVOKE ALL ON SCHEMA pgmq FROM authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA pgmq FROM authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pgmq FROM authenticated;

-- Service role keeps full access for background jobs
GRANT ALL ON SCHEMA pgmq TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA pgmq TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA pgmq TO service_role;

-- Add comments to document the queues and enum usage
COMMENT ON TYPE public.queue_job_status IS 
'Enum for tracking queue job status in message payloads. Use this in your queue message JSON.';

-- Log successful setup
DO $$
BEGIN
    RAISE NOTICE 'PGMQ queues setup completed:';
    RAISE NOTICE '- queue_job_status enum created: pending, running, completed, failed';
    RAISE NOTICE '- video_processing queue: For video upload and processing jobs';
    RAISE NOTICE '- clip_creation queue: For clip extraction and processing jobs';
    RAISE NOTICE '- Row Level Security (RLS) enabled on all queue tables';
    RAISE NOTICE '- Service role only access policies created for all queues';
    RAISE NOTICE '- Basic PGMQ setup completed - create functions and triggers manually as needed';
END $$; 