-- Fix is_valid_timestamp_format function accessibility issues during seed import
-- This migration ensures the function is properly accessible in all contexts

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS public.is_valid_timestamp_format(text);

-- Recreate function with explicit schema and security definer
CREATE OR REPLACE FUNCTION public.is_valid_timestamp_format(ts text)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Check if format matches MM:SS.mmm or MMM:SS.mmm pattern
    RETURN ts ~ '^[0-9]{2,3}:[0-5][0-9]\.[0-9]{3}$';
END;
$$;

-- Set proper ownership (postgres user owns the function)
ALTER FUNCTION public.is_valid_timestamp_format(text) OWNER TO postgres;

-- Grant execute permissions to all roles that might need it
GRANT EXECUTE ON FUNCTION public.is_valid_timestamp_format(text) TO postgres;
GRANT EXECUTE ON FUNCTION public.is_valid_timestamp_format(text) TO anon;
GRANT EXECUTE ON FUNCTION public.is_valid_timestamp_format(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_valid_timestamp_format(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.is_valid_timestamp_format(text) TO PUBLIC;

-- First drop the constraint that depends on the function
ALTER TABLE user_clips DROP CONSTRAINT IF EXISTS segments_timestamp_format_check;

-- Update validate_segments_timestamps to use fully qualified function name
DROP FUNCTION IF EXISTS public.validate_segments_timestamps(jsonb);

CREATE OR REPLACE FUNCTION public.validate_segments_timestamps(segments_data JSONB)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Empty array is valid
    IF segments_data = '[]'::jsonb THEN
        RETURN true;
    END IF;

    -- Validate timestamp format for each segment using fully qualified function name
    RETURN (
        SELECT bool_and(
            public.is_valid_timestamp_format(segment->>'start_timestamp') AND
            public.is_valid_timestamp_format(segment->>'end_timestamp')
        )
        FROM jsonb_array_elements(segments_data) AS segment
    );
END;
$$;

-- Set proper ownership
ALTER FUNCTION public.validate_segments_timestamps(jsonb) OWNER TO postgres;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.validate_segments_timestamps(jsonb) TO postgres;
GRANT EXECUTE ON FUNCTION public.validate_segments_timestamps(jsonb) TO anon;
GRANT EXECUTE ON FUNCTION public.validate_segments_timestamps(jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.validate_segments_timestamps(jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.validate_segments_timestamps(jsonb) TO PUBLIC;

-- Update add_clip_segment function to use fully qualified function name
DROP FUNCTION IF EXISTS public.add_clip_segment(UUID, TEXT, TEXT);

CREATE OR REPLACE FUNCTION public.add_clip_segment(
    clip_id UUID,
    p_start_timestamp TEXT,
    p_end_timestamp TEXT
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_segment JSONB;
BEGIN
    -- Validate timestamp formats using fully qualified function name
    IF NOT (public.is_valid_timestamp_format(p_start_timestamp) AND public.is_valid_timestamp_format(p_end_timestamp)) THEN
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

-- Set proper ownership
ALTER FUNCTION public.add_clip_segment(UUID, TEXT, TEXT) OWNER TO postgres;

-- Grant permissions
GRANT EXECUTE ON FUNCTION public.add_clip_segment(UUID, TEXT, TEXT) TO postgres;
GRANT EXECUTE ON FUNCTION public.add_clip_segment(UUID, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION public.add_clip_segment(UUID, TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.add_clip_segment(UUID, TEXT, TEXT) TO service_role;

-- Recreate the constraint to ensure it uses the updated function
ALTER TABLE user_clips
ADD CONSTRAINT segments_timestamp_format_check
CHECK (public.validate_segments_timestamps(segments));

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Fixed timestamp validation function permissions:';
    RAISE NOTICE '- Recreated is_valid_timestamp_format with SECURITY DEFINER';
    RAISE NOTICE '- Set explicit schema qualification (public.)';
    RAISE NOTICE '- Granted EXECUTE permissions to all roles including PUBLIC';
    RAISE NOTICE '- Updated dependent functions to use fully qualified names';
    RAISE NOTICE '- Recreated constraint with explicit schema reference';
    RAISE NOTICE 'This should resolve seed import errors related to function accessibility';
END;
$$;