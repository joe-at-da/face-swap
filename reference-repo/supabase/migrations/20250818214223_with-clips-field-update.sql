-- Add New Fields to User Clips Table Migration
-- Migration to add thumbnail URLs and session UID fields to user_clips table
-- These fields will support enhanced clip management and social media sharing

-- Add new columns to user_clips table
ALTER TABLE user_clips 
ADD COLUMN thumbnail_url TEXT DEFAULT NULL,
ADD COLUMN vertical_thumbnail_url TEXT DEFAULT NULL,
ADD COLUMN session_uid TEXT DEFAULT NULL;

-- Create indexes for better query performance on new fields
CREATE INDEX idx_user_clips_thumbnail_url ON user_clips(thumbnail_url) WHERE thumbnail_url IS NOT NULL;
CREATE INDEX idx_user_clips_vertical_thumbnail_url ON user_clips(vertical_thumbnail_url) WHERE vertical_thumbnail_url IS NOT NULL;
CREATE INDEX idx_user_clips_session_uid ON user_clips(session_uid) WHERE session_uid IS NOT NULL;

-- Create composite index for session-based queries
CREATE INDEX idx_user_clips_user_session ON user_clips(user_id, session_uid) WHERE session_uid IS NOT NULL AND is_deleted = FALSE;

-- Add column comments for documentation
COMMENT ON COLUMN user_clips.thumbnail_url IS 
'URL to the horizontal/landscape thumbnail image for this user clip. Used for social media sharing and previews.';

COMMENT ON COLUMN user_clips.vertical_thumbnail_url IS 
'URL to the vertical/portrait thumbnail image for this user clip. Used for mobile-first social media platforms like TikTok and Instagram Stories.';

COMMENT ON COLUMN user_clips.session_uid IS 
'Unique identifier for the session this clip belongs to. Used for grouping related clips and managing clip collections.';

-- Update the webhook trigger to include new fields if they affect processing
-- Note: The existing webhook trigger only fires on start_timestamp and end_timestamp changes
-- If you need webhook calls when thumbnail fields change, you can modify the trigger here

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Added new fields to user_clips table:';
    RAISE NOTICE '- thumbnail_url: Horizontal thumbnail image URL for social media sharing';
    RAISE NOTICE '- vertical_thumbnail_url: Vertical thumbnail image URL for mobile platforms';
    RAISE NOTICE '- session_uid: Session identifier for grouping related clips';
    RAISE NOTICE '- Created appropriate indexes for performance optimization';
    RAISE NOTICE '- Added comprehensive column documentation';
END $$;
