-- Add global watermark support to user_clips table and create watermarks storage bucket
-- This migration moves from per-segment watermarks to global clip watermarks

-- Add global watermark fields to user_clips table
ALTER TABLE user_clips 
ADD COLUMN watermark_url TEXT,
ADD COLUMN watermark_position watermark_position DEFAULT 'bottom_right';

-- Create watermarks storage bucket (public bucket for watermark images)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
SELECT 
  'watermarks',
  'watermarks',
  true,  -- Public bucket (watermarks need to be accessible during video processing)
  10485760,  -- 10MB file size limit for watermark images
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']  -- Only allow image formats
WHERE NOT EXISTS (
  SELECT 1 FROM storage.buckets WHERE id = 'watermarks'
);

-- RLS Policies for watermarks bucket
-- Users can view all watermarks (public bucket)
CREATE POLICY "Public can view all watermarks" 
ON storage.objects FOR SELECT
USING (bucket_id = 'watermarks');

-- Only authenticated users can upload watermarks to their own folder
CREATE POLICY "Users can upload their own watermarks" 
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'watermarks'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can update their own watermarks
CREATE POLICY "Users can update their own watermarks" 
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'watermarks'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can delete their own watermarks
CREATE POLICY "Users can delete their own watermarks" 
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'watermarks'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Update the segments validation function to remove watermark requirements
-- Since watermarks are now global, segments only need start_timestamp and end_timestamp
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
    
    -- Validate each segment (only timestamps required now)
    RETURN (
        SELECT bool_and(
            segment ? 'start_timestamp' AND 
            segment ? 'end_timestamp' AND
            jsonb_typeof(segment->'start_timestamp') = 'string' AND
            jsonb_typeof(segment->'end_timestamp') = 'string'
        )
        FROM jsonb_array_elements(segments_data) AS segment
    );
END;
$$;

-- Drop and recreate the get_clip_segments function to remove watermark fields from segments
DROP FUNCTION IF EXISTS get_clip_segments(UUID);
CREATE OR REPLACE FUNCTION get_clip_segments(clip_id UUID)
RETURNS TABLE (
    start_timestamp TEXT,
    end_timestamp TEXT
)
LANGUAGE sql
STABLE
AS $$
    SELECT 
        segment->>'start_timestamp' as start_timestamp,
        segment->>'end_timestamp' as end_timestamp
    FROM user_clips,
         LATERAL jsonb_array_elements(segments) AS segment
    WHERE id = clip_id;
$$;

-- Drop and recreate function to add a segment to a clip (simplified - no watermark fields)
DROP FUNCTION IF EXISTS add_clip_segment(UUID, TEXT, TEXT, TEXT, watermark_position);
CREATE OR REPLACE FUNCTION add_clip_segment(
    clip_id UUID,
    p_start_timestamp TEXT,
    p_end_timestamp TEXT
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

    -- Build the segment object (only timestamps now)
    new_segment := jsonb_build_object(
        'start_timestamp', p_start_timestamp,
        'end_timestamp', p_end_timestamp
    );

    -- Add the segment to the array
    UPDATE user_clips
    SET segments = segments || new_segment,
        updated_at = NOW()
    WHERE id = clip_id;

    RETURN FOUND;
END;
$$;

-- Create function to update global watermark for a clip
CREATE OR REPLACE FUNCTION update_clip_watermark(
    clip_id UUID,
    p_watermark_url TEXT DEFAULT NULL,
    p_watermark_position watermark_position DEFAULT 'bottom_right'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE user_clips
    SET watermark_url = p_watermark_url,
        watermark_position = p_watermark_position,
        updated_at = NOW()
    WHERE id = clip_id;

    RETURN FOUND;
END;
$$;

-- Update permissions
GRANT EXECUTE ON FUNCTION get_clip_segments(UUID) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION add_clip_segment(UUID, TEXT, TEXT) TO service_role, authenticated;
GRANT EXECUTE ON FUNCTION update_clip_watermark(UUID, TEXT, watermark_position) TO service_role, authenticated;

-- Update comments
COMMENT ON COLUMN user_clips.segments IS 'Array of clip segments, each containing only start_timestamp and end_timestamp. Watermarks are now stored globally at the clip level.';
COMMENT ON COLUMN user_clips.watermark_url IS 'Public URL of the watermark image stored in the watermarks bucket. Applied to all segments in this clip.';
COMMENT ON COLUMN user_clips.watermark_position IS 'Position where the watermark should be displayed on the video. Applied to all segments in this clip.';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Added global watermark support:';
    RAISE NOTICE '- Added watermark_url and watermark_position columns to user_clips table';
    RAISE NOTICE '- Created watermarks storage bucket with RLS policies';
    RAISE NOTICE '- Updated validation functions to remove per-segment watermark requirements';
    RAISE NOTICE '- Segments now only contain start_timestamp and end_timestamp';
    RAISE NOTICE '- Watermarks are applied globally at the clip level';
    RAISE NOTICE '- Bucket structure: watermarks/[user-id]/[filename]';
END;
$$;