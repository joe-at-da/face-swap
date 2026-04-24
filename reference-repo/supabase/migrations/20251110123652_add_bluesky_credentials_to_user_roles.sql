-- Add Bluesky Credentials to User Roles
-- Migration to add Bluesky integration fields to user_roles table

-- Add Bluesky credential columns to user_roles table
ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS bluesky_service text,
ADD COLUMN IF NOT EXISTS bluesky_identifier text,
ADD COLUMN IF NOT EXISTS bluesky_password text;

-- Add comments to document the new columns
COMMENT ON COLUMN public.user_roles.bluesky_service IS 'Bluesky service URL (e.g., https://bsky.social)';
COMMENT ON COLUMN public.user_roles.bluesky_identifier IS 'Bluesky account identifier/handle';
COMMENT ON COLUMN public.user_roles.bluesky_password IS 'Bluesky app password for authentication';

-- Log migration completion
DO $$
BEGIN
  RAISE NOTICE 'Added Bluesky credential columns to user_roles table:';
  RAISE NOTICE '- bluesky_service: text (nullable)';
  RAISE NOTICE '- bluesky_identifier: text (nullable)';
  RAISE NOTICE '- bluesky_password: text (nullable)';
  RAISE NOTICE 'Existing rows will have NULL values for these fields';
END $$;

