-- Add New Fields to Parliament Member Clips Table Migration
-- Migration to add thumbnail URLs and session UID fields to parliament_member_clips table
-- These fields will support enhanced clip management and social media sharing for parliament member clips

-- Add new columns to parliament_member_clips table
ALTER TABLE parliament_member_clips 
ADD COLUMN thumbnail_url TEXT DEFAULT NULL,
ADD COLUMN vertical_thumbnail_url TEXT DEFAULT NULL,
ADD COLUMN session_uid TEXT DEFAULT NULL;

ALTER TABLE user_clips 
ADD COLUMN transcript TEXT DEFAULT NULL,
ADD COLUMN transcript_embedding vector(1536) DEFAULT NULL;

-- Create indexes for better query performance on new fields
CREATE INDEX idx_parliament_member_clips_thumbnail_url ON parliament_member_clips(thumbnail_url) WHERE thumbnail_url IS NOT NULL;
CREATE INDEX idx_parliament_member_clips_vertical_thumbnail_url ON parliament_member_clips(vertical_thumbnail_url) WHERE vertical_thumbnail_url IS NOT NULL;
CREATE INDEX idx_parliament_member_clips_session_uid ON parliament_member_clips(session_uid) WHERE session_uid IS NOT NULL;

-- Create composite index for session-based queries
CREATE INDEX idx_parliament_member_clips_member_session ON parliament_member_clips(member_id, session_uid) WHERE session_uid IS NOT NULL AND is_deleted = FALSE;

-- Create composite index for session and date queries
CREATE INDEX idx_parliament_member_clips_session_uid_date ON parliament_member_clips(session_uid, session_date) WHERE session_uid IS NOT NULL AND is_deleted = FALSE;

-- Add column comments for documentation
COMMENT ON COLUMN parliament_member_clips.thumbnail_url IS 
'URL to the horizontal/landscape thumbnail image for this parliament member clip. Used for social media sharing and previews.';

COMMENT ON COLUMN parliament_member_clips.vertical_thumbnail_url IS 
'URL to the vertical/portrait thumbnail image for this parliament member clip. Used for mobile-first social media platforms like TikTok and Instagram Stories.';

COMMENT ON COLUMN parliament_member_clips.session_uid IS 
'Unique identifier for the parliamentary session this clip belongs to. Used for grouping related clips and managing clip collections.';

-- Update the updated_at trigger to include new fields if they affect processing
-- Note: The existing updated_at trigger will automatically update the updated_at column when any field changes

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Added new fields to parliament_member_clips table:';
    RAISE NOTICE '- thumbnail_url: Horizontal thumbnail image URL for social media sharing';
    RAISE NOTICE '- vertical_thumbnail_url: Vertical thumbnail image URL for mobile platforms';
    RAISE NOTICE '- session_uid: Session identifier for grouping related clips';
    RAISE NOTICE '- Created appropriate indexes for performance optimization';
    RAISE NOTICE '- Added comprehensive column documentation';
END $$;
