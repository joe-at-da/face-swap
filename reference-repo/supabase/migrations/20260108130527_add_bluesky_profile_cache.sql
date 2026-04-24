-- Add columns to cache Bluesky profile data
-- This avoids calling the Bluesky API on every poll (every 10 seconds)
-- Profile data is fetched once when connecting and cached here

ALTER TABLE user_roles
ADD COLUMN IF NOT EXISTS bluesky_avatar TEXT,
ADD COLUMN IF NOT EXISTS bluesky_display_name TEXT;

-- Add comment for documentation
COMMENT ON COLUMN user_roles.bluesky_avatar IS 'Cached Bluesky avatar URL, updated when connecting account';
COMMENT ON COLUMN user_roles.bluesky_display_name IS 'Cached Bluesky display name, updated when connecting account';
