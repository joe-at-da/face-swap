-- Update Notification Settings Defaults Migration
-- Migration to ensure proper default values for notification settings

-- First, ensure the column defaults are set correctly
ALTER TABLE public.user_roles 
ALTER COLUMN clip_processing_complete SET DEFAULT true,
ALTER COLUMN weekly_performance_report SET DEFAULT true,
ALTER COLUMN social_media_shares SET DEFAULT false,
ALTER COLUMN system_updates SET DEFAULT true;

-- Update any existing rows that have NULL values to use the defaults
UPDATE public.user_roles 
SET 
  clip_processing_complete = COALESCE(clip_processing_complete, true),
  weekly_performance_report = COALESCE(weekly_performance_report, true),
  social_media_shares = COALESCE(social_media_shares, false),
  system_updates = COALESCE(system_updates, true)
WHERE 
  clip_processing_complete IS NULL 
  OR weekly_performance_report IS NULL 
  OR social_media_shares IS NULL 
  OR system_updates IS NULL;

-- Add NOT NULL constraints since we now have proper defaults
ALTER TABLE public.user_roles 
ALTER COLUMN clip_processing_complete SET NOT NULL,
ALTER COLUMN weekly_performance_report SET NOT NULL,
ALTER COLUMN social_media_shares SET NOT NULL,
ALTER COLUMN system_updates SET NOT NULL;

-- Log migration completion
DO $$
DECLARE
  updated_rows integer;
BEGIN
  GET DIAGNOSTICS updated_rows = ROW_COUNT;
  RAISE NOTICE 'Updated notification settings defaults:';
  RAISE NOTICE '- clip_processing_complete: default TRUE';
  RAISE NOTICE '- weekly_performance_report: default TRUE';
  RAISE NOTICE '- social_media_shares: default FALSE';
  RAISE NOTICE '- system_updates: default TRUE';
  RAISE NOTICE 'Updated % existing rows with NULL values', updated_rows;
END $$; 