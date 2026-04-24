-- Modify user_clips table structure to replace start/end timestamps with segments array
-- Create enum for watermark positions
CREATE TYPE watermark_position AS ENUM ('center', 'top_left', 'top_right', 'bottom_left', 'bottom_right');

-- First, drop any triggers that depend on the columns we're about to remove
DROP TRIGGER IF EXISTS user_clips_webhook_trigger ON user_clips;

-- Remove old columns and add segments column to user_clips table
ALTER TABLE user_clips 
DROP COLUMN IF EXISTS start_timestamp,
DROP COLUMN IF EXISTS end_timestamp;

-- Add segments column as JSONB array
-- Each segment will have: start_timestamp, end_timestamp, watermark_url, watermark_position
ALTER TABLE user_clips 
ADD COLUMN segments JSONB DEFAULT '[]'::jsonb;

-- Create function to validate segments structure
CREATE OR REPLACE FUNCTION validate_segments_structure(segments_data JSONB)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Check if it's an array
    IF jsonb_typeof(segments_data) != 'array' THEN
        RETURN false;
    END IF;
    
    -- Empty array is valid
    IF segments_data = '[]'::jsonb THEN
        RETURN true;
    END IF;
    
    -- Validate each segment
    RETURN (
        SELECT bool_and(
            segment ? 'start_timestamp' AND 
            segment ? 'end_timestamp' AND
            jsonb_typeof(segment->'start_timestamp') = 'string' AND
            jsonb_typeof(segment->'end_timestamp') = 'string' AND
            -- Watermark fields are optional
            (NOT segment ? 'watermark_url' OR jsonb_typeof(segment->'watermark_url') = 'string') AND
            (NOT segment ? 'watermark_position' OR segment->>'watermark_position' IN ('center', 'top_left', 'top_right', 'bottom_left', 'bottom_right'))
        )
        FROM jsonb_array_elements(segments_data) AS segment
    );
END;
$$;

-- Add constraint using the validation function
ALTER TABLE user_clips 
ADD CONSTRAINT segments_structure_check 
CHECK (validate_segments_structure(segments));

-- Create index for better performance when querying segments
CREATE INDEX IF NOT EXISTS idx_user_clips_segments_gin ON user_clips USING gin (segments);

-- Add helpful comments
COMMENT ON COLUMN user_clips.segments IS 'Array of clip segments, each containing start_timestamp, end_timestamp, and optional watermark_url and watermark_position';

-- Example of segments structure:
-- [
--   {
--     "start_timestamp": "99:42.555",
--     "end_timestamp": "99:52.123", 
--     "watermark_url": "https://example.com/watermark.png",
--     "watermark_position": "bottom_right"
--   },
--   {
--     "start_timestamp": "102:15.977",
--     "end_timestamp": "102:45.234",
--     "watermark_position": "center"
--   }
-- ]

-- Create helper function to validate timestamp format (MM:SS.mmm)
CREATE OR REPLACE FUNCTION is_valid_timestamp_format(ts text)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Check if format matches MM:SS.mmm or MMM:SS.mmm pattern
    RETURN ts ~ '^[0-9]{2,3}:[0-5][0-9]\.[0-9]{3}$';
END;
$$;

-- Create function to validate segments timestamp format
CREATE OR REPLACE FUNCTION validate_segments_timestamps(segments_data JSONB)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Empty array is valid
    IF segments_data = '[]'::jsonb THEN
        RETURN true;
    END IF;
    
    -- Validate timestamp format for each segment
    RETURN (
        SELECT bool_and(
            is_valid_timestamp_format(segment->>'start_timestamp') AND
            is_valid_timestamp_format(segment->>'end_timestamp')
        )
        FROM jsonb_array_elements(segments_data) AS segment
    );
END;
$$;

-- Add constraint to validate timestamp format
ALTER TABLE user_clips 
ADD CONSTRAINT segments_timestamp_format_check 
CHECK (validate_segments_timestamps(segments));

-- Create function to get all segments for a clip
CREATE OR REPLACE FUNCTION get_clip_segments(clip_id UUID)
RETURNS TABLE (
    start_timestamp TEXT,
    end_timestamp TEXT,
    watermark_url TEXT,
    watermark_position watermark_position
)
LANGUAGE sql
STABLE
AS $$
    SELECT 
        segment->>'start_timestamp' as start_timestamp,
        segment->>'end_timestamp' as end_timestamp,
        segment->>'watermark_url' as watermark_url,
        (segment->>'watermark_position')::watermark_position as watermark_position
    FROM user_clips,
         LATERAL jsonb_array_elements(segments) AS segment
    WHERE id = clip_id;
$$;

-- Create function to add a segment to a clip
CREATE OR REPLACE FUNCTION add_clip_segment(
    clip_id UUID,
    p_start_timestamp TEXT,
    p_end_timestamp TEXT,
    p_watermark_url TEXT DEFAULT NULL,
    p_watermark_position watermark_position DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    new_segment JSONB;
BEGIN
    -- Validate timestamp formats
    IF NOT (is_valid_timestamp_format(p_start_timestamp) AND is_valid_timestamp_format(p_end_timestamp)) THEN
        RAISE EXCEPTION 'Invalid timestamp format. Expected format: MM:SS.mmm or MMM:SS.mmm';
    END IF;

    -- Build the segment object
    new_segment := jsonb_build_object(
        'start_timestamp', p_start_timestamp,
        'end_timestamp', p_end_timestamp
    );

    -- Add optional watermark fields
    IF p_watermark_url IS NOT NULL THEN
        new_segment := new_segment || jsonb_build_object('watermark_url', p_watermark_url);
    END IF;

    IF p_watermark_position IS NOT NULL THEN
        new_segment := new_segment || jsonb_build_object('watermark_position', p_watermark_position::text);
    END IF;

    -- Add the segment to the array
    UPDATE user_clips
    SET segments = segments || new_segment,
        updated_at = NOW()
    WHERE id = clip_id;

    RETURN FOUND;
END;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION get_clip_segments(UUID) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION add_clip_segment(UUID, TEXT, TEXT, TEXT, watermark_position) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION is_valid_timestamp_format(TEXT) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION validate_segments_structure(JSONB) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION validate_segments_timestamps(JSONB) TO service_role, authenticated;

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Modified user_clips table structure:';
    RAISE NOTICE '- Removed start_timestamp and end_timestamp columns';
    RAISE NOTICE '- Added segments JSONB array column with validation constraints';
    RAISE NOTICE '- Created watermark_position enum with values: center, top_left, top_right, bottom_left, bottom_right';
    RAISE NOTICE '- Added helper functions: get_clip_segments(), add_clip_segment(), is_valid_timestamp_format()';
    RAISE NOTICE '- Added GIN index on segments column for performance';
    RAISE NOTICE '- Segments format: [{"start_timestamp": "99:42.555", "end_timestamp": "99:52.123", "watermark_url": "...", "watermark_position": "bottom_right"}]';
END;
$$;