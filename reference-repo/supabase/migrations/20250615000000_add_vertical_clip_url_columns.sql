-- Add Vertical Clip URL Columns Migration
-- Migration to add vertical_clip_url field to parliament_member_clips and user_clips tables
-- This field will store URLs for vertical (portrait orientation) versions of video clips
-- optimized for social media platforms like TikTok, Instagram Stories, YouTube Shorts, etc.

-- Add vertical_clip_url column to parliament_member_clips table
ALTER TABLE parliament_member_clips 
ADD COLUMN vertical_clip_url TEXT DEFAULT NULL;

-- Add vertical_clip_url column to user_clips table
ALTER TABLE user_clips 
ADD COLUMN vertical_clip_url TEXT DEFAULT NULL;

-- Create indexes for better query performance when filtering by vertical clip URL existence
CREATE INDEX idx_parliament_member_clips_vertical_clip_url 
ON parliament_member_clips(vertical_clip_url) 
WHERE vertical_clip_url IS NOT NULL;

CREATE INDEX idx_user_clips_vertical_clip_url 
ON user_clips(vertical_clip_url) 
WHERE vertical_clip_url IS NOT NULL;

-- Add comments to document the new columns
COMMENT ON COLUMN parliament_member_clips.vertical_clip_url IS 
'URL to the vertical (portrait orientation) version of the video clip, optimized for social media platforms like TikTok, Instagram Stories, YouTube Shorts. NULL if no vertical version exists.';

COMMENT ON COLUMN user_clips.vertical_clip_url IS 
'URL to the vertical (portrait orientation) version of the user clip, optimized for social media platforms like TikTok, Instagram Stories, YouTube Shorts. NULL if no vertical version exists.';

-- Log successful migration completion
DO $$
BEGIN
    RAISE NOTICE 'Vertical clip URL columns migration completed:';
    RAISE NOTICE '- Added vertical_clip_url column to parliament_member_clips table';
    RAISE NOTICE '- Added vertical_clip_url column to user_clips table';
    RAISE NOTICE '- Created partial indexes for better query performance';
    RAISE NOTICE '- Added comprehensive column documentation';
    RAISE NOTICE 'These columns will store URLs for portrait-oriented video clips optimized for social media platforms';
END $$; 