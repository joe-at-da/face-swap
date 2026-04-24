-- Add Notification Settings Migration
-- Migration to add notification preference columns to user_roles table

-- Add notification settings columns to user_roles table
ALTER TABLE public.user_roles 
ADD COLUMN IF NOT EXISTS clip_processing_complete boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS weekly_performance_report boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS social_media_shares boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS system_updates boolean DEFAULT true;

-- Add comment to document the new columns
COMMENT ON COLUMN public.user_roles.clip_processing_complete IS 'User preference for clip processing completion notifications';
COMMENT ON COLUMN public.user_roles.weekly_performance_report IS 'User preference for weekly performance report notifications';
COMMENT ON COLUMN public.user_roles.social_media_shares IS 'User preference for social media share notifications';
COMMENT ON COLUMN public.user_roles.system_updates IS 'User preference for system update notifications';

-- Log migration completion
DO $$
BEGIN
  RAISE NOTICE 'Added notification settings columns to user_roles table:';
  RAISE NOTICE '- clip_processing_complete: boolean (default: true)';
  RAISE NOTICE '- weekly_performance_report: boolean (default: true)';
  RAISE NOTICE '- social_media_shares: boolean (default: false)';
  RAISE NOTICE '- system_updates: boolean (default: true)';
END $$; 