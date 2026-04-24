-- Add processing metrics columns to parliament_events table
-- These columns track detailed processing performance and operational metrics

-- Processing Performance columns (using idempotent approach)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'total_processing_time_seconds') THEN
        ALTER TABLE public.parliament_events ADD COLUMN total_processing_time_seconds DECIMAL(8,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'gpu_processing_time_seconds') THEN
        ALTER TABLE public.parliament_events ADD COLUMN gpu_processing_time_seconds DECIMAL(8,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'processing_started_at') THEN
        ALTER TABLE public.parliament_events ADD COLUMN processing_started_at TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'processing_completed_at') THEN
        ALTER TABLE public.parliament_events ADD COLUMN processing_completed_at TIMESTAMPTZ;
    END IF;
END $$;

-- File Information columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'video_file_size_mb') THEN
        ALTER TABLE public.parliament_events ADD COLUMN video_file_size_mb DECIMAL(10,2);
    END IF;
END $$;

-- Quality Metrics columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'mp_identification_accuracy_percent') THEN
        ALTER TABLE public.parliament_events ADD COLUMN mp_identification_accuracy_percent DECIMAL(5,2);
    END IF;
END $$;

-- Operational Metrics columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'parliament_events' AND column_name = 'retries_attempted') THEN
        ALTER TABLE public.parliament_events ADD COLUMN retries_attempted INTEGER DEFAULT 0;
    END IF;
END $$;

-- Add indexes for performance monitoring queries (idempotent)
CREATE INDEX IF NOT EXISTS idx_parliament_events_total_processing_time ON public.parliament_events(total_processing_time_seconds) WHERE total_processing_time_seconds IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_parliament_events_processing_completed_at ON public.parliament_events(processing_completed_at) WHERE processing_completed_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_parliament_events_retries ON public.parliament_events(retries_attempted) WHERE retries_attempted > 0;

-- Add constraints for data validation (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_parliament_processing_times_positive') THEN
        ALTER TABLE public.parliament_events ADD CONSTRAINT check_parliament_processing_times_positive
            CHECK (total_processing_time_seconds >= 0 AND gpu_processing_time_seconds >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_parliament_file_sizes_positive') THEN
        ALTER TABLE public.parliament_events ADD CONSTRAINT check_parliament_file_sizes_positive
            CHECK (video_file_size_mb >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_parliament_accuracy_valid') THEN
        ALTER TABLE public.parliament_events ADD CONSTRAINT check_parliament_accuracy_valid
            CHECK (mp_identification_accuracy_percent >= 0 AND mp_identification_accuracy_percent <= 100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_parliament_retries_positive') THEN
        ALTER TABLE public.parliament_events ADD CONSTRAINT check_parliament_retries_positive
            CHECK (retries_attempted >= 0);
    END IF;
END $$;

-- Add comments describing the purpose of these metrics
COMMENT ON COLUMN public.parliament_events.total_processing_time_seconds IS 'Total processing time in seconds for performance monitoring';
COMMENT ON COLUMN public.parliament_events.video_file_size_mb IS 'Size of parliament video file in megabytes';
COMMENT ON COLUMN public.parliament_events.mp_identification_accuracy_percent IS 'Accuracy percentage of MP identification process';
COMMENT ON COLUMN public.parliament_events.retries_attempted IS 'Number of processing retries attempted';