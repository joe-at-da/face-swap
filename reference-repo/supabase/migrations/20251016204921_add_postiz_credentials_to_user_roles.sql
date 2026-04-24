-- Add Postiz Credentials to User Roles
-- Migration to add Postiz integration fields to user_roles table

-- Add Postiz credential columns to user_roles table
ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS postiz_api_key text,
ADD COLUMN IF NOT EXISTS postiz_email text,
ADD COLUMN IF NOT EXISTS postiz_password text;

-- Add comments to document the new columns
COMMENT ON COLUMN public.user_roles.postiz_api_key IS 'Postiz API key for social media scheduling integration';
COMMENT ON COLUMN public.user_roles.postiz_email IS 'Postiz account email for authentication';
COMMENT ON COLUMN public.user_roles.postiz_password IS 'Postiz account password for authentication';

-- Log migration completion
DO $$
BEGIN
  RAISE NOTICE 'Added Postiz credential columns to user_roles table:';
  RAISE NOTICE '- postiz_api_key: text (nullable)';
  RAISE NOTICE '- postiz_email: text (nullable)';
  RAISE NOTICE '- postiz_password: text (nullable)';
  RAISE NOTICE 'Existing rows will have NULL values for these fields';
END $$;
