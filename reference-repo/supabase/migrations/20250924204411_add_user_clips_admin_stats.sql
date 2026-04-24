-- Add comprehensive admin dashboard stats to user_clips table
-- This migration adds performance, quality, and operational metrics for admin monitoring

-- Processing Performance columns
ALTER TABLE public.user_clips ADD COLUMN processing_time_total DECIMAL(8,2);
ALTER TABLE public.user_clips ADD COLUMN processing_time_download DECIMAL(8,2);
ALTER TABLE public.user_clips ADD COLUMN processing_time_clip_creation DECIMAL(8,2);
ALTER TABLE public.user_clips ADD COLUMN processing_time_upload DECIMAL(8,2);
ALTER TABLE public.user_clips ADD COLUMN processing_time_transcript DECIMAL(8,2);

-- File Information columns
ALTER TABLE public.user_clips ADD COLUMN input_video_size_mb DECIMAL(10,2);
ALTER TABLE public.user_clips ADD COLUMN output_clip_size_mb DECIMAL(10,2);
ALTER TABLE public.user_clips ADD COLUMN output_vertical_clip_size_mb DECIMAL(10,2);
ALTER TABLE public.user_clips ADD COLUMN clip_duration_seconds DECIMAL(8,2);

-- Quality & Content Metrics columns
ALTER TABLE public.user_clips ADD COLUMN transcript_word_count INTEGER;
ALTER TABLE public.user_clips ADD COLUMN transcript_confidence_score DECIMAL(5,3);
ALTER TABLE public.user_clips ADD COLUMN num_segments_processed INTEGER;
ALTER TABLE public.user_clips ADD COLUMN video_resolution VARCHAR(20);
ALTER TABLE public.user_clips ADD COLUMN video_bitrate_kbps INTEGER;
ALTER TABLE public.user_clips ADD COLUMN audio_sample_rate INTEGER;

-- System & Resource Usage columns
ALTER TABLE public.user_clips ADD COLUMN gpu_model VARCHAR(100);
ALTER TABLE public.user_clips ADD COLUMN gpu_memory_used_gb DECIMAL(6,2);
ALTER TABLE public.user_clips ADD COLUMN worker_id VARCHAR(50);
ALTER TABLE public.user_clips ADD COLUMN processing_node VARCHAR(50);
ALTER TABLE public.user_clips ADD COLUMN peak_memory_usage_gb DECIMAL(6,2);

-- Operational Metrics columns
ALTER TABLE public.user_clips ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE public.user_clips ADD COLUMN failed_steps TEXT[];
ALTER TABLE public.user_clips ADD COLUMN warnings TEXT[];
ALTER TABLE public.user_clips ADD COLUMN cost_estimate_usd DECIMAL(8,4);
ALTER TABLE public.user_clips ADD COLUMN processing_started_at TIMESTAMPTZ;
ALTER TABLE public.user_clips ADD COLUMN processing_completed_at TIMESTAMPTZ;
ALTER TABLE public.user_clips ADD COLUMN queue_wait_time_seconds DECIMAL(8,2);

-- Add indexes for admin dashboard queries
CREATE INDEX idx_user_clips_processing_time_total ON public.user_clips(processing_time_total) WHERE processing_time_total IS NOT NULL;
CREATE INDEX idx_user_clips_cost_estimate ON public.user_clips(cost_estimate_usd) WHERE cost_estimate_usd IS NOT NULL;
CREATE INDEX idx_user_clips_retry_count ON public.user_clips(retry_count) WHERE retry_count > 0;
CREATE INDEX idx_user_clips_processing_completed_at ON public.user_clips(processing_completed_at) WHERE processing_completed_at IS NOT NULL;
CREATE INDEX idx_user_clips_worker_id ON public.user_clips(worker_id) WHERE worker_id IS NOT NULL;
CREATE INDEX idx_user_clips_processing_node ON public.user_clips(processing_node) WHERE processing_node IS NOT NULL;
CREATE INDEX idx_user_clips_failed_steps ON public.user_clips USING GIN(failed_steps) WHERE failed_steps IS NOT NULL;
CREATE INDEX idx_user_clips_warnings ON public.user_clips USING GIN(warnings) WHERE warnings IS NOT NULL;

-- Add constraints for data validation
ALTER TABLE public.user_clips ADD CONSTRAINT check_processing_times_positive
    CHECK (processing_time_total >= 0 AND processing_time_download >= 0 AND
           processing_time_clip_creation >= 0 AND processing_time_upload >= 0 AND
           processing_time_transcript >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_file_sizes_positive
    CHECK (input_video_size_mb >= 0 AND output_clip_size_mb >= 0 AND
           output_vertical_clip_size_mb >= 0 AND clip_duration_seconds >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_transcript_metrics_positive
    CHECK (transcript_word_count >= 0 AND transcript_confidence_score >= 0 AND
           transcript_confidence_score <= 1 AND num_segments_processed >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_resource_usage_positive
    CHECK (gpu_memory_used_gb >= 0 AND peak_memory_usage_gb >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_retry_count_positive
    CHECK (retry_count >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_cost_positive
    CHECK (cost_estimate_usd >= 0);

ALTER TABLE public.user_clips ADD CONSTRAINT check_queue_wait_time_positive
    CHECK (queue_wait_time_seconds >= 0);

-- Add comment describing the purpose of these stats
COMMENT ON COLUMN public.user_clips.processing_time_total IS 'Total processing time in seconds for admin dashboard performance monitoring';
COMMENT ON COLUMN public.user_clips.cost_estimate_usd IS 'Estimated processing cost in USD for admin cost analysis';
COMMENT ON COLUMN public.user_clips.retry_count IS 'Number of processing retries for admin error monitoring';
COMMENT ON COLUMN public.user_clips.failed_steps IS 'Array of failed processing steps for admin debugging';
COMMENT ON COLUMN public.user_clips.warnings IS 'Array of processing warnings for admin quality monitoring';